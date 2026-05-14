from typing import AsyncGenerator
import httpx
import json as json_mod
from backend.llm.base import BaseLLM


class OllamaProvider(BaseLLM):
    """Ollama 本地模型提供商"""

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "qwen2.5"):
        self.base_url = base_url.rstrip('/')
        self.model = model

    async def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0.8) -> str:
        full_text = ""
        async for chunk in self.chat_stream(system_prompt, user_prompt, temperature):
            full_text += chunk
        return full_text

    async def chat_stream(self, system_prompt: str, user_prompt: str,
                          temperature: float = 0.8) -> AsyncGenerator[str, None]:
        async with httpx.AsyncClient(timeout=300.0) as client:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": user_prompt})

            async with client.stream(
                "POST",
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": messages,
                    "options": {"temperature": temperature},
                    "stream": True
                }
            ) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    yield f"[Ollama错误 {response.status_code}]: {error_text.decode('utf-8', errors='replace')[:200]}"
                    return

                async for line in response.aiter_lines():
                    if line.strip():
                        try:
                            data = json_mod.loads(line)
                            if "message" in data and "content" in data["message"]:
                                yield data["message"]["content"]
                            if data.get("done"):
                                break
                        except json_mod.JSONDecodeError:
                            continue

    async def list_models(self) -> list:
        """获取Ollama本地已安装的模型列表"""
        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                response = await client.get(f"{self.base_url}/api/tags")
                if response.status_code == 200:
                    data = response.json()
                    return [m["name"] for m in data.get("models", [])]
            except Exception:
                pass
            return []
