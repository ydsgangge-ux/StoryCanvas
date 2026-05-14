import os
from dotenv import load_dotenv
import json

load_dotenv()

LLM_CONFIG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'llm_settings.json')


def load_llm_settings() -> dict:
    """从JSON文件加载LLM设置，如果文件不存在则从环境变量读取"""
    if os.path.exists(LLM_CONFIG_FILE):
        try:
            with open(LLM_CONFIG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def save_llm_settings(settings: dict):
    """保存LLM设置到JSON文件"""
    os.makedirs(os.path.dirname(LLM_CONFIG_FILE), exist_ok=True)
    with open(LLM_CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


class Settings:
    # LLM - 从环境变量读取默认值，但优先使用JSON中的设置
    _llm_settings = load_llm_settings()

    @property
    def llm_provider(self) -> str:
        return self._llm_settings.get("provider", os.getenv("LLM_PROVIDER", "deepseek"))

    @property
    def llm_config(self) -> dict:
        """获取当前提供商的完整配置"""
        provider = self.llm_provider
        configs = self._llm_settings.get("configs", {})
        return configs.get(provider, {})

    # DeepSeek
    @property
    def deepseek_api_key(self) -> str:
        return self.llm_config.get("api_key", os.getenv("DEEPSEEK_API_KEY", ""))

    @property
    def deepseek_model(self) -> str:
        return self.llm_config.get("model", os.getenv("DEEPSEEK_MODEL", "deepseek-chat"))

    # OpenAI
    @property
    def openai_api_key(self) -> str:
        cfg = self._llm_settings.get("configs", {}).get("openai", {})
        return cfg.get("api_key", os.getenv("OPENAI_API_KEY", ""))

    @property
    def openai_model(self) -> str:
        cfg = self._llm_settings.get("configs", {}).get("openai", {})
        return cfg.get("model", os.getenv("OPENAI_MODEL", "gpt-4o"))

    @property
    def openai_base_url(self) -> str:
        cfg = self._llm_settings.get("configs", {}).get("openai", {})
        return cfg.get("base_url", os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"))

    # Claude
    @property
    def claude_api_key(self) -> str:
        cfg = self._llm_settings.get("configs", {}).get("claude", {})
        return cfg.get("api_key", os.getenv("CLAUDE_API_KEY", ""))

    @property
    def claude_model(self) -> str:
        cfg = self._llm_settings.get("configs", {}).get("claude", {})
        return cfg.get("model", os.getenv("CLAUDE_MODEL", "claude-3-sonnet-20240229"))

    @property
    def claude_base_url(self) -> str:
        cfg = self._llm_settings.get("configs", {}).get("claude", {})
        return cfg.get("base_url", os.getenv("CLAUDE_BASE_URL", "https://api.anthropic.com"))

    # Gemini
    @property
    def gemini_api_key(self) -> str:
        cfg = self._llm_settings.get("configs", {}).get("gemini", {})
        return cfg.get("api_key", os.getenv("GEMINI_API_KEY", ""))

    @property
    def gemini_model(self) -> str:
        cfg = self._llm_settings.get("configs", {}).get("gemini", {})
        return cfg.get("model", os.getenv("GEMINI_MODEL", "gemini-1.5-pro"))

    # Ollama
    @property
    def ollama_base_url(self) -> str:
        cfg = self._llm_settings.get("configs", {}).get("ollama", {})
        return cfg.get("base_url", os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))

    @property
    def ollama_model(self) -> str:
        cfg = self._llm_settings.get("configs", {}).get("ollama", {})
        return cfg.get("model", os.getenv("OLLAMA_MODEL", "qwen2.5"))

    # 自定义
    @property
    def custom_base_url(self) -> str:
        cfg = self._llm_settings.get("configs", {}).get("custom", {})
        return cfg.get("base_url", os.getenv("CUSTOM_BASE_URL", ""))

    @property
    def custom_api_key(self) -> str:
        cfg = self._llm_settings.get("configs", {}).get("custom", {})
        return cfg.get("api_key", os.getenv("CUSTOM_API_KEY", ""))

    @property
    def custom_model(self) -> str:
        cfg = self._llm_settings.get("configs", {}).get("custom", {})
        return cfg.get("model", os.getenv("CUSTOM_MODEL", ""))

    # Server
    port: int = int(os.getenv("PORT", "8767"))
    database_path: str = os.getenv("DATABASE_PATH", "./backend/data/storycanvas.db")
    story_cards_path: str = os.getenv("STORY_CARDS_PATH", "./backend/story_cards/cards.json")

    # Generation
    default_temperature: float = float(os.getenv("DEFAULT_TEMPERATURE", "0.8"))
    audit_temperature: float = float(os.getenv("AUDIT_TEMPERATURE", "0.0"))
    max_retries: int = int(os.getenv("MAX_RETRIES", "2"))
    chapter_word_target: int = int(os.getenv("CHAPTER_WORD_TARGET", "3000"))

    def get_settings_dict(self) -> dict:
        """返回完整设置字典（供前端使用）"""
        return {
            "provider": self.llm_provider,
            "configs": self._llm_settings.get("configs", {}),
        }

    def update_settings(self, new_settings: dict):
        """更新设置并保存"""
        self._llm_settings.update(new_settings)
        save_llm_settings(self._llm_settings)


settings = Settings()
