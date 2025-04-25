# Intelligent Inference Router (IIR) - MVP Phase 1a

A containerized, OpenAI-compatible LLM inference gateway that intelligently routes requests between a local GPU model (vLLM) and (future) external APIs. Includes prompt classification, Redis caching, monitoring, and robust configuration.

## Features
- OpenAI-compatible endpoints: `/v1/chat/completions`, `/v1/models`, `/health`
- Prompt classification (local vs remote)
- Local vLLM backend integration (Llama-3-8B-Instruct)
- Redis-based response caching
- Prometheus/Grafana monitoring
- API key authentication & rate limiting
- Docker Compose deployment

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
