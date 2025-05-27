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

To run the router, local agent and Redis using Docker Compose, execute:

```bash
make docker-dev
```

Copy `.env.example` to `.env` and adjust the values if needed.

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
Start a live preview with:

```bash
make docs-serve
```

CI builds the site using `mkdocs build` and deploys the generated `site/`
directory to GitHub Pages.
