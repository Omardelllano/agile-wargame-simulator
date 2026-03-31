# AGILE WARGAME SIMULATOR — MASTER BRIEFING FOR CLAUDE CODE
# Paste this entire file as your first message in Claude Code.
# Project path: C:\Users\omard\OneDrive\Documentos\Agile Wargame Simulator

---

## 1. PROJECT IDENTITY

**Name:** Agile Wargame Simulator
**Tagline:** Predict bottlenecks, team friction, and technical debt before your project starts.
**GitHub visibility:** Public open-source (MIT License)
**Language:** English throughout — all code, comments, docstrings, commit messages, README
**Python package name:** `wargame`
**CLI invocation:** `python -m wargame run --provider mock --scenario seeds/etp/`

---

## 2. TECH STACK (LOCKED — DO NOT DEVIATE)

| Layer | Technology | Version |
|-------|-----------|---------|
| Language | Python | 3.11 |
| CLI | Click | 8.x |
| Validation | Pydantic | v2 |
| Async | asyncio (stdlib) | — |
| HTTP client | httpx | 0.27+ |
| LLM routing | litellm | latest |
| Vector DB | chromadb | 0.5+ |
| Relational DB | SQLite (dev) via SQLAlchemy | 2.x |
| Migrations | Alembic | latest |
| API server | FastAPI | 0.110+ |
| SSE streaming | sse-starlette | latest |
| Frontend | Vanilla JS + HTML (no framework) | — |
| Terminal UI | rich | 13+ |
| Templates | Jinja2 | 3.x |
| Testing | pytest + pytest-asyncio | latest |
| Containers | Docker + Docker Compose v2 | — |
| Package mgmt | pyproject.toml (no requirements.txt) | — |

**NO Ollama.** It was explicitly removed. User has no local GPU.
**NO LangChain / LangGraph.** Direct provider calls only, own orchestration.
**NO React / Vue / Node frontend.** Vanilla JS served by FastAPI static files.

---

## 3. LLM PROVIDERS — PRIORITY ORDER

```
mock  →  gemini-free  →  deepseek  →  openai
```

| Flag value | Class | Model default | Cost |
|-----------|-------|--------------|------|
| `mock` | `MockProvider` | n/a | $0.00 |
| `gemini-free` | `GeminiProvider` | `gemini-2.0-flash` | Free quota |
| `deepseek` | `DeepSeekProvider` | `deepseek-chat` | ~$0.30/full sim |
| `openai` | `OpenAIProvider` | `gpt-4o-mini` | ~$6.40/full sim |

`mock` is the **default**. All CI/CD runs use `mock`. No API key required for any test.

---

## 4. EXACT REPOSITORY STRUCTURE

