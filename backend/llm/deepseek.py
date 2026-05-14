from typing import AsyncGenerator
import httpx
from backend.core.config import settings
from backend.llm.base import BaseLLM


class DeepSeekProvider(BaseLLM):
    def __init__(self):
        self.api_key = settings.deepseek_api_key
        self.model = settings.deepseek_model
        self.base_url = "https://api.deepseek.com/v1"

    async def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.8) -> str:
        full_text = ""
        async for chunk in self.chat_stream(system_prompt, user_prompt, temperature):
            full_text += chunk
        return full_text

    async def chat_stream(self, system_prompt: str, user_prompt: str,
                          temperature: float = 0.8) -> AsyncGenerator[str, None]:
        if not self.api_key:
            yield "[提示: 请设置 DEEPSEEK_API_KEY 环境变量]"
            return

        async with httpx.AsyncClient(timeout=120.0) as client:
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
