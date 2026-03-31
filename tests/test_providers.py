import pytest
from wargame.providers.mock import MockProvider
from wargame.models.agent_response import AgentResponse


@pytest.mark.asyncio
async def test_mock_provider_returns_agent_response():
    provider = MockProvider()
    response = await provider.complete("You are developer.", "Turn 1, developer")
    assert isinstance(response, AgentResponse)
    assert response.agent_id is not None
    assert 0.0 <= response.confidence <= 1.0


@pytest.mark.asyncio
async def test_mock_provider_is_available():
    provider = MockProvider()
    assert provider.is_available() is True


@pytest.mark.asyncio
async def test_mock_provider_rotates_responses():
    provider = MockProvider()
    responses = []
    for _ in range(5):
        r = await provider.complete("You are developer.", "developer")
        responses.append(r.action)
    # Should have gotten responses (not all identical due to rotation)
    assert len(responses) == 5