```
agile-wargame-simulator/
│
├── README.md
├── CONTRIBUTING.md
├── LICENSE                          (MIT)
├── pyproject.toml
├── .env.example
├── .gitignore
├── docker-compose.yml
├── Dockerfile
│
├── wargame/                         ← main Python package
│   ├── __init__.py                  ← version = "0.1.0"
│   ├── __main__.py                  ← enables `python -m wargame`
│   ├── cli.py                       ← Click entry point
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   ├── orchestrator.py          ← class Orchestrator
│   │   ├── turn.py                  ← class TurnManager
│   │   ├── state.py                 ← class WorldState (Pydantic BaseModel)
│   │   ├── events.py                ← class EventBus, dataclass AgentEvent
│   │   ├── context.py               ← class ContextInjector
│   │   └── friction.py              ← class FrictionDetector
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py                  ← class BaseAgent (ABC)
│   │   ├── developer.py             ← class DeveloperAgent(BaseAgent)
│   │   ├── qa_engineer.py           ← class QAEngineerAgent(BaseAgent)
│   │   ├── tech_lead.py             ← class TechLeadAgent(BaseAgent)
│   │   ├── product_owner.py         ← class ProductOwnerAgent(BaseAgent)
│   │   ├── security_architect.py    ← class SecurityArchitectAgent(BaseAgent)
│   │   ├── cloud_engineer.py        ← class CloudEngineerAgent(BaseAgent)
│   │   ├── scrum_master.py          ← class ScrumMasterAgent(BaseAgent)
│   │   └── software_architect.py   ← class SoftwareArchitectAgent(BaseAgent)
│   │
│   ├── god_agent/
│   │   ├── __init__.py
│   │   ├── god_agent.py             ← class GodAgent
│   │   ├── mapper.py                ← functions: map_friction(), map_dependencies(),
│   │   │                               map_tech_debt(), map_velocity()
│   │   ├── reducer.py               ← class GodAgentReducer
│   │   └── exporter.py              ← class ReportExporter
│   │
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py                  ← class BaseLLMProvider (ABC)
│   │   │                               class AgentResponse (Pydantic)
│   │   ├── mock.py                  ← class MockProvider(BaseLLMProvider)
│   │   ├── gemini.py                ← class GeminiProvider(BaseLLMProvider)
│   │   ├── deepseek.py              ← class DeepSeekProvider(BaseLLMProvider)
│   │   ├── openai_provider.py       ← class OpenAIProvider(BaseLLMProvider)
│   │   └── factory.py               ← function build_provider(name, model) → BaseLLMProvider
│   │
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── vector_store.py          ← class AgentVectorStore
│   │   └── interaction_log.py       ← class InteractionLog (SQLAlchemy)
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── agent_response.py        ← class AgentResponse (Pydantic v2)
│   │   ├── world_state.py           ← class WorldState, StoryStatus, SprintMetrics
│   │   ├── sprint_report.py         ← class SprintReport (God Agent output schema)
│   │   └── events.py                ← class AgentEvent, EventType (Enum)
│   │
│   ├── prompts/
│   │   ├── __init__.py
│   │   ├── renderer.py              ← class PromptRenderer (Jinja2 env)
│   │   └── templates/
│   │       ├── developer.j2
│   │       ├── qa_engineer.j2
│   │       ├── tech_lead.j2
│   │       ├── product_owner.j2
│   │       ├── security_architect.j2
│   │       ├── cloud_engineer.j2
│   │       ├── scrum_master.j2
│   │       ├── software_architect.j2
│   │       └── god_agent.j2
│   │
│   └── dashboard/
│       ├── __init__.py
│       ├── app.py                   ← FastAPI application
│       ├── routes/
│       │   ├── simulate.py          ← POST /simulate, GET /simulate/{id}/stream (SSE)
│       │   └── reports.py           ← GET /report/{id}, GET /reports
│       ├── templates/
│       │   └── index.html           ← Vanilla JS SPA
│       └── static/
│           ├── dashboard.js
│           └── style.css
│
├── seeds/
│   └── etp/                         ← "Evolución Tecnológica Portales" scenario
│       ├── backlog.json             ← 30 stories across 3 epics
│       ├── agent_profiles.json      ← personality params for all 8 agents
│       └── constraints.json         ← migration constraints, SLAs, timeline
│
├── output/                          ← generated at runtime, gitignored
│   └── .gitkeep
│
├── migrations/                      ← Alembic migrations
│   └── versions/
│
└── tests/
    ├── conftest.py                  ← shared fixtures
    ├── test_providers.py            ← all providers return valid AgentResponse
    ├── test_grounding.py            ← anti-hallucination: only real story IDs
    ├── test_friction.py             ← FrictionDetector calibration
    ├── test_god_agent.py            ← SprintReport Pydantic validation
    └── test_e2e_mock.py             ← full 8-agent, 5-turn sim, mock provider
```

---

## 5. PYDANTIC MODELS — EXACT SCHEMAS

### 5.1 AgentResponse (wargame/models/agent_response.py)

```python
from enum import Enum
from pydantic import BaseModel, Field

class ActionType(str, Enum):
    APPROVE    = "APPROVE"
    VETO       = "VETO"
    BLOCK_DONE = "BLOCK_DONE"
    COMPLETE   = "COMPLETE"
    ESCALATE   = "ESCALATE"
    FLAG       = "FLAG"           # security / architecture concern
    REPRIORITIZE = "REPRIORITIZE"
    IMPEDIMENT = "IMPEDIMENT"     # SM raises impediment
    IDLE       = "IDLE"           # agent has nothing to act on this turn

class AgentResponse(BaseModel):
    agent_id: str                          # e.g. "tech_lead"
    turn: int
    sprint: int
    action: ActionType
    rationale: str = Field(max_length=500)
    referenced_stories: list[str] = []    # e.g. ["HU-001", "HU-012"]
    events: list[dict] = []               # raw event dicts for EventBus
    artifacts: list[str] = []             # e.g. ["ADR-003", "PR-review-HU-001"]
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    tech_debt_added: int = 0              # story points of debt this action introduces
```

