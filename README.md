# Agile Wargame Simulator

> **Predict bottlenecks, team friction, and technical debt before your project starts.**

A multi-agent LLM simulation engine that runs an entire Agile software team as autonomous AI agents. Eight specialized agents (Developer, QA Engineer, Tech Lead, Product Owner, Security Architect, Cloud Engineer, Scrum Master, Software Architect) execute concurrent sprint simulations. After each sprint, a read-only **God Agent** runs a MAP→REDUCE pipeline over the interaction database and produces a structured `SprintReport` with predicted risks, friction hotspots, and recommendations — all before a single line of real code is written.

[![CI](https://github.com/your-org/agile-wargame-simulator/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/agile-wargame-simulator/actions/workflows/ci.yml)
![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)
![License: MIT](https://img.shields.io/badge/license-MIT-green)

---

## Quickstart

```bash
# 1. Install (Python 3.11+)
pip install -e ".[dev]"

# 2. Run a simulation — mock provider, no API key required
python -m wargame run --scenario seeds/etp/ --provider mock --sprints 2

# 3. Open the live dashboard
python -m wargame serve --port 8000
# → http://localhost:8000
```

Or with Docker Compose (recommended — includes ChromaDB + SQLite web UI):

```bash
docker compose up
# Dashboard:    http://localhost:8000
# SQLite Web:   http://localhost:8080
# ChromaDB API: http://localhost:8001
```

---

## Dashboard

The web dashboard (`wargame serve`) provides a real-time view of every simulation:

```
┌─────────────────────┬──────────────────────────────────┬──────────────────────┐
│  Configuration      │       Live Turn Log               │  God Agent Report    │
│                     │                                   │                      │
│  Provider: mock     │  Sprint Turn Agent   Action       │  [S1] [S2]           │
│  Scenario: etp      │  1     1   developer COMPLETE     │                      │
│  Sprints:  2        │  1     1   qa_eng    BLOCK_DONE   │  Velocity:    13 pts │
│                     │  1     1   tech_lead VETO         │  Tech Debt:   +13    │
│  [▶ RUN SIMULATION] │  1     2   sec_arch  FLAG         │  Friction:    45%    │
│                     │  ...                              │                      │
│  Friction Index     │                                   │  Risks               │
│  ████░░░░░░  42%    │                                   │  R-01 HIGH           │
│                     │                                   │  R-02 MEDIUM         │
│  Agent Status       │                                   │                      │
│  [developer DONE ]  │                                   │  Recommendations     │
│  [qa_eng  BLOCK ]   │                                   │  › Schedule conflict │
│  [tech_lead VETO]   │                                   │    resolution...     │
│  ...                │                                   │                      │
└─────────────────────┴──────────────────────────────────┴──────────────────────┘
```

- **Left panel**: provider/scenario/sprint configuration + live friction gauge (green→yellow→red) + 8 agent status cards updated in real time
- **Center panel**: scrollable turn log with colour-coded actions streamed via SSE
- **Right panel**: God Agent sprint reports with predicted risks, recommendations, and friction hotspots; tabbed by sprint number

---

## Provider Comparison

| Flag | Model | Requires Key | Approx. Cost (8 sprints) | Notes |
|------|-------|:---:|---:|---|
| `mock` | Deterministic rotating responses | No | $0.00 | Instant, zero latency, fully deterministic |
| `gemini-free` | `gemini-2.0-flash` | Yes (`GEMINI_API_KEY`) | $0.00* | Free quota (12 RPM); rate-limited automatically |
| `deepseek` | `deepseek-chat` | Yes (`DEEPSEEK_API_KEY`) | ~$0.30 | Cost-effective; requires JSON-mode prompt tuning |
| `openai` | `gpt-4o-mini` | Yes (`OPENAI_API_KEY`) | ~$6.40 | Highest reliability; native JSON mode |

\* Subject to Gemini free-tier quota limits.

Set API keys in `.env` (copy from `.env.example`):

```bash
cp .env.example .env
# Edit .env and add your keys
python -m wargame run --provider gemini-free --scenario seeds/etp/ --sprints 8
```

---

## Architecture

```
seeds/etp/
  backlog.json          ← Scenario: 30 user stories, 3 epics
  agent_profiles.json   ← Per-agent personality weights
  constraints.json      ← Sprint velocity caps, tech debt thresholds

wargame/
├── core/
│   ├── orchestrator.py   ← Main simulation loop (sprint → turns → reports)
│   ├── turn.py           ← TurnManager: asyncio.gather over all 8 agents
│   ├── events.py         ← EventBus: publish/drain AgentEvents per turn
│   └── friction.py       ← FrictionDetector: weighted conflict scoring
│
├── agents/               ← 8 role agents (BaseAgent + role-specific subclasses)
│   ├── base.py           ← decide() → prompt → LLM → grounding validation → ChromaDB
│   ├── developer.py
│   ├── qa_engineer.py
│   └── ...
│
├── providers/            ← LLM backends (mock / gemini / deepseek / openai)
│   ├── base.py           ← _parse_response(): strips markdown fences, validates JSON
│   ├── mock.py           ← 5 deterministic responses × 8 roles, zero-latency
│   └── ...
│
├── prompts/
│   ├── renderer.py       ← Jinja2 + StrictUndefined
│   └── templates/        ← 3-section .j2 per role: IDENTITY + WORLD STATE + CONSTRAINTS
│
├── memory/
│   ├── vector_store.py   ← ChromaDB per-agent RAG collections (all-MiniLM-L6-v2)
│   └── interaction_log.py← SQLAlchemy: 4 tables (turns, events, snapshots, reports)
│
├── god_agent/
│   ├── mapper.py         ← 4 parallel SQLAlchemy queries → plain dicts (no LLM)
│   ├── reducer.py        ← MAP results → SprintReport (heuristic or LLM insights)
│   ├── exporter.py       ← Writes sprint_NN.json + sprint_NN.csv
│   └── god_agent.py      ← MAP → REDUCE → EXPORT pipeline
│
└── dashboard/
    ├── app.py            ← FastAPI: GET /, POST /simulate, SSE /simulate/{id}/stream
    ├── sim_registry.py   ← In-process simulation state (asyncio.Queue per sim)
    ├── routes/
    │   ├── simulate.py   ← Background task + SSE event generator
    │   └── reports.py    ← /reports, /report/{sim_id}, /scenarios, /health
    ├── templates/
    │   └── index.html    ← Vanilla JS SPA (no frameworks)
    └── static/
        ├── dashboard.js  ← EventSource SSE client, DOM updates
        └── style.css     ← Dark terminal theme
```

### Simulation flow

```
Orchestrator.run()
  └─ for each sprint:
       ├─ TurnManager.run_turn() × N turns
       │    └─ asyncio.gather(agent.decide() for all 8 agents)
       │         ├─ ChromaDB RAG context retrieval
       │         ├─ Jinja2 prompt rendering
       │         ├─ LLM call (provider.complete)
       │         ├─ Grounding validation (GroundingError on hallucinated story IDs)
       │         └─ ChromaDB persistence
       └─ GodAgent.synthesize()
            ├─ MAP: 4 parallel SQLite queries (friction, deps, debt, velocity)
            ├─ REDUCE: confidence score + heuristic/LLM insights → SprintReport
            └─ EXPORT: sprint_NN.json + sprint_NN.csv (if confidence ≥ 0.70)
```

---

## Running Tests

```bash
pytest tests/ -v
```

The test suite requires **no API keys** — all tests run against the mock provider or with patched LiteLLM responses.

| Test file | What it covers |
|-----------|---------------|
| `test_providers.py` | All 4 providers return valid `AgentResponse` schema |
| `test_grounding.py` | `GroundingError` raised on fake story IDs, not on real ones |
| `test_friction.py` | `FrictionDetector.score()` — empty=0, known pairs score higher |
| `test_god_agent.py` | `SprintReport` Pydantic validation, confidence ≥ 0.70, heuristic risks |
| `test_e2e_mock.py` | Full 8-agent, 5-turn simulation — DB rows, JSON output, callbacks |

---

## Output Files

After each sprint (when `confidence_score ≥ 0.70`):

```
output/
  sprint_01.json   ← Full SprintReport (velocity, risks, recommendations, hotspots)
  sprint_01.csv    ← Flattened rows — one per predicted risk (for Excel/BI tools)
  sprint_02.json
  sprint_02.csv
  wargame.db       ← SQLite: interaction_turns, agent_events, world_state_snapshots
```

---

## License

MIT
