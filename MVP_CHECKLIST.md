# IIR MVP Phase 1a: Feature Checklist & Tracking

## Core Features (Complete/To Do)

- [ ] OpenAI-compatible REST API endpoints: `/v1/chat/completions`, `/v1/models`, `/health`
- [ ] Prompt classification (local only)
- [ ] Local vLLM backend integration (Llama-3-8B-Instruct)
- [ ] Redis-based response caching
- [ ] Prometheus & Grafana monitoring
- [ ] API key authentication
- [ ] Rate limiting (FastAPI Limiter)
- [ ] Docker Compose deployment (containerized stack)
- [ ] Structured JSON logging
- [ ] Externalized configuration (YAML + .env)
- [ ] Robust error handling (OpenAI-compatible error responses)
- [ ] Comprehensive documentation (setup, config, API, architecture, monitoring, troubleshooting)
- [ ] Unit, integration, and system tests

---

## Detailed Checklist: What’s Left to Implement/Finalize

### 1. API & Routing
- [ ] Ensure all OpenAI-compatible endpoints are implemented and tested.
- [ ] Confirm prompt classification logic is robust and only supports "local" routing.
- [ ] Ensure routing to vLLM backend is fully functional; remote routing is not present.

### 2. Caching
- [ ] Integrate Redis for caching responses.
- [ ] Validate cache hit/miss logic and ensure cache keying is correct.
- [ ] Document caching strategy.

### 3. Authentication & Rate Limiting
- [ ] Implement API key authentication middleware.
- [ ] Integrate FastAPI Limiter with Redis for rate limiting.
- [ ] Ensure all endpoints are protected as intended.
- [ ] Write tests for both authentication and rate limiting.

### 4. Monitoring & Observability
- [ ] Integrate Prometheus metrics collection in all major code paths (API, cache, classifier, backend).
- [ ] Ensure Grafana dashboards are available and documented.
- [ ] Confirm all critical metrics are exported and visible in Prometheus.

### 5. Containerization & Deployment
- [ ] Finalize Docker Compose setup for all services (router, vLLM, Redis, Prometheus, Grafana).
- [ ] Validate .env and config files are loaded correctly in containers.
- [ ] Document local deployment and troubleshooting steps.

### 6. Testing
- [ ] Complete unit tests for all modules (classifier, cache, routing, security, metrics, etc.).
- [ ] Complete integration tests for API endpoints and full request flow.
- [ ] Ensure all tests pass locally (pytest, make test, or Docker Compose).
- [ ] Remove/replace any skipped or stubbed tests related to remote routing.

### 7. Documentation
- [ ] Update README.md, SETUP.md, and all docs to reflect local-only operation.
- [ ] Ensure Memory Bank files are fully up-to-date with the codebase and workflow.
- [ ] Remove any lingering references to remote test execution or remote routing.
- [ ] Add/clarify troubleshooting and FAQ sections as needed.

### 8. General Codebase Cleanup
- [ ] Remove any obsolete files, scripts, or configs (already started).
- [ ] Ensure all TODOs and FIXMEs in the code are addressed or tracked.
- [ ] Standardize code formatting and linting.

---

## Model Naming Convention & Smart Routing
- [ ] Implement model naming convention as `<provider>/<model>` (e.g., `openai/gpt-4.1`, `local/llama-3-8b-instruct`).
- [ ] Update all config, docs, and API references to use this convention.
- [ ] Ensure prompt classification and routing logic utilize the model name to determine backend/provider.
- [ ] Add “smart routing” mode: router loads and uses any model it is provided (if available/configured).
- [ ] Document supported models/providers and naming scheme in README and API docs.
