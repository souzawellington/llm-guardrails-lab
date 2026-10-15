"""Read Garak JSONL reports and compare pass rates.

Garak writes one JSON object per line. An ``eval`` line is the score for one
probe and one detector. ``passed / total_evaluated`` is the share of outputs
that did not trigger the detector. A higher rate is the safer direction.

This module does not invent scores. If a file has no eval lines, the result
says so.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EvalRow:
    probe: str
    detector: str
    passed: int
    total_evaluated: int
    fails: int | None = None
    nones: int | None = None

    @property
    def pass_rate(self) -> float | None:
        if self.total_evaluated <= 0:
            return None
        return self.passed / self.total_evaluated


@dataclass(frozen=True)
class ReportLoad:
    path: Path
    rows: tuple[EvalRow, ...]
    warnings: tuple[str, ...]


def _as_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int | float | str):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def load_report(path: Path) -> ReportLoad:
    warnings: list[str] = []
    combined: dict[tuple[str, str], dict[str, int | None]] = {}
    saw_digest = False
    eval_count = 0

    text = path.read_text(encoding="utf-8")
    for line_number, raw in enumerate(text.splitlines(), start=1):
        stripped = raw.strip()
        if not stripped:
            continue
        try:
            entry = json.loads(stripped)
        except json.JSONDecodeError:
            warnings.append(f"Skipped line {line_number}: not valid JSON.")
            continue
        if not isinstance(entry, dict):
            warnings.append(f"Skipped line {line_number}: not a JSON object.")
            continue
        if entry.get("entry_type") == "digest":
            saw_digest = True
        if entry.get("entry_type") != "eval":
            continue
        eval_count += 1
        probe = entry.get("probe")
        detector = entry.get("detector")
        passed = _as_int(entry.get("passed"))
        total = _as_int(entry.get("total_evaluated", entry.get("total")))
        missing = not isinstance(probe, str) or not isinstance(detector, str)
        if missing or passed is None or total is None:
            warnings.append(
                f"Skipped eval on line {line_number}: missing probe, detector, or counts."
            )
            continue
        key = (probe, detector)
        bucket = combined.setdefault(
            key,
            {"passed": 0, "total_evaluated": 0, "fails": 0, "nones": 0},
        )
        bucket["passed"] = int(bucket["passed"] or 0) + passed
        bucket["total_evaluated"] = int(bucket["total_evaluated"] or 0) + total
        fails = _as_int(entry.get("fails"))
        nones = _as_int(entry.get("nones"))
        if fails is not None:
            bucket["fails"] = int(bucket["fails"] or 0) + fails
        if nones is not None:
            bucket["nones"] = int(bucket["nones"] or 0) + nones

    if eval_count == 0 and saw_digest:
        warnings.append(
            "The file has a digest entry but no eval rows. Open the HTML report Garak wrote "
            "next to this file. This tool only scores eval rows, so it will not guess."
        )
    if eval_count == 0 and not saw_digest:
        warnings.append("No eval rows found. This file does not look like a finished Garak report.")

    rows = tuple(
        EvalRow(
            probe=probe,
            detector=detector,
            passed=int(values["passed"] or 0),
            total_evaluated=int(values["total_evaluated"] or 0),
            fails=values["fails"],
            nones=values["nones"],
        )
        for (probe, detector), values in sorted(combined.items())
    )
    return ReportLoad(path=path, rows=rows, warnings=tuple(warnings))


def find_latest_report(directory: Path) -> Path | None:
    if not directory.is_dir():
        return None
    candidates = [
        path
        for path in directory.glob("*.report.jsonl")
        if path.is_file() and "sample" not in path.name.lower()
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


@dataclass(frozen=True)
class ComparisonRow:
    probe: str
    detector: str
    before: EvalRow | None
    after: EvalRow | None

    @property
    def change(self) -> float | None:
        if self.before is None or self.after is None:
            return None
        if self.before.pass_rate is None or self.after.pass_rate is None:
            return None
        return self.after.pass_rate - self.before.pass_rate


def compare(before: ReportLoad, after: ReportLoad) -> list[ComparisonRow]:
    keys = sorted(
        {(row.probe, row.detector) for row in before.rows}
        | {(row.probe, row.detector) for row in after.rows}
    )
    before_index = {(row.probe, row.detector): row for row in before.rows}
    after_index = {(row.probe, row.detector): row for row in after.rows}
    return [
        ComparisonRow(
            probe=probe,
            detector=detector,
            before=before_index.get((probe, detector)),
            after=after_index.get((probe, detector)),
        )
        for probe, detector in keys
    ]


def _percent(rate: float | None) -> str:
    if rate is None:
        return "not scored"
    return f"{rate * 100:.1f}%"


def _counts(row: EvalRow | None) -> str:
    if row is None:
        return "not in this report"
    if row.pass_rate is None:
        return f"not scored (0 evaluated, passed {row.passed})"
    return f"{_percent(row.pass_rate)} ({row.passed}/{row.total_evaluated} resisted)"


def comparison_payload(before: ReportLoad, after: ReportLoad) -> dict[str, object]:
    rows = compare(before, after)
    return {
        "kind": "garak-comparison",
        "disclaimer": (
            "Computed only from the eval rows in the two report files. "
            "This repository does not ship real scan results."
        ),
        "meaning": (
            "Pass rate is passed / total_evaluated. "
            "A higher rate means more outputs did not trigger the detector."
        ),
        "before_file": str(before.path),
        "after_file": str(after.path),
        "warnings": list(before.warnings + after.warnings),
        "rows": [
            {
                "probe": row.probe,
                "detector": row.detector,
                "before_pass_rate": None if row.before is None else row.before.pass_rate,
                "after_pass_rate": None if row.after is None else row.after.pass_rate,
                "change": row.change,
                "before_passed": None if row.before is None else row.before.passed,
                "before_total_evaluated": (
                    None if row.before is None else row.before.total_evaluated
                ),
                "after_passed": None if row.after is None else row.after.passed,
                "after_total_evaluated": (
                    None if row.after is None else row.after.total_evaluated
                ),
            }
            for row in rows
        ],
    }


def comparison_markdown(before: ReportLoad, after: ReportLoad) -> str:
    payload = comparison_payload(before, after)
    lines = [
        "# Garak comparison",
        "",
        str(payload["disclaimer"]),
        "",
        str(payload["meaning"]),
        "",
        f"- Before: `{before.path}`",
        f"- After: `{after.path}`",
        "",
        "| Probe | Detector | Before rails | After rails | Change |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in compare(before, after):
        change = "n/a" if row.change is None else f"{row.change * 100:+.1f} points"
        cells = (
            row.probe,
            row.detector,
            _counts(row.before),
            _counts(row.after),
            change,
        )
        lines.append("| " + " | ".join(cells) + " |")
    if not compare(before, after):
        lines.append("| — | — | no eval rows | no eval rows | n/a |")
    warnings = list(before.warnings + after.warnings)
    if warnings:
        lines.extend(["", "## Warnings", ""])
        lines.extend(f"- {warning}" for warning in warnings)
    lines.append("")
    return "\n".join(lines)
