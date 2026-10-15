"""Custom actions loaded automatically by NeMo Guardrails from this folder.

The heavy library import happens only when Guardrails loads the config.
Unit tests call app.checks directly and do not import this module.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.checks import jailbreak_pattern_match, mask_pii
from nemoguardrails.actions import action


@action(is_system_action=True)
async def mask_pii_regex(text: str = "", source: str = "input") -> str:
    """Mask emails, SSNs, Luhn-valid card numbers, and phone-like numbers."""
    del source
    return mask_pii(text or "")


@action(is_system_action=True)
async def check_jailbreak_patterns(text: str = "", context: dict | None = None) -> bool:
    """Return True when the message matches the small override-phrase list."""
    message = text or ""
    if not message and context:
        message = str(context.get("user_message") or "")
    return jailbreak_pattern_match(message)
