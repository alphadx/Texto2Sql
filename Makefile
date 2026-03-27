PYTHON ?= python
PIP ?= pip

.PHONY: install-dev test demo-install demo-build demo-up demo-down demo-logs

install-dev:
	$(PIP) install -r requirements.txt -r requirements-dev.txt

test: install-dev
	$(PYTHON) -m pytest tests/test_app.py


demo-install:
	bash demo/install-demo.sh

demo-build:
	docker compose -f demo/docker-compose.yml build

demo-up:
	docker compose -f demo/docker-compose.yml up -d --build

demo-down:
	docker compose -f demo/docker-compose.yml down

demo-logs:
	docker compose -f demo/docker-compose.yml logs -f
