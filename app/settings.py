"""Process settings. Secrets stay in the environment and are never written to disk."""

from __future__ import annotations

import os
from urllib.parse import urlparse

from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator

_TRUE = {"1", "true", "yes", "on"}


def _flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in _TRUE


def _api_key() -> str:
    return os.getenv("LLM_API_KEY", "").strip() or os.getenv("OPENAI_API_KEY", "").strip()


class Settings(BaseModel):
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = Field(default=120, gt=0, le=600)
    enable_jailbreak_heuristics: bool = False
    enable_presidio: bool = False
    lab_base_url: str = "http://127.0.0.1:8000"

    @field_validator("llm_base_url", "lab_base_url")
    @classmethod
    def http_url(cls, value: str) -> str:
        cleaned = value.strip().rstrip("/")
        parsed = urlparse(cleaned)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            raise ValueError("URL must start with http:// or https:// and include a host.")
        if parsed.username or parsed.password:
            raise ValueError("URL must not include a username or password.")
        return cleaned

    @property
    def key_configured(self) -> bool:
        return bool(self.llm_api_key)

    @property
    def llm_host(self) -> str:
        return urlparse(self.llm_base_url).netloc


def load_settings() -> Settings:
    """Read environment variables. Existing variables win over the .env file."""
    load_dotenv(override=False)
    timeout = os.getenv("LLM_TIMEOUT_SECONDS", "120").strip() or "120"
    return Settings(
        llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1"),
        llm_api_key=_api_key(),
        llm_model=os.getenv("LLM_MODEL", "gpt-4o-mini").strip() or "gpt-4o-mini",
        llm_timeout_seconds=float(timeout),
        enable_jailbreak_heuristics=_flag("ENABLE_JAILBREAK_HEURISTICS"),
        enable_presidio=_flag("ENABLE_PRESIDIO"),
        lab_base_url=os.getenv("LAB_BASE_URL", "http://127.0.0.1:8000"),
    )
