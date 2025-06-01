
# AGENTS.md

> **For the authoritative MVP/post-MVP feature list, see [IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md).**

#
# High-level instructions for OpenAI Codex (Copdex) or any
# compatible AI engineering agent working in this repository.

---

## MVP and Post-MVP Service Summary

**MVP includes:**
- Router (FastAPI gateway, OpenAI-compatible, vllm Docker workers only)
- Local Agent (macOS-native, Apple Silicon, vllm Docker workers only)
- Proxy to OpenAI
- SQLite model registry

**Explicitly NOT in MVP:**
- llm-d/worker_cluster (Kubernetes GPU workers)
- Redis caching
- Rate limiting
- Smart routing
- Additional providers (Anthropic, Google, OpenRouter, Grok, Venice)

See [IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md) for the up-to-date status.

---
#
# ────────────────────────────────────────────────────────────
# TL;DR for the agent
# • This repo contains a distributed inference router system.
# • Three main Python micro-services:
#     1. `router/`   – FastAPI gateway + smart routing logic (MVP: only vllm Docker, OpenAI proxy)
#     2. `local_agent/` – macOS-native service for Apple-Silicon inference (MVP: only vllm Docker)
#     3. `worker_cluster/` (post-MVP) – llm-d (vLLM) GPU workers on K8s
# • Redis is used for caching (post-MVP), SQLite for the model registry & API keys.
# • Tests are in `tests/`, run with `pytest -q`.
# • Activate the `.venv` created by the setup script before running any
#   `make` command (e.g. `source .venv/bin/activate`).

# • Use `make <target>` or `just <target>` commands below – **never**
#   call pip directly or hard-code paths inside Dockerfiles.
# • Follow PEP 8 + PEP 257, write type-hinted Python 3.10+.
# • All new code MUST include unit tests and docs.
#
# The Codex environment already runs **inside a Docker container** built from an
# Ubuntu 24.04 image. The Dockerfile installs common build tools and multiple
# language runtimes via `pyenv`, `nvm`, Rustup, Go, Swift and more. Python 3.11
# is the default. During container start-up the following initialization steps
# are executed **once** while network access is available:
#
# ```bash
# python3 -m venv .venv
# .venv/bin/pip install --upgrade pip
# .venv/bin/pip install -e .
# .venv/bin/pip install -r requirements-dev.txt
# .venv/bin/pip install pytest-asyncio
# ```
#
# After these commands run the network is disabled. Do **not** attempt to
# recreate the virtual environment or build new Docker images/containers.
#
# The rest of this file gives details.

## 1. Repository rules

### 1.1 Coding style
* Target **Python 3.10+**.
* Obey **PEP 8** (code) and **PEP 257** (docstrings).  
* Use descriptive, `snake_case` names.  
* Keep modules ≤ 400 LOC; refactor otherwise.  

### 1.2 Dependencies
* Declare runtime deps in **`pyproject.toml`** under `[project]`.
* For dev/test deps, use **`requirements-dev.txt`**.
* Never pin to `*`; use `^` or `~` semantic specifiers (PEP 440).

### 1.3 Directory structure (partial)
```

/router/               # FastAPI gateway
/local\_agent/          # macOS MPS-backed service
/worker\_cluster/chart/ # Helm chart for llm-d (optional)
/shared/               # code reused by multiple services
/tests/                # pytest test-suite
/scripts/              # automation / CI helpers
/docs/                 # MkDocs site

````

### 1.4 Make / Just targets
Codex SHOULD invoke these targets only after `.venv` is active so the
correct dependencies are used.
| Target            | Description                                  |
|-------------------|----------------------------------------------|
| `make dev`        | Start router + local_agent (no Docker)       |
| `make docker-dev` | Build & run all services via Docker Compose  |
| `make k3s-up`     | Spin up single-node k3s and deploy llm-d     |
| `make test`       | Run unit tests with coverage                 |
| `make lint`       | Run ruff, mypy, black (check mode)           |


Codex SHOULD invoke these targets rather than raw commands.

## 2. Service contracts

### 2.1 Router (`router/`)
* Exposes **OpenAI-compatible** endpoints  
  `POST /v1/chat/completions`, `GET /v1/models`, etc.  
* Env vars of interest:

| Var                | Purpose                                | Default |
|--------------------|----------------------------------------|---------|
| `SQLITE_DB_PATH`   | Path for model registry DB             | `data/models.db` |
| `REDIS_URL`        | Redis connection string                | `redis://localhost:6379/0` |
| `LLMD_ENDPOINT`    | Base URL for llm-d cluster             | unset   |
| `EXTERNAL_*_KEY`   | API keys for external providers        | unset   |

* **Tests**: `pytest -q tests/router`.

### 2.2 Local Agent (`local_agent/`)
* Runs on **macOS (Apple Silicon)**, not containerised.  
* Starts `uvicorn main:app --port 5000`.  
* Loads default model `local_mistral-7b-instruct-q4` using PyTorch MPS.  
* Provides `/infer` REST endpoint; payload schema:

```jsonc
{
  "prompt": "string",
  "max_tokens": 512,
  "temperature": 0.7,
  "stream": false
}
````

### 2.3 GPU Worker Cluster (`worker_cluster/`)

* Provided by **llm-d** Helm chart. *(Planned for post-MVP)*
* Router will call the llm-d **Inference-Gateway** at
  `${LLMD_ENDPOINT}/v1/chat/completions` (post-MVP only).

* The cluster handles prefill/decode scheduling; Router only sees the
  OpenAI JSON wire-format.

## 3. Tests & CI

* Unit tests are executed with `make test`, which calls plain `pytest`.
  A `pytest.ini` file excludes integration tests by default using the
  `-m "not integration"` option.
* Run `make test-integration` to execute integration tests marked with
  `@pytest.mark.integration`.
* The root **GitHub Actions** workflow (`.github/workflows/ci.yml`) runs
  `make lint` and `make test`. A second job runs `make test-integration`
  only when the workflow is triggered manually via `workflow_dispatch`.
* Integration tests spin up Router + Local Agent with `pytest-asyncio`
  and stub external APIs with **vcr.py**.

## 4. Security & secrets

* **Never** commit plaintext API keys – use GitHub secrets or
  `.env.example` template.
* For K8s deployments, secrets are mounted as
  `kind: Secret` and referenced via Helm values.

## 5. Contribution workflow

1. **Fork → feature branch → PR**; name branch `feat/<short-desc>` or
   `fix/<issue-id>`
2. Use Conventional Commits (`feat:`, `fix:`, `docs:`) – enforced by
   commitlint.
3. PR must pass CI and include changelog entry in `CHANGELOG.md`.

## 6. Known pain points

* Apple MPS backend occasionally stalls on > 4096 tokens; if CI fails
  on Mac, restart job.
* llm-d GPU pods can OOM if `max_model_len` is set too high.
  Monitor logs and adjust `values.yaml`.

## 7. What Codex MAY do

* Refactor Python modules to reduce duplication.
* Add unit tests for uncovered code paths (`pytest --cov`).
* Update Dockerfiles to slim images (e.g. switch to `python:3.10-slim`)
* Modify Helm chart under `/worker_cluster/chart` to expose metrics.

## 8. What Codex MUST NOT do

* Remove or rewrite database migrations in `router/migrations/`.
* Change public API routes without updating docs and tests.
* Push directly to `main`.

---

*Last updated: 2025-06-01*
