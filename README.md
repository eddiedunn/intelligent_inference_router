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

---

For full requirements and context, see the Memory Bank and PRD in `memory-bank/`.
