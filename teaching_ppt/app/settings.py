from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Teaching PPT Generator"
    output_dir: Path = Path("data/outputs")
    httpx_timeout_s: float = 120.0

    # DeepSeek（仅服务端读取，不在网页填写）
    deepseek_api_base: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"
    deepseek_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    s = Settings()
    s.output_dir.mkdir(parents=True, exist_ok=True)
    return s
