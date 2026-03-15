"""
Auto-Loop Orchestrator

Continuously checks if the last task is done, uses Claude to decide what to
build next based on the defined goal + last session artifacts, and dispatches
the next mission automatically.

Phase 3 upgrade: supports parallel task dispatch. The planner can return
either a single task or multiple tasks to run in parallel.

Flow:
  1. User defines a goal for a project (e.g., "Build complete auth system with JWT")
  2. Auto-loop starts: Claude analyzes codebase + goal + last report(s)
  3. Claude generates the next mission(s) — single or parallel
  4. Mission(s) are auto-dispatched to coding agents
  5. On completion, loop gathers all reports → decides next step → repeat
  6. Stops when Claude says "GOAL_COMPLETE" or user stops it
"""

import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone

import db
from prompt_template import build_prompt

# Use SDK engine if available, fall back to CLI dispatcher
try:
    from sdk_engine import dispatch_mission, running_tasks
except ImportError:
    from dispatcher import dispatch_mission, running_tasks

log = logging.getLogger("devfleet.autoloop")

MAX_CONCURRENT_AGENTS = int(os.environ.get("DEVFLEET_MAX_AGENTS", "3"))

# Active auto-loops: project_id -> task
_active_loops: dict[str, asyncio.Task] = {}

PLANNER_PROMPT = """You are a DevFleet planning agent. Your job is to analyze the current state of a project and decide the NEXT best coding task(s) to accomplish a defined goal.

## Goal
{goal}

## Project Path
{project_path}

## Last Session Report(s)
{last_report}

## Currently Running Agents
{running_info}

## Instructions
Based on the goal and what has been done so far, decide the next coding task(s).

If the goal is fully achieved, respond with exactly: GOAL_COMPLETE

For a SINGLE task, respond in this EXACT JSON format (no markdown, no code fences):
{{
  "title": "Short task title",
  "detailed_prompt": "Full detailed implementation prompt for the coding agent.",
  "acceptance_criteria": "Bullet list of what defines done for this task",
  "priority": 3
}}

For PARALLEL tasks (multiple tasks that can run simultaneously), respond with:
{{
  "parallel": true,
  "tasks": [
    {{
      "title": "Task 1 title",
      "detailed_prompt": "Task 1 prompt...",
      "acceptance_criteria": "...",
      "priority": 3
    }},
    {{
      "title": "Task 2 title",
      "detailed_prompt": "Task 2 prompt...",
      "acceptance_criteria": "...",
      "priority": 3
    }}
  ]
}}

Rules:
- Each task should be completable in a single agent session (30-60 min of work)
- Build incrementally — don't try to do everything at once
- Reference specific files and functions from the last report
- If the last session had errors, the next task should fix those first
- If tests are missing, prioritize adding them before new features
- Only use parallel tasks when they are truly independent (different files/features)
- Max {max_parallel} parallel tasks based on available agent slots
"""


async def _run_planner(project: dict, goal: str, last_reports: list[dict], running_info: str, max_parallel: int) -> list[dict] | None:
    """Use Claude to decide the next task(s). Returns None for GOAL_COMPLETE, or list of tasks."""
    if not last_reports:
        report_text = "No previous sessions — this is the first task."
    else:
        parts = []
        for i, r in enumerate(last_reports, 1):
            parts.append(f"### Report {i}\nWhat's Done: {r.get('what_done', 'N/A')}\n"
                         f"What's Open: {r.get('what_open', 'N/A')}\n"
                         f"What's Tested: {r.get('what_tested', 'N/A')}\n"
                         f"What's Not Tested: {r.get('what_untested', 'N/A')}\n"
                         f"Next Steps: {r.get('next_steps', 'N/A')}\n"
                         f"Errors: {r.get('errors_encountered', 'N/A')}")
        report_text = "\n\n".join(parts)

    prompt = PLANNER_PROMPT.format(
        goal=goal,
        project_path=project["path"],
        last_report=report_text,
        running_info=running_info or "No other agents currently running.",
        max_parallel=max_parallel,
    )

    output = await _call_planner(prompt, project["path"])

    if "GOAL_COMPLETE" in output:
        return None

    # Parse JSON from output — handle potential markdown fences
    text = output
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        log.error("Planner returned unparseable output: %s", output[:500])
        return None

    # Normalize to a list of tasks
    if parsed.get("parallel") and isinstance(parsed.get("tasks"), list):
        return parsed["tasks"][:max_parallel]
    else:
        return [parsed]


async def _call_planner(prompt: str, cwd: str) -> str:
    """Call the planner using SDK if available, fall back to CLI subprocess."""
    try:
        from claude_code_sdk import query as sdk_query, ClaudeCodeOptions
        from claude_code_sdk.types import TextBlock

        options = ClaudeCodeOptions(
            model="claude-sonnet-4-6",
            permission_mode="bypassPermissions",
            max_turns=1,
            cwd=cwd,
        )

        output_parts = []
        async for message in sdk_query(prompt=prompt, options=options):
            if message is None:
                continue
            if hasattr(message, "content"):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        output_parts.append(block.text)
            elif hasattr(message, "result") and message.result:
                output_parts.append(message.result)

        return "\n".join(output_parts).strip()

    except ImportError:
        # Fall back to CLI subprocess
        process = await asyncio.create_subprocess_exec(
            "claude",
            "--print",
            "--dangerously-skip-permissions",
            "--model", "claude-sonnet-4-6",
            "-p", prompt,
            cwd=cwd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env={**os.environ},
        )
        stdout, stderr = await process.communicate()
        return stdout.decode("utf-8", errors="replace").strip()


