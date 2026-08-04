"""
Workspace — the confined directory an agent works in, per team member.

Every member gets exactly one workspace:

    <DEVFLEET_WORKSPACE_ROOT>/<member_id>/

Projects live inside it as <workspace>/<project-slug>. Nothing outside it is a
valid project path, so the UI never asks anyone to type a path — it is derived.

Confinement is enforced at two levels, and it is worth being precise about which
is which:

  * `resolve()` rejects any path that escapes the workspace after symlinks are
    resolved. That stops the *API* being talked into pointing an agent somewhere
    else. It is a real boundary.

  * Whether the *agent process* can write outside its workspace is an OS
    question, not a Python one. sdk_engine already carries recovery code for
    agents whose writes landed outside the worktree, so this does happen. Real
    containment needs the agent to run as a user with no write access anywhere
    else. See enforce_commit_prefix() for what we can guarantee today.
"""

import logging
import os
import re
import stat

log = logging.getLogger("devfleet.workspace")

# Default keeps everything under the repo so a laptop checkout works untouched.
# On the box set this to something like /srv/devfleet.
ROOT = os.path.abspath(os.environ.get(
    "DEVFLEET_WORKSPACE_ROOT",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "workspaces"),
))

COMMIT_PREFIX = os.environ.get("DEVFLEET_COMMIT_PREFIX", "devfleet")


class OutsideWorkspace(ValueError):
    """Raised when a path would take an agent out of its workspace."""


def slug(name: str) -> str:
    """Filesystem-safe directory name. Never empty, never traversal."""
    s = re.sub(r"[^a-z0-9._-]+", "-", (name or "").strip().lower()).strip("-.")
    return s or "unnamed"


def member_workspace(member_id: str, create: bool = False) -> str:
    """The one directory this member's agents may write in."""
    path = os.path.join(ROOT, slug(member_id))
    if create:
        os.makedirs(path, mode=0o750, exist_ok=True)
    return path


def project_path(member_id: str, project_name: str, create: bool = False) -> str:
    """Where a named project lives inside its member's workspace."""
    ws = member_workspace(member_id, create=create)
    path = os.path.join(ws, slug(project_name))
    if create:
        os.makedirs(path, mode=0o750, exist_ok=True)
    return path


def resolve(member_id: str, path: str) -> str:
    """Return `path` as an absolute path, or raise if it escapes the workspace.

    Uses realpath on both sides so `..` and symlinks cannot be used to step out:
    a symlink inside the workspace pointing at /etc resolves to /etc and is
    rejected, which a string-prefix check would happily allow.
    """
    ws = os.path.realpath(member_workspace(member_id))
    target = os.path.realpath(os.path.join(ws, path) if not os.path.isabs(path) else path)
    if target != ws and not target.startswith(ws + os.sep):
        raise OutsideWorkspace(
            f"{target} is outside {member_id}'s workspace ({ws}). "
            f"Agents may read elsewhere but must write only in their workspace."
        )
    return target


def enforce_commit_prefix(repo_path: str) -> bool:
    """Install a commit-msg hook so every commit here carries the prefix.

    A hook is used rather than instructions in the prompt because the agent runs
    `git commit` itself — asking nicely is not enforcement. Per-worktree
    core.hooksPath needs extensions.worktreeConfig, which is enabled here.

    Returns True if the hook is in place.
    """
    hooks_dir = os.path.join(repo_path, ".devfleet-hooks")
    hook = os.path.join(hooks_dir, "commit-msg")
    try:
        os.makedirs(hooks_dir, exist_ok=True)
        with open(hook, "w") as f:
            f.write(
                "#!/bin/sh\n"
                "# Installed by DevFleet: every commit made in this workspace is\n"
                "# attributed to the fleet, so a human scanning git log can tell\n"
                "# agent commits from their own at a glance.\n"
                f'prefix="{COMMIT_PREFIX}"\n'
                'first=$(head -n1 "$1")\n'
                'case "$first" in\n'
                '  "$prefix":*|"$prefix"\\(*) exit 0 ;;\n'
                'esac\n'
                'printf "%s: %s\\n" "$prefix" "$first" > "$1.tmp"\n'
                'tail -n +2 "$1" >> "$1.tmp"\n'
                'mv "$1.tmp" "$1"\n'
            )
        os.chmod(hook, os.stat(hook).st_mode | stat.S_IXUSR | stat.S_IXGRP)
        return True
    except OSError as e:
        log.warning("could not install commit-msg hook in %s: %s", repo_path, e)
        return False
