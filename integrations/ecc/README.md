# DevFleet Skill for Claude Code (ECC)

Use Claude DevFleet as a multi-agent backend from Claude Code. Plan projects, dispatch agents, and monitor missions — all from your terminal.

## How It Works

```mermaid
sequenceDiagram
    participant U as User
    participant C as Claude Code
    participant D as DevFleet MCP
    participant A1 as Agent 1 (Worktree)
    participant A2 as Agent 2 (Worktree)

    U->>C: "Build a REST API with auth and tests"
    C->>D: plan_project(prompt)
    D-->>C: project_id + mission list (with depends_on DAG)
    C->>U: Confirm plan (missions + dependencies)
    U->>C: Approved
    C->>D: dispatch_mission(mission_id=M1)
    D->>A1: Spawn agent in isolated git worktree
    A1-->>D: Mission M1 complete → auto-merge
    D->>A2: Auto-dispatch M2 (depends_on M1 resolved)
    A2-->>D: Mission M2 complete → auto-merge
    C->>D: get_report(mission_id=M2)
    D-->>C: files_changed, what_done, errors, next_steps
    C-->>U: Summary of completed work
```

## Prerequisites

- Claude DevFleet API running (default: `http://localhost:18801`)
- Claude Code (CLI) installed

## Step 1: Add DevFleet as an MCP Server

DevFleet exposes an MCP server via Streamable HTTP at `/mcp`. Add it to your Claude Code configuration.

### Option A: Project-level (recommended)

Add to `.claude/settings.json` in your project:

```json
{
  "mcpServers": {
    "devfleet": {
      "type": "http",
      "url": "http://localhost:18801/mcp"
    }
  }
}
```

### Option B: User-level

Add to `~/.claude/settings.json` to make DevFleet available in all projects:

```json
{
  "mcpServers": {
    "devfleet": {
      "type": "http",
      "url": "http://localhost:18801/mcp"
    }
  }
}
```

### Option C: CLI flag

```bash
claude mcp add devfleet --transport http http://localhost:18801/mcp
```

## Step 2: Install the Skill

Copy the skill file into your Claude Code commands directory:

```bash
# Project-level (available in this project only)
mkdir -p .claude/commands
cp integrations/ecc/devfleet.md .claude/commands/devfleet.md

# User-level (available in all projects)
mkdir -p ~/.claude/commands
cp integrations/ecc/devfleet.md ~/.claude/commands/devfleet.md
```

## Step 3: Verify

Start Claude Code and confirm DevFleet tools are available:

```bash
claude
```

Then try:

```
/devfleet Build a CLI todo app in Python with SQLite storage and tests
```

Or use the tools directly in conversation:

```
Use devfleet to plan a project: "REST API with user auth and rate limiting"
```

## Example Usage

### Plan and launch a project

```
> /devfleet Create a markdown blog engine with static site generation

Claude will:
1. Call plan_project to break it into missions
2. Show you the plan (missions, dependencies)
3. Dispatch the first mission to start the chain
4. Report back with project ID and status
```

### Check on running work

```
> What's running in DevFleet right now?

Claude calls get_dashboard and summarizes active agents, slot usage, and recent completions.
```

### Get a report

```
> Show me the report for mission abc-123

Claude calls get_report and presents the structured results: what was done, files changed, what was tested, next steps.
```

## Troubleshooting

**"Connection refused" errors**: Make sure the DevFleet API is running on port 18801. Check with:
```bash
curl http://localhost:18801/api/dashboard
```

**Tools not appearing**: Restart Claude Code after adding the MCP server config. Check that the SSE endpoint is reachable.

**Agent slots full**: DevFleet defaults to 3 concurrent agents. Check `get_dashboard` for slot usage. Wait for running missions to complete or cancel one with `cancel_mission`.
