"""OpenAI-compatible chat client for the unguarded path."""

from __future__ import annotations

import httpx

from app.policy import SYSTEM_POLICY
from app.settings import Settings


class LLMError(Exception):
    """The model endpoint failed or returned a shape we cannot use."""


def redact(text: str, secret: str) -> str:
    if secret and secret in text:
        return text.replace(secret, "[redacted]")
    return text


def _message_text(content: object) -> str:
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") in {None, "text"}:
                parts.append(str(item.get("text", "")))
        return "\n".join(part for part in parts if part).strip()
    return ""


async def complete_chat(
    settings: Settings,
    message: str,
    client: httpx.AsyncClient | None = None,
) -> str:
    if not settings.key_configured:
        raise LLMError("Set LLM_API_KEY, or OPENAI_API_KEY, in the environment.")

    owns_client = client is None
    http = client or httpx.AsyncClient(timeout=settings.llm_timeout_seconds)
    try:
        try:
            response = await http.post(
                f"{settings.llm_base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.llm_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.llm_model,
                    "temperature": 0.2,
                    "messages": [
                        {"role": "system", "content": SYSTEM_POLICY},
                        {"role": "user", "content": message},
                    ],
                },
            )
        except httpx.HTTPError as exc:
            raise LLMError(redact(str(exc), settings.llm_api_key)) from exc

        if response.status_code >= 400:
            body = redact(response.text[:300], settings.llm_api_key)
            raise LLMError(f"Model endpoint returned HTTP {response.status_code}: {body}")

        try:
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise LLMError("Model endpoint returned an unexpected response.") from exc

        text = _message_text(content)
        if not text:
            raise LLMError("Model endpoint returned an empty reply.")
        return text
    finally:
        if owns_client:
            await http.aclose()
