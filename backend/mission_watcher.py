"""
Mission Watcher — Auto-dispatch engine for sub-missions and dependencies.

Background task that polls for missions marked auto_dispatch=1 whose
dependencies are satisfied, then dispatches them to available agent slots.

This is the core coordination layer for Phase 3 multi-agent teams:
- Agents create sub-missions via MCP tools → watcher auto-dispatches them
- Missions with depends_on wait until all dependencies complete
- Respects MAX_CONCURRENT_AGENTS concurrency limit
- Emits mission_events for observability

Dispatch is gated by night_window: overnight the backlog drains, at dawn agents
are paused (worktree preserved) and resumed the following night from the same
conversation. Manual dispatch via the API is never gated.
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone

import db
import night_window
import usage_budget

log = logging.getLogger("devfleet.mission_watcher")

_watcher_task: asyncio.Task | None = None
POLL_INTERVAL = int(os.environ.get("DEVFLEET_WATCHER_INTERVAL", "5"))
MAX_CONCURRENT_AGENTS = int(os.environ.get("DEVFLEET_MAX_AGENTS", "3"))

# session_id → mission_id for agents this watcher started tonight. Only these
# get paused when the window closes; a human's manual daytime dispatch is left
# alone.
_night_sessions: dict[str, str] = {}
_last_gate_reason = ""
_last_budget_reason = ""


async def _find_eligible_missions(limit: int) -> list[dict]:
    """Find auto_dispatch missions whose dependencies are all completed.

    Ordered round-robin across projects so one project's long backlog cannot
    starve the others all night: every project's top mission comes first, then
    every project's second, and so on. Within a project it is priority first,
    then oldest.
    """
    conn = await db.get_db()
    try:
        # SQLite json_each lets us check each dependency ID is completed
        rows = await conn.execute_fetchall(
            """SELECT * FROM (
                 SELECT m.*, p.path AS project_path, p.name AS project_name,
                        ROW_NUMBER() OVER (
                          PARTITION BY m.project_id
                          ORDER BY m.priority DESC, m.created_at ASC
                        ) AS project_rank
                 FROM missions m
                 JOIN projects p ON p.id = m.project_id
                 LEFT JOIN team_members t
                   ON t.id = COALESCE(NULLIF(m.assignee, ''), NULLIF(p.owner, ''))
                 WHERE m.auto_dispatch = 1
                   AND m.status = 'draft'
                   -- on_hold / completed / archived projects don't drain.
                   -- COALESCE so a legacy row with no state still counts as active.
                   AND COALESCE(NULLIF(p.state, ''), 'active') = 'active'
                   -- A member's missions WAIT while their tokens are unverified,
                   -- rather than dispatching and failing the whole backlog overnight.
                   AND (COALESCE(NULLIF(m.assignee, ''), NULLIF(p.owner, '')) IS NULL
                        OR (t.github_verified_at IS NOT NULL
                            AND t.claude_verified_at IS NOT NULL))
                   AND NOT EXISTS (
                     SELECT 1 FROM json_each(m.depends_on) dep
                     WHERE dep.value NOT IN (
                       SELECT id FROM missions WHERE status = 'completed'
                     )
                   )
               )
               ORDER BY project_rank ASC, priority DESC, created_at ASC
               LIMIT ?""",
            (limit,),
        )
        return [dict(r) for r in rows]
    finally:
        await conn.close()


async def _emit_event(mission_id: str, event_type: str, source_mission_id: str | None = None, data: dict | None = None):
    """Record a mission event for observability."""
    conn = await db.get_db()
    try:
        await conn.execute(
            "INSERT INTO mission_events (mission_id, event_type, source_mission_id, data) VALUES (?, ?, ?, ?)",
            (mission_id, event_type, source_mission_id, json.dumps(data or {})),
        )
        await conn.commit()
    except Exception as e:
        log.warning("Failed to emit event %s for %s: %s", event_type, mission_id, e)
    finally:
        await conn.close()


async def _dispatch_eligible(mission: dict) -> str:
    """Dispatch a single eligible mission. Returns the session id.

    A mission carrying resume_session_id was paused by a previous night's hard
    stop — resume that session instead of starting over, so its worktree and
    conversation continue where they stopped.
    """
    # Import here to avoid circular imports
    from sdk_engine import dispatch_mission, resume_mission, running_tasks
    from prompt_template import build_prompt

    mission_id = mission["id"]
    resume_sid = mission.get("resume_session_id") or ""
    if resume_sid:
        return await _resume_paused(mission, resume_sid, resume_mission, running_tasks)

    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    # Get last report for context (from parent or previous runs)
    conn = await db.get_db()
    try:
        # Check for report from parent mission first
        parent_id = mission.get("parent_mission_id")
        if parent_id:
            rows = await conn.execute_fetchall(
                "SELECT * FROM reports WHERE mission_id=? ORDER BY created_at DESC LIMIT 1",
                (parent_id,),
            )
        else:
            rows = await conn.execute_fetchall(
                "SELECT * FROM reports WHERE mission_id=? ORDER BY created_at DESC LIMIT 1",
                (mission_id,),
            )
        last_report = dict(rows[0]) if rows else None

        # Create session
        model = mission.get("model") or "claude-opus-4-6"
        await conn.execute(
            "INSERT INTO agent_sessions (id, mission_id, model) VALUES (?, ?, ?)",
            (session_id, mission_id, model),
        )
        await conn.execute(
            "UPDATE missions SET status='running', updated_at=? WHERE id=?",
            (now, mission_id),
        )
        await conn.commit()
    finally:
        await conn.close()

    await _emit_event(mission_id, "auto_dispatched", data={"session_id": session_id})

    log.info("Auto-dispatching mission '%s' (session %s)", mission["title"], session_id)

    task = asyncio.create_task(dispatch_mission(session_id, mission, last_report))
    running_tasks[session_id] = task
    return session_id


async def _resume_paused(mission: dict, session_id: str, resume_mission, running_tasks) -> str:
    """Continue a session that a previous night's hard stop paused."""
    now = datetime.now(timezone.utc).isoformat()
    conn = await db.get_db()
    try:
        rows = await conn.execute_fetchall(
            "SELECT claude_session_id FROM agent_sessions WHERE id=?", (session_id,),
        )
        claude_session_id = dict(rows[0])["claude_session_id"] if rows else ""
        await conn.execute(
            "UPDATE agent_sessions SET status='running', ended_at=NULL WHERE id=?",
            (session_id,),
        )
        await conn.execute(
            "UPDATE missions SET status='running', resume_session_id=NULL, updated_at=? WHERE id=?",
            (now, mission["id"]),
        )
        await conn.commit()
    finally:
        await conn.close()

    await _emit_event(mission["id"], "night_resumed", data={"session_id": session_id})
    log.info("Resuming paused mission '%s' (session %s)", mission["title"], session_id)

    task = asyncio.create_task(resume_mission(session_id, mission, claude_session_id))
    running_tasks[session_id] = task
    return session_id


