from abc import ABC, abstractmethod
from typing import AsyncGenerator, Any, Optional


class BaseLLM(ABC):
    """LLM抽象基类"""

    @abstractmethod
    async def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.8) -> str:
        pass

    @abstractmethod
    async def chat_stream(self, system_prompt: str, user_prompt: str,
                          temperature: float = 0.8) -> AsyncGenerator[str, None]:
        pass

    async def chat_with_tools(self, system_prompt: str, user_prompt: str,
                              tools: list, temperature: float = 0.8,
                              tool_choice: Any = None) -> Optional[dict]:
        """支持 tool calling 的对话方法，返回工具调用参数 dict。
        默认实现：不支持 tool calling 的 provider 返回 None，由调用方 fallback 到普通 chat。
        子类可覆盖此方法以支持 strict tool calling。
        """
        return None


def create_llm() -> BaseLLM:
    """根据当前设置创建LLM实例"""
    from backend.core.config import settings
    provider = settings.llm_provider

    if provider == "ollama":
        from backend.llm.ollama import OllamaProvider
        return OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model
        )
    elif provider == "claude":
        from backend.llm.claude import ClaudeProvider
        return ClaudeProvider(
            api_key=settings.claude_api_key,
            model=settings.claude_model,
            base_url=settings.claude_base_url
        )
    elif provider == "gemini":
        from backend.llm.gemini import GeminiProvider
        return GeminiProvider(
            api_key=settings.gemini_api_key,
            model=settings.gemini_model
        )
    elif provider == "custom":
        from backend.llm.openai_compat import OpenAICompatibleProvider
        return OpenAICompatibleProvider(
            api_key=settings.custom_api_key,
            model=settings.custom_model,
            base_url=settings.custom_base_url
        )
    elif provider == "relay":
        from backend.llm.openai_compat import OpenAICompatibleProvider
        return OpenAICompatibleProvider(
            api_key=settings.relay_api_key,
            model=settings.relay_model,
            base_url=settings.relay_base_url
        )
    elif provider == "openai":
        from backend.llm.openai_compat import OpenAICompatibleProvider
        return OpenAICompatibleProvider(
            api_key=settings.openai_api_key,
            model=settings.openai_model,
            base_url=settings.openai_base_url
        )
    else:  # deepseek (default)
        from backend.llm.openai_compat import OpenAICompatibleProvider
        return OpenAICompatibleProvider(
            api_key=settings.deepseek_api_key,
            model=settings.deepseek_model,
            base_url="https://api.deepseek.com/v1"
        )
