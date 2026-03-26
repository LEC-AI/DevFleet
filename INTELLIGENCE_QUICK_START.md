# Intelligence Features — Quick Start

## What's New

5 new AI-powered features for developers to better see and understand their DevFleet projects:

### 1. **Intelligent Project Planner** 🧠
- **Extended thinking** for smarter mission planning
- Analyzes complexity, suggests parallelization
- Estimates hours and critical path

```bash
curl -X POST http://localhost:18801/api/plan-intelligent \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Build a REST API with Node.js"}'
```

### 2. **Project Analyzer** 👁️
- **Vision-based** understanding of your codebase
- Reads architecture docs, diagrams, code
- Identifies tech debt and suggests missions

```bash
curl -X POST http://localhost:18801/api/projects/{pid}/analyze \
  -H "Content-Type: application/json" \
  -d '{"custom_prompt": "Focus on performance"}'
```

### 3. **Health Dashboard** 📊
- Real-time project metrics
- Cost tracking by mission type & model
- Bottleneck detection & recommendations

```bash
curl http://localhost:18801/api/projects/{pid}/health
```

### 4. **Mission Dependency Visualizer** 📈
- **Mermaid diagrams** of mission flow
- Critical path analysis
- Parallelization opportunities

```bash
# Get dependency DAG
curl "http://localhost:18801/api/projects/{pid}/missions/graph?diagram_type=dag"

# Get execution timeline
curl "http://localhost:18801/api/projects/{pid}/missions/graph?diagram_type=timeline"

# Get critical path
curl "http://localhost:18801/api/projects/{pid}/missions/graph?diagram_type=critical_path"
```

### 5. **Cost Optimizer** 💰
- Batch analysis of all spending
- Model downgrade suggestions (Opus → Sonnet)
- Parallelization opportunities
- Estimated savings

```bash
curl http://localhost:18801/api/projects/{pid}/costs
```

## Architecture

```
NEW MODULES (in backend/):
├── planner_v2.py          → Extended thinking planner
├── project_analyzer.py    → Vision-based analysis
├── health_metrics.py      → Analytics & insights
├── visualizer.py          → Mermaid diagrams
├── cost_optimizer.py      → Spending analysis
└── app.py (updated)       → 5 new endpoints
```

## Quick Integration

All features are already wired into `app.py`. Just restart the backend:

```bash
cd backend
uvicorn app:app --reload
```

Visit the endpoints above with your project IDs.

## Features at a Glance

| Feature | Use Case | Key Benefit |
|---------|----------|-------------|
| Intelligent Planner | New complex projects | Smarter mission breaking, parallelization suggestions |
| Project Analyzer | Understand what to work on | Vision-based project insights + tech debt detection |
| Health Dashboard | Track project health | Real-time success rates, costs, bottlenecks |
| Visualizer | See the big picture | Mermaid diagrams of mission flow & critical path |
| Cost Optimizer | Control spending | Model suggestions, parallelization, savings estimates |

## Models Used

- **Intelligent Planner**: claude-opus-4-6 + extended thinking (8000 token budget)
- **Project Analyzer**: claude-opus-4-6 + vision
- **Others**: Local analysis (no LLM calls)

## Example Workflow

```
1. POST /api/plan-intelligent
   → Creates project + 4 smart missions with dependencies

2. GET /api/projects/{pid}/missions/graph
   → Visualize the plan (Mermaid diagram)

3. GET /api/projects/{pid}/costs
   → Check projected costs before running

4. Mission Watcher auto-dispatches missions
   → Agents execute in optimal order

5. GET /api/projects/{pid}/health
   → Monitor progress, success rates, cost
```

## Documentation

Full details in `INTELLIGENCE.md`:
- Complete API reference
- Response examples
- Technical architecture
- Extending the system

## Next Steps

1. Test with a real project: `/api/plan-intelligent`
2. Analyze an existing project: `/api/projects/{pid}/analyze`
3. Monitor health in real-time: `/api/projects/{pid}/health`
4. Optimize costs: `/api/projects/{pid}/costs`

Enjoy! 🚀
