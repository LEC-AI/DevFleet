"""
Night Window — global gate so autonomous dispatch only burns quota overnight.

Claude subscription limits are rolling 5-hour session windows. Stopping at
sunrise is not enough: an agent that opens the window at 07:00 keeps it open
until 12:00, so anything it drains is drained from the human's morning. A 5-hour
window must therefore never be *opened* if it would still be live at DAY_START.

Three phases per night (defaults, Europe/London):

    21:00  dispatch opens   — new agents start, backlog drains
    07:00  dispatch closes  — the next 5h window (07:00-12:00) would overrun
                              DAY_START 09:00, so no new agents. Running ones
                              keep going.
    08:30  hard stop        — night-dispatched agents are paused (worktree kept,
                              resumed next night from the same conversation).

The 07:00 cutoff is not configured, it falls out of the window arithmetic. Move
NIGHT_START or DAY_START and it moves with them.

Env:
    DEVFLEET_NIGHT_ENABLED  default true   — false restores 24/7 dispatch
    DEVFLEET_TZ             default Europe/London
    DEVFLEET_NIGHT_START    default 21:00  — dispatch may open
    DEVFLEET_NIGHT_END      default 08:30  — hard stop
    DEVFLEET_DAY_START      default 09:00  — human needs full quota from here
    DEVFLEET_SESSION_HOURS  default 5      — Anthropic session window length
"""

import os
from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo


def _hhmm(env_key: str, default: str) -> time:
    hh, mm = os.environ.get(env_key, default).split(":")
    return time(int(hh), int(mm))


ENABLED = os.environ.get("DEVFLEET_NIGHT_ENABLED", "true").lower() == "true"
TZ = ZoneInfo(os.environ.get("DEVFLEET_TZ", "Europe/London"))
NIGHT_START = _hhmm("DEVFLEET_NIGHT_START", "21:00")
NIGHT_END = _hhmm("DEVFLEET_NIGHT_END", "08:30")
DAY_START = _hhmm("DEVFLEET_DAY_START", "09:00")
SESSION_HOURS = float(os.environ.get("DEVFLEET_SESSION_HOURS", "5"))


def _at(day: datetime, t: time) -> datetime:
    return day.replace(hour=t.hour, minute=t.minute, second=0, microsecond=0)


def _elapsed_plus(anchor: datetime, hours: float) -> datetime:
    """anchor + `hours` of *real elapsed* time, not wall-clock time.

    A session window is 5 hours of actual time, so on the two DST nights a year
    it must not stretch or shrink with the clock. Doing the addition in UTC
    keeps the quota maths honest.
    """
    return (anchor.astimezone(timezone.utc) + timedelta(hours=hours)).astimezone(anchor.tzinfo)


def _bounds(now: datetime) -> tuple[datetime, datetime, datetime]:
    """(night_start, night_end, day_start) for the night `now` sits in."""
    anchor = _at(now, NIGHT_START)
    if now < anchor:
        anchor -= timedelta(days=1)  # we're past midnight, night began yesterday
    night_end = _at(anchor, NIGHT_END)
    if night_end <= anchor:
        night_end += timedelta(days=1)
    day_start = _at(anchor, DAY_START)
    if day_start <= anchor:
        day_start += timedelta(days=1)
    return anchor, night_end, day_start


def state(now: datetime | None = None) -> dict:
    """Current gate state. `dispatch_open` and `hard_stop` are what callers act on."""
    now = now or datetime.now(TZ)

    if not ENABLED:
        return {"enabled": False, "dispatch_open": True, "hard_stop": False,
                "now": now.isoformat(), "reason": "night window disabled"}

    night_start, night_end, day_start = _bounds(now)
    in_night = night_start <= now < night_end

    index = int((now - night_start).total_seconds() / 3600 // SESSION_HOURS)
    window_start = _elapsed_plus(night_start, SESSION_HOURS * index)
    window_end = _elapsed_plus(night_start, SESSION_HOURS * (index + 1))
    window_safe = window_end <= day_start

    if not in_night:
        reason = (f"outside night window "
                  f"({NIGHT_START:%H:%M}–{NIGHT_END:%H:%M} {TZ.key})")
    elif not window_safe:
        reason = (f"draining only — session window {index} would stay open "
                  f"until {window_end:%H:%M}, past day start {DAY_START:%H:%M}")
    else:
        reason = f"open — session window {index} ends {window_end:%H:%M}"

    return {
        "enabled": True,
        "in_night": in_night,
        "dispatch_open": in_night and window_safe,
        "hard_stop": not in_night,
        "now": now.isoformat(),
        "timezone": TZ.key,
        "night_start": night_start.isoformat(),
        "night_end": night_end.isoformat(),
        "day_start": day_start.isoformat(),
        "session_window": index,
        "session_window_start": window_start.isoformat(),
        "session_window_end": window_end.isoformat(),
        "reason": reason,
    }
