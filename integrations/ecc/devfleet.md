---
name: devfleet
description: Orchestrate multi-agent coding tasks via Claude DevFleet
---

# DevFleet Orchestration

You have access to a running Claude DevFleet instance via MCP tools. DevFleet is a multi-agent coding platform that dispatches Claude Code agents to work on missions (coding tasks). Each agent runs in an isolated git worktree.

Use the `mcp__devfleet__*` tools to plan projects, dispatch agents, and monitor their work.

## Core Workflow

### 1. Plan a project from natural language

When the user describes something to build, use `plan_project` to break it into missions with dependencies:

```
mcp__devfleet__plan_project(prompt="Build a REST API with auth, database, and tests")
```

This returns a project ID and a list of missions with dependency chains. The first mission has no dependencies; subsequent missions auto-dispatch as their dependencies complete.

After planning, dispatch the first mission (the one with no `depends_on`) to kick off the chain.

### 2. Dispatch a mission

```
mcp__devfleet__dispatch_mission(mission_id="<id>")
```

Optional overrides: `model` (e.g., "claude-sonnet-4-20250514"), `max_turns` (integer).

The agent runs asynchronously. You do not need to wait for it.

### 3. Check status

Check a single mission:
```
mcp__devfleet__get_mission_status(mission_id="<id>")
```

Get an overview of all DevFleet activity:
```
mcp__devfleet__get_dashboard()
```

The dashboard shows running agents, agent slot usage, mission stats by status, and recent completions.

### 4. Wait for completion

If you need the result before proceeding, block until the mission finishes:

```
mcp__devfleet__wait_for_mission(mission_id="<id>", timeout_seconds=600)
```

Returns the final status and report when done. Default timeout is 600 seconds (10 minutes), max is 1800 seconds (30 minutes).

### 5. Read reports

After a mission completes, read the structured agent report:

```
mcp__devfleet__get_report(mission_id="<id>")
```

Reports contain: `files_changed`, `what_done`, `what_open`, `what_tested`, `what_untested`, `next_steps`, `errors_encountered`.

### 6. Create individual missions

For fine-grained control, create missions manually instead of using the planner:

```
mcp__devfleet__create_mission(
  project_id="<id>",
  title="Add JWT authentication",
  prompt="Implement JWT auth middleware...",
  acceptance_criteria="All /api routes require valid token",
  depends_on=["<other-mission-id>"],
  auto_dispatch=true,
  priority=1
)
```

Set `auto_dispatch=true` so the mission starts automatically when its `depends_on` missions complete.

### 7. Cancel a mission

```
mcp__devfleet__cancel_mission(mission_id="<id>")
```

Stops the running agent and marks the mission as failed.

## Additional tools

- `mcp__devfleet__list_projects()` -- List all projects.
- `mcp__devfleet__list_missions(project_id="<id>")` -- List missions in a project. Optional `status` filter: `draft`, `running`, `completed`, `failed`.
- `mcp__devfleet__create_project(name="My Project")` -- Create a project manually (plan_project does this automatically).

## Patterns

### Full auto: plan and launch

1. `plan_project` with the user's description.
2. Dispatch the first mission (the one with empty `depends_on`).
3. The rest auto-dispatch as dependencies resolve. Report back to the user with the project ID and mission count.

### Monitor and report

1. Call `get_dashboard` to see what is running.
2. For each running or completed mission of interest, call `get_mission_status`.
3. For completed missions, call `get_report` to summarize what was done.

### Sequential with review

1. `create_mission` for the implementation task.
2. `dispatch_mission` to start it.
3. `wait_for_mission` to block until done.
4. `get_report` to read results.
5. `create_mission` for a review task with `depends_on` set to the first mission and `auto_dispatch=true`.

## Guidelines

- Always confirm the plan with the user before dispatching missions, unless they said to go ahead.
- When reporting status, include mission titles and IDs so the user can reference them.
- If a mission fails, read its report to understand what went wrong before retrying.
- DevFleet runs up to 3 agents concurrently by default. Check `get_dashboard` for slot availability before bulk dispatching.
- Mission dependencies form a DAG. Do not create circular dependencies.
