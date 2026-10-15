"""Locate the repository root whether the app is launched from here or elsewhere."""

from __future__ import annotations

from pathlib import Path


def project_root() -> Path:
    here = Path(__file__).resolve()
    candidates = [here.parents[1], Path.cwd()]
    for candidate in candidates:
        if (candidate / "guardrails" / "config.yml").is_file():
            return candidate
    return here.parents[1]
