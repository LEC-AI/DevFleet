"""
Per-member credentials and environment readiness.

A member's tab stays locked until their environment is *proven* working: a
GitHub token that authenticates, and a Claude token that can actually complete a
call. Both are tested against the real services — a token that merely looks
well-formed tells you nothing.

Secrets are never stored in the database. They go to one file per member, mode
0600, and the DB records only whether verification succeeded and when. That
avoids inventing a credential vault, keeps secrets out of DB backups, and lines
up with per-Linux-user execution: on the box this file is the member's own
`~/.devfleet/env`, readable only by them.

    IMPORTANT: this is a *readiness* gate, not authentication. The API has no
    auth, so anyone who can reach the port can drive any member's tab. Gating on
    readiness stops half-configured environments dispatching agents; it does not
    stop an unauthorised caller. That needs API auth, which does not exist yet.

Only revocable, scopable credentials are accepted: a GitHub PAT or a fine-grained
token. Passwords are refused outright — they cannot be scoped or revoked
individually.
"""

import asyncio
import logging
import os
import shutil
import stat
import tempfile

import httpx

import workspace

log = logging.getLogger("devfleet.credentials")

SECRETS_DIR = os.environ.get(
    "DEVFLEET_SECRETS_DIR", os.path.join(workspace.ROOT, ".secrets"))

# A trivial Haiku call, which is what a real verification costs. Not free —
# roughly a few cents — so verification is on demand, never on a poll.
VERIFY_MODEL = "claude-haiku-4-5-20251001"
VERIFY_PROMPT = "Reply with exactly: TOKEN_OK"


def _secrets_path(member_id: str) -> str:
    return os.path.join(SECRETS_DIR, f"{workspace.slug(member_id)}.env")


def store(member_id: str, github_token: str | None, claude_token: str | None) -> None:
    """Merge the given secrets into the member's 0600 env file."""
    for name, tok in (("github", github_token), ("claude", claude_token)):
        if tok and tok.strip().lower() in ("password", "pass"):
            raise ValueError(f"{name}: passwords are not accepted — use a token")

    existing = load(member_id)
    if github_token:
        existing["GITHUB_TOKEN"] = github_token.strip()
    if claude_token:
        existing["CLAUDE_CODE_OAUTH_TOKEN"] = claude_token.strip()

    os.makedirs(SECRETS_DIR, mode=0o700, exist_ok=True)
    os.chmod(SECRETS_DIR, 0o700)
    path = _secrets_path(member_id)
    # Write via a 0600 temp file then rename, so the secret is never briefly
    # world-readable between create and chmod.
    tmp = path + ".tmp"
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        for k, v in existing.items():
            f.write(f"{k}={v}\n")
    os.replace(tmp, path)
    os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def delete(member_id: str) -> None:
    """Remove a member's secrets file. Deleting a member must not leave their
    tokens on disk, where re-adding the same name would silently resurrect them."""
    try:
        os.remove(_secrets_path(member_id))
    except FileNotFoundError:
        pass


def load(member_id: str) -> dict:
    path = _secrets_path(member_id)
    out = {}
    if not os.path.exists(path):
        return out
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip()
    return out


def has(member_id: str) -> dict:
    """Which secrets are present, without reading their values out."""
    creds = load(member_id)
    return {
        "github": bool(creds.get("GITHUB_TOKEN")),
        "claude": bool(creds.get("CLAUDE_CODE_OAUTH_TOKEN")),
    }


async def verify_github(token: str) -> dict:
    """Hit the real API. Returns {ok, login, scopes, error}."""
    if not token:
        return {"ok": False, "error": "no GitHub token stored"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                "https://api.github.com/user",
                headers={"Authorization": f"Bearer {token}",
                         "Accept": "application/vnd.github+json"},
            )
        if r.status_code == 401:
            return {"ok": False, "error": "GitHub rejected the token (401) — expired or revoked"}
        if r.status_code != 200:
            return {"ok": False, "error": f"GitHub returned {r.status_code}: {r.text[:120]}"}
        data = r.json()
        scopes = r.headers.get("x-oauth-scopes", "")
        # A token that cannot touch repos is useless for cloning or pushing.
        if scopes and "repo" not in scopes:
            return {"ok": False, "login": data.get("login"), "scopes": scopes,
                    "error": f"token lacks 'repo' scope (has: {scopes or 'none'})"}
        return {"ok": True, "login": data.get("login"), "scopes": scopes or "fine-grained"}
    except Exception as e:
        return {"ok": False, "error": f"could not reach GitHub: {e}"}


async def verify_claude(token: str) -> dict:
    """Run a real Claude call with a scrubbed env, so only this token can auth.

    Without the scrubbing the CLI happily falls back to whatever login is on the
    box and a dead token still passes.
    """
    if not token:
        return {"ok": False, "error": "no Claude token stored"}
    cli = shutil.which("claude") or os.path.expanduser("~/.local/bin/claude")
    if not os.path.exists(cli):
        return {"ok": False, "error": "claude CLI not found on PATH"}

    # A fresh throwaway HOME per call: a shared one accumulates CLI state from
    # earlier verifications, and a stale login there could vouch for a dead token.
    with tempfile.TemporaryDirectory(prefix="devfleet-verify-") as sandbox_home:
        env = {
            "HOME": sandbox_home,
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "CLAUDE_CODE_OAUTH_TOKEN": token,
        }
        try:
            proc = await asyncio.create_subprocess_exec(
                cli, "--print", "--model", VERIFY_MODEL, "-p", VERIFY_PROMPT,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
                env=env, cwd=sandbox_home,
            )
            out, err = await asyncio.wait_for(proc.communicate(), timeout=120)
        except asyncio.TimeoutError:
            return {"ok": False, "error": "Claude verification timed out after 120s"}
        except Exception as e:
            return {"ok": False, "error": f"could not run claude: {e}"}

    text = out.decode("utf-8", "replace")
    if proc.returncode != 0 or "TOKEN_OK" not in text:
        detail = (err.decode("utf-8", "replace") or text)[-300:]
        return {"ok": False, "error": f"claude exited {proc.returncode}: {detail}"}
    return {"ok": True, "model": VERIFY_MODEL}