async def _create_and_dispatch(project_id: str, task: dict, last_report: dict | None) -> str:
    """Create a mission + session from a planner task and dispatch it. Returns session_id."""
    mid = str(uuid.uuid4())
    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    conn = await db.get_db()
    try:
        num_rows = await conn.execute_fetchall(
            "SELECT COALESCE(MAX(mission_number), 0) + 1 AS next_num FROM missions WHERE project_id=?",
            (project_id,),
        )
        next_num = num_rows[0][0] if num_rows else 1
        await conn.execute(
            """INSERT INTO missions (id, project_id, title, detailed_prompt, acceptance_criteria, priority, tags, mission_number)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (mid, project_id, task["title"], task["detailed_prompt"],
             task.get("acceptance_criteria", ""), task.get("priority", 2),
             json.dumps(["autoloop"]), next_num),
        )

        rows = await conn.execute_fetchall(
            "SELECT m.*, p.path AS project_path FROM missions m JOIN projects p ON p.id=m.project_id WHERE m.id=?",
            (mid,),
        )
        mission = dict(rows[0])

        await conn.execute(
            "INSERT INTO agent_sessions (id, mission_id) VALUES (?, ?)",
            (session_id, mid),
        )
        await conn.execute(
            "UPDATE missions SET status='running', updated_at=? WHERE id=?",
            (now, mid),
        )
        await conn.commit()
    finally:
        await conn.close()

    log.info("Auto-loop dispatching: %s (session %s)", task["title"], session_id)
    dispatch_task = asyncio.create_task(dispatch_mission(session_id, mission, last_report))
    running_tasks[session_id] = dispatch_task
    return session_id


async def auto_loop(project_id: str, goal: str):
    """Main auto-loop: plan → dispatch (parallel) → wait → repeat."""
    log.info("Auto-loop started for project %s with goal: %s", project_id, goal[:100])

    conn = await db.get_db()
    try:
        rows = await conn.execute_fetchall("SELECT * FROM projects WHERE id=?", (project_id,))
        if not rows:
            log.error("Project %s not found", project_id)
            return
        project = dict(rows[0])
    finally:
        await conn.close()

    iteration = 0
    max_iterations = 20  # Safety limit

    while iteration < max_iterations:
        iteration += 1
        log.info("Auto-loop iteration %d for project %s", iteration, project["name"])

        # Get recent reports for this project (multiple for parallel context)
        conn = await db.get_db()
        try:
            rows = await conn.execute_fetchall(
                """SELECT r.* FROM reports r
                   JOIN missions m ON m.id = r.mission_id
                   WHERE m.project_id=?
                   ORDER BY r.created_at DESC LIMIT 5""",
                (project_id,),
            )
            last_reports = [dict(r) for r in rows]
        finally:
            await conn.close()

        # Calculate available slots
        running = sum(1 for t in running_tasks.values() if not t.done())
        available_slots = max(1, MAX_CONCURRENT_AGENTS - running)

        # Get running agent info for the planner
        running_info = ""
        if running > 0:
            conn = await db.get_db()
            try:
                rrows = await conn.execute_fetchall(
                    """SELECT m.title, s.status FROM agent_sessions s
                       JOIN missions m ON m.id = s.mission_id
                       WHERE m.project_id=? AND s.status='running'""",
                    (project_id,),
                )
                if rrows:
                    running_info = "\n".join(f"- {dict(r)['title']} ({dict(r)['status']})" for r in rrows)
            finally:
                await conn.close()

        # Ask planner what to do next
        try:
            tasks = await _run_planner(project, goal, last_reports, running_info, available_slots)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            log.error("Planner failed: %s", e)
            await asyncio.sleep(10)
            continue

        if tasks is None:
            log.info("Auto-loop: GOAL COMPLETE for project %s", project["name"])
            break

        # Dispatch all tasks (parallel if multiple)
        last_report = last_reports[0] if last_reports else None
        session_ids = []
        for task in tasks:
            try:
                sid = await _create_and_dispatch(project_id, task, last_report)
                session_ids.append(sid)
            except Exception as e:
                log.error("Failed to dispatch task '%s': %s", task.get("title", "?"), e)

        if not session_ids:
            log.error("Auto-loop: no tasks dispatched, retrying...")
            await asyncio.sleep(10)
            continue

        # Wait for ALL dispatched tasks to complete
        log.info("Auto-loop waiting for %d task(s) to complete", len(session_ids))
        while True:
            all_done = all(
                sid not in running_tasks or running_tasks[sid].done()
                for sid in session_ids
            )
            if all_done:
                break
            await asyncio.sleep(5)

        # Brief pause between iterations
        await asyncio.sleep(5)

    log.info("Auto-loop finished for project %s after %d iterations", project["name"], iteration)


def start_auto_loop(project_id: str, goal: str) -> bool:
    """Start an auto-loop for a project. Returns False if already running."""
    if project_id in _active_loops and not _active_loops[project_id].done():
        return False
    task = asyncio.create_task(auto_loop(project_id, goal))
    _active_loops[project_id] = task
    return True


def stop_auto_loop(project_id: str) -> bool:
    """Stop a running auto-loop."""
    task = _active_loops.get(project_id)
    if not task or task.done():
        return False
    task.cancel()
    return True


def get_auto_loop_status(project_id: str) -> dict:
    """Get the status of an auto-loop."""
    task = _active_loops.get(project_id)
    if not task:
        return {"active": False}
    return {"active": not task.done()}
