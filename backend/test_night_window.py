#!/usr/bin/env python3
"""Self-check for the overnight system: python3 test_night_window.py

Covers the window arithmetic (no deps) and the backlog ordering SQL (temp DB).
No agents are spawned.
"""

import asyncio
import json
import os
import tempfile
import uuid
from datetime import datetime

os.environ.setdefault("DEVFLEET_DB", os.path.join(tempfile.mkdtemp(), "selfcheck.db"))

import night_window as nw

TZ = nw.TZ


def at(month, day, hour, minute=0):
    return datetime(2026, month, day, hour, minute, tzinfo=TZ)


def demo():
    assert nw.ENABLED, "run with defaults (DEVFLEET_NIGHT_ENABLED unset)"
    assert (nw.NIGHT_START.hour, nw.NIGHT_END.hour, nw.DAY_START.hour) == (21, 8, 9)

    # ── Daytime: closed, and hard_stop so overnight agents get reaped ──
    for hour in (9, 12, 17, 20):
        s = nw.state(at(8, 4, hour))
        assert not s["dispatch_open"], f"{hour}:00 should be closed"
        assert s["hard_stop"], f"{hour}:00 should hard-stop night agents"

    # ── Dispatch phase: 21:00 → 07:00, spanning midnight ──
    for m, d, hour in ((8, 4, 21), (8, 4, 23), (8, 5, 0), (8, 5, 1), (8, 5, 3), (8, 5, 6)):
        s = nw.state(at(m, d, hour))
        assert s["dispatch_open"], f"{hour}:00 should be open: {s['reason']}"
        assert not s["hard_stop"]

    # ── The whole point: the 07:00 window would run to 12:00, so it never opens ──
    for hour, minute in ((7, 0), (7, 30), (8, 0), (8, 29)):
        s = nw.state(at(8, 5, hour, minute))
        assert s["in_night"], f"{hour}:{minute:02d} still inside the night"
        assert not s["dispatch_open"], f"{hour}:{minute:02d} must not open a window past 09:00"
        assert not s["hard_stop"], "drain phase lets running agents finish"

    # ── 08:30 hard stop ──
    s = nw.state(at(8, 5, 8, 30))
    assert not s["in_night"] and s["hard_stop"], "08:30 is the hard stop"

    # ── Session windows are numbered and 5h long ──
    assert nw.state(at(8, 4, 21))["session_window"] == 0
    assert nw.state(at(8, 5, 1, 59))["session_window"] == 0
    assert nw.state(at(8, 5, 2))["session_window"] == 1
    assert nw.state(at(8, 5, 7))["session_window"] == 2
    assert nw.state(at(8, 4, 22))["session_window_end"].startswith("2026-08-05T02:00")

    # ── DST: the clocks-back night is 25h wall, windows stay 5h real time ──
    # 2026-10-25 02:00 BST → 01:00 GMT. Window 0 opens 21:00 BST, must end after
    # 5 real hours (01:00 GMT), not at "02:00" on the wall.
    s = nw.state(at(10, 24, 21, 30))
    assert s["session_window_end"].startswith("2026-10-25T01:00"), s["session_window_end"]

    print("night_window: window arithmetic ok")


async def demo_backlog():
    """The watcher's queue ordering: round-robin across projects, priority within."""
    import db
    import mission_watcher

    await db.init_db()
    conn = await db.get_db()

    cols = {r[1] for r in await conn.execute_fetchall("PRAGMA table_info(missions)")}
    assert "resume_session_id" in cols, "migration missing resume_session_id"

    pids = {}
    for name, state in (("alpha", "active"), ("beta", ""), ("shelved", "archived"),
                        ("resting", "on_hold")):
        pids[name] = str(uuid.uuid4())
        await conn.execute("INSERT INTO projects (id,name,path,state) VALUES (?,?,?,?)",
                           (pids[name], name, f"/tmp/{name}", state))   # beta: legacy blank state

    async def queue(project, title, priority, depends_on=()):
        mid = str(uuid.uuid4())
        await conn.execute(
            """INSERT INTO missions (id,project_id,title,detailed_prompt,priority,
                                     depends_on,auto_dispatch,status)
               VALUES (?,?,?,?,?,?,1,'draft')""",
            (mid, pids[project], title, "do it", priority, json.dumps(list(depends_on))))
        return mid

    # alpha has a deep backlog; without fairness it would eat every slot
    for p in (5, 4, 3, 1):
        await queue("alpha", f"alpha-p{p}", p)
    await queue("beta", "beta-p4", 4)
    await queue("beta", "beta-p0", 0)
    await queue("shelved", "never-run", 5)
    await queue("resting", "on-hold-task", 5)
    blocker = await queue("alpha", "blocker", 2)
    await queue("alpha", "blocked", 5, depends_on=[blocker])
    await conn.commit()
    await conn.close()

    got = [(m["project_name"], m["priority"])
           for m in await mission_watcher._find_eligible_missions(limit=4)]
    assert [p for p, _ in got] == ["alpha", "beta", "alpha", "beta"], got
    assert [pr for _, pr in got] == [5, 4, 4, 0], got
    print("night_window: backlog round-robin + priority ok")

    everything = [m["title"] for m in await mission_watcher._find_eligible_missions(limit=99)]
    assert "never-run" not in everything, "archived project must not drain"
    assert "on-hold-task" not in everything, "on_hold project must not drain"
    assert "beta-p4" in everything, "blank/legacy state must count as active"
    assert "blocked" not in everything, "unmet depends_on must still block"
    assert "blocker" in everything
    print("night_window: archived + on_hold skipped, depends_on honoured")


if __name__ == "__main__":
    demo()
    asyncio.run(demo_backlog())
    print("all checks passed")
