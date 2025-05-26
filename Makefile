.PHONY: dev lint test

dev:
	uvicorn router.main:app --reload --port 8000

lint:
	ruff check .
	black --check .
	mypy router tests

test:
	pytest --cov=router --cov=local_agent --cov-report=term-missing --cov-report=xml -q
