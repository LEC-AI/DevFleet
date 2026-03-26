# DevFleet Intelligence Features

## Overview

The Intelligence module adds AI-powered project analysis, planning, visualization, and optimization capabilities to DevFleet. Developers can now understand their projects better, plan missions intelligently, and make data-driven decisions about resource allocation.

## Features

### 1. **Intelligent Project Planner** (`/api/plan-intelligent`)

Enhanced version of the basic planner using **extended thinking** (reasoning tokens) for better mission breakdown.

**What it does:**
- Uses Claude's extended thinking to reason deeply about project structure
- Suggests optimal mission ordering and parallelization opportunities
- Estimates complexity and time for each mission
- Identifies critical path (longest dependency chain)
- Suggests which missions can run in parallel

**Endpoint:**
```
POST /api/plan-intelligent
{
  "prompt": "Build a task management REST API with Node.js",
  "project_path": "/path/to/project" // optional
}
```

**Response includes:**
- Project metadata
- Mission list with estimated hours and complexity
- Analysis: estimated_total_hours, can_parallelize, critical_path_length

**Use case:** When you have a complex project and want smarter mission breaking

---

### 2. **Project Analyzer** (`/api/projects/{pid}/analyze`)

Vision-based project understanding. Analyzes code structure, architecture diagrams, screenshots, and documentation.

**What it does:**
- Reads project files, READMEs, architecture diagrams
- Uses Claude vision to understand project structure
- Identifies tech stack, key components, testing status
- Detects tech debt and bottlenecks
- Suggests targeted missions to address issues

**Endpoint:**
```
POST /api/projects/{pid}/analyze
{
  "files": ["README.md", "ARCHITECTURE.md", "diagram.png"], // optional
  "custom_prompt": "Focus on performance optimization"  // optional
}
```

**Response includes:**
- Project type and tech stack
- Architecture summary
- Testing/documentation assessment
- Identified issues and tech debt
- Suggested missions with priorities

**Use case:** Understand what a project needs and what to work on next

---

### 3. **Project Health Dashboard** (`/api/projects/{pid}/health`)

Real-time analytics and insights on project execution performance.

**What it does:**
- Analyzes all missions and sessions in the project
- Calculates success rates and cost metrics
- Breaks down costs by mission type and model
- Identifies bottlenecks (expensive types, low success rates, blocking dependencies)
- Generates actionable recommendations

**Endpoint:**
```
GET /api/projects/{pid}/health
```

**Response includes:**
- Mission stats: total, by status, by type, by priority
- Session stats: success rate, total cost, avg cost per session, cost by model
- Bottlenecks: high-cost missions, low success rates, blocking dependencies
- Recommendations: cost optimization, parallelization, mission breaking

**Use case:** Get a bird's eye view of project health and where to improve

---

### 4. **Mission Dependency Visualizer** (`/api/projects/{pid}/missions/graph`)

Generates Mermaid diagrams of mission structure and execution flow.

**Diagram types:**
- **dag** (default): Directed acyclic graph showing dependencies
- **timeline**: Sequential execution stages with parallel opportunities
- **critical_path**: Highlights the critical path that determines completion time

**Endpoint:**
```
GET /api/projects/{pid}/missions/graph?diagram_type=dag
```

Response returns Mermaid diagram markdown ready to render.

**Example use in markdown:**
````markdown
```mermaid
GET /api/projects/{pid}/missions/graph?diagram_type=dag
```
````

**Use case:** Visualize project flow, identify parallelization opportunities, understand dependencies

---

### 5. **Project Summary Diagram** (`/api/projects/{pid}/missions/summary-diagram`)

High-level project overview showing mission count and status distribution.

**Endpoint:**
```
GET /api/projects/{pid}/missions/summary-diagram
```

**Use case:** Quick visual check of project progress for dashboards

---

### 6. **Cost Optimizer** (`/api/projects/{pid}/costs`)

Batch analysis of spending patterns and optimization opportunities.

**What it does:**
- Analyzes spending by mission type and model
- Identifies expensive mission types
- Suggests model downgrades (Sonnet vs Opus)
- Recommends parallelization to reduce sequential costs
- Estimates potential savings

