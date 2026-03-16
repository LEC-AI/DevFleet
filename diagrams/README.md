# DevFleet Architecture Diagrams

Visual documentation of the DevFleet platform architecture.

> **Tip:** Open the `.html` files locally in a browser for styled, interactive versions of these diagrams.

---

## System Overview

```mermaid
graph TD
    subgraph UI["Claude DevFleet UI :3101"]
        Web["React 19 + Vite"]
    end

    subgraph API["Claude DevFleet API :18801"]
        FastAPI["FastAPI + SQLite"]
    end

    subgraph Services["Background Services"]
        SDK["SDK Engine"]
        Watcher["Mission Watcher"]
        Sched["Scheduler"]
        AutoLoop["Auto-Loop"]
        Remote["Remote Control"]
    end

    subgraph Agents["Agent Pool (max 3)"]
        A1["Agent"] --> MCP1["MCP Servers"]
        A2["Agent"] --> MCP2["MCP Servers"]
        A3["Agent"] --> MCP3["MCP Servers"]
    end

    Web -->|"HTTP"| FastAPI
    FastAPI --> SDK
    FastAPI --> Watcher
    FastAPI --> Sched
    FastAPI --> AutoLoop
    FastAPI --> Remote
    SDK -->|"dispatch"| A1 & A2 & A3
    Watcher -->|"auto-dispatch on dependency satisfaction"| SDK
    Sched -->|"cron clone then dispatch"| Watcher
    AutoLoop -->|"plan then parallel dispatch"| SDK
    MCP1 -->|"create_sub_mission"| Watcher
```

---

## MCP Ecosystem

Two stdio MCP servers auto-attached to every agent, plus per-project external servers.

```mermaid
graph TD
    subgraph Agent["Running Agent"]
        SDK["Claude Code SDK Loop"]
    end

    subgraph ContextMCP["devfleet-context -- Auto-Attached"]
        ProjCtx["get_project_context"]
        MissionCtx["get_mission_context"]
        HistoryCtx["get_session_history"]
        TeamCtx["get_team_context"]
        PastReports["read_past_reports"]
    end

    subgraph ToolsMCP["devfleet-tools -- Auto-Attached"]
        SubmitReport["submit_report"]
        CreateSub["create_sub_mission"]
        RequestReview["request_review"]
        SubStatus["get_sub_mission_status"]
        ListMissions["list_project_missions"]
    end

    subgraph ExternalMCP["Per-Project MCP Configs"]
        GH["GitHub"]
        Brave["Brave Search"]
        Custom["Custom Servers"]
    end

    SDK -->|"always connected"| ContextMCP
    SDK -->|"always connected"| ToolsMCP
    SDK -->|"configured per project"| ExternalMCP
    CreateSub -->|"auto-dispatch"| Agent
```

---

## Multi-Agent Orchestration

Mission dependencies, scheduling, and autonomous dispatch flow.

```mermaid
graph TD
    subgraph Scheduler["Scheduler"]
        Cron["Cron Engine\nrecurring missions, intervals"]
    end

    subgraph Coordinator["Mission Coordinator"]
        Planner["Planner\nnatural language to chained missions"]
        Watcher["Mission Watcher\npolls every 5s, checks depends_on"]
        AutoLoop["Auto-Loop\nparallel-aware plan then dispatch"]
    end

    subgraph AgentPool["Agent Pool (max 3)"]
        W1["Agent 1"]
        W2["Agent 2"]
        W3["Agent 3"]
    end

    subgraph Outputs["Outputs"]
        Reports["Structured Reports\nfiles changed, what done, next steps"]
        SubMissions["Sub-Missions\ncreated by agents, auto-dispatched"]
    end

    Cron -->|"clone template"| Watcher
    Planner -->|"create missions with depends_on"| Watcher
    AutoLoop -->|"plan + dispatch"| W1 & W2 & W3
    Watcher -->|"deps satisfied, dispatch"| W1 & W2 & W3
    W1 & W2 & W3 -->|"submit_report"| Reports
    W1 & W2 & W3 -->|"create_sub_mission"| SubMissions
    SubMissions -->|"auto-dispatch"| Watcher
```

---

## DevFleet-as-MCP Server

External agents (Claude Code, Cursor, Windsurf) integrate via Streamable HTTP or SSE.

```mermaid
graph LR
    subgraph Clients["External Agents"]
        CC["Claude Code"]
        Cursor["Cursor"]
        Wind["Windsurf"]
    end

    subgraph DevFleetMCP["DevFleet MCP Server"]
        Plan["plan_project"]
        Create["create_project / create_mission"]
        Dispatch["dispatch_mission"]
        Status["get_mission_status / get_report"]
        Wait["wait_for_mission"]
        Dashboard["get_dashboard"]
        Cancel["cancel_mission"]
        List["list_projects / list_missions"]
    end

    CC -->|"Streamable HTTP :18801/mcp"| DevFleetMCP
    Cursor -->|"Streamable HTTP :18801/mcp"| DevFleetMCP
    Wind -->|"SSE :18801/mcp/sse"| DevFleetMCP
```

---

## Files

| File | Description |
|------|-------------|
| [`devfleet-architecture-evolution.html`](devfleet-architecture-evolution.html) | Architecture evolution diagram across 4 phases (open in browser) |
| [`devfleet-evolution-plan.html`](devfleet-evolution-plan.html) | Detailed roadmap with phase breakdowns (open in browser) |
