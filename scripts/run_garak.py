"""Run Garak against the local lab. Before uses the raw bot; after uses the rails.

The scan talks to the lab API on this machine. Point it only at a service you
are allowed to test. Reports are written under results/ and are not sample data.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.garak_config import PROBE_NOTES, parse_spec, write_configs
from app.paths import project_root
from app.settings import load_settings


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    return int(raw)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan the local lab with Garak.")
    parser.add_argument("--mode", choices=("before", "after"), required=True)
    parser.add_argument(
        "--base-url",
        default=None,
        help="Lab API origin. Defaults to LAB_BASE_URL.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Write configs and print the command.",
    )
    args = parser.parse_args(argv)

    settings = load_settings()
    root = project_root()
    base_url = (args.base_url or settings.lab_base_url).rstrip("/")
    probes = parse_spec(os.getenv("GARAK_SPEC"))
    generations = _int_env("GARAK_GENERATIONS", 1)
    prompt_cap = _int_env("GARAK_PROMPT_CAP", 8)
    report_dir = root / "results" / args.mode
    config_path, generator_path = write_configs(
        root / "results" / ".generated",
        base_url=base_url,
        mode=args.mode,
        probes=probes,
        report_dir=report_dir,
        generations=generations,
        prompt_cap=prompt_cap,
    )

    print(f"Mode: {args.mode}")
    print(f"Target: {base_url}{'/v1/chat/raw' if args.mode == 'before' else '/v1/chat/guarded'}")
    print("Probes:")
    for probe in probes:
        note = PROBE_NOTES.get(probe, "custom spec")
        print(f"  - {probe} ({note})")
    print(
        "This sends Garak's own probes to YOUR lab process and spends credits on the model in .env."
    )
    print(f"Reports: {report_dir}")
    command = [
        sys.executable,
        "-m",
        "garak",
        "--config",
        str(config_path),
        "-G",
        str(generator_path),
    ]
    print("Command:", " ".join(command))
    if args.dry_run:
        print("Dry run: Garak was not started.")
        return 0

    completed = subprocess.run(command, cwd=root, check=False)
    if completed.returncode != 0:
        print("Garak failed. If the module is missing, install requirements-lab.txt.")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
