"""
Remote Control Manager

Spawns `claude remote-control` sessions so users can take over
running agent missions from their phone or browser via claude.ai/code.

Each remote-control session:
  - Runs in the mission's project directory (or worktree)
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


class RemoteControlNotEnabled(Exception):
    """Raised when the Anthropic account doesn't have remote-control enabled."""
    pass


class RemoteSession:
    def __init__(self, session_id: str, mission_id: str, work_dir: str, name: str,
                 prompt: str | None = None):
        self.session_id = session_id
        self.mission_id = mission_id
        self.work_dir = work_dir
        self.name = name
        self.prompt = prompt
        self.process: asyncio.subprocess.Process | None = None
        self.remote_url: str | None = None
        self.active = False
        self._task: asyncio.Task | None = None

    async def start(self) -> str | None:
        """Start remote-control process and wait for URL."""
        log.info("Starting remote-control for session %s in %s", self.session_id, self.work_dir)

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
            "--spawn=worktree",        # isolated git worktree per session
        ]
        if self.prompt:
            cmd.extend(["--prompt", self.prompt])

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
            log.debug("remote-control output chunk: %s", text.strip()[:200])

            # Detect Anthropic account-level feature gate
            lower = buffer.lower()
            if "not yet enabled" in lower or "not enabled for your account" in lower:
                raise RemoteControlNotEnabled(
                    "Remote Control is not yet enabled for your Anthropic account. "
                    "This feature requires account-level activation from Anthropic."
                )

            match = pattern.search(buffer)
            if match:
                return match.group(1)

    async def _monitor(self):
        """Monitor the remote-control process until it exits."""
        try:
            while True:
                chunk = await self.process.stdout.read(4096)
                if not chunk:
                    break
            await self.process.wait()
            log.info("Remote-control process exited for session %s (code %s)",
                     self.session_id, self.process.returncode)
        except asyncio.CancelledError:
            pass
        finally:
            self.active = False
            _remote_sessions.pop(self.session_id, None)

    async def stop(self):
        """Terminate the remote-control session."""
        self.active = False
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
        log.info("Remote-control stopped for session %s", self.session_id)


async def start_remote_control(
    session_id: str,
    mission_id: str,
    work_dir: str,
    mission_title: str,
    prompt: str | None = None,
) -> str | None:
    """Start a remote-control session. Returns the claude.ai URL or None on failure."""
    # Check if already active
    existing = _remote_sessions.get(session_id)
    if existing and existing.active:
        return existing.remote_url

    session = RemoteSession(
        session_id=session_id,
        mission_id=mission_id,
        work_dir=work_dir,
        name=f"DevFleet: {mission_title}",
        prompt=prompt,
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
