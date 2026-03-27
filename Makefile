PYTHON ?= python
PIP ?= pip

.PHONY: install-dev install-main-config test demo-install demo-check-env demo-build demo-up demo-down demo-logs demo-smoke

install-dev:
	$(PIP) install -r requirements.txt -r requirements-dev.txt

test: install-dev
	$(PYTHON) -m pytest tests/test_app.py


demo-install:
	bash demo/install-demo.sh

demo-build: demo-check-env
	docker compose -f demo/docker-compose.yml build

demo-up: demo-check-env
	docker compose -f demo/docker-compose.yml up -d --build

demo-down:
	docker compose -f demo/docker-compose.yml down

demo-logs:
	docker compose -f demo/docker-compose.yml logs -f

demo-check-env:
	@test -f demo/.env || (echo "Falta demo/.env. Ejecuta: make demo-install" && exit 1)

install-main-config:
	bash scripts/install-main.sh


demo-smoke:
	bash scripts/demo-smoke.sh
