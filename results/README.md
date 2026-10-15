# Results

`before/` and `after/` stay empty in git. A real scan writes Garak's `*.report.jsonl` and HTML report there. `make compare` reads those files and writes `comparison.json` and `comparison.md`, which are also ignored by git.

`sample/` is an illustration of the layout. It is not a Garak report. The compare script does not read it.
