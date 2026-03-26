"""
Mission Dependency Visualizer — Creates Mermaid diagrams

Generates:
- Mission dependency graphs (DAG)
- Critical path visualization
- Parallel execution opportunities
- Timeline views
"""

import json
import logging
from typing import List, Dict, Tuple

from db import get_db

log = logging.getLogger("devfleet.visualizer")


async def generate_mission_graph(project_id: str, diagram_type: str = "dag") -> str:
    """
    Generate a Mermaid diagram of missions and dependencies.

    Args:
        project_id: Project to visualize
        diagram_type: "dag" (dependency DAG), "timeline" (execution timeline), "critical_path"

    Returns: Mermaid diagram markdown
    """
    db = await get_db()

    missions = await db.execute_fetchall(
        "SELECT * FROM missions WHERE project_id = ? ORDER BY created_at ASC",
        (project_id,)
    )
    missions = [dict(row) for row in missions]
    await db.close()

    if not missions:
        return "graph LR\n  A[No missions yet]"

    if diagram_type == "dag":
        return _generate_dag_diagram(missions)
    elif diagram_type == "timeline":
        return _generate_timeline_diagram(missions)
    elif diagram_type == "critical_path":
        return _generate_critical_path_diagram(missions)
    else:
        return _generate_dag_diagram(missions)


def _generate_dag_diagram(missions: List[dict]) -> str:
    """Generate dependency DAG (directed acyclic graph)."""
    lines = ["graph TD"]

    # Build mission nodes
    for mission in missions:
        mid = mission["id"][:8]  # Use short ID
        title = mission["title"][:30]  # Truncate long titles
        status = mission.get("status", "draft")

        # Color based on status
        color_map = {
            "draft": "lightgray",
            "ready": "lightyellow",
            "running": "lightblue",
            "completed": "lightgreen",
            "failed": "lightcoral"
        }
        color = color_map.get(status, "white")

        lines.append(f'  {mid}["{title}<br/>({status})" style="fill:{color}"]')

    # Build edges (dependencies)
    for mission in missions:
        mid = mission["id"][:8]
        depends_on = json.loads(mission.get("depends_on", "[]") or "[]")

        for dep_id in depends_on:
            dep_short = dep_id[:8]
            lines.append(f'  {dep_short} --> {mid}')

    return "\n".join(lines)


def _generate_timeline_diagram(missions: List[dict]) -> str:
    """Generate a timeline showing sequential and parallel execution."""
    lines = ["timeline"]
    lines.append('  title Mission Execution Timeline')

    # Group missions by execution level (depth in dependency graph)
    levels = _calculate_mission_levels(missions)

    for level in sorted(levels.keys()):
        level_missions = levels[level]
        level_title = f"Stage {level + 1}"
        lines.append(f"  section {level_title}")

        for mission in level_missions:
            title = mission["title"][:30]
            lines.append(f"    {title}: done, m{mission['id'][:6]}, 0, 1d")

    return "\n".join(lines)


def _generate_critical_path_diagram(missions: List[dict]) -> str:
    """
    Generate a diagram highlighting the critical path
    (longest chain that determines project completion time).
    """
    lines = ["graph TD"]

    # Calculate critical path
    critical_path = _calculate_critical_path(missions)
    critical_ids = {m["id"] for m in critical_path}

    # Build nodes
    for mission in missions:
        mid = mission["id"][:8]
        title = mission["title"][:30]
        status = mission.get("status", "draft")

        # Highlight critical path
        if mission["id"] in critical_ids:
            lines.append(f'  {mid}["{title}<br/>({status})<br/>⚠️ CRITICAL"]')
            lines.append(f'  style {mid} stroke:red,stroke-width:3px,fill:lightyellow')
        else:
            color_map = {
                "draft": "lightgray",
                "ready": "lightyellow",
                "running": "lightblue",
                "completed": "lightgreen",
                "failed": "lightcoral"
            }
            color = color_map.get(status, "white")
            lines.append(f'  {mid}["{title}<br/>({status})" style="fill:{color}"]')

    # Build edges, highlighting critical path
    for mission in missions:
        mid = mission["id"][:8]
        depends_on = json.loads(mission.get("depends_on", "[]") or "[]")

        for dep_id in depends_on:
            dep_short = dep_id[:8]
            if mission["id"] in critical_ids and dep_id in critical_ids:
                lines.append(f'  {dep_short} -->|CRITICAL| {mid}')
            else:
                lines.append(f'  {dep_short} --> {mid}')

    return "\n".join(lines)