**Endpoint:**
```
GET /api/projects/{pid}/costs
```

**Response includes:**
- Current spending metrics: total, avg per session, token counts
- Cost breakdown by mission type
- Cost breakdown by model
- Optimization opportunities with estimated savings
- Actionable recommendations

**Sample opportunities:**
- "Switch {mission_type} from Opus to Sonnet → save $X"
- "Parallelize {mission_type} ({N} sequential sessions → save $X)"
- "Break large missions into smaller tasks → save $X"

**Use case:** Keep project costs under control and optimize spending

---

## Technical Details

### Architecture

```
Intelligence Module
├── planner_v2.py         → Enhanced planner (extended thinking)
├── project_analyzer.py   → Vision-based analysis
├── health_metrics.py     → Analytics & bottleneck detection
├── visualizer.py         → Mermaid diagram generation
├── cost_optimizer.py     → Cost analysis & recommendations
└── app.py (new routes)   → FastAPI endpoints
```

### Model Usage

| Feature | Model | Why |
|---------|-------|-----|
| Intelligent Planner | claude-opus-4-6 | Needs deep reasoning for mission breaking |
| Project Analyzer | claude-opus-4-6 | Vision + understanding requires best model |
| Health/Cost/Viz | N/A (local analysis) | Purely algorithmic, no LLM calls |

### Thinking Tokens

The Intelligent Planner uses **extended thinking** (up to 8000 budget tokens) for better reasoning about:
- Mission decomposition
- Dependency ordering
- Parallelization opportunities
- Complexity estimation

---

## Integration with Existing Features

### Auto-dispatch Integration
All missions created by the Intelligent Planner have `auto_dispatch=true` by default, enabling automatic execution as dependencies are met.

### Mission Watcher
Works seamlessly with the existing mission watcher to execute intelligent plans:
```
1. Intelligent Planner breaks down project
2. Creates missions with dependencies in DB
3. Mission Watcher polls and dispatches as dependencies are met
4. Agents execute missions in optimal order
5. Health Dashboard shows progress in real-time
```

### Reports & Sessions
Health Dashboard and Cost Optimizer analyze data from:
- `agent_sessions` table — execution cost, tokens, status
- `reports` table — mission outcomes
- `missions` table — metadata, dependencies
- `mission_events` table — execution history

---

## Example Workflow

### Scenario: New project, need guidance

1. **Create project with intelligent planning:**
   ```bash
   POST /api/plan-intelligent
   {
     "prompt": "Build a customer analytics dashboard with React, Python backend, PostgreSQL"
   }
   ```
   → Generates project + 4 intelligently-broken missions

2. **Analyze the project:**
   ```bash
   POST /api/projects/{pid}/analyze
   {
     "files": ["README.md"],
     "custom_prompt": "What are our biggest gaps?"
   }
   ```
   → Identifies testing gaps, architecture concerns

3. **Visualize the plan:**
   ```bash
   GET /api/projects/{pid}/missions/graph?diagram_type=critical_path
   ```
   → Shows critical path, identifies bottlenecks

4. **Optimize costs before execution:**
   ```bash
   GET /api/projects/{pid}/costs
   ```
   → Suggests Sonnet for test missions, highlights parallelization

5. **Monitor execution:**
   ```bash
   GET /api/projects/{pid}/health
   ```
   → Real-time success rates, costs, recommendations

---

## API Reference

### Request/Response Examples

#### Intelligent Planner
```json
// Request
POST /api/plan-intelligent
{
  "prompt": "Build a REST API for a blogging platform with auth, posts, comments, full CRUD",
  "project_path": "/home/user/blog-api"
}

// Response
{
  "project": {
    "id": "uuid",
    "name": "Blog API",
    "description": "REST API for blogging platform",
    "path": "/home/user/blog-api"
  },
  "missions": [
    {
      "id": "m1",
      "title": "Set up Express server & auth",
      "order": 1,
      "depends_on": [],
      "complexity": "medium",
      "estimated_hours": 2
    },
    {
      "id": "m2",
      "title": "Implement post CRUD endpoints",
      "order": 2,
      "depends_on": ["m1"],
      "complexity": "medium",
      "estimated_hours": 1.5
    }
  ],
  "analysis": {
    "complexity": "medium",
    "estimated_total_hours": 6,
    "can_parallelize": false,
    "critical_path_length": 3
  }
}
```