### 5.2 WorldState (wargame/models/world_state.py)

```python
from enum import Enum
from pydantic import BaseModel
from datetime import datetime

class StoryStatus(str, Enum):
    TODO        = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    IN_REVIEW   = "IN_REVIEW"
    BLOCKED     = "BLOCKED"
    DONE        = "DONE"

class Story(BaseModel):
    id: str                    # "HU-001"
    epic_id: str               # "EPIC-01"
    title: str
    points: int
    status: StoryStatus = StoryStatus.TODO
    assigned_to: str | None = None
    blocked_by: str | None = None   # agent_id that blocked it
    blocked_days: int = 0

class SprintMetrics(BaseModel):
    sprint: int
    velocity: int = 0              # story points completed
    friction_index: float = 0.0    # 0.0–1.0
    tech_debt_delta: int = 0       # points added minus points paid
    blocked_count: int = 0

class WorldState(BaseModel):
    simulation_id: str
    scenario: str              # "etp"
    current_sprint: int = 1
    current_turn: int = 0
    total_sprints: int = 8
    stories: list[Story] = []
    sprint_history: list[SprintMetrics] = []
    tech_debt_total: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

    def snapshot(self) -> dict:
        """Return JSON-serializable dict for persistence."""
        return self.model_dump(mode="json")
```

### 5.3 AgentEvent (wargame/models/events.py)

```python
from enum import Enum
from pydantic import BaseModel

class EventType(str, Enum):
    STORY_BLOCKED    = "STORY_BLOCKED"
    STORY_UNBLOCKED  = "STORY_UNBLOCKED"
    STORY_COMPLETED  = "STORY_COMPLETED"
    PR_VETOED        = "PR_VETOED"
    SCOPE_CHANGED    = "SCOPE_CHANGED"
    IMPEDIMENT_RAISED = "IMPEDIMENT_RAISED"
    SECURITY_FLAG    = "SECURITY_FLAG"
    TECH_DEBT_ADDED  = "TECH_DEBT_ADDED"
    CONFLICT         = "CONFLICT"          # friction trigger

class AgentEvent(BaseModel):
    event_type: EventType
    source_agent: str
    target_agent: str | None = None
    story_id: str | None = None
    payload: dict = {}
    turn: int
    sprint: int
```

### 5.4 SprintReport — God Agent output (wargame/models/sprint_report.py)

```python
from pydantic import BaseModel, Field
from datetime import datetime

class FrictionHotspot(BaseModel):
    agent_pair: tuple[str, str]
    conflict_count: int
    root_cause: str

class BlockedDependency(BaseModel):
    story_id: str
    blocked_by_agent: str
    blocking_reason: str
    days_blocked: int
    impact: str    # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"

class PredictedRisk(BaseModel):
    id: str        # "R-01"
    severity: str  # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    sprint_impact: int   # which sprint this risk will materialize
    description: str
    recommendation: str

class SprintReport(BaseModel):
    simulation_id: str
    sprint: int
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    confidence_score: float = Field(ge=0.0, le=1.0)
    is_reliable: bool = True   # False if confidence_score < 0.70

    friction_index: float
    friction_hotspots: list[FrictionHotspot] = []
    blocked_dependencies: list[BlockedDependency] = []
    tech_debt_delta: int
    velocity: int
    velocity_decay_pct: float   # vs previous sprint, 0.0 on sprint 1

    predicted_risks: list[PredictedRisk] = []
    recommendations: list[str] = []

    @classmethod
    def reliability_threshold(cls) -> float:
        return 0.70
```

---

## 6. CLASS INTERFACES — EXACT SIGNATURES

### 6.1 BaseLLMProvider (wargame/providers/base.py)

