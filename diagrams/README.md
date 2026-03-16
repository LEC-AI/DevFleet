# DevFleet Architecture Diagrams

Visual documentation of the DevFleet platform architecture and its evolution from CLI subprocess spawning to an autonomous multi-agent platform.

> **Tip:** Open the `.html` files locally in a browser for styled, interactive versions of these diagrams.

---

## Architecture Evolution

From CLI subprocess to autonomous multi-agent platform across 4 phases.

```mermaid
graph TD
    subgraph Phase0["Phase 0 -- Foundation (CLI Subprocess)"]
        P0_UI["React UI\nSSE live output"]
        P0_API["FastAPI\nRoutes + dispatch"]
        P0_CLI["CLI Subprocess\nclaude --output-format stream-json"]
        P0_Parse["Stream Parser\nstdout to SSE events"]
        P0_State["In-Memory State\nrunning_tasks dict"]
        P0_DB["SQLite\nmissions, sessions"]

        P0_UI -->|"HTTP/SSE"| P0_API
        P0_API -->|"spawn"| P0_CLI
        P0_CLI -->|"stdout"| P0_Parse
        P0_Parse -->|"broadcast"| P0_State
        P0_State -->|"persist"| P0_DB
    end

    subgraph Phase1["Phase 1 -- SDK Migration"]
        P1_SDK["Claude Code SDK\nPython API"]
        P1_Stream["Structured Messages\nTextBlock, ToolUseBlock, ResultBlock"]
        P1_Conv["Conversation Persistence\nconversations table"]
        P1_Cost["Cost Tracking\nReal-time token + USD"]
        P1_Resume["Session Resume\nFull context preserved"]

        P1_SDK -->|"async iterator"| P1_Stream
        P1_Stream -->|"save"| P1_Conv
        P1_SDK -->|"result.usage"| P1_Cost
        P1_Conv -->|"reload"| P1_Resume
    end

    subgraph Phase2["Phase 2 -- MCP Ecosystem"]
        P2_Ctx["Context Server\ndevfleet-context (stdio)"]
        P2_Tools["Tools Server\ndevfleet-tools (stdio)"]
        P2_Proj["Per-Project MCP\nmcp_configs table"]
        P2_Report["Report Pickup\nFile-based JSON handoff"]

        P2_Ctx -->|"5 context tools"| P2_Agent["Agent"]
        P2_Tools -->|"5 self-service tools"| P2_Agent
        P2_Proj -->|"custom servers"| P2_Agent
        P2_Agent -->|"submit_report"| P2_Report
    end

    subgraph Phase3["Phase 3 -- Autonomous Multi-Agent"]
        P3_Watcher["Mission Watcher\npolls every 5s, checks deps"]
        P3_Sched["Scheduler\nCron-based, template cloning"]
        P3_AutoLoop["Auto-Loop\nParallel plan then dispatch cycle"]
        P3_SubM["Sub-Missions\nAgent-created, auto-dispatched"]
        P3_Deps["Dependency Graph\ndepends_on + json_each()"]

        P3_Watcher -->|"auto-dispatch"| P3_Agents["Agent Pool"]
        P3_Sched -->|"clone + dispatch"| P3_Watcher
        P3_AutoLoop -->|"plan tasks"| P3_Watcher
        P3_SubM -->|"create"| P3_Deps
        P3_Deps -->|"satisfied?"| P3_Watcher
    end

    Phase0 -->|"replace CLI with SDK"| Phase1
    Phase1 -->|"add stdio MCP servers"| Phase2
    Phase2 -->|"add orchestration layer"| Phase3
```

---

## Current State to Target Architecture

High-level overview of the evolution plan.

```mermaid
graph TD
    subgraph Current["Current -- CLI Subprocess Model"]
        C_UI["React UI\nSSE streaming, dispatch panel"]
        C_API["FastAPI\napp.py, routes, in-memory state"]
        C_DISP["Dispatcher\nsubprocess.spawn, stream-json parse"]
        C_CLI["Claude CLI\n--output-format stream-json"]
        C_WT["Worktree\ngit isolation per agent"]
        C_DB["SQLite\nmissions, sessions, reports"]
        C_AL["Auto-Loop\nplan then dispatch then repeat"]
    end

    subgraph Phase1["Phase 1 -- Agent SDK Core"]
        P1_SDK["Agent SDK Engine\nPython API, native streaming"]
        P1_CONV["Conversation Store\nmessage history, resume state"]
        P1_STRUCT["Structured Output\ntool-based reports, JSON schema"]
        P1_HOOKS["Hooks System\npre/post tool, safety gates"]
        P1_SUB["Custom Subagents\nimplement, review, test, fix"]
    end

    subgraph Phase2["Phase 2 -- MCP Ecosystem"]
        P2_CTX["Context Model MCP\ndefault server for all agents"]
        P2_SELF["DevFleet-as-MCP\nexpose missions, reports, status"]
        P2_STACK["MCP Tool Stack\nGitHub, Brave, Notion, Memory"]
        P2_RESUME["Session Continuity\nMCP-backed resume with context"]
    end

    subgraph Phase3["Phase 3 -- Autonomous Platform"]
        P3_TEAMS["Agent Teams\nparallel workers, coordinator"]
        P3_SCHED["Scheduled Agents\ncron, recurring missions"]
        P3_MULTI["Multi-Phase Missions\nplan then implement then review then test"]
        P3_VALID["Output Validation\nschema enforce, quality gates"]
    end

    Current -->|"migrate"| Phase1
    Phase1 -->|"extend"| Phase2
    Phase2 -->|"orchestrate"| Phase3
```

