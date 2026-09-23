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
        # 注意：deepseek-chat 和 deepseek-reasoner 别名将于 2026-07-24 停用，
        # 已迁移到 deepseek-v4-flash（非思考模式）。如需思考模式用 deepseek-v4-pro。
        return self.llm_config.get("model", os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro"))

    @property
    def deepseek_base_url(self) -> str:
        return self.llm_config.get("base_url", os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"))

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

    # MiMo (Xiaomi)
    @property
    def mimo_api_key(self) -> str:
        cfg = self._llm_settings.get("configs", {}).get("mimo", {})
        return cfg.get("api_key", os.getenv("MIMO_API_KEY", ""))

    @property
    def mimo_model(self) -> str:
        cfg = self._llm_settings.get("configs", {}).get("mimo", {})
        return cfg.get("model", os.getenv("MIMO_MODEL", "mimo-v2.6-pro"))

    # GLM (Zhipu)
    @property
    def glm_api_key(self) -> str:
        cfg = self._llm_settings.get("configs", {}).get("glm", {})
        return cfg.get("api_key", os.getenv("GLM_API_KEY", ""))

    @property
    def glm_model(self) -> str:
        cfg = self._llm_settings.get("configs", {}).get("glm", {})
        return cfg.get("model", os.getenv("GLM_MODEL", "glm-5.3"))

    # 腾讯混元 (Hunyuan)
    @property
    def hunyuan_api_key(self) -> str:
        cfg = self._llm_settings.get("configs", {}).get("hunyuan", {})
        return cfg.get("api_key", os.getenv("HUNYUAN_API_KEY", ""))

    @property
    def hunyuan_model(self) -> str:
        cfg = self._llm_settings.get("configs", {}).get("hunyuan", {})
        return cfg.get("model", os.getenv("HUNYUAN_MODEL", "hy4-preview"))

    @property
    def hunyuan_base_url(self) -> str:
        cfg = self._llm_settings.get("configs", {}).get("hunyuan", {})
        return cfg.get("base_url", os.getenv("HUNYUAN_BASE_URL", "https://tokenhub.tencentmaas.com/v1"))

    @property
    def qwen_api_key(self) -> str:
        cfg = self._llm_settings.get("configs", {}).get("qwen", {})
        return cfg.get("api_key", os.getenv("QWEN_API_KEY", ""))

    @property
    def qwen_model(self) -> str:
        cfg = self._llm_settings.get("configs", {}).get("qwen", {})
        return cfg.get("model", os.getenv("QWEN_MODEL", "qwen3.8-flash"))

    @property
    def qwen_base_url(self) -> str:
        cfg = self._llm_settings.get("configs", {}).get("qwen", {})
        return cfg.get("base_url", os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1"))

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

    # 中转站
    @property
    def relay_base_url(self) -> str:
        cfg = self._llm_settings.get("configs", {}).get("relay", {})
        return cfg.get("base_url", os.getenv("RELAY_BASE_URL", ""))

    @property
    def relay_api_key(self) -> str:
        cfg = self._llm_settings.get("configs", {}).get("relay", {})
        return cfg.get("api_key", os.getenv("RELAY_API_KEY", ""))

    @property
    def relay_model(self) -> str:
        cfg = self._llm_settings.get("configs", {}).get("relay", {})
        return cfg.get("model", os.getenv("RELAY_MODEL", ""))

    # 图片生成模型
    @property
    def image_provider(self) -> str:
        return self._llm_settings.get("image_provider", "zhipu_image")

    @property
    def image_config(self) -> dict:
        """获取当前图片生成提供商的完整配置"""
        provider = self.image_provider
        configs = self._llm_settings.get("image_configs", {})
        return configs.get(provider, {})

    @property
    def image_api_key(self) -> str:
        return self.image_config.get("api_key", os.getenv("IMAGE_API_KEY", ""))

    @property
    def image_base_url(self) -> str:
        return self.image_config.get("base_url", os.getenv("IMAGE_BASE_URL", "https://open.bigmodel.cn/api/paas/v4"))

    @property
    def image_model(self) -> str:
        return self.image_config.get("model", os.getenv("IMAGE_MODEL", "cogview-3-flash"))

    @property
    def image_size(self) -> str:
        return self.image_config.get("size", "1024x1024")

    @property
    def image_quality(self) -> str:
        return self.image_config.get("quality", "standard")

    # Server
    port: int = int(os.getenv("PORT", "8767"))
    database_path: str = os.getenv("DATABASE_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'storycanvas.db'))
    story_cards_path: str = os.getenv("STORY_CARDS_PATH", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'story_cards', 'cards.json'))

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
            "image_provider": self.image_provider,
            "image_configs": self._llm_settings.get("image_configs", {}),
        }

    def update_settings(self, new_settings: dict):
        """更新设置并保存"""
        merged = dict(self._llm_settings)
        # configs / image_configs 深合并，避免前端全量提交时用脱敏/空 key 覆盖真实 key
        for config_key in ("configs", "image_configs"):
            old_map = merged.get(config_key, {})
            new_map = new_settings.get(config_key) or {}
            for provider, cfg in new_map.items():
                old_cfg = old_map.get(provider, {})
                for field, value in cfg.items():
                    # 前端会把后端脱敏值(如 sk-1234...abcd)原样写回，必须回退为旧值
                    if field == "api_key" and isinstance(value, str) and "..." in value:
                        cfg[field] = old_cfg.get("api_key", value)
                    # 空 key 视为未修改，保留旧 key（避免误清空）
                    elif field == "api_key" and not value and old_cfg.get("api_key"):
                        cfg[field] = old_cfg["api_key"]
        merged.update(new_settings)
        self._llm_settings = merged
        save_llm_settings(self._llm_settings)


settings = Settings()
