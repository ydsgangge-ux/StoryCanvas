from typing import AsyncGenerator
import httpx
import json as json_mod
from backend.llm.base import BaseLLM


class GeminiProvider(BaseLLM):
    """Google Gemini API 提供商"""

    def __init__(self, api_key: str, model: str = "gemini-1.5-pro"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://generativelanguage.googleapis.com/v1beta"

    async def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.8) -> str:
        full_text = ""
        async for chunk in self.chat_stream(system_prompt, user_prompt, temperature):
            full_text += chunk
        return full_text

    async def chat_stream(self, system_prompt: str, user_prompt: str,
                          temperature: float = 0.8) -> AsyncGenerator[str, None]:
        if not self.api_key:
            yield "[提示: 请设置 Gemini 的 API Key]"
            return

        contents = [{"role": "user", "parts": [{"text": user_prompt}]}]

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 4096,
            },
        }

        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}

        url = f"{self.base_url}/models/{self.model}:streamGenerateContent?alt=sse&key={self.api_key}"

        async with httpx.AsyncClient(timeout=180.0) as client:
            async with client.stream(
                "POST",
                url,
                headers={"Content-Type": "application/json"},
                json=payload,
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    yield f"[Gemini API错误 {response.status_code}]: {error_text.decode('utf-8', errors='replace')[:200]}"
                    return

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data = line[6:].strip()
                        if not data:
                            continue
                        try:
                            chunk = json_mod.loads(data)
                            candidates = chunk.get("candidates", [])
                            if candidates:
                                content = candidates[0].get("content", {})
                                parts = content.get("parts", [])
                                for part in parts:
                                    yield part.get("text", "")
                        except json_mod.JSONDecodeError:
                            continue