---

## Phase 1 -- SDK Engine Detail

API layer, SDK engine internals, persistence, and mission-type subagents.

```mermaid
graph TD
    subgraph APILayer["API Layer"]
        Routes["FastAPI Routes\ndispatch, resume, cancel"]
        WS["WebSocket\nbidirectional streaming"]
    end

    subgraph SDKEngine["SDK Engine -- replaces dispatcher.py"]
        AgentLoop["Agent Loop\nclaude_agent_sdk.create_agent"]
        ToolReg["Tool Registry\ncustom tools per mission type"]
        HooksMgr["Hooks Manager\npre_tool, post_tool, on_error"]
        ReportTool["submit_report Tool\nstructured JSON, replaces text markers"]
        CostTrack["Cost Tracker\ntoken counting, budget enforcement"]
    end

    subgraph Persistence["Persistence Layer"]
        ConvoDB["Conversations Table\nrole, content, tool_calls"]
        SessionDB["Sessions Table\n+ sdk_thread_id, hook_config"]
        ToolConfDB["Tool Configs Table\nper-project tool definitions"]
    end

    subgraph Subagents["Mission-Type Subagents"]
        Implement["Implement Agent\nfull tools, write access"]
        Review["Review Agent\nread-only, Bash restricted"]
        Test["Test Agent\nBash + test runners only"]
        Fix["Fix Agent\ntargeted edit, test, verify"]
        Explore["Explore Agent\nread + search only"]
    end

    Routes -->|"dispatch"| AgentLoop
    WS -->|"stream events"| AgentLoop
    AgentLoop --> ToolReg
    AgentLoop --> HooksMgr
    AgentLoop --> ReportTool
    AgentLoop --> CostTrack
    AgentLoop -->|"spawn"| Subagents
    ReportTool -->|"persist"| ConvoDB
    AgentLoop -->|"save state"| SessionDB
    ToolReg -->|"load config"| ToolConfDB
```

---

## Phase 2 -- MCP Ecosystem Detail

Context server, DevFleet-as-MCP, and external MCP integrations.

```mermaid
graph TD
    subgraph Agent["Running Agent"]
        SDK["Agent SDK Loop"]
    end

    subgraph DefaultMCP["Context Model MCP -- Auto-Attached"]
        ProjCtx["Project Context\ncodebase structure, conventions"]
        MissionCtx["Mission Context\nrequirements, acceptance criteria"]
        HistoryCtx["Session History\npast reports, decisions, learnings"]
        TeamCtx["Team Context\nother agents progress, blockers"]
    end

    subgraph DevFleetMCP["DevFleet-as-MCP Server"]
        CreateMission["create_mission\nagents can spawn sub-missions"]
        ReadReport["read_report\nquery past session reports"]
        UpdateStatus["update_status\nreal-time progress updates"]
        RequestReview["request_review\ntrigger review agent on work"]
    end

    subgraph ExternalMCP["External MCP Stack"]
        GH["GitHub MCP\nPRs, issues, code search"]
        Brave["Brave Search MCP\nweb research, docs lookup"]
        Memory["Memory MCP\npersistent knowledge graph"]
        Notion["Notion MCP\nproject docs, wikis"]
    end

    SDK -->|"always connected"| DefaultMCP
    SDK -->|"self-service"| DevFleetMCP
    SDK -->|"configured per project"| ExternalMCP
    CreateMission -->|"dispatch"| Agent
    HistoryCtx -->|"resume context"| SDK
```

---

## Phase 3 -- Autonomous Multi-Agent Detail

Scheduler, mission coordination, parallel agent teams, and output validation.

```mermaid
graph TD
    subgraph Scheduler["Scheduler"]
        Cron["Cron Engine\nrecurring missions, intervals"]
        Trigger["Event Triggers\non PR, on push, on incident"]
    end

    subgraph Coordinator["Mission Coordinator"]
        Planner["Planner Agent\nSDK-based, structured plan output"]
        Orchestrator["Orchestrator\nphase sequencing, dependency graph"]
        QualityGate["Quality Gate\ntests pass, review approved, schema valid"]
    end

    subgraph TeamExec["Agent Team Execution"]
        W1["Worker 1\nimplement feature A"]
        W2["Worker 2\nimplement feature B"]
        W3["Test Worker\nparallel test suite"]
        R1["Review Worker\ncode review all changes"]
    end

    subgraph Validation["Output Validation"]
        Schema["JSON Schema\nreport structure enforcement"]
        Lint["Lint and Build\nautomated quality checks"]
        Merge["Auto-Merge\nworktree to main on pass"]
    end

    Scheduler -->|"trigger"| Coordinator
    Planner -->|"plan phases"| Orchestrator
    Orchestrator -->|"dispatch parallel"| W1 & W2
    Orchestrator -->|"then"| W3
    W3 -->|"then"| R1
    W1 & W2 & W3 & R1 -->|"submit"| QualityGate
    QualityGate -->|"validate"| Validation
    Schema --> Lint --> Merge
```

---

## Files

| File | Description |
|------|-------------|
| [`devfleet-architecture-evolution.html`](devfleet-architecture-evolution.html) | Styled single-page architecture evolution diagram (open in browser) |
| [`devfleet-evolution-plan.html`](devfleet-evolution-plan.html) | Multi-section roadmap with 4 detailed phase diagrams (open in browser) |
