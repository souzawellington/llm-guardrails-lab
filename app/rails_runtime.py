"""Load NeMo Guardrails and apply the process settings on top of config.yml."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from app.paths import project_root
from app.policy import BLOCKED_REPLIES
from app.settings import Settings


class GuardrailsUnavailable(Exception):
    """The guarded path cannot run until an optional dependency is installed."""


@dataclass(frozen=True)
class GuardResult:
    reply: str
    blocked: bool


def guardrails_dir():
    return project_root() / "guardrails"


def _flow_list(rails_section: Any, name: str) -> list[str]:
    section = getattr(rails_section, name, None)
    if section is None or getattr(section, "flows", None) is None:
        return []
    return list(section.flows)


def _set_flows(rails_section: Any, name: str, flows: list[str]) -> None:
    section = getattr(rails_section, name)
    section.flows = flows


def apply_settings(config: Any, settings: Settings) -> Any:
    """Point the main model at the configured OpenAI-compatible endpoint.

    The key is passed through the LLM_API_KEY environment variable, not a file.
    """
    if settings.llm_api_key:
        os.environ["LLM_API_KEY"] = settings.llm_api_key

    for model in config.models:
        if getattr(model, "type", None) != "main":
            continue
        model.engine = "openai"
        model.model = settings.llm_model
        model.api_key_env_var = "LLM_API_KEY"
        parameters = dict(model.parameters or {})
        parameters["base_url"] = settings.llm_base_url
        parameters["temperature"] = 0.2
        parameters.pop("api_key", None)
        model.parameters = parameters

    if settings.enable_jailbreak_heuristics:
        _require_module("transformers", "pip install torch transformers")
        flows = _flow_list(config.rails, "input")
        if "jailbreak detection heuristics" not in flows:
            flows.insert(0, "jailbreak detection heuristics")
            _set_flows(config.rails, "input", flows)
        if config.rails.config.jailbreak_detection is None:
            from nemoguardrails.library.jailbreak_detection.rail_config import (
                JailbreakDetectionConfig,
            )

            # NVIDIA defaults: length/perplexity 89.79, prefix/suffix perplexity 1845.65.
            # No server_endpoint, so the check runs in-process (testing only).
            config.rails.config.jailbreak_detection = JailbreakDetectionConfig()

    if settings.enable_presidio:
        _require_module("presidio_analyzer", 'pip install "nemoguardrails[sdd]==0.24.1"')
        for section_name, flow_name in (
            ("input", "mask sensitive data on input"),
            ("output", "mask sensitive data on output"),
        ):
            flows = _flow_list(config.rails, section_name)
            if flow_name not in flows:
                flows.append(flow_name)
                _set_flows(config.rails, section_name, flows)
    return config


def _require_module(module: str, install_hint: str) -> None:
    try:
        __import__(module)
    except ImportError as exc:
        raise GuardrailsUnavailable(
            f"Optional rail dependency '{module}' is not installed. {install_hint}"
        ) from exc


def build_rails(settings: Settings) -> Any:
    try:
        from nemoguardrails import LLMRails, RailsConfig
    except ImportError as exc:
        raise GuardrailsUnavailable(
            "NeMo Guardrails is not installed. From the repo root run: "
            "python -m pip install -r requirements-lab.txt"
        ) from exc

    config_path = guardrails_dir()
    if not (config_path / "config.yml").is_file():
        raise GuardrailsUnavailable(f"Guardrails config not found at {config_path}.")

    # RailsConfig checks api_key_env_var while the YAML is parsed.
    if settings.llm_api_key:
        os.environ["LLM_API_KEY"] = settings.llm_api_key

    config = RailsConfig.from_path(str(config_path))
    apply_settings(config, settings)
    return LLMRails(config)


def reply_text(result: Any) -> str:
    if isinstance(result, dict):
        content = result.get("content", "")
        return content.strip() if isinstance(content, str) else str(content).strip()
    if isinstance(result, list) and result:
        last = result[-1]
        if isinstance(last, dict):
            content = last.get("content", "")
            return content.strip() if isinstance(content, str) else str(content).strip()
    if isinstance(result, str):
        return result.strip()
    return ""


def is_blocked(reply: str) -> bool:
    return reply.strip() in BLOCKED_REPLIES


async def guarded_reply(rails: Any, message: str) -> GuardResult:
    result = await rails.generate_async(messages=[{"role": "user", "content": message}])
    text = reply_text(result)
    if not text:
        raise RuntimeError("Guardrails returned an empty reply.")
    return GuardResult(reply=text, blocked=is_blocked(text))
