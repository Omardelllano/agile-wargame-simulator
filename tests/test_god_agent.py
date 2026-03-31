"""
tests/test_god_agent.py
SprintReport Pydantic validation, confidence scoring, heuristic insights.
Uses mock provider + in-memory SQLite — zero API keys required.
"""
import pytest

from wargame.god_agent.reducer import GodAgentReducer
from wargame.models.sprint_report import SprintReport
from wargame.models.world_state import SprintMetrics, Story, WorldState
from wargame.providers.mock import MockProvider


# ---------------------------------------------------------------------------
# Shared world state
# ---------------------------------------------------------------------------

@pytest.fixture
def world_state():
    ws = WorldState(
        simulation_id="test-god-agent",
        scenario="etp",
        total_sprints=2,
        current_sprint=1,
        current_turn=5,
        stories=[
            Story(id="HU-001", epic_id="EPIC-01", title="Configure API Gateway", points=8),
            Story(id="HU-002", epic_id="EPIC-01", title="Define microservice domains", points=5),
        ],
    )
    ws.sprint_history.append(SprintMetrics(sprint=1, velocity=13, friction_index=0.4))
    return ws


@pytest.fixture
def reducer():
    return GodAgentReducer(provider=MockProvider())


# ---------------------------------------------------------------------------
# MAP result fixtures (plain dicts, as returned by mapper functions)
# ---------------------------------------------------------------------------

@pytest.fixture
def rich_map_results():
    friction_map = {
        "sprint": 1,
        "total_friction_events": 4,
        "friction_index": 0.5,
        "friction_hotspots": [
            {
                "agent_pair": ["product_owner", "tech_lead"],
                "conflict_count": 4,
                "root_cause": "Tech Lead perfectionism vs. Product Owner scope pressure",
            }
        ],
    }
    deps_map = {
        "sprint": 1,
        "total_blocked": 1,
        "blocked_dependencies": [
            {
                "story_id": "HU-001",
                "blocked_by_agent": "qa_engineer",
                "blocking_reason": "Integration test failing under load",
                "days_blocked": 2,
                "impact": "MEDIUM",
            }
        ],
    }
    debt_map = {"sprint": 1, "tech_debt_delta": 13, "debt_by_agent": {"tech_lead": 5, "security_architect": 8}}
    vel_map  = {"sprint": 1, "velocity": 13, "velocity_decay_pct": 0.0, "total_completed": 2}
    return friction_map, deps_map, debt_map, vel_map


@pytest.fixture
def empty_map_results():
    return (
        {"sprint": 1, "total_friction_events": 0, "friction_hotspots": []},
        {"sprint": 1, "total_blocked": 0, "blocked_dependencies": []},
        {"sprint": 1, "tech_debt_delta": 0, "debt_by_agent": {}},
        {"sprint": 1, "velocity": 0, "velocity_decay_pct": 0.0, "total_completed": 0},
    )


# ---------------------------------------------------------------------------
# SprintReport Pydantic validation
# ---------------------------------------------------------------------------

def test_sprint_report_pydantic_schema_valid():
    report = SprintReport(
        simulation_id="sim-001",
        sprint=1,
        confidence_score=0.85,
        is_reliable=True,
        friction_index=0.3,
        tech_debt_delta=5,
        velocity=21,
        velocity_decay_pct=0.0,
    )
    assert report.simulation_id == "sim-001"
    assert report.sprint == 1
    assert report.is_reliable is True


def test_sprint_report_reliability_threshold():
    assert SprintReport.reliability_threshold() == 0.70


def test_sprint_report_is_reliable_when_confidence_above_threshold():
    report = SprintReport(
        simulation_id="sim-001",
        sprint=1,
        confidence_score=0.85,
        is_reliable=True,
        friction_index=0.0,
        tech_debt_delta=0,
        velocity=10,
        velocity_decay_pct=0.0,
    )
    assert report.confidence_score >= SprintReport.reliability_threshold()
    assert report.is_reliable is True


# ---------------------------------------------------------------------------
# Reducer confidence scoring
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_reducer_produces_report_with_rich_data(reducer, rich_map_results, world_state):
    report = await reducer.reduce(rich_map_results, world_state)

    assert isinstance(report, SprintReport)
    assert report.sprint == 1
    assert report.confidence_score >= 0.70, f"confidence={report.confidence_score}"
    assert report.is_reliable is True
    assert report.velocity == 13
    assert report.tech_debt_delta == 13


@pytest.mark.asyncio
async def test_reducer_confidence_increases_with_data(reducer, world_state):
    """More signal (friction + blocked + velocity) should push confidence higher."""
    empty = (
        {"sprint": 1, "total_friction_events": 0, "friction_hotspots": []},
        {"sprint": 1, "total_blocked": 0, "blocked_dependencies": []},
        {"sprint": 1, "tech_debt_delta": 0, "debt_by_agent": {}},
        {"sprint": 1, "velocity": 0, "velocity_decay_pct": 0.0, "total_completed": 0},
    )
    rich = (
        {"sprint": 1, "total_friction_events": 3, "friction_hotspots": [
            {"agent_pair": ["tech_lead", "product_owner"], "conflict_count": 3, "root_cause": "scope"}
        ]},
        {"sprint": 1, "total_blocked": 2, "blocked_dependencies": [
            {"story_id": "HU-001", "blocked_by_agent": "qa_engineer", "blocking_reason": "test fail", "days_blocked": 1, "impact": "MEDIUM"},
        ]},
        {"sprint": 1, "tech_debt_delta": 5, "debt_by_agent": {}},
        {"sprint": 1, "velocity": 8, "velocity_decay_pct": 0.0, "total_completed": 1},
    )
    r_empty = await reducer.reduce(empty, world_state)
    r_rich  = await reducer.reduce(rich, world_state)

    assert r_rich.confidence_score >= r_empty.confidence_score


@pytest.mark.asyncio
async def test_heuristic_generates_risks_for_friction(reducer, rich_map_results, world_state):
    report = await reducer.reduce(rich_map_results, world_state)

    assert len(report.predicted_risks) > 0
    severities = {r.severity for r in report.predicted_risks}
    assert severities <= {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


@pytest.mark.asyncio
async def test_heuristic_generates_recommendations(reducer, rich_map_results, world_state):
    report = await reducer.reduce(rich_map_results, world_state)

    assert len(report.recommendations) > 0
    assert all(isinstance(r, str) for r in report.recommendations)


@pytest.mark.asyncio
async def test_empty_data_still_produces_valid_report(reducer, empty_map_results, world_state):
    report = await reducer.reduce(empty_map_results, world_state)

    assert isinstance(report, SprintReport)
    assert report.velocity == 0
    assert report.tech_debt_delta == 0
    # At least a fallback recommendation
    assert len(report.recommendations) >= 1
