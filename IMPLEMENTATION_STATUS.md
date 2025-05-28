# MVP Implementation Checklist

This section tracks only the features required for the MVP release. Only items checked here are required for the MVP milestone.

## MVP Features

### Router
- [x] Build OpenAI-compatible API
- [x] Connect Router to Local Agent
- [x] Proxy External API Calls
- [x] Implement SQLite Model Registry

### Local Agent
- [x] Provide Local LLM Service via vLLM

### Shared / Infra
- [ ] Docker Compose for Dev Stack
- [ ] Continuous Integration Workflow
- [ ] Documentation Site with MkDocs

### Explicitly NOT in MVP
- [x] Enable Redis Caching
- [ ] Rate Limiting
- [ ] Smart Routing
- [ ] Add Request Logging and Metrics
- [ ] Register Agent with Router
- [ ] Send Periodic Heartbeats
- [ ] Forward to llm-d Cluster
- [ ] Deploy llm-d via Helm
- [ ] Expose Cluster Endpoint to Router
- [ ] Additional Inference Worker Types (only vllm in Docker for MVP)

---

# Post-MVP Roadmap

This section tracks features, integrations, and improvements to be implemented after the MVP milestone.

## Features Deferred Until After MVP
- Caching (e.g., Redis caching)
- Rate limiting
- Smart routing (intelligent request dispatch)
- Request Logging and Metrics
- Agent registration & heartbeats
- llm-d cluster support (forwarding, deployment, endpoint exposure)
- Additional inference worker types (llm-d)

## Planned Provider Integrations (Post-MVP)
- Anthropic
- Google
- OpenRouter
- Grok
- Venice

---

**Note:** Only `vllm` (Docker-based) inference workers are supported for MVP. All other worker types and provider integrations are deferred until after MVP. This separation is intentional to accelerate MVP delivery. Track deferred features and integrations for post-MVP development.
