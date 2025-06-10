# Changelog

> **For the authoritative MVP/post-MVP feature list, see [IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md).**

---

## [Unreleased]
### Added

- llm-d cluster support (`make k3s-up` and router forwarding)
- In-memory caching layer with TTL (`CACHE_TTL`)
- Venice provider forwarding support
- Hugging Face weight provider for local models
- Model registry `kind` column with migration and CLI support
- Unified provider architecture for API and weight-based providers
- Example Hugging Face env vars in `.env.example`
- Updated provider streaming logic for HTTPX 0.28 and closed TestClient sessions in tests
- CLI command `list-models` to display registry entries
- Module-level docstrings across router and local agent modules
- Optional shared-secret auth middleware (`ROUTER_SHARED_SECRET`)



## [MVP Release]
### Added
- OpenAI-compatible API endpoint (`/v1/chat/completions`)
- Local agent forwarding (vllm, Docker-based only)
- Proxy to OpenAI provider
- SQLite-based model registry with CLI
- Agent registration & heartbeat endpoints
- Initial Docker Compose/dev stack setup (in progress)
- CI workflow (in progress)
- MkDocs documentation site with GitHub Pages

### Not included in MVP (deferred):
- Rate limiting
- Smart routing
- Request logging and metrics
- llm-d cluster support (Kubernetes, Helm)
- Additional inference worker types (llm-d)
- Provider integrations: Anthropic, Google, OpenRouter, Grok, Venice

---

## [Planned/Upcoming]
- Rate limiting
- Smart routing
- Request logging and metrics
- llm-d cluster support (forwarding, deployment, endpoint exposure)
- Additional inference worker types (llm-d)
- Provider integrations: Anthropic, Google, OpenRouter, Grok, Venice

See [IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md) for the up-to-date status.
