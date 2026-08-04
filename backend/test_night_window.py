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
from datetime import datetime, timedelta, timezone

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

    # ── Weekend nights run through to 09:00 with no window-overrun check ──
    # 2026-08-07 is a Friday, 2026-08-08 Saturday, 2026-08-09 Sunday.
    assert at(8, 7, 21).weekday() == 4, "expected Friday"
    for m, d, hour in ((8, 7, 21), (8, 8, 3), (8, 8, 7), (8, 8, 8, ), (8, 8, 22), (8, 9, 7)):
        s = nw.state(at(m, d, hour))
        assert s["weekend"], f"{m}/{d} {hour}:00 should be a weekend night"
        assert s["dispatch_open"], f"{m}/{d} {hour}:00 should stay open: {s['reason']}"

    # 07:00-09:00 is the slice weeknights refuse and weekends allow
    assert not nw.state(at(8, 5, 7))["dispatch_open"], "Wed 07:00 closed"
    assert nw.state(at(8, 8, 7))["dispatch_open"], "Sat 07:00 open"

    # Weekend hard stop is 09:00, not 08:30
    assert nw.state(at(8, 8, 8, 45))["dispatch_open"], "Sat 08:45 still open"
    assert nw.state(at(8, 8, 9))["hard_stop"], "Sat 09:00 hard stop"

    # Sunday *evening* runs into a workday, so it keeps weeknight rules
    sun = nw.state(at(8, 9, 22))
    assert not sun["weekend"], "Sunday evening is a weeknight"
    assert not nw.state(at(8, 10, 7, 30))["dispatch_open"], "Mon 07:30 closed again"

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


async def demo_budget():
    """Spend caps. The timestamp format here is the whole point of this test:
    started_at is SQLite's 'YYYY-MM-DD HH:MM:SS', and comparing it against an
    isoformat() string silently matches nothing, so spend reads 0 forever."""
    import db
    import usage_budget as ub

    ub.WINDOW_BUDGET_USD = 10.0
    ub.WEEK_BUDGET_USD = 50.0
    ub.WEEKEND_BUDGET_PCT = 90.0

    await db.init_db()
    conn = await db.get_db()
    pid, mid = str(uuid.uuid4()), str(uuid.uuid4())
    await conn.execute("INSERT INTO projects (id,name,path) VALUES (?,?,'/tmp/b')", (pid, "budget"))
    await conn.execute(
        "INSERT INTO missions (id,project_id,title,detailed_prompt) VALUES (?,?,'t','t')", (mid, pid))

    # window starts 1h ago (local tz, as night_window reports it)
    win_start = datetime.now(TZ) - timedelta(hours=1)

    async def session(cost, minutes_ago, status="completed"):
        sid = str(uuid.uuid4())
        stamp = (datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
                 ).strftime("%Y-%m-%d %H:%M:%S")
        await conn.execute(
            """INSERT INTO agent_sessions (id,mission_id,status,started_at,total_cost_usd)
               VALUES (?,?,?,?,?)""", (sid, mid, status, stamp, cost))
        await conn.commit()

    await session(4.0, 30)                     # inside the window
    st = await ub.state(win_start.isoformat())
    assert st["window_spent_usd"] == 4.0, st   # 0.0 here = the format bug is back
    assert st["dispatch_open"], st

    await session(3.0, 600)                    # 10h ago: this week, not this window
    st = await ub.state(win_start.isoformat())
    assert st["window_spent_usd"] == 4.0, st
    assert st["week_spent_usd"] == 7.0, st

    await session(7.0, 20)                     # window now at 11.0, over the 10 cap
    st = await ub.state(win_start.isoformat())
    assert not st["dispatch_open"], st
    assert "session-window spend cap" in st["reason"], st

    # Weekend tightens the same cap to 90% → 9.0, so 11.0 is over that too
    stw = await ub.state(win_start.isoformat(), weekend=True)
    assert stw["window_budget_usd"] == 9.0, stw
    assert not stw["dispatch_open"], stw

    # In-flight spend counts even though the DB still says 0 for it
    import sdk_engine
    sdk_engine.live_usage["live-1"] = {"cost": 2.5, "tokens": 100}
    ub.WINDOW_BUDGET_USD = 100.0
    st = await ub.state(win_start.isoformat())
    assert st["in_flight_usd"] == 2.5, st
    assert st["window_spent_usd"] == 13.5, st   # 11.0 settled + 2.5 in flight
    sdk_engine.live_usage.clear()

    # A running session's DB cost is excluded (its spend is in live_usage instead)
    await session(99.0, 5, status="running")
    st = await ub.state(win_start.isoformat())
    assert st["window_spent_usd"] == 11.0, st

    await conn.close()
    print("night_window: spend caps + weekend cap + in-flight accounting ok")


if __name__ == "__main__":
    demo()
    asyncio.run(demo_backlog())
    asyncio.run(demo_budget())
    print("all checks passed")
