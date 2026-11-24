from functools import lru_cache
from typing import Literal
from urllib.parse import urlparse

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    supabase_url: str
    supabase_publishable_key: str
    gemini_api_key: SecretStr = SecretStr("")
    groq_api_key: SecretStr = SecretStr("")
    gemini_model: str = Field(default="", max_length=200)
    groq_model: str = Field(default="", max_length=200)
    ai_primary_provider: Literal["gemini", "groq"] = "gemini"
    ai_fallback_enabled: bool = False
    ai_free_tier_confirmed: bool = False
    cors_origins: list[str] = ["http://localhost:5173"]

    @field_validator("supabase_url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        url = urlparse(value)
        if not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError("Set a valid Supabase project origin")
        if url.path not in ("", "/"):
            raise ValueError("Supabase URL must not include a path")
        if url.scheme != "https" and not (
            url.scheme == "http" and url.hostname in ("localhost", "127.0.0.1")
        ):
            raise ValueError("Supabase must use HTTPS (except local development)")
        return value.rstrip("/")

    @field_validator("supabase_publishable_key")
    @classmethod
    def validate_key(cls, value: str) -> str:
        if not value.startswith("sb_publishable_") or len(value) < 20:
            raise ValueError("Use a Supabase publishable key, never a backend secret")
        return value

    @field_validator("cors_origins")
    @classmethod
    def validate_origins(cls, origins: list[str]) -> list[str]:
        if not origins or any(
            urlparse(origin).scheme not in ("http", "https")
            or not urlparse(origin).hostname
            or urlparse(origin).path not in ("", "/")
            or urlparse(origin).query
            or urlparse(origin).fragment
            or urlparse(origin).username
            for origin in origins
        ):
            raise ValueError("CORS origins must be explicit HTTP(S) origins")
        return [origin.rstrip("/") for origin in origins]


@lru_cache
def get_settings() -> Settings:
    return Settings()
