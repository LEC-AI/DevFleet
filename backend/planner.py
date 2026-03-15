"""
Project Planner — One-prompt project planning

Takes a natural language description of what to build and uses Claude to:
1. Generate a project name and description
2. Break down the work into sequential/parallel missions with dependencies
3. Create everything in the database, ready to dispatch

Example input: "Build a task management REST API with Node.js, Express,
               in-memory storage, full CRUD, and automated tests"

Output: Project + 3-4 chained missions with depends_on and auto_dispatch set.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone

from db import get_db

log = logging.getLogger("devfleet.planner")

PLANNER_PROMPT = """You are a DevFleet project planner. Given a high-level project description, break it down into a project and a sequence of well-scoped coding missions.

## User's Request
{user_prompt}

## Project Path
{project_path}

## Instructions

Create a project plan with 2-5 missions. Each mission should be:
- Completable by a single AI coding agent in one session (30-60 min of work)
- Specific enough that an agent can work independently
- Properly sequenced — later missions build on earlier ones

Respond in this EXACT JSON format (no markdown, no code fences, just raw JSON):

{{
  "project_name": "Short project name",
  "project_description": "One-line description of what this project does",
  "missions": [
    {{
      "title": "Short mission title",
      "detailed_prompt": "Full detailed prompt for the coding agent. Be specific — mention exact files to create, frameworks to use, endpoints to build, etc. The agent has no other context.",
      "acceptance_criteria": "Bullet list of what defines done. Be concrete — 'server starts on port X', 'GET /endpoint returns 200', etc.",
      "mission_type": "scaffold|implement|feature|test|fix|review",
      "tags": ["tag1", "tag2"],
      "depends_on_index": null,
      "priority": 1
    }},
    {{
      "title": "Second mission that builds on the first",
      "detailed_prompt": "Detailed prompt referencing what the first mission created...",
      "acceptance_criteria": "...",
      "mission_type": "feature",
      "tags": ["tag1"],
      "depends_on_index": 0,
      "priority": 1
    }}
  ]
}}

CRITICAL — keep it concise:
- Each `detailed_prompt` should be 3-6 sentences max. The agent is smart — give clear requirements, not step-by-step tutorials.
- Each `acceptance_criteria` should be 3-5 bullet points max.
- Total JSON response must be under 2000 characters.