async def _pause_night_agents():
    """Window closed — stop tonight's agents without throwing their work away.

    Uses the takeover path so the worktree survives, then hands the mission back
    to the queue tagged for resume. Next night it continues the same
    conversation instead of restarting.
    """
    from sdk_engine import takeover_session

    for session_id, mission_id in list(_night_sessions.items()):
        _night_sessions.pop(session_id, None)
        try:
            if not await takeover_session(session_id):
                continue
            conn = await db.get_db()
            try:
                await conn.execute(
                    "UPDATE agent_sessions SET status='paused', last_error=?, error_type='night_paused' WHERE id=?",
                    ("Paused at the end of the night window", session_id),
                )
                await conn.execute(
                    """UPDATE missions SET status='draft', resume_session_id=?,
                           updated_at=datetime('now') WHERE id=?""",
                    (session_id, mission_id),
                )
                await conn.commit()
            finally:
                await conn.close()
            await _emit_event(mission_id, "night_paused", data={"session_id": session_id})
            log.warning("Night window closed — paused session %s for resume", session_id)
        except Exception as e:
            log.error("Failed to pause session %s: %s", session_id, e)


async def _watch_loop():
    """Main polling loop — find and dispatch eligible missions."""
    global _last_gate_reason, _last_budget_reason
    log.info("Mission watcher started (poll every %ds)", POLL_INTERVAL)

    while True:
        try:
            # Import here to get current state
            from sdk_engine import running_tasks

            gate = night_window.state()
            if gate["reason"] != _last_gate_reason:
                log.info("Night window: %s", gate["reason"])
                _last_gate_reason = gate["reason"]

            if gate["hard_stop"]:
                await _pause_night_agents()
            elif gate["dispatch_open"]:
                # Clock says go; spend still has to agree. Checked here rather
                # than inside night_window so the time gate stays pure/sync.
                budget = await usage_budget.state(gate.get("session_window_start"),
                                                 weekend=gate.get("weekend", False))
                if not budget["dispatch_open"]:
                    if budget["reason"] != _last_budget_reason:
                        log.warning("Holding dispatch — %s", budget["reason"])
                        _last_budget_reason = budget["reason"]
                    await asyncio.sleep(POLL_INTERVAL)
                    continue
                _last_budget_reason = ""

                running = sum(1 for t in running_tasks.values() if not t.done())
                slots = MAX_CONCURRENT_AGENTS - running

                if slots > 0:
                    eligible = await _find_eligible_missions(limit=slots)
                    for mission in eligible:
                        try:
                            sid = await _dispatch_eligible(mission)
                            _night_sessions[sid] = mission["id"]
                        except Exception as e:
                            log.error("Failed to auto-dispatch mission %s: %s", mission["id"], e)
                            await _emit_event(mission["id"], "dispatch_failed", data={"error": str(e)})

        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.error("Mission watcher error: %s", e)

        await asyncio.sleep(POLL_INTERVAL)


async def start_watcher():
    """Start the mission watcher background task."""
    global _watcher_task
    if _watcher_task and not _watcher_task.done():
        return
    _watcher_task = asyncio.create_task(_watch_loop())
    log.info("Mission watcher started")


async def stop_watcher():
    """Stop the mission watcher."""
    global _watcher_task
    if _watcher_task and not _watcher_task.done():
        _watcher_task.cancel()
        try:
            await _watcher_task
        except asyncio.CancelledError:
            pass
    _watcher_task = None
    log.info("Mission watcher stopped")


def get_watcher_status() -> dict:
    """Get the watcher status."""
    return {
        "active": _watcher_task is not None and not _watcher_task.done(),
        "poll_interval": POLL_INTERVAL,
        "night_sessions": len(_night_sessions),
        "night_window": night_window.state(),
    }
