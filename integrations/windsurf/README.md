# DevFleet MCP Server for Windsurf

Use Claude DevFleet as a multi-agent backend from Windsurf. Dispatch coding agents, plan projects, and read mission reports through Windsurf's MCP integration.

## Prerequisites

- Claude DevFleet API running (default: `http://localhost:18801`)
- Windsurf (by Codeium) with MCP support enabled

## Setup

### Step 1: Open Windsurf MCP Settings

1. Open Windsurf Settings (`Cmd+,` on macOS, `Ctrl+,` on Windows/Linux).
2. Search for **MCP** in the settings search bar.
3. Click **Add Server** to configure a new MCP server.

### Step 2: Add DevFleet

Add the following to your project's `.windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "devfleet": {
      "type": "http",
      "serverUrl": "http://localhost:18801/mcp"
    }
  }
}
```

Or to your global Windsurf config at `~/.codeium/windsurf/mcp_config.json` for access in all projects.

> **Note**: Some Windsurf versions use `"serverUrl"` while others use `"url"`. If one doesn't work, try the other:
>
> ```json
> {
>   "mcpServers": {
>     "devfleet": {
>       "type": "http",
>       "url": "http://localhost:18801/mcp"
>     }
>   }
> }
> ```

### Step 3: Verify

After adding the server, Windsurf should show the DevFleet tools in its MCP tool list. You can verify by asking Windsurf's AI:

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
      "serverUrl": "http://<host>:<port>/mcp"
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

**Tools not showing up**: Restart Windsurf after adding the MCP server. Check that `mcp_config.json` is valid JSON. Try toggling between `"serverUrl"` and `"url"` if your Windsurf version doesn't recognize one.

**"Agent slots full"**: DevFleet defaults to 3 concurrent agents. Use `get_dashboard` to check slot usage. Wait for missions to finish or cancel one with `cancel_mission`.

**Config file not found**: Ensure the config file is in the correct location. For project-level config, create `.windsurf/mcp_config.json` in your project root. For global config, create `~/.codeium/windsurf/mcp_config.json`.
