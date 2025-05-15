# Intelligent Inference Router (IIR) - MVP Phase 1a

A containerized, OpenAI-compatible LLM inference gateway that intelligently routes requests to a local GPU model (vLLM). Includes prompt classification, Redis caching, monitoring, and robust configuration.

## Features

### Recent Updates
- **API Key Authentication**: All API key registration and authentication is now database-backed. Keys registered via `/api/v1/apikeys` are instantly usable for all protected endpoints. No more reliance on environment variables for key validation in production.
- **Pydantic v2 Compatibility**: All models and settings use `model_dump()` instead of `.dict()` and leverage `json_schema_extra` for environment variable field mapping, ensuring compatibility with Pydantic v2 and beyond.
- **Test Suite Parity**: The test suite robustly validates API key registration and authentication using the same DB-backed logic as production, ensuring tests reflect real-world usage.

- OpenAI-compatible endpoints: `/v1/chat/completions`, `/v1/models`, `/health`
- Prompt classification (local only)
- Local vLLM backend integration (Llama-3-8B-Instruct)
- Redis-based response caching
- Prometheus/Grafana monitoring
- API key authentication & rate limiting (DB-backed, production-grade)
- Pydantic v2 compatible (uses model_dump and json_schema_extra for env fields)
- Robust test suite: registration/auth tests mirror production behavior
- Docker Compose deployment

## Model Naming Convention & Smart Routing

- All model names must use the format `<provider>/<model>`, e.g.:
  - `local/llama-3-8b-instruct`
  - `openai/gpt-4.1`
  - `anthropic/claude-3-opus`
- The router will parse the provider from the model name and route requests to the correct backend.
- "Smart routing" mode: If a model is available and configured, the router will load and use it automatically.
- If an unknown provider or model is provided, a clear error will be returned.

## Model Registry, Discovery & Hardware-Aware Recommendations

The model registry database (usually ~/.agent_coder/models.db) is the ONLY source of truth for available models. Do NOT manually edit the database; use provided admin tools or scripts for all changes.

- The router uses a dynamic model registry that supports multiple providers (local, OpenAI, Hugging Face, OpenRouter, Google Gemini/PaLM, etc.).
- Hardware-aware model discovery can be triggered on demand to recommend the best models for your system (GPU/CPU detected automatically).
- Model registry and discovery are **persisted** and only refreshed when explicitly requested.
- API endpoints:
  - `GET /v1/models`: List all available models in OpenAI-compatible format
  - `POST /v1/registry/refresh`: Run hardware/model discovery and refresh the registry
  - `GET /v1/registry/status`: Get last refresh time and hardware info
- Registry metadata is stored in `~/.agent_coder/` by default.
- To update the registry after hardware or model changes, call `/v1/registry/refresh`.

### Requirements
- Python 3.9+
- `sqlite3`, `requests`, `torch` (for GPU detection), `openai` (for LLM-powered recommendations)
- Set `OPENAI_API_KEY` in your environment for discovery

## Quick Start
See `docs/SETUP.md` for prerequisites and setup instructions.

## Documentation
- `docs/SETUP.md`: Setup & deployment
- `docs/CONFIGURATION.md`: Config reference
- `docs/API.md`: API details
- `docs/ARCHITECTURE.md`: Design & diagrams
- `docs/MONITORING.md`: Metrics & dashboards
- `docs/TROUBLESHOOTING.md`: Common issues

## Redis Environment Pattern (Test & Dev Reliability)

- The project uses a lazy environment variable lookup for `REDIS_URL` to ensure robust Redis connectivity in all environments.
- Always set `REDIS_URL=redis://localhost:6379/0` in your `.env` for local development and testing.
- See `docs/SETUP.md` for details.

# Gaia Infra Platform Onboarding

This repository is structured for seamless onboarding to the Gaia Infra Platform. It follows the canonical app stack pattern described in the central Gaia ONBOARDING.md. This enables automated import, monitoring, and provisioning by the Gaia infra team or CI/CD.

## Directory Structure for Gaia Onboarding

```
intelligent_inference_router/
  docker-compose.yml
  .env.example
  monitoring/
    prometheus.yml
    grafana-dashboard.json (or router-cache-metrics.json)
  db-provisioning/
    # (empty or with DB manifests)
  n8n/
    # (empty or with n8n workflows)
  README.md
  .gitlab-ci.yml
```

- **monitoring/**: Prometheus scrape config and Grafana dashboards for this app.
- **db-provisioning/**: Reserved for DB manifests (leave empty if not needed).
- **n8n/**: Reserved for n8n workflow exports (leave empty if not needed).
- **.gitlab-ci.yml**: GitLab CI/CD pipeline for lint, test, build, push, and deploy.

## Gaia Import Script Usage

To onboard this app into a Gaia environment, use the import script from the Gaia Infra Platform:

```bash
# Usage: ./scripts/import-app-stack.sh <path-to-app-repo> <environment>
./scripts/import-app-stack.sh ../intelligent_inference_router dev
```

This will validate the structure and copy all required files into the correct environment stack.

For more, see the Gaia Infra Platform [ONBOARDING.md](../gaia-infra-platform/ONBOARDING.md).

---

# GitLab CI/CD for Gaia

This project uses **GitLab Community Edition (CE)** for all CI/CD automation:
- All pipelines are defined in `.gitlab-ci.yml` at the repo root.
- Pipelines run on GitLab Runners and push images to the GitLab Container Registry.
- Key branches: `main` (production), `dev` (development), `test` (pre-prod/integration).
- All build, lint, test, and deploy steps are visible in GitLab’s UI.

## Pipeline Overview
- **lint**: Checks code style (flake8, black)
- **unit_test**: Runs all Python tests
- **build**: Builds Docker image
- **push**: Pushes image to GitLab Container Registry
- **deploy_dev**: Manual deploy to dev environment
- **deploy_prod**: Manual deploy to prod environment

## Example Pipeline Trigger
- Push to `main`, `dev`, or `test` will trigger the pipeline.
- Manual deploy steps can be triggered from the GitLab UI.

For more, see Gaia’s [ONBOARDING.md](../gaia-infra-platform/ONBOARDING.md) and the `.gitlab-ci.yml` in this repo.

---

## Project Decoupling: ml_ops

As of 2025-04-24, this project no longer depends on the `ml_ops` repository. All code, tests, and infrastructure for the Intelligent Inference Router are now self-contained. Any prior references to `ml_ops` as a submodule, symlink, or dependency have been removed for clarity and maintainability.

If you require legacy utilities, refer to the archived `ml_ops` repository separately.

---

For full requirements and context, see the Memory Bank and PRD in `memory-bank/`.
