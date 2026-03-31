# Agile Wargame Simulator

> Predict bottlenecks, team friction, and technical debt before your project starts.

Multi-agent LLM simulation engine: 8 specialized agents (Developer, QA Engineer, Tech Lead, Product Owner, Security Architect, Cloud Engineer, Scrum Master, Software Architect) run concurrent sprint simulations. A God Agent synthesizes friction reports after each sprint.

## Quickstart

```bash
# Install
pip install -e ".[dev]"

# Run a simulation (mock provider, no API key needed)
python -m wargame run --scenario seeds/etp/ --provider mock --sprints 1

# Start dashboard
python -m wargame serve --port 8000
```

## Providers

| Flag | Model | Cost |
|------|-------|------|
| `mock` (default) | deterministic | $0.00 |
| `gemini-free` | gemini-2.0-flash | Free quota |
| `deepseek` | deepseek-chat | ~$0.30/run |
| `openai` | gpt-4o-mini | ~$6.40/run |

## License

MIT
