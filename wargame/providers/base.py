import json
import re
from abc import ABC, abstractmethod

from wargame.exceptions import SchemaValidationError
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

    def _parse_response(self, raw: str) -> AgentResponse:
        """Extract JSON from LLM output and validate into AgentResponse."""
        # Strip markdown fences
        text = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.MULTILINE)
        text = re.sub(r"\s*```$", "", text.strip(), flags=re.MULTILINE)
        # Extract first JSON object
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise SchemaValidationError(
                f"No JSON object found in LLM response: {raw[:200]}"
            )
        try:
            data = json.loads(match.group())
            return AgentResponse(**data)
        except Exception as exc:
            raise SchemaValidationError(
                f"Failed to parse AgentResponse: {exc}"
            ) from exc