def _calculate_mission_levels(missions: List[dict]) -> Dict[int, List[dict]]:
    """
    Calculate execution level for each mission (depth in dependency DAG).
    Missions at the same level can run in parallel.
    """
    mission_map = {m["id"]: m for m in missions}
    levels = {}
    visited = set()

    def get_level(mission_id: str, memo: dict = {}) -> int:
        if mission_id in memo:
            return memo[mission_id]

        mission = mission_map.get(mission_id)
        if not mission:
            return 0

        depends_on = json.loads(mission.get("depends_on", "[]") or "[]")
        if not depends_on:
            level = 0
        else:
            level = max(get_level(dep_id, memo) for dep_id in depends_on) + 1

        memo[mission_id] = level
        return level

    memo = {}
    for mission in missions:
        level = get_level(mission["id"], memo)
        if level not in levels:
            levels[level] = []
        levels[level].append(mission)

    return levels


def _calculate_critical_path(missions: List[dict]) -> List[dict]:
    """
    Calculate the critical path: the longest dependency chain
    that determines minimum project completion time.
    """
    mission_map = {m["id"]: m for m in missions}
    depths = {}

    def get_depth(mission_id: str, memo: dict = {}) -> Tuple[int, List[str]]:
        if mission_id in memo:
            return memo[mission_id]

        mission = mission_map.get(mission_id)
        if not mission:
            return (0, [])

        depends_on = json.loads(mission.get("depends_on", "[]") or "[]")
        if not depends_on:
            result = (1, [mission_id])
        else:
            max_depth = 0
            max_path = []
            for dep_id in depends_on:
                dep_depth, dep_path = get_depth(dep_id, memo)
                if dep_depth > max_depth:
                    max_depth = dep_depth
                    max_path = dep_path

            result = (max_depth + 1, max_path + [mission_id])

        memo[mission_id] = result
        return result

    # Find mission with maximum depth
    max_depth = 0
    critical_path_ids = []

    memo = {}
    for mission in missions:
        depth, path = get_depth(mission["id"], memo)
        if depth > max_depth:
            max_depth = depth
            critical_path_ids = path

    return [mission_map[mid] for mid in critical_path_ids if mid in mission_map]


async def generate_project_summary_diagram(project_id: str) -> str:
    """Generate a high-level project summary diagram."""
    db = await get_db()

    project_rows = await db.execute_fetchall(
        "SELECT * FROM projects WHERE id = ?",
        (project_id,)
    )
    project = dict(project_rows[0]) if project_rows else {}

    missions = await db.execute_fetchall(
        "SELECT * FROM missions WHERE project_id = ?",
        (project_id,)
    )
    missions = [dict(row) for row in missions]

    sessions = await db.execute_fetchall("""
        SELECT COUNT(*) as count, status FROM agent_sessions
        WHERE mission_id IN (SELECT id FROM missions WHERE project_id = ?)
        GROUP BY status
    """, (project_id,))

    await db.close()

    status_counts = {dict(row)["status"]: dict(row)["count"] for row in sessions}

    lines = [
        "graph LR",
        f'  A["{project.get("name", "Project")}"]',
        f'  B["📊 {len(missions)} Missions<br/>"]',
        f'  C["✅ {status_counts.get("completed", 0)} Completed<br/>"]',
        f'  D["⏳ {status_counts.get("running", 0)} Running<br/>"]',
        f'  E["❌ {status_counts.get("failed", 0)} Failed<br/>"]',
        "  A --> B",
        "  B --> C",
        "  B --> D",
        "  B --> E"
    ]

    return "\n".join(lines)