#### Project Health
```json
// Response
{
  "project_id": "pid",
  "missions": {
    "total": 5,
    "by_status": {"completed": 3, "running": 1, "draft": 1},
    "by_type": {"implement": 3, "test": 2},
    "by_priority": {1: 4, 2: 1}
  },
  "sessions": {
    "total_sessions": 4,
    "total_cost_usd": 24.50,
    "avg_cost_per_session": 6.12,
    "success_rate_percent": 75.0,
    "by_model": {
      "claude-opus-4-6": {
        "count": 3,
        "total_cost": 18.00,
        "avg_cost": 6.00
      }
    }
  },
  "bottlenecks": [
    {
      "type": "high_cost_mission_type",
      "mission_type": "test",
      "avg_cost_usd": 8.50,
      "severity": "medium"
    }
  ],
  "recommendations": [
    "Success rate is 75%. Review failed missions to identify patterns.",
    "test missions cost $8.50 on average. Try using Sonnet for these routine tasks."
  ]
}
```

#### Cost Analysis
```json
// Response
{
  "project_id": "pid",
  "current_spending": {
    "total_usd": 45.23,
    "avg_per_session": 9.04,
    "total_sessions": 5
  },
  "optimization_opportunities": [
    {
      "type": "mission_model_downgrade",
      "mission_type": "test",
      "suggested_model": "claude-sonnet-4-6",
      "potential_savings": 3.40,
      "rationale": "test missions average $2.80. These could use Sonnet."
    },
    {
      "type": "parallelization",
      "mission_type": "implement",
      "session_count": 3,
      "potential_savings": 2.70
    }
  ],
  "estimated_savings_usd": 6.10,
  "savings_percent": 13.5,
  "recommendations": [
    "💰 You could save $6.10 (13.5%) by implementing the recommendations below.",
    "• test missions: Switch from Opus to Sonnet (save $3.40)",
    "• Parallelize implement (3 sequential sessions, save $2.70)"
  ]
}
```

---

## Developer Guide

### Adding Intelligence Features

The modules are designed to be extensible. To add a new intelligence feature:

1. **Create a new module** (e.g., `performance_analyzer.py`)
2. **Implement analysis function** using the DB patterns in health_metrics.py
3. **Add FastAPI endpoint** in app.py following the Intelligence section pattern
4. **Return structured JSON** with insights and recommendations

### Example: Adding a Custom Analyzer
```python
# performance_analyzer.py
async def analyze_performance(project_id: str) -> dict:
    db = await get_db()
    sessions = await db.execute_fetchall(...)
    # Your analysis...
    return {
        "metrics": {...},
        "insights": [...],
        "recommendations": [...]
    }

# In app.py
from performance_analyzer import analyze_performance

@app.get("/api/projects/{pid}/performance")
async def api_performance(pid: str):
    return await analyze_performance(pid)
```

---

## Future Enhancements

Potential additions:
- **Time-series trend analysis** — Cost/success trends over time
- **Agent efficiency ranking** — Which agents complete missions fastest
- **Dependency optimization** — Suggest restructuring for maximum parallelization
- **Predictive analytics** — Estimate project completion time and cost
- **Automated alerts** — Flag cost spikes, low success rates
- **Historical comparisons** — Compare similar project types
- **Team insights** — Cross-project learning and patterns

---

## Troubleshooting

### "Extended thinking not supported"
The planner requires Claude API with thinking support. Ensure you're using a recent `claude-code-sdk` version.

### Diagrams don't render
Mermaid diagrams need markdown rendering. Ensure your client supports Mermaid (GitHub, VS Code, etc.).

### Costs show as $0
The cost tracking depends on session data. Ensure agents have completed at least one mission with cost tracking enabled.

### Analysis missing
Project Analyzer requires file access. Ensure the project path is readable and contains documentation files.

---

## See Also

- **CLAUDE.md** — Main project architecture
- **planner.py** — Basic project planner
- **mission_watcher.py** — Auto-dispatch engine
- **sdk_engine.py** — Mission execution