```python
from abc import ABC, abstractmethod
from wargame.models.agent_response import AgentResponse

class BaseLLMProvider(ABC):
    provider_name: str = "base"

    @abstractmethod
    async def complete(self, system_prompt: str, user_prompt: str) -> AgentResponse:
        """Call the LLM and return a structured AgentResponse."""
        ...

    @abstractmethod
    def is_available(self) -> bool:
        """Check if provider credentials/connection are available."""
        ...
```

### 6.2 MockProvider (wargame/providers/mock.py)

```python
# Returns realistic but fully deterministic responses.
# Rotates through a fixed set of responses per role.
# Used in ALL tests and CI. Zero latency, zero cost.

MOCK_RESPONSES: dict[str, list[AgentResponse]] = {
    "developer": [...],         # 5 rotating responses
    "qa_engineer": [...],
    "tech_lead": [...],         # must include at least 1 VETO
    "product_owner": [...],     # must include at least 1 REPRIORITIZE
    "security_architect": [...],# must include at least 1 FLAG
    "cloud_engineer": [...],
    "scrum_master": [...],      # must include at least 1 IMPEDIMENT
    "software_architect": [...],
}
```

### 6.3 BaseAgent (wargame/agents/base.py)

```python
from abc import ABC, abstractmethod
from wargame.models.agent_response import AgentResponse
from wargame.models.world_state import WorldState
from wargame.providers.base import BaseLLMProvider
from wargame.prompts.renderer import PromptRenderer
from wargame.memory.vector_store import AgentVectorStore

class BaseAgent(ABC):
    role: str = "base"          # overridden in each subclass
    template_name: str = ""     # e.g. "developer.j2"

    def __init__(
        self,
        provider: BaseLLMProvider,
        vector_store: AgentVectorStore,
        renderer: PromptRenderer,
    ): ...

    async def decide(self, world_state: WorldState, turn: int) -> AgentResponse:
        """Main method: build prompt → call LLM → validate → return response."""
        context = await self._retrieve_context(world_state)
        system_prompt = self.renderer.render(
            self.template_name,
            role=self.role,
            world_state=world_state,
            context=context,
        )
        user_prompt = self._build_user_prompt(world_state, turn)
        response = await self.provider.complete(system_prompt, user_prompt)
        self._validate_grounding(response, world_state)
        await self.vector_store.persist(self.role, response)
        return response

    def _validate_grounding(self, response: AgentResponse, state: WorldState) -> None:
        """Raise GroundingError if response references non-existent story IDs."""
        real_ids = {s.id for s in state.stories}
        for story_id in response.referenced_stories:
            if story_id not in real_ids:
                raise GroundingError(
                    f"[{self.role}] hallucinated story ID: {story_id}"
                )

    @abstractmethod
    def _build_user_prompt(self, world_state: WorldState, turn: int) -> str: ...

    async def _retrieve_context(self, world_state: WorldState) -> list[dict]:
        """RAG: fetch last 5 relevant interactions for this agent from ChromaDB."""
        return await self.vector_store.query(
            agent_id=self.role,
            query=f"sprint {world_state.current_sprint} decisions",
            n_results=5,
        )
```

### 6.4 Orchestrator (wargame/core/orchestrator.py)

```python
class Orchestrator:
    def __init__(
        self,
        provider: BaseLLMProvider,
        scenario_path: str,
        total_sprints: int = 8,
    ): ...

    async def run(self) -> list[SprintReport]:
        """Main simulation loop. Returns list of SprintReport, one per sprint."""
        ...

    async def _run_sprint(self, sprint_num: int) -> SprintReport:
        """Run all turns for one sprint, then invoke GodAgent."""
        ...

    async def _run_turn(self, turn_num: int) -> list[AgentResponse]:
        """Run all agents concurrently for one turn using asyncio.gather."""
        responses = await asyncio.gather(*[
            agent.decide(self.state, turn_num)
            for agent in self.agents
        ])
        events = self._collect_events(responses)
        self.event_bus.publish_batch(events)
        self.state = self.state_manager.apply_events(self.state, events)
        friction = self.friction_detector.score(events)
        self.state.sprint_history[-1].friction_index = friction
        self.interaction_log.record_turn(turn_num, responses, events)
        return responses
```

