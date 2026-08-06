#!/usr/bin/env python3
"""Self-check for per-member isolation: python3 test_member_isolation.py

Covers the upgrade migration, the ownership guards, the watcher readiness gate,
the member identity resolution at dispatch, and the commit-prefix hook.
No agents are spawned, no network calls are made.
"""

import asyncio
import os
import sqlite3
import subprocess
import tempfile
import uuid

_TMP = tempfile.mkdtemp()
os.environ["DEVFLEET_DB"] = os.path.join(_TMP, "selfcheck.db")
os.environ["DEVFLEET_WORKSPACE_ROOT"] = os.path.join(_TMP, "workspaces")
os.environ["DEVFLEET_SECRETS_DIR"] = os.path.join(_TMP, "secrets")

import credentials
import db
import workspace


def demo_upgrade_migration():
    """init_db on a PRE-v9 database (no missions.assignee) must not crash —
    the index used to live in SCHEMA and ran before the ALTER, crash-looping
    every existing deployment at startup."""
    old = sqlite3.connect(db.DB_PATH)
    # Minimal pre-v9 shape: missions exists, has no assignee column.
    old.executescript(
        "CREATE TABLE missions (id TEXT PRIMARY KEY, project_id TEXT, title TEXT,"
        " status TEXT DEFAULT 'draft', created_at TEXT DEFAULT (datetime('now')));"
    )
    old.close()

    asyncio.run(db.init_db())

    conn = sqlite3.connect(db.DB_PATH)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(missions)")}
    assert "assignee" in cols, "migration must add assignee to an existing DB"
    idx = {r[1] for r in conn.execute("PRAGMA index_list(missions)")}
    assert "idx_missions_assignee" in idx, "index must exist after migration"
    members = conn.execute("SELECT id FROM team_members").fetchall()
    assert members, "empty team_members must be seeded"
    assert all(m[0] == workspace.slug(m[0]) for m in members), \
        "member ids must be their own slug (secrets + workspace dirs key on slug(id))"
    conn.close()
    print("member_isolation: pre-v9 upgrade + slug-id seeding ok")


def demo_seed_only_when_empty():
    """A member deleted in the UI must stay deleted across restarts."""
    conn = sqlite3.connect(db.DB_PATH)
    victim = conn.execute("SELECT id FROM team_members LIMIT 1").fetchone()[0]
    conn.execute("DELETE FROM team_members WHERE id=?", (victim,))
    conn.commit()
    conn.close()

    asyncio.run(db.init_db())  # a restart

    conn = sqlite3.connect(db.DB_PATH)
    assert not conn.execute("SELECT 1 FROM team_members WHERE id=?", (victim,)).fetchall(), \
        "restart must not resurrect a deleted member"
    conn.close()
    print("member_isolation: deleted members stay deleted ok")


async def demo_ownership_guards():
    """Member A cannot create/move missions into member B's project, and an
    owned project's path/owner cannot be re-pointed after creation."""
    from fastapi import HTTPException
    from models import MissionCreate, ProjectUpdate
    import app

    conn = await db.get_db()
    alice_p, bob_p = str(uuid.uuid4()), str(uuid.uuid4())
    await conn.execute("INSERT OR IGNORE INTO team_members (id,name) VALUES ('alice','alice')")
    await conn.execute("INSERT OR IGNORE INTO team_members (id,name) VALUES ('bob','bob')")
    await conn.execute("INSERT INTO projects (id,name,path,owner) VALUES (?,?,?,?)",
                       (alice_p, "ap", workspace.project_path("alice", "ap", create=True), "alice"))
    await conn.execute("INSERT INTO projects (id,name,path,owner) VALUES (?,?,?,?)",
                       (bob_p, "bp", workspace.project_path("bob", "bp", create=True), "bob"))
    await conn.commit()
    await conn.close()

    def mission(**kw):
        return MissionCreate(title="t", detailed_prompt="t", **kw)

    ok = await app.create_mission(mission(project_id=alice_p, assignee="alice"))
    assert ok["assignee"] == "alice"

    for bad in (mission(project_id=bob_p, assignee="alice"),       # cross-member
                mission(project_id=alice_p, assignee="nobody")):   # unknown assignee
        try:
            await app.create_mission(bad)
            raise AssertionError(f"must reject: {bad.assignee} on {bad.project_id}")
        except HTTPException as e:
            assert e.status_code == 400

    # Reassigning an existing mission across members is refused too
    from models import MissionUpdate
    try:
        await app.update_mission(ok["id"], MissionUpdate(assignee="bob"))
        raise AssertionError("must reject reassigning into a project bob doesn't own")
    except HTTPException as e:
        assert e.status_code == 400

    # Owned projects: path and owner are immutable
    for upd in (ProjectUpdate(path=_TMP), ProjectUpdate(owner="bob")):
        try:
            await app.update_project(alice_p, upd)
            raise AssertionError(f"must reject {upd}")
        except HTTPException as e:
            assert e.status_code == 400

    print("member_isolation: ownership guards ok")
    return alice_p


