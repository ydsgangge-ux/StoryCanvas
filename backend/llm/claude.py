from typing import AsyncGenerator
import httpx
import json as json_mod
from backend.llm.base import BaseLLM


class ClaudeProvider(BaseLLM):
    """Anthropic Claude API 提供商"""

    def __init__(self, api_key: str, model: str, base_url: str = "https://api.anthropic.com"):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip('/')
        self.api_version = "2023-06-01"

    async def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.8) -> str:
        full_text = ""
        async for chunk in self.chat_stream(system_prompt, user_prompt, temperature):
            full_text += chunk
        return full_text

    async def chat_stream(self, system_prompt: str, user_prompt: str,
                          temperature: float = 0.8) -> AsyncGenerator[str, None]:
        if not self.api_key:
            yield "[提示: 请设置 Claude 的 API Key]"
            return

        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": self.api_version,
            "Content-Type": "application/json",
        }

        messages = [{"role": "user", "content": user_prompt}]

        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }

        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/v1/messages",
                headers=headers,
                json=payload,
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    yield f"[Claude API错误 {response.status_code}]: {error_text.decode('utf-8', errors='replace')[:200]}"
                    return

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:].strip()
                        if data == "[DONE]" or not data:
                            continue
                        try:
                            chunk = json_mod.loads(data)
                            if chunk.get("type") == "content_block_delta":
                                delta = chunk.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    yield delta.get("text", "")
                        except json_mod.JSONDecodeError:
                            continue
