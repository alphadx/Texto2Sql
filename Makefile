PYTHON ?= python
PIP ?= pip

.PHONY: install-dev test

install-dev:
	$(PIP) install -r requirements.txt -r requirements-dev.txt

test: install-dev
	$(PYTHON) -m pytest tests/test_app.py
