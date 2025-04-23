# Project Brief: Intelligent Inference Router (IIR) - MVP Phase 1a

## Purpose
Establish a robust, modular gateway for LLM inference requests, capable of intelligent routing between local and (future) external model backends. The MVP focuses on validating core routing, local model integration, caching, and monitoring, running on a high-performance local machine with GPU acceleration.

## Scope (Phase 1a)
- OpenAI-compatible API endpoints (`/v1/chat/completions`, `/v1/models`, `/health`)
- Prompt classification (local vs remote)
- Routing logic (fully implemented for local, stub for remote)
- Local vLLM backend integration (Llama-3-8B-Instruct)
- Redis-based caching (local path)
- Monitoring: Prometheus + Grafana
- API key authentication & rate limiting
- Docker Compose deployment

## Out of Scope (Phase 1a)
- External provider integration (stub only)
- Advanced routing, dynamic model loading, Kubernetes, advanced security, streaming, etc.

## Success Metrics
- Local path latency (TTFT p95 ≤ 200ms)
- Token throughput (TTPS p95 ≥ 30/sec)
- Uptime ≥ 99.9%
- Cache hit rate ≥ 25%
- Prompt classification latency p95 < 50ms

## Audience
AI engineers and developers deploying/test-driving LLM inference gateways on-premises.
