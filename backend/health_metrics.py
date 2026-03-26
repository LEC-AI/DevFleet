"""
Project Health Metrics — Analytics and insights for project status

Tracks and analyzes:
- Cost per mission and mission type
- Success/failure rates
- Performance trends
- Bottleneck detection
- Agent efficiency
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from db import get_db

log = logging.getLogger("devfleet.health_metrics")


async def get_project_health(project_id: str) -> dict:
    """
    Comprehensive health analysis for a project.

    Returns metrics on:
    - Mission status distribution
    - Cost analysis
    - Performance trends
    - Identified bottlenecks
    """
    db = await get_db()

    # Get all missions and sessions
    missions = await db.execute_fetchall(
        "SELECT * FROM missions WHERE project_id = ? ORDER BY created_at DESC",
        (project_id,)
    )
    missions = [dict(row) for row in missions]

    sessions = await db.execute_fetchall("""
        SELECT s.*, m.mission_type, m.title as mission_title
        FROM agent_sessions s
        JOIN missions m ON s.mission_id = m.id
        WHERE m.project_id = ?
        ORDER BY s.started_at DESC
    """, (project_id,))
    sessions = [dict(row) for row in sessions]

    await db.close()

    # Analyze missions
    mission_stats = {
        "total": len(missions),
        "by_status": {},
        "by_type": {},
        "by_priority": {}
    }

    for m in missions:
        status = m.get("status", "draft")
        mission_stats["by_status"][status] = mission_stats["by_status"].get(status, 0) + 1

        mtype = m.get("mission_type", "implement")
        mission_stats["by_type"][mtype] = mission_stats["by_type"].get(mtype, 0) + 1

        priority = m.get("priority", 0)
        mission_stats["by_priority"][priority] = mission_stats["by_priority"].get(priority, 0) + 1

    # Analyze sessions (cost, performance, success rate)
    session_stats = {
        "total_sessions": len(sessions),
        "total_cost_usd": 0,
        "total_tokens": 0,
        "success_count": 0,
        "failed_count": 0,
        "avg_cost_per_session": 0,
        "avg_duration_seconds": 0,
        "by_model": {},
        "by_mission_type": {}
    }

    durations = []

    for s in sessions:
        cost = float(s.get("total_cost_usd", 0) or 0)
        session_stats["total_cost_usd"] += cost

        tokens = int(s.get("total_tokens", 0) or 0)
        session_stats["total_tokens"] += tokens

        status = s.get("status", "unknown")
        if status == "completed":
            session_stats["success_count"] += 1
        elif status == "failed":
            session_stats["failed_count"] += 1

        # Duration
        if s.get("started_at") and s.get("ended_at"):
            try:
                start = datetime.fromisoformat(s["started_at"])
                end = datetime.fromisoformat(s["ended_at"])
                duration = (end - start).total_seconds()
                durations.append(duration)
            except:
                pass

        # By model
        model = s.get("model", "unknown")
        if model not in session_stats["by_model"]:
            session_stats["by_model"][model] = {
                "count": 0,
                "total_cost": 0,
                "total_tokens": 0,
                "avg_cost": 0
            }
        session_stats["by_model"][model]["count"] += 1
        session_stats["by_model"][model]["total_cost"] += cost
        session_stats["by_model"][model]["total_tokens"] += tokens

        # By mission type
        mtype = s.get("mission_type", "unknown")
        if mtype not in session_stats["by_mission_type"]:
            session_stats["by_mission_type"][mtype] = {
                "count": 0,
                "total_cost": 0,
                "success": 0,
                "failed": 0
            }
        session_stats["by_mission_type"][mtype]["count"] += 1
        session_stats["by_mission_type"][mtype]["total_cost"] += cost
        if status == "completed":
            session_stats["by_mission_type"][mtype]["success"] += 1
        elif status == "failed":
            session_stats["by_mission_type"][mtype]["failed"] += 1

    if session_stats["total_sessions"] > 0:
        session_stats["avg_cost_per_session"] = round(
            session_stats["total_cost_usd"] / session_stats["total_sessions"], 4
        )

    if durations:
        session_stats["avg_duration_seconds"] = round(sum(durations) / len(durations), 1)

    # Calculate averages per model
    for model_stats in session_stats["by_model"].values():
        if model_stats["count"] > 0:
            model_stats["avg_cost"] = round(model_stats["total_cost"] / model_stats["count"], 4)

    # Calculate success rates
    success_rate = 0
    if session_stats["success_count"] + session_stats["failed_count"] > 0:
        success_rate = round(
            100 * session_stats["success_count"] /
            (session_stats["success_count"] + session_stats["failed_count"]),
            1
        )

    # Identify bottlenecks
    bottlenecks = _identify_bottlenecks(missions, sessions)

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "project_id": project_id,
        "missions": mission_stats,
        "sessions": {
            **session_stats,
            "success_rate_percent": success_rate
        },
        "bottlenecks": bottlenecks,
        "recommendations": _generate_recommendations(mission_stats, session_stats, bottlenecks)
    }


def _identify_bottlenecks(missions: List[dict], sessions: List[dict]) -> List[dict]:
    """Identify performance bottlenecks and issues."""
    bottlenecks = []

    # Find missions with high dependency counts (blocking many others)
    for mission in missions:
        depends_on = json.loads(mission.get("depends_on", "[]") or "[]")
        if depends_on:
            mission_id = mission["id"]
            blocked_by_this = sum(
                1 for m in missions
                if mission_id in json.loads(m.get("depends_on", "[]") or "[]")
            )
            if blocked_by_this > 2:
                bottlenecks.append({
                    "type": "blocking_dependency",
                    "mission_id": mission_id,
                    "mission_title": mission.get("title", "Unknown"),
                    "blocks_count": blocked_by_this,
                    "severity": "high" if blocked_by_this > 5 else "medium"
                })

    # Find expensive mission types
    type_costs = {}
    type_counts = {}
    for session in sessions:
        mtype = session.get("mission_type", "unknown")
        cost = float(session.get("total_cost_usd", 0) or 0)
        type_costs[mtype] = type_costs.get(mtype, 0) + cost
        type_counts[mtype] = type_counts.get(mtype, 0) + 1

    for mtype, total_cost in type_costs.items():
        avg_cost = total_cost / type_counts.get(mtype, 1)
        if avg_cost > 10:  # Expensive
            bottlenecks.append({
                "type": "high_cost_mission_type",
                "mission_type": mtype,
                "avg_cost_usd": round(avg_cost, 2),
                "total_cost_usd": round(total_cost, 2),
                "severity": "medium"
            })

    # Find failing mission types (from session_stats by_mission_type)
    # Need to recalculate failure stats from actual sessions
    type_stats = {}
    for session in sessions:
        mtype = session.get("mission_type", "unknown")
        if mtype not in type_stats:
            type_stats[mtype] = {"success": 0, "failed": 0}

        if session.get("status") == "completed":
            type_stats[mtype]["success"] += 1
        elif session.get("status") == "failed":
            type_stats[mtype]["failed"] += 1

    for mtype, stats in type_stats.items():
        if stats["failed"] > stats["success"] and (stats["success"] + stats["failed"]) > 0:
            bottlenecks.append({
                "type": "low_success_rate",
                "mission_type": mtype,
                "success_count": stats["success"],
                "failed_count": stats["failed"],
                "severity": "high"
            })

    return bottlenecks


def _generate_recommendations(
    mission_stats: dict,
    session_stats: dict,
    bottlenecks: List[dict]
) -> List[str]:
    """Generate actionable recommendations based on metrics."""
    recommendations = []

    # Cost optimization
    if session_stats["total_cost_usd"] > 100:
        recommendations.append(
            f"Total spend is ${session_stats['total_cost_usd']:.2f}. "
            f"Consider using claude-sonnet-4-6 for some mission types to reduce cost."
        )

    # Success rate
    if session_stats.get("success_rate_percent", 100) < 80:
        recommendations.append(
            f"Success rate is {session_stats.get('success_rate_percent')}%. "
            f"Review failed missions to identify patterns."
        )

    # Complexity
    if mission_stats["total"] > 10 and mission_stats["by_status"].get("draft", 0) > 3:
        recommendations.append(
            f"You have {mission_stats['by_status'].get('draft', 0)} draft missions. "
            f"Consider breaking them into smaller, more focused tasks."
        )

    # Parallelization (skip if not enough missions to analyze)
    if mission_stats.get("total", 0) >= 3:
        recommendations.append(
            "Review mission dependencies to identify parallelization opportunities. "
            "Parallel execution speeds up project delivery."
        )

    # Bottleneck fixes
    for bottleneck in bottlenecks:
        if bottleneck["type"] == "high_cost_mission_type":
            recommendations.append(
                f"{bottleneck['mission_type']} missions cost ${bottleneck['avg_cost_usd']} on average. "
                f"Try using a cheaper model for these routine tasks."
            )

    return recommendations
