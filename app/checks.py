"""Small, local checks used by the NeMo actions and by the tests.

These are teaching detectors. They are not a complete safety system, and they
do not contain attack prompts.
"""

from __future__ import annotations

import re

_EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_SSN = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")
_CARD = re.compile(r"\b(?:\d[ -]?){13,19}\b")
_PHONE = re.compile(
    r"(?<!\w)(?:\+\d{1,3}[\s.-]?)?(?:\(\d{3}\)|\d{3})[\s.-]?\d{3}[\s.-]?\d{4}(?!\w)"
)

# Defensive signatures for instruction-override attempts. A rephrased attack
# can pass these patterns. The LLM self-check rail is the broader check.
_JAILBREAK_PATTERNS = (
    re.compile(
        r"\bignore\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions|rules|prompts)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bdisregard\s+(?:your|the|all)\s+(?:previous\s+)?(?:rules|instructions|guidelines)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:reveal|print|show)\s+(?:me\s+)?(?:your\s+)?"
        r"(?:system\s+prompt|hidden\s+instructions|developer\s+message)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\byou\s+are\s+now\s+(?:dan|jailbroken|unrestricted)\b",
        re.IGNORECASE,
    ),
)


def luhn_ok(number: str) -> bool:
    digits = [int(character) for character in number if character.isdigit()]
    if not 13 <= len(digits) <= 19:
        return False
    total = 0
    for index, digit in enumerate(reversed(digits)):
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def mask_pii(text: str) -> str:
    """Replace common identifiers with tokens. The original text is not logged."""
    masked = _EMAIL.sub("[EMAIL]", text)
    masked = _SSN.sub("[SSN]", masked)

    def replace_card(match: re.Match[str]) -> str:
        raw = match.group(0)
        digits = "".join(character for character in raw if character.isdigit())
        if luhn_ok(digits):
            return "[CARD]"
        return raw

    masked = _CARD.sub(replace_card, masked)
    return _PHONE.sub("[PHONE]", masked)


def jailbreak_pattern_match(text: str) -> bool:
    """Return True when the text matches a small set of override phrases."""
    return any(pattern.search(text) for pattern in _JAILBREAK_PATTERNS)
