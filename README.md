# Intelligent Inference Router (IIR) - MVP Phase 1a

A containerized, OpenAI-compatible LLM inference gateway that intelligently routes requests to a local GPU model (vLLM). Includes prompt classification, Redis caching, monitoring, and robust configuration.

## Features
- OpenAI-compatible endpoints: `/v1/chat/completions`, `/v1/models`, `/health`
- Prompt classification (local only)
- Local vLLM backend integration (Llama-3-8B-Instruct)
- Redis-based response caching
- Prometheus/Grafana monitoring
- API key authentication & rate limiting
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

## Project Decoupling: ml_ops

As of 2025-04-24, this project no longer depends on the `ml_ops` repository. All code, tests, and infrastructure for the Intelligent Inference Router are now self-contained. Any prior references to `ml_ops` as a submodule, symlink, or dependency have been removed for clarity and maintainability.

If you require legacy utilities, refer to the archived `ml_ops` repository separately.

---

For full requirements and context, see the Memory Bank and PRD in `memory-bank/`.