async def demo_watcher_readiness(alice_p: str):
    """Unverified members' missions WAIT in the queue; verified ones drain."""
    import mission_watcher

    conn = await db.get_db()
    await conn.execute(
        "INSERT INTO missions (id,project_id,title,detailed_prompt,assignee,auto_dispatch,status)"
        " VALUES (?,?,?,?,?,1,'draft')",
        (str(uuid.uuid4()), alice_p, "alice-task", "do", "alice"))
    await conn.commit()
    await conn.close()

    got = [m["title"] for m in await mission_watcher._find_eligible_missions(limit=99)]
    assert "alice-task" not in got, "unverified member's mission must wait, not dispatch"

    conn = await db.get_db()
    await conn.execute(
        "UPDATE team_members SET github_verified_at='2026-01-01', claude_verified_at='2026-01-01'"
        " WHERE id='alice'")
    await conn.commit()
    await conn.close()

    got = [m["title"] for m in await mission_watcher._find_eligible_missions(limit=99)]
    assert "alice-task" in got, "verified member's mission must be eligible"
    print("member_isolation: watcher readiness gate ok")


async def demo_member_context():
    """Dispatch resolves the mission to its member's own tokens, and refuses
    to run when unready or pointed at another member's project."""
    import sdk_engine

    conn = await db.get_db()
    rows = await conn.execute_fetchall("SELECT id FROM projects WHERE owner='alice'")
    alice_p = dict(rows[0])["id"]
    rows = await conn.execute_fetchall("SELECT id FROM projects WHERE owner='bob'")
    bob_p = dict(rows[0])["id"]
    await conn.close()

    credentials.store("alice", "ghp_selfcheck", "sk-ant-oat-selfcheck")

    ctx = await sdk_engine._member_context({"project_id": alice_p, "assignee": "alice"})
    assert ctx["env"]["GITHUB_TOKEN"] == "ghp_selfcheck"
    assert ctx["env"]["CLAUDE_CODE_OAUTH_TOKEN"] == "sk-ant-oat-selfcheck"

    # Unassigned mission in an owned project runs as the owner
    ctx = await sdk_engine._member_context({"project_id": alice_p})
    assert ctx["member_id"] == "alice"

    for bad in ({"project_id": bob_p, "assignee": "alice"},   # not alice's workspace
                {"project_id": bob_p, "assignee": "bob"}):    # bob unverified
        try:
            await sdk_engine._member_context(bad)
            raise AssertionError(f"must refuse {bad}")
        except RuntimeError:
            pass

    # No member anywhere → legacy behaviour, no env overrides
    conn = await db.get_db()
    legacy = str(uuid.uuid4())
    await conn.execute("INSERT INTO projects (id,name,path) VALUES (?, 'legacy', ?)", (legacy, _TMP))
    await conn.commit()
    await conn.close()
    ctx = await sdk_engine._member_context({"project_id": legacy})
    assert ctx == {"member_id": "", "owner": "", "env": {}}
    print("member_isolation: member identity at dispatch ok")


def demo_commit_prefix():
    """The hook must actually fire on a real commit — including in a worktree."""
    repo = os.path.join(_TMP, "hookrepo")
    os.makedirs(repo)
    run = lambda *a, **kw: subprocess.run(a, cwd=kw.pop("cwd", repo), check=True,
                                          capture_output=True, text=True, **kw)
    run("git", "init", "-q")
    run("git", "config", "user.email", "t@t")
    run("git", "config", "user.name", "t")

    assert workspace.enforce_commit_prefix(repo)
    open(os.path.join(repo, "f"), "w").write("x")
    run("git", "add", "f")
    run("git", "commit", "-q", "-m", "fix bug")
    subject = run("git", "log", "-1", "--format=%s").stdout.strip()
    assert subject == f"{workspace.COMMIT_PREFIX}: fix bug", subject

    wt = os.path.join(_TMP, "hookwt")
    run("git", "worktree", "add", "-q", wt)
    open(os.path.join(wt, "g"), "w").write("x")
    run("git", "add", "g", cwd=wt)
    run("git", "commit", "-q", "-m", "wt change", cwd=wt)
    subject = run("git", "log", "-1", "--format=%s", cwd=wt).stdout.strip()
    assert subject == f"{workspace.COMMIT_PREFIX}: wt change", subject

    # Someone else's hook is never clobbered
    hook = run("git", "rev-parse", "--git-path", "hooks").stdout.strip()
    hook = os.path.join(repo, hook, "commit-msg")
    open(hook, "w").write("#!/bin/sh\nexit 0\n")
    assert not workspace.enforce_commit_prefix(repo), "foreign hooks are left untouched"
    print("member_isolation: commit-prefix hook ok")


if __name__ == "__main__":
    demo_upgrade_migration()
    demo_seed_only_when_empty()
    # The remaining demos want the full current schema, not the pre-v9 skeleton
    # the upgrade test migrated — switch to a fresh DB.
    db.DB_PATH = os.path.join(_TMP, "selfcheck-fresh.db")
    asyncio.run(db.init_db())
    alice_p = asyncio.run(demo_ownership_guards())
    asyncio.run(demo_watcher_readiness(alice_p))
    asyncio.run(demo_member_context())
    demo_commit_prefix()
    print("all checks passed")
