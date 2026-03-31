from wargame.providers.base import BaseLLMProvider


def build_provider(name: str, model: str | None = None) -> BaseLLMProvider:
    if name == "mock":
        from wargame.providers.mock import MockProvider
        return MockProvider()
    elif name == "gemini-free":
        from wargame.providers.gemini import GeminiProvider
        return GeminiProvider(model=model or "gemini-2.0-flash")
    elif name == "deepseek":
        from wargame.providers.deepseek import DeepSeekProvider
        return DeepSeekProvider(model=model or "deepseek-chat")
    elif name == "openai":
        from wargame.providers.openai_provider import OpenAIProvider
        return OpenAIProvider(model=model or "gpt-4o-mini")
    else:
        raise ValueError(f"Unknown provider: {name}. Choose from: mock, gemini-free, deepseek, openai")
