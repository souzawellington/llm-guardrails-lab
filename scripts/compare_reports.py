"""Compare the newest Garak reports in results/before and results/after."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.paths import project_root
from app.reporting import comparison_markdown, comparison_payload, find_latest_report, load_report


def main(argv: list[str] | None = None) -> int:
    del argv
    root = project_root()
    before_path = find_latest_report(root / "results" / "before")
    after_path = find_latest_report(root / "results" / "after")
    if before_path is None or after_path is None:
        print("No Garak report found in results/before and results/after.")
        print("Run scripts/run_garak.py --mode before, then --mode after.")
        print("Files in results/sample are illustrations, not scans. They are ignored here.")
        return 2

    before = load_report(before_path)
    after = load_report(after_path)
    payload = comparison_payload(before, after)
    markdown = comparison_markdown(before, after)
    out_dir = root / "results"
    json_path = out_dir / "comparison.json"
    md_path = out_dir / "comparison.md"
    json_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(markdown, encoding="utf-8")
    print(markdown)
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