### 6.5 FrictionDetector (wargame/core/friction.py)

```python
class FrictionDetector:
    CONFLICT_PAIRS = [
        ("tech_lead", "product_owner"),
        ("qa_engineer", "developer"),
        ("security_architect", "cloud_engineer"),
        ("software_architect", "developer"),
    ]

    def score(self, events: list[AgentEvent]) -> float:
        """
        Returns Friction Index for a turn: 0.0 (no friction) to 1.0 (max).
        Formula: conflict_events / total_events, capped at 1.0
        A CONFLICT event between a known friction pair counts double.
        """
        ...
```

### 6.6 GodAgent (wargame/god_agent/god_agent.py)

```python
class GodAgent:
    """
    Read-only observer. Never modifies WorldState.
    Runs after every sprint. Produces a SprintReport.
    """
    def __init__(self, provider: BaseLLMProvider, interaction_log: InteractionLog): ...

    async def synthesize(self, world_state: WorldState) -> SprintReport:
        """
        1. Run all MAP functions in parallel
        2. Pass MAP results to reducer (LLM call)
        3. Validate with Pydantic
        4. Export if confidence >= 0.70
        """
        map_results = await asyncio.gather(
            mapper.map_friction(self.log, world_state.current_sprint),
            mapper.map_dependencies(self.log, world_state.current_sprint),
            mapper.map_tech_debt(self.log, world_state.current_sprint),
            mapper.map_velocity(self.log, world_state.current_sprint),
        )
        report = await self.reducer.reduce(map_results, world_state)
        report.is_reliable = report.confidence_score >= SprintReport.reliability_threshold()
        if report.is_reliable:
            self.exporter.export(report)
        return report
```

---

## 7. DATABASE SCHEMA (SQLite via SQLAlchemy)

```python
# Table: interaction_turns
# - id (PK, autoincrement)
# - simulation_id (str)
# - sprint (int)
# - turn (int)
# - agent_id (str)
# - action (str)           ActionType value
# - rationale (str)
# - referenced_stories (JSON)
# - events (JSON)
# - artifacts (JSON)
# - confidence (float)
# - tech_debt_added (int)
# - created_at (datetime)

# Table: agent_events
# - id (PK, autoincrement)
# - simulation_id (str)
# - sprint (int)
# - turn (int)
# - event_type (str)       EventType value
# - source_agent (str)
# - target_agent (str, nullable)
# - story_id (str, nullable)
# - payload (JSON)
# - created_at (datetime)

# Table: sprint_reports
# - id (PK, autoincrement)
# - simulation_id (str)
# - sprint (int)
# - report_json (JSON)     Full SprintReport serialized
# - confidence_score (float)
# - is_reliable (bool)
# - created_at (datetime)

# Table: world_state_snapshots
# - id (PK, autoincrement)
# - simulation_id (str)
# - sprint (int)
# - turn (int)
# - snapshot_json (JSON)   WorldState.snapshot()
# - created_at (datetime)
```

---

## 8. CLI — EXACT COMMANDS

```bash
# Run simulation (minimum required)
python -m wargame run --scenario seeds/etp/

# Run with specific provider
python -m wargame run --scenario seeds/etp/ --provider gemini-free
python -m wargame run --scenario seeds/etp/ --provider deepseek
python -m wargame run --scenario seeds/etp/ --provider openai

# Override model within a provider
python -m wargame run --scenario seeds/etp/ --provider gemini-free --model gemini-1.5-pro

# Limit sprints (useful during development)
python -m wargame run --scenario seeds/etp/ --sprints 2

# Start web dashboard only (no simulation)
python -m wargame serve --port 8000

# Run simulation and stream to dashboard
python -m wargame run --scenario seeds/etp/ --serve

# List available scenarios
python -m wargame scenarios

# Show last report for a simulation
python -m wargame report --sim-id <simulation_id>
```

---

## 9. AGENT SYSTEM PROMPT STRUCTURE (all 8 agents)

Every agent's Jinja2 template MUST follow this exact 3-section structure:

