"""
tests/test_grounding.py
GroundingError raised on fake story IDs, not raised on real ones.
"""
import pytest

from wargame.agents.base import BaseAgent
from wargame.exceptions import GroundingError
from wargame.models.agent_response import ActionType, AgentResponse
from wargame.models.world_state import Story, WorldState


# ---------------------------------------------------------------------------
# Minimal concrete subclass (no LLM, no vector store)
# ---------------------------------------------------------------------------

class _StubAgent(BaseAgent):
    role = "developer"
    template_name = "developer"

    def _build_user_prompt(self, world_state, turn):
        return "stub"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def world_state():
    return WorldState(
        simulation_id="test-sim",
        scenario="etp",
        stories=[
            Story(id="HU-001", epic_id="EPIC-01", title="Configure API Gateway", points=8),
            Story(id="HU-002", epic_id="EPIC-01", title="Define microservice boundaries", points=5),
        ],
    )


def _response_with(story_ids: list[str]) -> AgentResponse:
    return AgentResponse(
        agent_id="developer",
        turn=1,
        sprint=1,
        action=ActionType.COMPLETE,
        rationale="Some rationale",
        referenced_stories=story_ids,
        confidence=0.9,
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_grounding_raises_on_fake_story_id(world_state):
    agent = _StubAgent.__new__(_StubAgent)
    response = _response_with(["HU-999"])

    with pytest.raises(GroundingError, match="HU-999"):
        agent._validate_grounding(response, world_state)


def test_grounding_passes_on_real_story_id(world_state):
    agent = _StubAgent.__new__(_StubAgent)
    response = _response_with(["HU-001"])

    # must not raise
    agent._validate_grounding(response, world_state)


def test_grounding_passes_on_multiple_real_ids(world_state):
    agent = _StubAgent.__new__(_StubAgent)
    response = _response_with(["HU-001", "HU-002"])

    agent._validate_grounding(response, world_state)


def test_grounding_raises_on_mixed_ids(world_state):
    """Real ID + fake ID must still raise GroundingError."""
    agent = _StubAgent.__new__(_StubAgent)
    response = _response_with(["HU-001", "HU-999"])

    with pytest.raises(GroundingError, match="HU-999"):
        agent._validate_grounding(response, world_state)


def test_grounding_passes_with_empty_referenced_stories(world_state):
    agent = _StubAgent.__new__(_StubAgent)
    response = _response_with([])

    agent._validate_grounding(response, world_state)
