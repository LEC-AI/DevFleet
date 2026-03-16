# DevFleet MCP Server for Cursor

Use Claude DevFleet as a multi-agent backend from Cursor. Dispatch coding agents, plan projects, and read mission reports through Cursor's MCP integration.

## Prerequisites

- Claude DevFleet API running (default: `http://localhost:18801`)
- Cursor with MCP support enabled

## Setup

### Step 1: Open Cursor MCP Settings

1. Open Cursor Settings (`Cmd+,` on macOS, `Ctrl+,` on Windows/Linux).
2. Navigate to **Features** > **MCP Servers**.
3. Click **Add new MCP server**.

### Step 2: Add DevFleet

Configure the server with these values:

- **Name**: `devfleet`
- **Type**: `http`
- **URL**: `http://localhost:18801/mcp`

Alternatively, add it directly to your project's `.cursor/mcp.json`:

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

Or to your global Cursor config at `~/.cursor/mcp.json` for access in all projects.

### Step 3: Verify

After adding the server, Cursor should show the DevFleet tools in its MCP tool list. You can verify by asking Cursor's AI:

```
List the available DevFleet tools
```

## Available Tools

| Tool | Description |
|------|-------------|
| `plan_project` | Break a natural language prompt into a project with chained missions |
| `create_project` | Create a project manually |
| `create_mission` | Create a mission with dependencies and auto-dispatch |
| `dispatch_mission` | Start an agent on a mission |
| `get_mission_status` | Check mission status and session details |
| `get_report` | Read the structured report from a completed mission |
| `list_projects` | List all projects |
| `list_missions` | List missions in a project (filterable by status) |
| `cancel_mission` | Cancel a running mission |
| `wait_for_mission` | Block until a mission completes (with timeout) |
| `get_dashboard` | Overview of running agents, slots, and recent activity |

## Example Prompts

### Plan and dispatch

```
Use DevFleet to plan a project: "Build a FastAPI microservice with PostgreSQL,
JWT auth, and comprehensive tests". Then dispatch the first mission.
```

### Monitor progress

```
Show me the DevFleet dashboard. What agents are running?
```

### Read results

```
Get the report for DevFleet mission <paste-mission-id-here>
```

## Docker / Remote Access

If DevFleet runs in Docker or on a remote host, update the URL accordingly:

```json
{
  "mcpServers": {
    "devfleet": {
      "type": "http",
      "url": "http://<host>:<port>/mcp"
    }
  }
}
```

The default Docker Compose setup exposes the API on port `18801`.

## Troubleshooting

**Server not connecting**: Confirm the DevFleet API is reachable:
```bash
curl http://localhost:18801/api/dashboard
```

**Tools not showing up**: Restart Cursor after adding the MCP server. Check the MCP Servers panel in settings for connection status.

**"Agent slots full"**: DevFleet defaults to 3 concurrent agents. Use `get_dashboard` to check slot usage. Wait for missions to finish or cancel one with `cancel_mission`.