```
### SECTION A — IDENTITY
You are a [ROLE] with [N] years of experience in [DOMAIN].
Personality: [2-3 sentences on cognitive bias and working style]
Your primary bias: [specific technical or behavioral bias]
Your conflict source: [what triggers friction with other roles]

### SECTION B — WORLD STATE (injected by ContextInjector)
Current sprint: {{ world_state.current_sprint }} / {{ world_state.total_sprints }}
Current turn: {{ turn }}
Sprint velocity so far: {{ metrics.velocity }} points
Friction index this sprint: {{ metrics.friction_index | round(2) }}
Tech debt total: {{ world_state.tech_debt_total }} points

Active stories assigned to you:
{% for story in my_stories %}
- {{ story.id }}: {{ story.title }} ({{ story.points }} pts) [{{ story.status }}]
{% endfor %}

Recent context from memory:
{% for ctx in context %}
- Turn {{ ctx.turn }}: {{ ctx.summary }}
{% endfor %}

### SECTION C — BEHAVIORAL CONSTRAINTS
You MUST respond with a valid JSON object matching this exact schema:
{
  "agent_id": "{{ role }}",
  "turn": {{ turn }},
  "sprint": {{ world_state.current_sprint }},
  "action": "<one of: APPROVE|VETO|BLOCK_DONE|COMPLETE|ESCALATE|FLAG|REPRIORITIZE|IMPEDIMENT|IDLE>",
  "rationale": "<max 500 chars>",
  "referenced_stories": ["HU-XXX"],    ← ONLY IDs that exist in the backlog above
  "events": [],
  "artifacts": [],
  "confidence": 0.0-1.0,
  "tech_debt_added": 0
}

CRITICAL: You may ONLY reference story IDs from the active stories list above.
Never invent story IDs. Never reference stories not listed above.
```

### Agent-specific identities:

| Role | Bias | Primary conflict |
|------|------|-----------------|
| `developer` | Optimism bias — underestimates legacy complexity | Pressured by QA and Tech Lead |
| `qa_engineer` | Pessimism bias — never closes stories without full evidence | Blocks Dev throughput |
| `tech_lead` | Perfectionism — rejects shortcuts | Vetoes PO scope demands |
| `product_owner` | Feature-driven — minimizes tech concerns | Scope creep pressure on team |
| `security_architect` | Risk-averse — sees attack surface everywhere | Can veto entire deployments |
| `cloud_engineer` | Cost-pragmatic — overestimates automation readiness | Bottleneck on IaC provisioning |
| `scrum_master` | Neutral mediator — detects dysfunction patterns | Intervenes but never decides |
| `software_architect` | Long-term vision — sacrifices velocity for consistency | Slows team for design quality |

---

## 10. ETP SCENARIO SEEDS — STRUCTURE

### seeds/etp/backlog.json structure:
```json
{
  "scenario_id": "etp",
  "scenario_name": "Evolución Tecnológica Portales",
  "description": "Migration of Java/Oracle PL/SQL monolith to Spring Boot microservices on Azure",
  "total_sprints": 8,
  "team_size": 8,
  "epics": [
    {
      "id": "EPIC-01",
      "title": "Strangler Fig — Customer Portal",
      "stories": [
        {
          "id": "HU-001",
          "title": "Configure API Gateway on Azure APIM",
          "points": 8,
          "epic_id": "EPIC-01",
          "sprint_target": 1,
          "depends_on": [],
          "tech_risk": "MEDIUM",
          "description": "Set up Azure API Management to front the legacy monolith while microservices are built"
        }
        // ... 9 more stories in EPIC-01
      ]
    },
    {
      "id": "EPIC-02",
      "title": "Oracle PL/SQL Schema Migration",
      "stories": [/* 10 stories */]
    },
    {
      "id": "EPIC-03",
      "title": "Azure DevOps CI/CD Pipeline",
      "stories": [/* 10 stories */]
    }
  ]
}
```

