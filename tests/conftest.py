import pytest
from wargame.providers.mock import MockProvider
from wargame.models.world_state import WorldState, Story
import uuid


@pytest.fixture
def mock_provider():
    return MockProvider()


@pytest.fixture
def sample_world_state():
    return WorldState(
        simulation_id=str(uuid.uuid4()),
        scenario="etp",
        stories=[
            Story(id="HU-001", epic_id="EPIC-01", title="Configure API Gateway", points=8),
            Story(id="HU-002", epic_id="EPIC-01", title="Define microservice boundaries", points=5),
        ]
    )
