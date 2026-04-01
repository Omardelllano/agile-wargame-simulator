# Agile Wargame Simulator

> **Predict team friction, bottlenecks, and technical debt before your project starts.**
> A multi-agent LLM swarm that simulates sprint-by-sprint execution — in seconds, not weeks.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Tests](https://img.shields.io/badge/Tests-36%20passing-brightgreen)
![Providers](https://img.shields.io/badge/LLM-mock%20%7C%20gemini%20%7C%20deepseek%20%7C%20openai-purple)

---

## The problem

Most teams discover their real bottlenecks after 6 weeks of sprints.
By then, the Tech Lead has vetoed 12 PRs, the QA Engineer has blocked half the backlog,
the Cloud Engineer is waiting on security approvals, and the Product Owner is escalating
to the CTO.

**Agile Wargame Simulator runs those sprints in 60 seconds — before a single line of
code is written.**

---

## Quickstart

```bash
git clone https://github.com/omardelllano/agile-wargame-simulator
cd agile-wargame-simulator
pip install -e .
python -m wargame serve --port 8000
```

Open http://localhost:8000 — select **mock** provider, click **Run Simulation**.
No API key required.

---

## How it works

You provide three files:

| File | Contents |
|------|---------|
| `backlog.json` | Epics, stories, story points, dependencies, sprint targets |
| `agent_profiles.json` | Team roles, seniority, cognitive bias, velocity multipliers |
| `constraints.json` | Migration strategy, SLAs, compliance requirements |

The simulator runs a turn-based swarm where **9 specialized AI agents** debate,
block, approve, and escalate — exactly like a real team under pressure.

After each sprint, the **God Agent** reads the full interaction log, runs a
Map-Reduce pipeline over friction events and blocked dependencies, and produces
a structured `SprintReport` — without participating in the simulation itself.

---

## The swarm — 9 agents, 9 cognitive biases

| Agent | Bias | What they detect |
|-------|------|-----------------|
| Dev Agent (Senior) | Optimism — "that PL/SQL conversion is 2 days, tops" | Underestimated legacy complexity |
| Dev Agent (Junior) | Uncertainty — asks for help, introduces accidental debt | Knowledge gaps in migration tasks |
| QA Engineer | Pessimism — never closes a story without evidence | Missing test coverage on Oracle conversions |
| Tech Lead | Perfectionism — rejects shortcuts, writes ADRs | Architectural shortcuts that become permanent debt |
| Product Owner | Feature bias — pushes scope beyond team capacity | Sprint overcommitment, GDPR stories added last minute |
| Security Architect | Risk aversion — sees attack surface everywhere | PCI-DSS/GDPR violations in new microservice endpoints |
| Cloud Engineer | Cost optimization — loves automation, hates manual approvals | IaC bottlenecks, Azure quota limits |
| Scrum Master | Process visibility — surfaces patterns, not incidents | Recurring impediments the team has normalized |
| Software Architect | Long-term vision — writes an ADR for everything | Bounded context violations, synchronous coupling |

---

## Live dashboard

The web dashboard streams the simulation in real time:

- **Simulation Log** — turn-by-turn agent decisions with rationale
- **Agent Graph** — D3 force-directed graph: node size = activity, edge color = friction level (green → amber → red)
- **God Agent Report** — predicted risks, friction hotspots, blocked dependencies, recommendations

The friction graph updates live as agents interact. High-friction pairs (Tech Lead ↔ Product Owner, Cloud Engineer ↔ Security Architect) show red pulsing edges.

---

## God Agent output — real data from DeepSeek-V3

This is actual output from simulating the ETP migration scenario:

```json
{
  "sprint": 1,
  "confidence_score": 1.0,
  "friction_index": 0.99,
  "friction_hotspots": [
    {
      "agent_pair": ["developer", "qa_engineer"],
      "conflict_count": 158,
      "root_cause": "QA pessimism bias blocking Developer throughput"
    },
    {
      "agent_pair": ["cloud_engineer", "security_architect"],
      "conflict_count": 81,
      "root_cause": "Security requirements complicating IaC automation"
    },
    {
      "agent_pair": ["product_owner", "tech_lead"],
      "conflict_count": 38,
      "root_cause": "Tech Lead perfectionism vs. Product Owner scope pressure"
    }
  ],
  "blocked_dependencies": [
    {
      "story_id": "HU-001",
      "blocked_by_agent": "qa_engineer",
      "blocking_reason": "API Gateway returns 503 under load. Cannot mark done.",
      "days_blocked": 1
    },
    {
      "story_id": "HU-022",
      "blocked_by_agent": "cloud_engineer",
      "blocking_reason": "Azure DevOps service connection not authorized.",
      "days_blocked": 2
    },
    {
      "story_id": "HU-011",
      "blocked_by_agent": "qa_engineer",
      "blocking_reason": "Missing regression suite for Oracle migration path.",
      "days_blocked": 3
    }
  ],
  "velocity": 39,
  "tech_debt_delta": 78,
  "predicted_risks": [
    {
      "id": "R-01", "severity": "HIGH",
      "description": "developer vs qa_engineer: 158 conflict events. QA pessimism blocking throughput.",
      "recommendation": "Schedule mediated sync before next sprint planning."
    },
    {
      "id": "R-02", "severity": "HIGH",
      "description": "HU-001, HU-022, HU-011 blocked by qa_engineer and cloud_engineer.",
      "recommendation": "Prioritize unblocking sessions with cloud_engineer, qa_engineer."
    },
    {
      "id": "R-03", "severity": "HIGH",
      "description": "Tech debt spike: +78 points this sprint — threatens migration velocity.",
      "recommendation": "Allocate 20% of next sprint to debt remediation."
    }
  ]
}
```

Output is also exported as CSV — ready for Power BI or Microsoft Loop.

---

## LLM providers

| Provider | Cost per sprint | Setup | Best for |
|---------|----------------|-------|---------|
| `mock` | Free | None | Development, CI, demos |
| `gemini-free` | Free (quota) | `GEMINI_API_KEY` in `.env` | Realistic demos, no cost |
| `deepseek` | ~$0.03–0.05 | `DEEPSEEK_API_KEY` in `.env` | Production quality, near-free |
| `openai` | ~$0.80 | `OPENAI_API_KEY` in `.env` | Maximum quality |

Switch providers with one flag:

```bash
python -m wargame run --provider deepseek --scenario seeds/etp/ --sprints 2
```

---

## Included scenario — Evolución Tecnológica Portales (ETP)

A realistic migration project included out of the box:

- **Legacy:** Java 8 monolith + Oracle 12c PL/SQL (47 stored procedures, 12% test coverage)
- **Target:** Spring Boot 3 microservices on Azure Kubernetes Service
- **Scope:** 30 stories across 3 epics, 8 sprints, strangler fig pattern
- **Predefined friction:** `cloud_engineer ↔ security_architect` (IaC vs security reviews), `tech_lead ↔ product_owner` (quality vs scope)
- **Compliance:** GDPR + PCI-DSS constraints baked in

---

## Add your own scenario

Create three files in `seeds/your-scenario/`:

```bash
seeds/your-scenario/
├── backlog.json        # epics + stories + sprint targets
├── agent_profiles.json # team composition + cognitive bias params
└── constraints.json    # migration strategy + compliance + SLAs
```

Then run:

```bash
python -m wargame run --provider mock --scenario seeds/your-scenario/
```

Full guide: [docs/custom-scenarios.md](docs/custom-scenarios.md)

---

## Project structure

```
wargame/
├── core/          # Orchestrator, TurnManager, EventBus, FrictionDetector
├── agents/        # 8 specialized agents (BaseAgent + role implementations)
├── god_agent/     # Map-Reduce synthesizer → SprintReport JSON
├── providers/     # mock, gemini, deepseek, openai (swap with --provider)
├── memory/        # ChromaDB vector store + SQLite interaction log
├── prompts/       # Jinja2 templates — edit these to tune agent behavior
└── dashboard/     # FastAPI + SSE + Vanilla JS + D3 force graph
seeds/etp/         # Pilot scenario: Java/Oracle → Spring Boot/Azure migration
tests/             # 36 tests, all run with mock provider (no API key needed)
```

---

## Running tests

```bash
pytest tests/ -v
```

All 36 tests use the mock provider — no API key required. Tests cover:
provider schema validation, grounding validator (anti-hallucination),
friction detection calibration, God Agent report validation, and full e2e simulation.

---

## Roadmap

- [ ] Power BI connector — direct dataflow from SprintReport JSON
- [ ] Jira / Azure DevOps import — load real backlog with one command
- [ ] Scenario builder UI — create scenarios without editing JSON
- [ ] Multi-team simulation — simulate dependencies between two teams
- [ ] Slack / Teams alerts — notify when friction index exceeds threshold

**Good first issues:** Add a new scenario · Add a new agent role · Improve God Agent prompts · Add Portuguese/Spanish scenario

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for dev setup, architecture overview, and PR checklist.

---

## License

MIT © 2025
