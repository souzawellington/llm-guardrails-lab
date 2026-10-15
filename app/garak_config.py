"""Build the Garak config for a before or after scan. No secrets are written."""

from __future__ import annotations

import json
import re
from pathlib import Path

# Short educational set. Each name is a real Garak 0.17 probe class.
# The prompts themselves stay inside the Garak package; this repo does not copy them.
DEFAULT_PROBES = (
    "probes.promptinject.HijackLongPrompt",
    "probes.dan.Dan_11_0",
    "probes.leakreplay.LiteratureCloze",
    "probes.realtoxicityprompts.RTPBlank",
)

PROBE_NOTES = {
    "probes.promptinject.HijackLongPrompt": "prompt injection",
    "probes.dan.Dan_11_0": "one jailbreak probe (DAN 11.0), not the whole DAN family",
    "probes.leakreplay.LiteratureCloze": "training-data leakage style check",
    "probes.realtoxicityprompts.RTPBlank": "toxicity",
}

# Garak records these HTTP statuses as a skipped prompt and keeps scanning.
# 504 is a model timeout. 502 is any other failed model call.
SKIP_HTTP_CODES = [502, 504]
# Stay above the lab's own model timeout so Garak receives the skip, not a read timeout.
GARAK_TIMEOUT_BUFFER_SECONDS = 30


def parse_spec(raw: str | None) -> list[str]:
    if raw is None or not raw.strip():
        return list(DEFAULT_PROBES)
    probes = [item.strip() for item in raw.split(",") if item.strip()]
    if not probes:
        return list(DEFAULT_PROBES)
    return probes


def endpoint_for(mode: str) -> str:
    if mode == "before":
        return "/v1/chat/raw"
    if mode == "after":
        return "/v1/chat/guarded"
    raise ValueError("mode must be 'before' or 'after'")


def garak_request_timeout(llm_timeout_seconds: float, override: int | None = None) -> int:
    """Seconds Garak waits for the lab. Defaults to the model timeout plus a small buffer."""
    if override is not None:
        return override
    return int(llm_timeout_seconds) + GARAK_TIMEOUT_BUFFER_SECONDS


def report_prefix_for(mode: str, probes: list[str]) -> str:
    """One-probe runs get their own file so a resume does not overwrite earlier probes."""
    if len(probes) != 1:
        return mode
    leaf = probes[0].rsplit(".", 1)[-1].lower()
    slug = re.sub(r"[^a-z0-9]+", "-", leaf).strip("-") or "probe"
    return f"{mode}.{slug}"


def rest_generator(base_url: str, mode: str, timeout_seconds: int = 330) -> dict[str, object]:
    uri = base_url.rstrip("/") + endpoint_for(mode)
    return {
        "rest": {
            "RestGenerator": {
                "name": f"llm-guardrails-lab-{mode}",
                "uri": uri,
                "method": "post",
                "headers": {"Content-Type": "application/json"},
                "req_template_json_object": {"message": "$INPUT"},
                "response_json": True,
                "response_json_field": "reply",
                "request_timeout": timeout_seconds,
                "skip_codes": list(SKIP_HTTP_CODES),
            }
        }
    }


def run_config(
    report_dir: Path,
    mode: str,
    probes: list[str],
    generations: int = 1,
    prompt_cap: int = 8,
) -> dict[str, object]:
    return {
        "system": {"lite": True, "narrow_output": True},
        "run": {
            "generations": generations,
            "soft_probe_prompt_cap": prompt_cap,
            "spec": {"include": probes},
        },
        "plugins": {"target_type": "rest"},
        "reporting": {
            "report_dir": str(report_dir),
            "report_prefix": report_prefix_for(mode, probes),
        },
    }


def write_configs(
    directory: Path,
    *,
    base_url: str,
    mode: str,
    probes: list[str],
    report_dir: Path,
    generations: int = 1,
    prompt_cap: int = 8,
    request_timeout: int = 330,
) -> tuple[Path, Path]:
    directory.mkdir(parents=True, exist_ok=True)
    report_dir.mkdir(parents=True, exist_ok=True)
    generator_path = directory / f"rest.{mode}.json"
    config_path = directory / f"garak.{mode}.json"
    generator = rest_generator(base_url, mode, timeout_seconds=request_timeout)
    generator_path.write_text(json.dumps(generator, indent=2) + "\n", encoding="utf-8")
    config_path.write_text(
        json.dumps(
            run_config(report_dir, mode, probes, generations=generations, prompt_cap=prompt_cap),
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return config_path, generator_path
