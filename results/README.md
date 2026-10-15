# Results

The landing page does not read this folder. GitHub Pages publishes `site/`, including `site/comparison.json` from the author's laptop on 2026-10-15 (Garak 0.17.0, NeMo Guardrails 0.24.1, one xAI model via an OpenAI-compatible API, one run).

`before/` and `after/` stay empty in git. A real scan writes Garak's `*.report.jsonl` and HTML report there. `make compare` reads those files and writes `comparison.json` and `comparison.md`, which are also ignored by git. That local comparison does not replace `site/comparison.json`.

`sample/` is an illustration of the layout. The counts in it are made up. It is not a Garak report. The compare script does not read it.