### seeds/etp/agent_profiles.json structure:
```json
{
  "agents": [
    {
      "role": "developer",
      "display_name": "Dev Agent",
      "seniority": "senior",
      "experience_years": 5,
      "tech_stack": ["Java 17", "Spring Boot 3", "Hibernate", "Maven"],
      "cognitive_bias": "optimism_bias",
      "friction_sensitivity": 0.3,
      "velocity_multiplier": 1.0,
      "tech_debt_tolerance": 0.6
    }
    // ... 7 more agents
  ]
}
```

### seeds/etp/constraints.json structure:
```json
{
  "migration_strategy": "strangler_fig",
  "timeline_weeks": 16,
  "budget_constraint": "fixed",
  "sla_downtime_minutes_per_month": 30,
  "compliance": ["GDPR", "PCI-DSS"],
  "legacy_system": {
    "language": "Java 8",
    "database": "Oracle 12c",
    "deployment": "on-premise",
    "test_coverage_pct": 12
  },
  "target_system": {
    "language": "Java 17",
    "framework": "Spring Boot 3",
    "database": "PostgreSQL on Azure",
    "deployment": "Azure Kubernetes Service",
    "test_coverage_target_pct": 80
  }
}
```

---

## 11. DOCKER COMPOSE — EXACT SERVICES

```yaml
# docker-compose.yml
services:
  wargame-api:
    build: .
    ports: ["8000:8000"]
    volumes:
      - ./output:/app/output
      - ./seeds:/app/seeds
    environment:
      - PROVIDER=mock
      - GEMINI_API_KEY=${GEMINI_API_KEY:-}
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY:-}
      - OPENAI_API_KEY=${OPENAI_API_KEY:-}
      - CHROMA_HOST=chromadb
      - DATABASE_URL=sqlite:///./output/wargame.db
    depends_on: [chromadb]

  chromadb:
    image: chromadb/chroma:latest
    ports: ["8001:8000"]
    volumes:
      - chroma_data:/chroma/chroma

  sqlite-web:
    image: coleifer/sqlite-web
    ports: ["8080:8080"]
    volumes:
      - ./output:/data
    command: sqlite_web --host 0.0.0.0 /data/wargame.db

volumes:
  chroma_data:
```

---

## 12. GITHUB ACTIONS CI

```yaml
# .github/workflows/ci.yml
name: CI
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -e ".[dev]"
      - run: pytest tests/ -v --provider mock
      # No API keys needed — mock provider only in CI
```

---

## 13. pyproject.toml STRUCTURE

```toml
[project]
name = "agile-wargame-simulator"
version = "0.1.0"
description = "Multi-agent LLM simulation engine for predicting project friction"
requires-python = ">=3.11"
dependencies = [
    "click>=8.0",
    "pydantic>=2.0",
    "httpx>=0.27",
    "litellm>=1.0",
    "chromadb>=0.5",
    "sqlalchemy>=2.0",
    "alembic>=1.13",
    "fastapi>=0.110",
    "sse-starlette>=1.6",
    "uvicorn>=0.29",
    "rich>=13.0",
    "jinja2>=3.0",
    "python-dotenv>=1.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0", "pytest-asyncio>=0.23", "httpx>=0.27"]

[project.scripts]
wargame = "wargame.cli:main"

[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"
```

---

## 14. BUILD PHASES — GATES (DO NOT SKIP)

### Phase P0 — Foundation (implement first, nothing else)
**Deliver:**
- Full folder structure (all files, can be stubs)
- `pyproject.toml` with all dependencies
- `wargame/providers/mock.py` fully working (not a stub)
- `wargame/models/` all 4 Pydantic models complete
- `wargame/cli.py` with `run` command, `--provider` flag
- `wargame/core/state.py` WorldState complete
- SQLite schema + Alembic initial migration
- `docker-compose.yml`
- `seeds/etp/` all 3 JSON files with real data (30 stories)

**P0 Gate — must pass before P1:**
```bash
python -m wargame run --provider mock --scenario seeds/etp/ --sprints 1
```
Expected output:
- Rich table printed to terminal showing 8 agents × N turns
- `output/wargame.db` created with rows in `interaction_turns`
- `output/sprint_01.json` written by God Agent (even if stub report)
- Zero Python errors

