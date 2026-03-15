"""
Remote Control Manager

Spawns `claude remote-control` sessions so users can take over
running agent missions from their phone or browser via claude.ai/code.

Each remote-control session:
  - Writes mission context into the project's CLAUDE.md so the session
    picks up full mission details automatically
  - Runs in the mission's project directory
  - Parses stdout for the session URL
  - Broadcasts the URL via SSE to connected frontend clients
  - Tracks active sessions for cleanup
"""

import asyncio
import logging
import os
import re

import db

log = logging.getLogger("devfleet.remote_control")

# Active remote-control sessions: session_id -> RemoteSession
_remote_sessions: dict[str, "RemoteSession"] = {}

# Marker used to find and remove injected mission context from CLAUDE.md
_MISSION_MARKER_START = "\n\n<!-- DEVFLEET-REMOTE-MISSION-START -->\n"
_MISSION_MARKER_END = "\n<!-- DEVFLEET-REMOTE-MISSION-END -->\n"


class RemoteControlNotEnabled(Exception):
    """Raised when the Anthropic account doesn't have remote-control enabled."""
    pass


class WorkspaceNotTrusted(Exception):
    """Raised when the project directory hasn't been trusted via `claude` first."""
    pass


def _build_mission_context(mission: dict, agent_progress: str = "") -> str:
    """Build CLAUDE.md content block with full mission context.

    If agent_progress is provided (from a taken-over session), includes what
    the previous agent accomplished so the user can continue seamlessly.
    """
    parts = [
        _MISSION_MARKER_START,
        "# ACTIVE MISSION — Continue working immediately",
        "",
    ]

    if agent_progress:
        parts += [
            "A human has taken over this mission from an autonomous agent.",
            "The agent was working on this task and made progress (see below).",
            "When the user sends their first message (even just 'go' or 'continue'),",
            "pick up where the agent left off. Do NOT redo completed work.",
        ]
    else:
        parts += [
            "A human has taken over this mission via DevFleet Remote Control.",
            "When the user sends their first message (even just 'go' or 'start'),",
            "immediately begin executing the task below. Do NOT wait for more details.",
        ]

    parts += [
        "",
        f"## Mission: {mission['title']}",
        "",
        "### Task",
        mission.get("detailed_prompt", ""),
    ]
    if mission.get("acceptance_criteria"):
        parts += ["", "### Acceptance Criteria", mission["acceptance_criteria"]]
    if mission.get("tags"):
        parts += ["", f"**Tags:** {mission['tags']}"]
    if mission.get("mission_type"):
        parts += [f"**Type:** {mission['mission_type']}"]

    if agent_progress:
        parts += [
            "",
            "## Agent Progress (before takeover)",
            "The autonomous agent was working on this and made the following progress:",
            "",
            agent_progress,
        ]

    parts.append(_MISSION_MARKER_END)
    return "\n".join(parts)


def _inject_mission_context(work_dir: str, mission: dict, agent_progress: str = "") -> None:
    """Write or append mission context to the project's CLAUDE.md."""
    claude_md_path = os.path.join(work_dir, "CLAUDE.md")
    context_block = _build_mission_context(mission, agent_progress)

    if os.path.exists(claude_md_path):
        with open(claude_md_path, "r") as f:
            existing = f.read()
        # Remove any previous mission block first
        cleaned = _strip_mission_context_from_text(existing)
        with open(claude_md_path, "w") as f:
            f.write(cleaned + context_block)
        log.info("Appended mission context to existing CLAUDE.md in %s", work_dir)
    else:
        with open(claude_md_path, "w") as f:
            f.write(context_block.lstrip("\n"))
        log.info("Created CLAUDE.md with mission context in %s", work_dir)


def _strip_mission_context_from_text(text: str) -> str:
    """Remove injected mission context block from text."""
    start_idx = text.find(_MISSION_MARKER_START)
    if start_idx == -1:
        # Also try without leading newlines (for files we created from scratch)
        marker_stripped = _MISSION_MARKER_START.lstrip("\n")
        start_idx = text.find(marker_stripped)
        if start_idx == -1:
            return text
        end_marker = _MISSION_MARKER_END
    else:
        end_marker = _MISSION_MARKER_END

    end_idx = text.find(end_marker, start_idx)
    if end_idx == -1:
        return text
    return text[:start_idx] + text[end_idx + len(end_marker):]


def _cleanup_mission_context(work_dir: str) -> None:
    """Remove injected mission context from the project's CLAUDE.md."""
    claude_md_path = os.path.join(work_dir, "CLAUDE.md")
    if not os.path.exists(claude_md_path):
        return

    with open(claude_md_path, "r") as f:
        content = f.read()

    if _MISSION_MARKER_START.strip() not in content:
        return  # Nothing to clean

    cleaned = _strip_mission_context_from_text(content).strip()
    if cleaned:
        with open(claude_md_path, "w") as f:
            f.write(cleaned + "\n")
        log.info("Cleaned mission context from CLAUDE.md in %s", work_dir)
    else:
        # We created this file — remove it entirely
        os.remove(claude_md_path)
        log.info("Removed CLAUDE.md (was created by DevFleet) in %s", work_dir)


