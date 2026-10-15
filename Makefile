.PHONY: install install-dev install-lab lint test smoke serve scan-before scan-after compare

PYTHON ?= python3

install:
	$(PYTHON) -m pip install -r requirements.txt

install-dev:
	$(PYTHON) -m pip install -r requirements-dev.txt

install-lab:
	$(PYTHON) -m pip install -r requirements-lab.txt

lint:
	$(PYTHON) -m ruff check .

test:
	$(PYTHON) -m pytest

smoke:
	$(PYTHON) -m app.smoke

serve:
	$(PYTHON) -m uvicorn app.main:app --host 127.0.0.1 --port 8000

scan-before:
	$(PYTHON) scripts/run_garak.py --mode before

scan-after:
	$(PYTHON) scripts/run_garak.py --mode after

compare:
	$(PYTHON) scripts/compare_reports.py
