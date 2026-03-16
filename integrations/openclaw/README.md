# Claude DevFleet + OpenClaw Integration

Use Claude DevFleet as a multi-agent coding backend from OpenClaw. Dispatch coding missions, plan projects, and orchestrate parallel agents — all from your OpenClaw assistant.

## Setup

### 1. Start Claude DevFleet

```bash
git clone https://github.com/LEC-AI/claude-devfleet.git
cd claude-devfleet
./start.sh
```

### 2. Connect via MCP

OpenClaw supports MCP tool registration. Add DevFleet as an MCP server:

```json
{
  "devfleet": {
    "type": "sse",
    "url": "http://localhost:18801/mcp/sse"
  }
}
```

This gives your OpenClaw agent access to all 11 DevFleet tools.

### 3. Install the Workspace Skill (Optional)

Copy the skill file to your OpenClaw workspace skills directory:

```bash
cp integrations/openclaw/devfleet-skill.md ~/.openclaw/skills/devfleet.md
```

This teaches your OpenClaw agent the best patterns for using DevFleet.

## Available Tools

Once connected, your OpenClaw agent can use:

| Tool | Description |
|------|-------------|
| `plan_project` | Break a natural language description into a project with chained missions |
| `create_project` | Create a project manually |
| `create_mission` | Add a mission with dependencies and auto-dispatch |
| `dispatch_mission` | Send an agent to work on a mission |
| `cancel_mission` | Stop a running agent |
| `wait_for_mission` | Block until a mission completes, return the report |
| `get_mission_status` | Check mission progress |
| `get_report` | Read the structured agent report |
| `get_dashboard` | System overview: running agents, stats, recent activity |
| `list_projects` | Browse all projects |
| `list_missions` | List missions in a project |

## Example Conversations

**Plan and execute a project:**
> "Use DevFleet to build a Python CLI tool that converts CSV to JSON. Plan it, dispatch the first mission, and let me know when it's done."

**Check on running work:**
> "What's happening on DevFleet right now? Show me the dashboard."

**Add a mission to an existing project:**
> "Add a test suite mission to the calculator project on DevFleet, depending on the main implementation mission."

## Architecture

```
OpenClaw Agent
    |
    | (MCP over SSE)
    v
Claude DevFleet API (:18801)
    |
    +-- Plan projects (Claude Sonnet)
    +-- Dispatch agents (Claude Code SDK)
    +-- Monitor progress
    +-- Read reports
    +-- Cancel/wait
```

## Notes

- DevFleet runs agents locally using Claude Code SDK — you need a valid Anthropic API key
- Each agent runs in an isolated git worktree and auto-merges on completion
- Missions can have dependencies — the mission watcher auto-dispatches when deps are met
- Max 3 concurrent agents by default (configurable via `DEVFLEET_MAX_AGENTS`)
