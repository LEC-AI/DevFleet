"""
Usage Budget — spend caps measured from what the fleet actually consumed.

The night window keeps the fleet out of the human's *session* windows. It does
nothing about the *weekly* allowance, which is shared: a fleet that never idles
will drain the week and then nobody can work at 9am, which is the exact failure
the night window exists to prevent. So autonomous dispatch is capped by spend as
well as by clock.

Two caps, both optional (0 or unset = off):

    DEVFLEET_WINDOW_BUDGET_USD   per 5-hour session window
    DEVFLEET_WEEK_BUDGET_USD     rolling 7 days

Spend is settled cost from agent_sessions plus live cost from sessions still
streaming — sdk_engine only writes total_cost_usd at a terminal state, so without
the live half a cap could be overshot by a whole mission per agent.

The figures are the SDK's own cost numbers. On a subscription they are not a bill;
they are the best available proxy for how much of the allowance has been eaten.
"""

import logging
import os
from datetime import datetime, timedelta, timezone

import db

log = logging.getLogger("devfleet.usage_budget")


def _budget(env_key: str) -> float:
    """0 / unset / unparseable = no cap."""
    try:
        return float(os.environ.get(env_key, "0") or 0)
    except ValueError:
        log.warning("%s is not a number — treating as no cap", env_key)
        return 0.0


WINDOW_BUDGET_USD = _budget("DEVFLEET_WINDOW_BUDGET_USD")
WEEK_BUDGET_USD = _budget("DEVFLEET_WEEK_BUDGET_USD")

# On weekend nights the clock stops holding dispatch back (night_window runs
# through to 09:00 with no window-overrun check), so this cap becomes the only
# thing keeping a Saturday worker from finding the window already drained. 90
# means the fleet may use 90% of a window's budget and must leave 10% spare.
WEEKEND_BUDGET_PCT = _budget("DEVFLEET_WEEKEND_BUDGET_PCT") or 90.0


def _live_spend() -> float:
    """Cost of sessions still streaming, absent from the DB until they finish."""
    try:
        from sdk_engine import live_usage
    except ImportError:
        return 0.0
    return sum(float(v.get("cost") or 0) for v in live_usage.values())


# agent_sessions.started_at is always SQLite's datetime('now') — UTC, formatted
# "YYYY-MM-DD HH:MM:SS" with a space and no offset. These comparisons are string
# comparisons, so the threshold has to be in exactly that shape: isoformat()
# yields a 'T' separator, and ' ' < 'T', which silently excludes every row and
# reports zero spend forever.
_SQLITE_TS = "%Y-%m-%d %H:%M:%S"


def _utc_stamp(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime(_SQLITE_TS)


async def _settled_since(since: datetime) -> float:
    """Cost of sessions that started at or after `since` and have finished.

    Running sessions are excluded because their DB cost is still 0 — their real
    spend comes from _live_spend() instead, so counting both would either
    double-count or under-count depending on timing.
    """
    conn = await db.get_db()
    try:
        rows = await conn.execute_fetchall(
            """SELECT COALESCE(SUM(total_cost_usd), 0) AS spent
               FROM agent_sessions
               WHERE started_at >= ? AND status != 'running'""",
            (_utc_stamp(since),),
        )
        return float(dict(rows[0])["spent"] or 0)
    finally:
        await conn.close()


async def state(window_start_iso: str | None = None, weekend: bool = False) -> dict:
    """Budget state. `dispatch_open` is what callers act on.

    `window_start_iso` should be night_window's current session_window_start so
    the per-window cap lines up with the real 5-hour boundary. Without it only
    the weekly cap is evaluated. `weekend` tightens the window cap to
    WEEKEND_BUDGET_PCT, holding the rest back for anyone working that morning.
    """
    if not WINDOW_BUDGET_USD and not WEEK_BUDGET_USD:
        return {"enabled": False, "dispatch_open": True, "reason": "no spend cap set"}

    live = _live_spend()
    now = datetime.now(timezone.utc)

    window_cap = WINDOW_BUDGET_USD
    if weekend and window_cap:
        window_cap = window_cap * WEEKEND_BUDGET_PCT / 100.0

    week_spent = None
    if WEEK_BUDGET_USD:
        week_spent = await _settled_since(now - timedelta(days=7)) + live

    window_spent = None
    if window_cap and window_start_iso:
        # night_window reports a local-tz (Europe/London) timestamp; _settled_since
        # converts to UTC to match how SQLite stored started_at.
        try:
            window_spent = await _settled_since(datetime.fromisoformat(window_start_iso)) + live
        except ValueError:
            log.warning("unparseable window start %r — skipping window cap", window_start_iso)

    over_week = week_spent is not None and week_spent >= WEEK_BUDGET_USD
    over_window = window_spent is not None and window_spent >= window_cap

    suffix = f" (weekend cap: {WEEKEND_BUDGET_PCT:g}% of ${WINDOW_BUDGET_USD:.2f})" if weekend else ""
    if over_week:
        reason = (f"weekly spend cap reached: ${week_spent:.2f} of "
                  f"${WEEK_BUDGET_USD:.2f} over the last 7 days")
    elif over_window:
        reason = (f"session-window spend cap reached: ${window_spent:.2f} of "
                  f"${window_cap:.2f} this window{suffix}")
    else:
        parts = []
        if window_spent is not None:
            parts.append(f"window ${window_spent:.2f}/${window_cap:.2f}")
        if week_spent is not None:
            parts.append(f"week ${week_spent:.2f}/${WEEK_BUDGET_USD:.2f}")
        reason = "within budget — " + ", ".join(parts) + suffix

    return {
        "enabled": True,
        "dispatch_open": not (over_week or over_window),
        "weekend": weekend,
        "window_budget_usd": round(window_cap, 4) if window_cap else None,
        "week_budget_usd": WEEK_BUDGET_USD or None,
        "window_spent_usd": round(window_spent, 4) if window_spent is not None else None,
        "week_spent_usd": round(week_spent, 4) if week_spent is not None else None,
        "in_flight_usd": round(live, 4),
        "reason": reason,
    }
