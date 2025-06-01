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
- [x] Docker Compose for Dev Stack
- [x] Continuous Integration Workflow
- [x] Documentation Site with MkDocs

### Testing
- [x] Unit Tests
- [x] Integration Tests

---

# Post-MVP Roadmap

This section tracks features, integrations, and improvements planned for after the MVP milestone.

## Post-MVP Features (Implemented)
- [x] Request Logging and Metrics
- [x] Agent Registration with Router
- [x] Send Periodic Heartbeats
- [x] Anthropic Provider Integration
- [x] Google Provider Integration
- [x] OpenRouter Provider Integration
- [x] Grok Provider Integration
- [x] Venice Provider Integration

## Post-MVP Features (Planned)
- [ ] Smart Routing
- [ ] Forward to llm-d Cluster
- [ ] Deploy llm-d via Helm
- [ ] Expose Cluster Endpoint to Router
- [ ] Additional Inference Worker Types (llm-d)
- [ ] Caching (in-memory TTL; Redis later)
- [ ] Rate limiting
- [ ] Hugging Face Provider Integration

---

**Note:** Only `vllm` (Docker-based) inference workers are supported for MVP. All other worker types and provider integrations are deferred until after MVP. This separation is intentional to accelerate MVP delivery. Track deferred features and integrations for post-MVP development.
