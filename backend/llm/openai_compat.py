from typing import AsyncGenerator
import httpx
from backend.llm.base import BaseLLM


class OpenAICompatibleProvider(BaseLLM):
    """OpenAI 兼容协议提供商（适用于 DeepSeek、OpenAI、以及任何兼容 OpenAI API 格式的服务）"""

    def __init__(self, api_key: str, model: str, base_url: str):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url.rstrip('/')

    async def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.8) -> str:
        full_text = ""
        async for chunk in self.chat_stream(system_prompt, user_prompt, temperature):
            full_text += chunk
        return full_text

    async def chat_stream(self, system_prompt: str, user_prompt: str,
                          temperature: float = 0.8) -> AsyncGenerator[str, None]:
        if not self.api_key:
            yield f"[提示: 请设置 {self._provider_name()} 的 API Key]"
            return
        if not self.model:
            yield "[提示: 请设置模型名称]"
            return

        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    "temperature": temperature,
                    "stream": True
                }
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    yield f"[API错误 {response.status_code}]: {error_text.decode('utf-8', errors='replace')[:200]}"
                    return

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        import json
                        try:
                            chunk = json.loads(data)
                            delta = chunk["choices"][0].get("delta", {})
                            if "content" in delta:
                                yield delta["content"]
                        except (json.JSONDecodeError, KeyError):
                            continue

    def _provider_name(self) -> str:
        if "deepseek" in self.base_url:
            return "DeepSeek"
        elif "openai" in self.base_url:
            return "OpenAI"
        return "自定义API"
