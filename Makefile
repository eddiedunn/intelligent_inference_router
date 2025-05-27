.PHONY: dev lint test migrate seed docs-serve
.PHONY: dev lint test migrate seed docker-dev


dev:
	uvicorn router.main:app --reload --port 8000

lint:
	ruff check .
	black --check .
	mypy router tests

test:
	pytest --cov=router --cov=local_agent --cov-report=term-missing --cov-report=xml -q

migrate:
	python -m router.cli migrate

seed:
	python -m router.cli seed docs/models_seed.json


docs-serve:
	mkdocs serve -a 0.0.0.0:8001

docker-dev:
	docker compose up