### Phase P1 — Turn Engine + DeveloperAgent
**Deliver:**
- `wargame/core/orchestrator.py` Orchestrator class
- `wargame/core/turn.py` TurnManager with asyncio.gather
- `wargame/agents/base.py` BaseAgent with validate_grounding
- `wargame/agents/developer.py` fully implemented
- `wargame/memory/vector_store.py` ChromaDB integration
- `wargame/prompts/renderer.py` + `developer.j2` template

**P1 Gate:**
```bash
python -m wargame run --provider mock --scenario seeds/etp/ --sprints 1
```
- DeveloperAgent completes turns with real prompt rendering
- Grounding validator runs on every response
- ChromaDB has embeddings after run

### Phase P2 — Full Swarm
- All 7 remaining agents implemented
- EventBus pub/sub working
- FrictionDetector scoring
- Gemini Free provider working

**P2 Gate:**
```bash
python -m wargame run --provider mock --scenario seeds/etp/ --sprints 2
```
- FrictionDetector reports FI > 0 in at least 1 turn
- Behavioral coverage test passes

### Phase P3 — God Agent
- mapper.py 4 functions
- reducer.py LLM synthesis
- exporter.py JSON + CSV

**P3 Gate:**
```bash
python -m wargame run --provider mock --scenario seeds/etp/ --sprints 1
cat output/sprint_01.json | python -m json.tool
```
- Valid SprintReport JSON
- blocked_dependencies matches EventBus BLOCKED events

### Phase P4 — Dashboard
**P4 Gate:**
```
docker compose up
# Open http://localhost:8000
# Click Run → watch live simulation → see God Agent report
```

### Phase P5 — Tests + GitHub launch
```bash
pytest tests/ -v
# All green with --provider mock
```

---

## 15. ERRORS AND EXCEPTION CLASSES

```python
# wargame/exceptions.py
class WargameError(Exception): pass
class GroundingError(WargameError): pass       # agent hallucinated a story ID
class ProviderError(WargameError): pass        # LLM call failed
class ScenarioNotFoundError(WargameError): pass
class LowConfidenceError(WargameError): pass   # God Agent confidence < 0.70
class SchemaValidationError(WargameError): pass
```

---

## 16. ENVIRONMENT VARIABLES (.env.example)

```bash
# Provider API keys (only needed for non-mock providers)
GEMINI_API_KEY=             # Get free at: aistudio.google.com
DEEPSEEK_API_KEY=           # Get at: platform.deepseek.com
OPENAI_API_KEY=             # Get at: platform.openai.com

# Infrastructure
CHROMA_HOST=localhost       # chromadb in docker-compose
CHROMA_PORT=8001
DATABASE_URL=sqlite:///./output/wargame.db

# Simulation defaults
DEFAULT_PROVIDER=mock
DEFAULT_SPRINTS=8
DEFAULT_TURNS_PER_SPRINT=10

# Dashboard
DASHBOARD_PORT=8000
```

---

## 17. FIRST MESSAGE AFTER THIS BRIEFING

After acknowledging this briefing, implement **Phase P0 only**.
Do not implement P1 until I explicitly say "implement P1".

Start with this exact sequence:
1. Create full folder structure (all files as stubs with correct imports)
2. Write `pyproject.toml` complete
3. Write `wargame/models/` — all 4 Pydantic models (no stubs, fully implemented)
4. Write `wargame/exceptions.py`
5. Write `wargame/providers/base.py` + `wargame/providers/mock.py` (fully working)
6. Write `wargame/providers/factory.py`
7. Write `wargame/core/state.py` WorldState (fully working)
8. Write `wargame/memory/interaction_log.py` SQLAlchemy models + Alembic config
9. Write `wargame/cli.py` with `run` and `serve` commands
10. Write `seeds/etp/backlog.json` (30 stories — real data, not placeholder)
11. Write `seeds/etp/agent_profiles.json` (8 agents — real data)
12. Write `seeds/etp/constraints.json`
13. Write `docker-compose.yml`
14. Write `.env.example`
15. Write `README.md` (brief, with quickstart)
16. Run: `pip install -e ".[dev]"` then `python -m wargame run --provider mock --scenario seeds/etp/ --sprints 1`
17. Fix any errors until the P0 gate passes.
18. Report back with: files created, gate result, any issues found.
