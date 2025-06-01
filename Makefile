.PHONY: dev lint test test-integration migrate seed docker-dev docs-serve k3s-up

dev:
	uvicorn router.main:app --reload --port 8000

lint:
	ruff check .
	black --check .
	mypy router tests

test:
	pytest

test-integration:
	pytest -m integration

migrate:
	python -m router.cli migrate

seed:
	python -m router.cli seed docs/models_seed.json

docs-serve:
	mkdocs serve -a 0.0.0.0:8001

docker-dev:
	docker compose up

k3s-up:
	k3d cluster create llmd --image rancher/k3s:v1.29.4-k3s1 --wait || true
	helm upgrade --install llm-d worker_cluster/chart -n llmd --create-namespace
	docker compose up
	docker compose down