class RemoteSession:
    def __init__(self, session_id: str, mission_id: str, work_dir: str,
                 name: str, mission: dict, agent_progress: str = ""):
        self.session_id = session_id
        self.mission_id = mission_id
        self.work_dir = work_dir
        self.name = name
        self.mission = mission
        self.agent_progress = agent_progress
        self.process: asyncio.subprocess.Process | None = None
        self.remote_url: str | None = None
        self.active = False
        self._task: asyncio.Task | None = None
        self._subscribers: list[asyncio.Queue] = []
        self._output_buffer: list[str] = []  # Keep last N chunks for backfill

    def subscribe(self) -> asyncio.Queue:
        """Subscribe to live output. Returns a queue that receives text chunks."""
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        """Remove a subscriber."""
        try:
            self._subscribers.remove(q)
        except ValueError:
            pass

    def _broadcast(self, text: str) -> None:
        """Send a text chunk to all subscribers."""
        self._output_buffer.append(text)
        # Keep last 500 chunks (~2MB) for backfill
        if len(self._output_buffer) > 500:
            self._output_buffer = self._output_buffer[-500:]
        for q in list(self._subscribers):
            try:
                q.put_nowait(text)
            except asyncio.QueueFull:
                pass  # Drop if subscriber is too slow

    async def start(self) -> str | None:
        """Start remote-control process and wait for URL."""
        log.info("Starting remote-control for session %s in %s", self.session_id, self.work_dir)

        # Inject mission context into CLAUDE.md so the remote session has it
        try:
            _inject_mission_context(self.work_dir, self.mission, self.agent_progress)
        except Exception as e:
            log.warning("Failed to inject mission context: %s", e)

        # Strip API key / SDK env vars so the CLI uses OAuth login instead.
        # Remote-control requires OAuth auth — API keys don't have access.
        strip_vars = {
            "ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN",
            "CLAUDE_AGENT_SDK_VERSION", "CLAUDE_CODE_ENTRYPOINT",
            "CLAUDE_CODE_ENABLE_ASK_USER_QUESTION_TOOL",
            "CLAUDE_CODE_EMIT_TOOL_USE_SUMMARIES",
            "CLAUDE_CODE_ENABLE_FINE_GRAINED_TOOL_STREAMING",
            "CLAUDE_CODE_DISABLE_CRON", "CLAUDECODE",
        }
        rc_env = {k: v for k, v in os.environ.items() if k not in strip_vars}

        cmd = [
            "claude", "remote-control",
            "--name", self.name,
            "--spawn", "same-dir",
        ]

        self.process = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=self.work_dir,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=rc_env,
        )
        self.active = True

        # Auto-answer "y" to the "Enable Remote Control?" prompt
        try:
            self.process.stdin.write(b"y\n")
            await self.process.stdin.drain()
        except Exception as e:
            log.debug("stdin write (enable prompt): %s", e)

        # Parse output for the session URL (with timeout)
        # URL format: https://claude.ai/code?bridge=env_XXXX
        url_pattern = re.compile(r'(https://claude\.ai/code[^\s]+)')
        try:
            url = await asyncio.wait_for(
                self._read_until_url(url_pattern),
                timeout=30,
            )
            self.remote_url = url
            log.info("Remote-control URL for session %s: %s", self.session_id, url)

            # Store URL in DB
            try:
                conn = await db.get_db()
                await conn.execute(
                    "UPDATE agent_sessions SET remote_url=? WHERE id=?",
                    (url, self.session_id),
                )
                await conn.commit()
                await conn.close()
            except Exception as e:
                log.warning("Failed to store remote URL: %s", e)

            # Keep reading output in background (keeps process alive)
            self._task = asyncio.create_task(self._monitor())
            return url

        except RemoteControlNotEnabled:
            log.warning("Remote Control not enabled for this account (session %s)", self.session_id)
            await self.stop()
            raise

        except WorkspaceNotTrusted:
            log.warning("Workspace not trusted for session %s in %s", self.session_id, self.work_dir)
            await self.stop()
            raise

        except asyncio.TimeoutError:
            log.error("Timed out waiting for remote-control URL (session %s)", self.session_id)
            await self.stop()
            return None

    async def _read_until_url(self, pattern: re.Pattern) -> str:
        """Read stdout chunks until we find a URL.

        The CLI uses interactive output with ANSI codes and carriage returns,
        so we read in chunks rather than lines.
        """
        buffer = ""
        while True:
            chunk = await self.process.stdout.read(4096)
            if not chunk:
                raise RuntimeError(
                    f"Remote-control process exited before providing URL. Output so far: {buffer[-500:]}"
                )
            text = chunk.decode("utf-8", errors="replace")
            buffer += text
            self._broadcast(text)
            log.debug("remote-control output chunk: %s", text.strip()[:200])

            # Detect Anthropic account-level feature gate
            lower = buffer.lower()
            if "not yet enabled" in lower or "not enabled for your account" in lower:
                raise RemoteControlNotEnabled(
                    "Remote Control is not yet enabled for your Anthropic account. "
                    "This feature requires account-level activation from Anthropic."
                )

            # Detect workspace trust requirement
            if "workspace not trusted" in lower or "workspace trust" in lower:
                raise WorkspaceNotTrusted(
                    f"Workspace not trusted. Run `claude` once in the project directory "
                    f"({self.work_dir}) to accept the trust dialog, then try again."
                )

            match = pattern.search(buffer)
            if match:
                return match.group(1)

    async def _monitor(self):
        """Monitor the remote-control process and broadcast output to subscribers."""
        try:
            while True:
                chunk = await self.process.stdout.read(4096)
                if not chunk:
                    break
                text = chunk.decode("utf-8", errors="replace")
                self._broadcast(text)
            await self.process.wait()
            log.info("Remote-control process exited for session %s (code %s)",
                     self.session_id, self.process.returncode)
            # Notify subscribers that the session ended
            self._broadcast("\n[Remote control session ended]\n")
        except asyncio.CancelledError:
            pass
        finally:
            self.active = False
            # Signal end to all subscribers
            for q in list(self._subscribers):
                try:
                    q.put_nowait(None)  # None = end of stream
                except asyncio.QueueFull:
                    pass
            _remote_sessions.pop(self.session_id, None)
            # Clean up injected CLAUDE.md context
            try:
                _cleanup_mission_context(self.work_dir)
            except Exception as e:
                log.warning("Failed to clean up mission context: %s", e)

    async def stop(self):
        """Terminate the remote-control session."""
        self.active = False
        # Signal end to all subscribers
        for q in list(self._subscribers):
            try:
                q.put_nowait(None)
            except asyncio.QueueFull:
                pass
        if self._task:
            self._task.cancel()
        if self.process and self.process.returncode is None:
            try:
                self.process.terminate()
                await asyncio.sleep(2)
                if self.process.returncode is None:
                    self.process.kill()
            except ProcessLookupError:
                pass
        _remote_sessions.pop(self.session_id, None)
        # Clean up injected CLAUDE.md context
        try:
            _cleanup_mission_context(self.work_dir)
        except Exception as e:
            log.warning("Failed to clean up mission context: %s", e)
        log.info("Remote-control stopped for session %s", self.session_id)


