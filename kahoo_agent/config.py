"""
Configuration manager for kahoo-agent.
"""

import os
from pathlib import Path
from typing import List, Optional
import yaml
from pydantic import BaseModel, Field


class AppConfig(BaseModel):
    debug: bool = False
    log_level: str = "INFO"


class BrowserConfig(BaseModel):
    cdp_url: str = "http://localhost:9222"
    target_url_keyword: str = "kahoot.it"
    tab_timeout_sec: int = 30


class AIConfig(BaseModel):
    provider: str = "gemini"
    api_key: Optional[str] = None
    model_name: str = "gemini-2.5-flash"
    temperature: float = 0.1
    timeout_sec: float = 4.0


class GameplayConfig(BaseModel):
    mode: str = "auto"  # "auto" or "assist"
    answer_delay_sec: float = 0.4
    auto_proceed: bool = True


class VisionConfig(BaseModel):
    roi: Optional[List[int]] = None  # [top, left, width, height]
    poll_interval_sec: float = 0.5


class Settings(BaseModel):
    app: AppConfig = Field(default_factory=AppConfig)
    browser: BrowserConfig = Field(default_factory=BrowserConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    gameplay: GameplayConfig = Field(default_factory=GameplayConfig)
    vision: VisionConfig = Field(default_factory=VisionConfig)

    @classmethod
    def load(cls, config_path: Optional[str] = None) -> "Settings":
        """Load settings from YAML file and environment variables."""
        data = {}

        # Search order for config file
        candidates = []
        if config_path:
            candidates.append(Path(config_path))
        candidates.extend([
            Path("config.yaml"),
            Path("config.yml"),
            Path("config.example.yaml"),
        ])

        for path in candidates:
            if path.exists():
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        loaded = yaml.safe_load(f)
                        if isinstance(loaded, dict):
                            data = loaded
                            break
                except Exception:
                    pass

        # Load environment variables into dictionary
        gemini_key = os.getenv("GEMINI_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")
        cdp_url = os.getenv("KAHOOT_CDP_URL")

        if "ai" not in data:
            data["ai"] = {}
        if gemini_key and not data["ai"].get("api_key"):
            data["ai"]["api_key"] = gemini_key
        elif openai_key and not data["ai"].get("api_key"):
            data["ai"]["api_key"] = openai_key
            data["ai"]["provider"] = "openai"

        if "browser" not in data:
            data["browser"] = {}
        if cdp_url:
            data["browser"]["cdp_url"] = cdp_url

        return cls(**data)


# Global settings instance helper
def get_settings(config_path: Optional[str] = None) -> Settings:
    return Settings.load(config_path)
