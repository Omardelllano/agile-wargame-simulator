# Contributing to Agile Wargame Simulator

Thank you for your interest in contributing! This project is open source (MIT License) and welcomes contributions of all kinds.

---

## Getting Started

```bash
# 1. Fork and clone the repository
git clone https://github.com/your-org/agile-wargame-simulator.git
cd agile-wargame-simulator

# 2. Install in editable mode with dev dependencies
pip install -e ".[dev]"

# 3. Run the test suite (mock provider — no API key required)
python -m pytest tests/ -v

# 4. Start a simulation to verify everything works
python -m wargame run --provider mock --scenario seeds/etp/ --sprints 1
```

---

## Project Structure

```
wargame/
  agents/       — 8 specialized agent classes (BaseAgent subclasses)
  core/         — Orchestrator, TurnManager, FrictionDetector, EventBus
  god_agent/    — MAP→REDUCE pipeline for SprintReport generation
  models/       — Pydantic v2 schemas (AgentResponse, WorldState, SprintReport, …)
  prompts/      — Jinja2 templates for each agent's system prompt
  providers/    — LLM backends (mock, gemini-free, deepseek, openai)
  memory/       — ChromaDB vector store + SQLAlchemy interaction log
  dashboard/    — FastAPI app + Vanilla JS SPA
seeds/etp/      — "Evolución Tecnológica Portales" scenario data
tests/          — pytest suite (36 tests, all runnable with mock provider)
```

---

## How to Contribute

### Adding a new scenario

1. Create a new directory under `seeds/<scenario-id>/`
2. Add three files: `backlog.json`, `agent_profiles.json`, `constraints.json`
3. Follow the schema in `seeds/etp/` as reference
4. Add a test in `tests/` that loads and validates the scenario

### Adding a new LLM provider

1. Create `wargame/providers/<name>.py` subclassing `BaseLLMProvider`
2. Implement `complete()` and `is_available()`
3. Register in `wargame/providers/factory.py`
4. Add to `tests/test_providers.py`

### Adding a new agent role

1. Create `wargame/agents/<role>.py` subclassing `BaseAgent`
2. Add a Jinja2 template in `wargame/prompts/templates/<role>.j2`
3. Add mock responses in `wargame/providers/mock.py`
4. Register the agent in `wargame/core/orchestrator.py`

---

## Code Standards

- **Language:** English throughout — all code, comments, docstrings, commit messages
- **Python:** 3.11+, type hints where they add clarity
- **Models:** Pydantic v2 (`BaseModel`, not `dataclass`)
- **Async:** `asyncio` — no threads, no `concurrent.futures`
- **Tests:** All tests must pass with `--provider mock` (no API keys in CI)
- **No new dependencies** without discussion — the tech stack is locked by design

---

## Commit Message Convention

```
feat: short description of new feature
fix: short description of bug fix
chore: tooling, deps, non-functional changes
test: adding or updating tests
docs: documentation only
```

---

## Pull Request Checklist

- [ ] `pytest tests/ -v` passes (all green with mock provider)
- [ ] `python -m wargame run --provider mock --scenario seeds/etp/ --sprints 1` runs without errors
- [ ] New code has corresponding tests
- [ ] No API keys or secrets in code or test fixtures
- [ ] English throughout

---

## Reporting Issues

Please open a GitHub Issue with:
- Python version (`python --version`)
- Provider used
- Full error traceback
- Minimal reproduction steps
