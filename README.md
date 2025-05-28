# Intelligent Inference Router

This project provides a prototype OpenAI-compatible API that returns a dummy response.

## Development

Start the router using `make dev` and access `http://localhost:8000/v1/chat/completions`.

Before running any `make` command, activate the local virtual environment:

```bash
source .venv/bin/activate
```

For local models, run the Local Agent service:

```bash
uvicorn local_agent.main:app --port 5000
```


Any request whose `model` starts with `local` will be forwarded to this agent.

### Docker

The development stack is defined in `docker-compose.yml` and includes the
router service and a Redis instance. The SQLite model registry is stored in a
named volume so data persists between runs.

Start the stack with:

```bash
make docker-dev
```

On macOS you may also run the Local Agent container by enabling the `darwin`
profile:

```bash
COMPOSE_PROFILES=darwin make docker-dev
```

Press `Ctrl+C` to stop the services; the `docker-dev` target will automatically
remove the containers. Copy `.env.example` to `.env` and adjust the values if
needed.

Run the unit tests with coverage enabled using:

```bash
make test
```

The command writes a coverage report to `coverage.xml` and prints a summary in
the terminal.

### Model Registry

Create the SQLite registry and seed default entries:

```bash
make migrate
make seed
```

Add or update a single model entry:

```bash
python -m router.cli add-model <name> <type> <endpoint>
```

Fetch the latest models from OpenAI and refresh the registry:

```bash
python -m router.cli refresh-openai
```

## Documentation

This project uses [MkDocs](https://www.mkdocs.org/) with the
[Material for MkDocs](https://squidfunk.github.io/mkdocs-material/) theme.
Key pages include `setup.md`, `usage.md` and `api_examples.md` under `docs/`.
Start a live preview with:

```bash
make docs-serve
```

CI builds the site using `mkdocs build` and a dedicated workflow deploys the
generated `site/` directory to GitHub Pages.
