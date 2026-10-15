"""FastAPI lab server: one unguarded chat route and one guarded chat route."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, field_validator

from app import __version__
from app.llm_client import LLMError, LLMTimeout, complete_chat
from app.rails_runtime import GuardrailsUnavailable, build_rails, guarded_reply
from app.settings import Settings, load_settings

logger = logging.getLogger("guardrails_lab")

app = FastAPI(
    title="LLM Guardrails Lab",
    version=__version__,
    description=(
        "Local defensive lab. /v1/chat/raw is the bot before rails. "
        "/v1/chat/guarded is the same bot with NeMo Guardrails."
    ),
)

_rails: object | None = None
_STATIC = Path(__file__).resolve().parent / "static" / "chat.html"


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=32000)

    @field_validator("message")
    @classmethod
    def not_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Message is empty.")
        return cleaned


class ChatResponse(BaseModel):
    reply: str
    guardrails: str
    blocked: bool = False


def reset_rails() -> None:
    """Drop the cached rails object. Tests and a settings change use this."""
    global _rails
    _rails = None


def _settings_or_400() -> Settings:
    try:
        return load_settings()
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _rails_for(settings: Settings) -> object:
    global _rails
    if _rails is None:
        try:
            _rails = build_rails(settings)
        except GuardrailsUnavailable as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
    return _rails


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "llm-guardrails-lab"}


@app.get("/meta")
def meta() -> dict[str, object]:
    settings = _settings_or_400()
    return {
        "service": "llm-guardrails-lab",
        "version": __version__,
        "model": settings.llm_model,
        "llm_host": settings.llm_host,
        "key_configured": settings.key_configured,
        "jailbreak_heuristics": settings.enable_jailbreak_heuristics,
        "presidio": settings.enable_presidio,
        "authentication": "none — bind to localhost only",
    }


@app.get("/ui")
def chat_page() -> FileResponse:
    return FileResponse(_STATIC)


@app.post("/v1/chat/raw", response_model=ChatResponse)
async def chat_raw(body: ChatRequest) -> ChatResponse:
    settings = _settings_or_400()
    try:
        reply = await complete_chat(settings, body.message)
    except LLMTimeout as exc:
        raise HTTPException(status_code=504, detail=str(exc)) from exc
    except LLMError as exc:
        status = 503 if "LLM_API_KEY" in str(exc) or "OPENAI_API_KEY" in str(exc) else 502
        raise HTTPException(status_code=status, detail=str(exc)) from exc
    return ChatResponse(reply=reply, guardrails="off", blocked=False)


@app.post("/v1/chat/guarded", response_model=ChatResponse)
async def chat_guarded(body: ChatRequest) -> ChatResponse:
    settings = _settings_or_400()
    if not settings.key_configured:
        raise HTTPException(
            status_code=503,
            detail="Set LLM_API_KEY, or OPENAI_API_KEY, in the environment.",
        )
    rails = _rails_for(settings)
    try:
        result = await guarded_reply(rails, body.message)
    except GuardrailsUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Guarded chat failed.")
        raise HTTPException(status_code=502, detail="Guarded chat failed.") from exc
    return ChatResponse(reply=result.reply, guardrails="on", blocked=result.blocked)
