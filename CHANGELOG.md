# Changelog

> **For the authoritative MVP/post-MVP feature list, see [IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md).**

---

## [Unreleased]
### Added
- llm-d cluster support (`make k3s-up` and router forwarding)

## [MVP Release]
### Added
- OpenAI-compatible API endpoint (`/v1/chat/completions`)
- Local agent forwarding (vllm, Docker-based only)
- Proxy to OpenAI provider
- SQLite-based model registry with CLI
- Initial Docker Compose/dev stack setup (in progress)
- CI workflow (in progress)
- MkDocs documentation site (in progress)

### Not included in MVP (deferred):
- Redis caching
- Rate limiting
- Smart routing
- Request logging and metrics
- Agent registration & heartbeats
- llm-d cluster support (Kubernetes, Helm)
- Additional inference worker types (llm-d)
- Provider integrations: Anthropic, Google, OpenRouter, Grok, Venice

---

## [Planned/Upcoming]
- Redis caching layer
- Rate limiting
- Smart routing
- Request logging and metrics
- Agent registration & heartbeats
- llm-d cluster support (forwarding, deployment, endpoint exposure)
- Additional inference worker types (llm-d)
- Provider integrations: Anthropic, Google, OpenRouter, Grok, Venice

See [IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md) for the up-to-date status.
