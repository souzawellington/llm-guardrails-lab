"""Remove reasoning traces before a person, or a rail parser, can read them.

NeMo Guardrails 0.24.1 extracts a reasoning trace and, on the normal
generate_async path, pastes it back onto the reply inside <think> tags.
A reasoning model such as Grok often puts the rail prompt itself in that
trace. This module drops the trace. The model's answer stays.
"""

from __future__ import annotations

import re
from collections.abc import Callable

# Closed blocks, including the tags NeMo prepends and the ones models emit.
_CLOSED_BLOCK = re.compile(
    r"<\s*(think|thinking|reasoning)\b[^>]*>.*?<\s*/\s*\1\s*>",
    re.IGNORECASE | re.DOTALL,
)
# A trace that started and never closed. Drop it so it cannot leak.
_UNCLOSED_BLOCK = re.compile(
    r"<\s*(think|thinking|reasoning)\b[^>]*>[\s\S]*\Z",
    re.IGNORECASE,
)

def strip_reasoning(text: str) -> str:
    """Return text with reasoning blocks removed."""
    cleaned = text
    previous = None
    while cleaned != previous:
        previous = cleaned
        cleaned = _CLOSED_BLOCK.sub("", cleaned)
    cleaned = _UNCLOSED_BLOCK.sub("", cleaned)
    return cleaned.strip()


def wrap_parser(parser: Callable[..., object]) -> Callable[..., object]:
    """Run a NeMo output parser on text that no longer contains a trace."""

    def wrapped(response: str) -> object:
        if not isinstance(response, str):
            return parser(response)
        return parser(strip_reasoning(response))

    return wrapped


def install_parser_stripping(output_parsers: dict[str, Callable[..., object]]) -> None:
    """Replace each parser with one that strips reasoning first.

    Mutates the dict NeMo uses, so self-check and intent parsing see the
    verdict instead of the trace.
    """
    for name, parser in list(output_parsers.items()):
        if getattr(parser, "_strips_reasoning", False):
            continue
        wrapped = wrap_parser(parser)
        wrapped._strips_reasoning = True  # type: ignore[attr-defined]
        output_parsers[name] = wrapped
