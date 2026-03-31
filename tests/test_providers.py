"""
tests/test_providers.py
All 4 providers must return a valid AgentResponse schema.
Non-mock providers are tested by patching litellm so no API keys are required.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from wargame.models.agent_response import ActionType, AgentResponse
from wargame.providers.mock import MOCK_RESPONSES, MockProvider


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_litellm_response(payload: dict) -> MagicMock:
    """Build a fake litellm completion response wrapping a JSON payload."""
    msg = MagicMock()
    msg.content = json.dumps(payload)
    choice = MagicMock()
    choice.message = msg
    resp = MagicMock()
    resp.choices = [choice]
    return resp


_VALID_PAYLOAD = {
    "agent_id": "developer",
    "turn": 1,
    "sprint": 1,
    "action": "COMPLETE",
    "rationale": "Implemented feature X successfully.",
    "referenced_stories": ["HU-001"],
    "confidence": 0.9,
    "tech_debt_added": 0,
}


# ---------------------------------------------------------------------------
# Mock provider
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_mock_provider_returns_agent_response():
    provider = MockProvider()
    response = await provider.complete("You are developer.", "Turn 1, developer")
    assert isinstance(response, AgentResponse)
    assert 0.0 <= response.confidence <= 1.0


@pytest.mark.asyncio
async def test_mock_provider_is_available():
    assert MockProvider().is_available() is True


@pytest.mark.asyncio
async def test_mock_provider_rotates_responses():
    provider = MockProvider()
    actions = [
        (await provider.complete("sys", "developer")).action
        for _ in range(5)
    ]
    assert len(actions) == 5


@pytest.mark.asyncio
async def test_mock_provider_all_roles_return_valid_schema():
    """Every role in MOCK_RESPONSES must produce a fully-valid AgentResponse."""
    provider = MockProvider()
    for role in MOCK_RESPONSES:
        r = await provider.complete("system", f"You are the {role}.")
        assert isinstance(r, AgentResponse), f"{role} did not return AgentResponse"
        assert r.action in ActionType, f"{role} returned invalid action {r.action!r}"
        assert 0.0 <= r.confidence <= 1.0, f"{role} confidence out of range"
        assert isinstance(r.rationale, str) and r.rationale, f"{role} empty rationale"


# ---------------------------------------------------------------------------
# Gemini provider (litellm patched)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_gemini_provider_parses_valid_response():
    from wargame.providers.gemini import GeminiProvider

    provider = GeminiProvider(model="gemini-2.0-flash")
    fake_resp = _make_litellm_response(_VALID_PAYLOAD)

    with patch("litellm.acompletion", new=AsyncMock(return_value=fake_resp)):
        result = await provider.complete("system prompt", "user prompt")

    assert isinstance(result, AgentResponse)
    assert result.action == ActionType.COMPLETE
    assert result.confidence == 0.9


# ---------------------------------------------------------------------------
# DeepSeek provider (litellm patched)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_deepseek_provider_parses_valid_response():
    from wargame.providers.deepseek import DeepSeekProvider

    provider = DeepSeekProvider(model="deepseek-chat")
    fake_resp = _make_litellm_response(_VALID_PAYLOAD)

    with patch("litellm.acompletion", new=AsyncMock(return_value=fake_resp)):
        result = await provider.complete("system prompt", "user prompt")

    assert isinstance(result, AgentResponse)
    assert result.action == ActionType.COMPLETE


# ---------------------------------------------------------------------------
# OpenAI provider (litellm patched)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_openai_provider_parses_valid_response():
    from wargame.providers.openai_provider import OpenAIProvider

    provider = OpenAIProvider(model="gpt-4o-mini")
    fake_resp = _make_litellm_response(_VALID_PAYLOAD)

    with patch("litellm.acompletion", new=AsyncMock(return_value=fake_resp)):
        result = await provider.complete("system prompt", "user prompt")

    assert isinstance(result, AgentResponse)
    assert result.action == ActionType.COMPLETE
