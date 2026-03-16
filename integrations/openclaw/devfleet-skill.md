# DevFleet Multi-Agent Orchestration

You have access to a running Claude DevFleet instance via MCP tools. DevFleet dispatches multiple Claude Code agents to work on coding tasks in parallel, each in an isolated git worktree.

Use the `mcp__devfleet__*` tools to plan projects, dispatch agents, and monitor their work.

## Tools

| Tool | Usage |
|------|-------|
| `plan_project(prompt)` | AI breaks a description into a project with chained missions |
| `create_project(name, path?, description?)` | Create a project manually |
| `create_mission(project_id, title, prompt, depends_on?, auto_dispatch?)` | Add a mission |
| `dispatch_mission(mission_id, model?, max_turns?)` | Start an agent on a mission |
| `cancel_mission(mission_id)` | Stop a running agent |
| `wait_for_mission(mission_id, timeout_seconds?)` | Block until done (max 1800s) |
| `get_mission_status(mission_id)` | Check progress |
| `get_report(mission_id)` | Structured report: files_changed, what_done, what_tested, errors, next_steps |
| `get_dashboard()` | System overview: running agents, stats, recent activity |
| `list_projects()` | Browse all projects |
| `list_missions(project_id, status?)` | List missions in a project |

## Workflow: Plan → Dispatch → Report

### Step 1: Plan the project

When the user describes something to build, call:
```
mcp__devfleet__plan_project(prompt="<user's description>")
```
This returns a `project_id` and a list of missions with dependency chains (`depends_on`).

**Always show the plan to the user before dispatching.** Include:
- Project name
- Each mission: number, title, type, what it depends on
- Which mission starts first (the one with empty `depends_on`)

### Step 2: Dispatch the first mission

After the user approves (or says "go ahead"), dispatch the root mission:
```
mcp__devfleet__dispatch_mission(mission_id="<first_mission_id>")
```
The remaining missions auto-dispatch as their dependencies complete. You do not need to dispatch them manually.

### Step 3: Monitor progress

Check what's running:
```
mcp__devfleet__get_dashboard()
```

Check a specific mission:
```
mcp__devfleet__get_mission_status(mission_id="<id>")
```

### Step 4: Wait and report

If you need the result before proceeding:
```
mcp__devfleet__wait_for_mission(mission_id="<id>", timeout_seconds=600)
```

Read the structured report:
```
mcp__devfleet__get_report(mission_id="<id>")
```

Report highlights to the user: files changed, what was done, what's tested, any errors, next steps.

## Patterns

### Full auto: plan and launch
1. `plan_project` → show plan → get approval
2. `dispatch_mission` on root mission (empty `depends_on`)
3. Rest auto-dispatches via dependency chain
4. `get_dashboard` to monitor
5. `get_report` on final mission when done

### Add to existing project
1. `list_projects` to find the project
2. `list_missions(project_id)` to see existing missions
3. `create_mission` with `depends_on` pointing to prerequisite missions and `auto_dispatch=true`
4. Mission starts automatically when deps are met

### Sequential with review
1. `create_mission` for implementation
2. `dispatch_mission` → `wait_for_mission`
3. `get_report` → review results
4. `create_mission` for test/review with `depends_on=[first_mission]` and `auto_dispatch=true`

## Guidelines

- **Always confirm the plan** before dispatching, unless the user said "go ahead"
- **Include mission titles and IDs** when reporting status so the user can reference them
- **If a mission fails**, read `get_report` for error details before retrying
- **Max 3 concurrent agents** — check `get_dashboard` for slot availability before bulk dispatching
- **Dependencies form a DAG** — never create circular dependencies
- **Each agent auto-merges** its worktree branch on completion
