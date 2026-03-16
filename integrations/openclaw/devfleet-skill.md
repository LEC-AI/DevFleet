# DevFleet Multi-Agent Orchestration

You have access to a Claude DevFleet instance via MCP tools. DevFleet dispatches multiple Claude Code agents to work on coding tasks in parallel, each in an isolated git worktree.

## Tools Available

- `plan_project(prompt)` — AI breaks a description into a project with chained missions
- `create_project(name, path?, description?)` — Create a project manually
- `create_mission(project_id, title, prompt, depends_on?, auto_dispatch?)` — Add a mission
- `dispatch_mission(mission_id)` — Start an agent on a mission
- `cancel_mission(mission_id)` — Stop a running agent
- `wait_for_mission(mission_id, timeout_seconds?)` — Wait for completion
- `get_mission_status(mission_id)` — Check progress
- `get_report(mission_id)` — Read structured report (what's done, tested, errors, next steps)
- `get_dashboard()` — System overview
- `list_projects()` — Browse projects
- `list_missions(project_id, status?)` — List missions

## Workflow

### Quick: One-prompt project
1. Call `plan_project` with the user's description
2. Call `dispatch_mission` on the first mission (mission with no dependencies)
3. The rest auto-dispatch as dependencies complete
4. Use `wait_for_mission` or `get_mission_status` to track progress
5. Use `get_report` to read results

### Manual: Step-by-step
1. `create_project` to set up the workspace
2. `create_mission` for each task, setting `depends_on` for ordering
3. `dispatch_mission` to start work
4. `get_report` when done

## Guidelines

- Always show the user what was planned before dispatching
- Use `get_dashboard` first to check agent availability (max 3 concurrent)
- After completion, share the report highlights: files changed, what's tested, any errors
- If a mission fails, check `get_report` for error details before retrying