Rules:
- `depends_on_index` is the 0-based index of the mission this depends on, or null for the first mission
- A mission can only depend on ONE earlier mission (use the index, not the title)
- The first mission should ALWAYS have `depends_on_index: null`
- Mission types: scaffold (project setup), implement (build features), feature (add a feature), test (write tests), fix (bug fix), review (code review)
- Each detailed_prompt must be self-contained — assume the agent only sees that prompt plus the previous mission's report
- Be specific about technology choices, file paths, port numbers, data structures
- Include validation, error handling, and edge cases in acceptance criteria
- The last mission should ideally be tests or integration verification
"""


async def _call_planner(prompt: str, cwd: str) -> str:
    """Call Claude to generate the project plan."""
    try:
        from claude_code_sdk import query as sdk_query, ClaudeCodeOptions
        from claude_code_sdk.types import TextBlock

        options = ClaudeCodeOptions(
            model="claude-sonnet-4-6",
            permission_mode="bypassPermissions",
            max_turns=1,
            cwd=cwd,
        )

        output_parts = []
        async for message in sdk_query(prompt=prompt, options=options):
            if message is None:
                continue
            if hasattr(message, "content"):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        output_parts.append(block.text)
            elif hasattr(message, "result") and message.result:
                output_parts.append(message.result)

        return "\n".join(output_parts).strip()

    except ImportError:
        import asyncio
        proc = await asyncio.create_subprocess_exec(
            "claude", "-p", prompt, "--output-format", "text",
            "--model", "claude-sonnet-4-6", "--max-turns", "1",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
        stdout, _ = await proc.communicate()
        return stdout.decode().strip()


async def plan_project(user_prompt: str, project_path: str) -> dict:
    """
    Take a natural language prompt, use Claude to plan the project,
    and create everything in the database.

    Returns: {"project": {...}, "missions": [...]}
    """
    # Ensure project path exists
    os.makedirs(project_path, exist_ok=True)

    # Initialize git repo if needed
    git_dir = os.path.join(project_path, ".git")
    if not os.path.exists(git_dir):
        import asyncio
        proc = await asyncio.create_subprocess_exec(
            "git", "init", cwd=project_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()
        # Create initial commit for worktree support
        proc = await asyncio.create_subprocess_exec(
            "git", "commit", "--allow-empty", "-m", "Initial commit",
            cwd=project_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

    # Call Claude planner
    prompt = PLANNER_PROMPT.format(
        user_prompt=user_prompt,
        project_path=project_path,
    )

    log.info("Planning project from prompt: %s", user_prompt[:100])
    output = await _call_planner(prompt, project_path)

    # Parse JSON from output — handle markdown fences, trailing text, etc.
    text = output
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0].strip()
    elif "```" in text:
        text = text.split("```")[1].split("```")[0].strip()

    # Try to extract JSON object even if there's surrounding text
    plan = None
    try:
        plan = json.loads(text)
    except json.JSONDecodeError:
        # Find the first { and try to parse from there
        start = text.find("{")
        if start >= 0:
            # Try progressively shorter substrings to find valid JSON
            for end in range(len(text), start, -1):
                try:
                    plan = json.loads(text[start:end])
                    break
                except json.JSONDecodeError:
                    continue

    if plan is None:
        log.error("Planner returned unparseable output: %s", output[:500])
        raise ValueError(f"Failed to parse planner output. Raw response: {output[:500]}")

    # Validate plan structure
    if "project_name" not in plan or "missions" not in plan:
        raise ValueError(f"Invalid plan structure: missing project_name or missions")

    if not plan["missions"]:
        raise ValueError("Plan has no missions")

    # Create project in DB
    project_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

    conn = await get_db()
    try:
        await conn.execute(
            "INSERT INTO projects (id, name, path, description, created_at) VALUES (?, ?, ?, ?, ?)",
            (project_id, plan["project_name"], project_path, plan.get("project_description", ""), now),
        )

        # Create missions with proper dependency chain
        created_missions = []
        mission_ids = []  # index -> mission_id mapping

        for i, m in enumerate(plan["missions"]):
            mission_id = str(uuid.uuid4())
            mission_ids.append(mission_id)

            # Resolve depends_on_index to actual mission ID
            depends_on_idx = m.get("depends_on_index")
            depends_on = []
            if depends_on_idx is not None and 0 <= depends_on_idx < len(mission_ids) - 1:
                depends_on = [mission_ids[depends_on_idx]]

            # Auto-dispatch all except the first mission
            auto_dispatch = 1 if depends_on else 0

            # Get mission number
            row = await conn.execute(
                "SELECT COALESCE(MAX(mission_number), 0) + 1 FROM missions WHERE project_id = ?",
                (project_id,),
            )
            mission_number = (await row.fetchone())[0]

            tags = json.dumps(m.get("tags", []))

            await conn.execute(
                """INSERT INTO missions
                   (id, project_id, title, detailed_prompt, acceptance_criteria,
                    status, priority, tags, model, mission_type,
                    depends_on, auto_dispatch, mission_number, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, 'draft', ?, ?, 'claude-sonnet-4-6', ?, ?, ?, ?, ?, ?)""",
                (
                    mission_id, project_id,
                    m["title"], m["detailed_prompt"], m.get("acceptance_criteria", ""),
                    m.get("priority", 1), tags,
                    m.get("mission_type", "implement"),
                    json.dumps(depends_on), auto_dispatch, mission_number,
                    now, now,
                ),
            )

            created_missions.append({
                "id": mission_id,
                "mission_number": mission_number,
                "title": m["title"],
                "mission_type": m.get("mission_type", "implement"),
                "depends_on": depends_on,
                "auto_dispatch": bool(auto_dispatch),
            })

        await conn.commit()
    finally:
        await conn.close()

    log.info("Created project '%s' with %d missions", plan["project_name"], len(created_missions))

    return {
        "project": {
            "id": project_id,
            "name": plan["project_name"],
            "path": project_path,
            "description": plan.get("project_description", ""),
        },
        "missions": created_missions,
    }
