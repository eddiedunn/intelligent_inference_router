# Project Brief: Intelligent Inference Router (IIR) - MVP Phase 1a

## Error Handling & Validation Initiative (2025-05)
- The project enforces robust, explicit error codes and messages for all API validation and routing errors.
- Model IDs must always be in <provider>/<model> format (e.g., 'openai/gpt-3.5-turbo').
- The model registry is the authoritative source for available models, and all validation/tests must align with this.
- Error precedence: token/rate limit errors take precedence over unknown provider errors.
- All tests and code must be kept in sync with the error contract for maintainability and reliability.

---

> **For further details and onboarding:**
> - **Setup Guide:** See `docs/SETUP.md` for installation and running the stack.
> - **Developer Onboarding:** See `docs/DEVELOPER_ONBOARDING.md` for dev setup, contribution, and API key management.
> - **Architecture:** See `docs/ARCHITECTURE.md` for high-level system diagrams and request lifecycle.

## Purpose
Establish a robust, modular gateway for LLM inference requests, capable of intelligent routing between local and (future) external model backends. The MVP focuses on validating core routing, local model integration, caching, and monitoring, running on a high-performance local machine with GPU acceleration.

## Scope (Phase 1a)
- OpenAI-compatible API endpoints (`/v1/chat/completions`, `/v1/models`, `/health`)
- Prompt classification (local)
- Routing logic (fully implemented for local)
- Local vLLM backend integration (Llama-3-8B-Instruct)
- Redis-based caching (local path)
- Monitoring: Prometheus + Grafana
- API key authentication & rate limiting
- Docker Compose deployment

## Out of Scope (Phase 1a)
- External provider integration 
- Advanced routing, dynamic model loading, Kubernetes, advanced security, streaming, etc.
- Remote routing

## Success Metrics
- Local path latency (TTFT p95 ≤ 200ms)
- Token throughput (TTPS p95 ≥ 30/sec)
- Uptime ≥ 99.9%
- Cache hit rate ≥ 25%
- Prompt classification latency p95 < 50ms

## Audience
AI engineers and developers deploying/test-driving LLM inference gateways on-premises.