async def start_remote_control(
    session_id: str,
    mission_id: str,
    work_dir: str,
    mission: dict,
    agent_progress: str = "",
) -> str | None:
    """Start a remote-control session. Returns the claude.ai URL or None on failure.

    Args:
        session_id: Unique session ID
        mission_id: Mission ID
        work_dir: Project directory to run in
        mission: Full mission dict (title, detailed_prompt, acceptance_criteria, etc.)
        agent_progress: Summary of what the previous agent accomplished (for takeover)
    """
    # Check if already active
    existing = _remote_sessions.get(session_id)
    if existing and existing.active:
        return existing.remote_url

    session = RemoteSession(
        session_id=session_id,
        mission_id=mission_id,
        work_dir=work_dir,
        name=f"DevFleet: {mission.get('title', 'Mission')}",
        mission=mission,
        agent_progress=agent_progress,
    )
    _remote_sessions[session_id] = session
    url = await session.start()
    if not url:
        _remote_sessions.pop(session_id, None)
    return url


async def stop_remote_control(session_id: str) -> bool:
    """Stop a remote-control session."""
    session = _remote_sessions.get(session_id)
    if not session:
        return False
    await session.stop()
    return True


async def subscribe_remote_session(session_id: str):
    """Async generator that yields output chunks from a remote-control session.
    Used by SSE endpoint to stream live output to the frontend."""
    session = _remote_sessions.get(session_id)
    if not session:
        yield {"type": "error", "text": "No active remote-control session"}
        return

    # Send backfill of buffered output
    if session._output_buffer:
        yield {"type": "backfill", "text": "".join(session._output_buffer)}

    # Subscribe and stream new chunks
    q = session.subscribe()
    try:
        while True:
            chunk = await q.get()
            if chunk is None:
                yield {"type": "done", "status": "completed"}
                break
            yield {"type": "text", "text": chunk}
    finally:
        session.unsubscribe(q)


def get_remote_status(session_id: str) -> dict:
    """Get status of a remote-control session."""
    session = _remote_sessions.get(session_id)
    if not session:
        return {"active": False, "url": None}
    return {
        "active": session.active,
        "url": session.remote_url,
        "mission_id": session.mission_id,
    }


def list_remote_sessions() -> list[dict]:
    """List all active remote-control sessions."""
    return [
        {
            "session_id": sid,
            "mission_id": s.mission_id,
            "url": s.remote_url,
            "active": s.active,
        }
        for sid, s in _remote_sessions.items()
        if s.active
    ]


async def cleanup_all():
    """Stop all remote-control sessions (called on shutdown)."""
    for session in list(_remote_sessions.values()):
        await session.stop()
