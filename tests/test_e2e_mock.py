"""
tests/test_e2e_mock.py
Full end-to-end simulation: 8 agents, 5 turns, mock provider.
Verifies:
  - All 8 agents produce AgentResponse objects
  - DB rows written (interaction_turns + agent_events + sprint_reports)
  - sprint_01.json is written and parses as valid SprintReport
  - Simulation ID is consistent across all records
"""
import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from wargame.core.orchestrator import Orchestrator
from wargame.memory.interaction_log import InteractionTurn, SprintReportRow
from wargame.models.sprint_report import SprintReport
from wargame.providers.mock import MockProvider


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def scenario_path():
    return "seeds/etp"


@pytest.fixture
def db_url(tmp_path):
    return f"sqlite:///{tmp_path}/test_wargame.db"


@pytest.fixture
def output_dir(tmp_path):
    d = tmp_path / "output"
    d.mkdir()
    return d


@pytest.fixture
def orchestrator(scenario_path, db_url, output_dir):
    return Orchestrator(
        provider=MockProvider(),
        scenario_path=scenario_path,
        total_sprints=1,
        db_url=db_url,
        output_dir=str(output_dir),
        turns_per_sprint=5,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_full_simulation_runs_without_error(orchestrator):
    reports = await orchestrator.run()

    assert len(reports) == 1
    assert isinstance(reports[0], SprintReport)


@pytest.mark.asyncio
async def test_all_8_agents_contribute(orchestrator):
    collected_responses = []

    def on_turn(sprint, turn, responses):
        collected_responses.extend(responses)

    await orchestrator.run(on_turn_complete=on_turn)

    agent_ids = {r.agent_id for r in collected_responses}
    # Core roles must be present; developer may appear as role or display_name slug
    non_dev = {"qa_engineer", "tech_lead", "product_owner",
               "security_architect", "cloud_engineer", "scrum_master", "software_architect"}
    assert non_dev.issubset(agent_ids), f"Missing agents: {non_dev - agent_ids}"
    has_dev = "developer" in agent_ids or any(a.startswith("dev_agent") for a in agent_ids)
    assert has_dev, "No developer agent found in responses"


@pytest.mark.asyncio
async def test_5_turns_per_sprint_run(orchestrator):
    turns_seen = []

    def on_turn(sprint, turn, responses):
        turns_seen.append(turn)

    await orchestrator.run(on_turn_complete=on_turn)

    assert turns_seen == list(range(1, 6)), f"Turns: {turns_seen}"


@pytest.mark.asyncio
async def test_db_rows_written(orchestrator, db_url):
    sim_id = orchestrator.state.simulation_id
    await orchestrator.run()

    engine = create_engine(db_url)
    with Session(engine) as session:
        turn_rows = session.query(InteractionTurn).filter_by(simulation_id=sim_id).all()
        report_rows = session.query(SprintReportRow).filter_by(simulation_id=sim_id).all()

    # agents × 5 turns (9 agents when dual-dev is active from agent_profiles.json)
    agents_count = len(orchestrator._agents)
    expected_rows = agents_count * 5
    assert len(turn_rows) == expected_rows, f"Expected {expected_rows} turn rows, got {len(turn_rows)}"
    assert len(report_rows) == 1


@pytest.mark.asyncio
async def test_sprint_report_json_written(orchestrator, output_dir):
    await orchestrator.run()

    sim_id = orchestrator.state.simulation_id
    report_path = output_dir / sim_id / "sprint_01.json"
    assert report_path.exists(), f"sprint_01.json not written at {report_path}"

    data = json.loads(report_path.read_text(encoding="utf-8"))
    report = SprintReport(**data)

    assert report.sprint == 1
    assert report.simulation_id == orchestrator.state.simulation_id
    assert report.confidence_score >= 0.0
    assert isinstance(report.is_reliable, bool)


@pytest.mark.asyncio
async def test_sprint_report_confidence_and_reliability(orchestrator):
    """With 5 turns of mock data the confidence score must reach the reliable threshold."""
    reports = await orchestrator.run()
    report = reports[0]

    assert report.confidence_score >= SprintReport.reliability_threshold(), (
        f"confidence={report.confidence_score} below threshold"
    )
    assert report.is_reliable is True


@pytest.mark.asyncio
async def test_simulation_id_consistent_in_db(orchestrator, db_url):
    sim_id = orchestrator.state.simulation_id
    await orchestrator.run()

    engine = create_engine(db_url)
    with Session(engine) as session:
        turn_sims = {r.simulation_id for r in session.query(InteractionTurn).all()}
        report_sims = {r.simulation_id for r in session.query(SprintReportRow).all()}

    assert turn_sims == {sim_id}
    assert report_sims == {sim_id}


@pytest.mark.asyncio
async def test_on_sprint_complete_callback_fires(orchestrator):
    sprint_reports_received = []

    def on_sprint(report):
        sprint_reports_received.append(report)

    await orchestrator.run(on_sprint_complete=on_sprint)

    assert len(sprint_reports_received) == 1
    assert isinstance(sprint_reports_received[0], SprintReport)
