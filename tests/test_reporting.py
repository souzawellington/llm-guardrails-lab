import os
from pathlib import Path

from app.reporting import compare, comparison_payload, find_latest_report, load_report, load_reports

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_report_scores_eval_rows_and_warns_on_bad_lines() -> None:
    loaded = load_report(FIXTURES / "after.report.jsonl")
    assert len(loaded.rows) == 2
    injection = loaded.rows[1]
    assert injection.probe == "promptinject.HijackLongPrompt"
    assert injection.pass_rate == 1
    assert any("Skipped line" in warning for warning in loaded.warnings)


def test_compare_shows_the_change_in_pass_rate() -> None:
    before = load_report(FIXTURES / "before.report.jsonl")
    after = load_report(FIXTURES / "after.report.jsonl")
    rows = {(row.probe, row.detector): row for row in compare(before, after)}
    change = rows[("promptinject.HijackLongPrompt", "example.Detector")].change
    assert change == 0.75
    payload = comparison_payload(before, after)
    assert payload["kind"] == "garak-comparison"
    assert "does not ship real scan results" in str(payload["disclaimer"])


def test_load_reports_pools_separate_probe_files(tmp_path: Path) -> None:
    first = tmp_path / "before.dan-11-0.report.jsonl"
    second = tmp_path / "before.literaturecloze.report.jsonl"
    before_text = (FIXTURES / "before.report.jsonl").read_text(encoding="utf-8")
    after_text = (FIXTURES / "after.report.jsonl").read_text(encoding="utf-8")
    first.write_text(before_text, encoding="utf-8")
    second.write_text(after_text, encoding="utf-8")
    pooled = load_reports([first, second])
    injection = next(row for row in pooled.rows if row.probe == "promptinject.HijackLongPrompt")
    assert injection.passed == 5
    assert injection.total_evaluated == 8


def test_find_latest_report_ignores_sample_files(tmp_path: Path) -> None:
    older = tmp_path / "before.report.jsonl"
    newer = tmp_path / "later.report.jsonl"
    sample = tmp_path / "sample.report.jsonl"
    older.write_text("{}\n", encoding="utf-8")
    newer.write_text("{}\n", encoding="utf-8")
    sample.write_text("{}\n", encoding="utf-8")
    os.utime(older, (1_000, 1_000))
    os.utime(newer, (2_000, 2_000))
    os.utime(sample, (3_000, 3_000))
    assert find_latest_report(tmp_path) == newer
