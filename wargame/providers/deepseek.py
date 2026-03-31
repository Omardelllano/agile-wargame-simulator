import os

from wargame.exceptions import ProviderError
from wargame.models.agent_response import AgentResponse
from wargame.providers.base import BaseLLMProvider


class DeepSeekProvider(BaseLLMProvider):
    provider_name = "deepseek"

    def __init__(self, model: str = "deepseek-chat"):
        self.model = model

    async def complete(self, system_prompt: str, user_prompt: str) -> AgentResponse:
        import litellm

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        try:
            response = await litellm.acompletion(
                model=f"deepseek/{self.model}",
                messages=messages,
                api_key=os.environ.get("DEEPSEEK_API_KEY"),
            )
            raw = response.choices[0].message.content
            return self._parse_response(raw)
        except Exception as exc:
            raise ProviderError(f"DeepSeekProvider error: {exc}") from exc

    def is_available(self) -> bool:
        return bool(os.environ.get("DEEPSEEK_API_KEY"))
