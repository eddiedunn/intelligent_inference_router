# Intelligent Inference Router – MVP Feature Checklist

## Router

### Build OpenAI-compatible API
**MoSCoW:** Must
**User story:** As a developer I want a FastAPI server exposing `/v1/chat/completions`
so that clients can use existing OpenAI SDKs.
**Acceptance criteria:**
- ✅ Router starts via `make dev` and listens on `:8000`.
- ✅ `POST /v1/chat/completions` returns a dummy response.
- ✅ Project uses type-hinted Python 3.10+ following PEP 8.
**Implementation hints:**
- Create `router/main.py` using FastAPI.
- Use env vars `SQLITE_DB_PATH` and `REDIS_URL` from `.env`.
- Include a simple `make dev` target to run `uvicorn`.
**Test cases:**
- `curl -X POST localhost:8000/v1/chat/completions -d '{"model":"dummy"}'` returns 200.
- `pytest tests/router/test_api.py` covers happy path.
**Dependencies/blocks:** None.

### Connect Router to Local Agent
**User story:** As a router user I want requests for local models forwarded to the Mac agent
so that lightweight prompts run on-device.
**Acceptance criteria:**
- ✅ Router resolves model type `local` via the registry.
- ✅ Requests are sent to `http://<agent-host>:5000/infer` and response relayed.
- ✅ Errors from the agent are surfaced to the client.
**Implementation hints:**
- Use `httpx.AsyncClient` for forwarding.
- Agent URL stored in SQLite registry.
**Test cases:**
- Start agent with sample model and run `curl` through router.
- Unit test with `pytest` mocking agent replies.
**Dependencies/blocks:** Build Local Agent service.

### Proxy External API Calls
**User story:** As a developer I want the router to proxy to OpenAI or Anthropic
so that I can use remote models when needed.
**Acceptance criteria:**
- ✅ Router reads `EXTERNAL_*_KEY` from env to call providers.
- ✅ API requests mirror the OpenAI chat JSON format.
- ✅ Streaming and non-streaming responses work.
**Implementation hints:**
- Use `httpx` or provider SDKs.
- Allow provider base URL via env var.
**Test cases:**
- Mock external call in `pytest` to verify forwarding logic.
- `curl` with real key returns provider output.
**Dependencies/blocks:** Model registry entry for external provider.

### Enable Redis Caching
**MoSCoW:** Should
**User story:** As a frequent caller I want identical prompts cached so that repeat requests return faster.
**Acceptance criteria:**
- ✅ Router checks Redis before forwarding a request.
- ✅ Cached entries expire after a configurable TTL.
- ✅ Cache key includes model name and prompt hash.
**Implementation hints:**
- Use `redis-py` with `REDIS_URL`.
- Add `CACHE_TTL` env var.
**Test cases:**
- `pytest` ensures cache hit skips backend call.
- Observe log message indicating cache usage.
**Dependencies/blocks:** Build Router API.

### Implement SQLite Model Registry
**MoSCoW:** Must
**User story:** As an operator I want a registry of models and endpoints
so that routing rules are configurable without code changes.
**Acceptance criteria:**
- ✅ SQLite DB stores model name, type, and endpoint.
- ✅ Router loads registry on startup.
- ✅ Admin CLI can add or update models.
**Implementation hints:**
- Use `sqlalchemy` ORM with file path from `SQLITE_DB_PATH`.
- Provide `make migrate` and `make seed` commands.
**Test cases:**
- `pytest tests/router/test_registry.py` for CRUD operations.
- Manual check: adding new model allows immediate routing.
**Dependencies/blocks:** Router API skeleton.

### Forward to llm-d Cluster
**MoSCoW:** Could
**User story:** As a user with heavy workloads I want to route to a GPU cluster so that large models run efficiently.
**Acceptance criteria:**
- ✅ Router recognizes model type `llm-d`.
- ✅ Requests hit `${LLMD_ENDPOINT}/v1/chat/completions`.
- ✅ Failures return informative HTTP errors.
**Implementation hints:**
- Configure llm-d via Helm chart in `worker_cluster/chart`.
- Use env var `LLMD_ENDPOINT`.
**Test cases:**
- `curl` through router to cluster returns completion.
- Integration test mocks llm-d endpoint.
**Dependencies/blocks:** Model registry with llm-d entry.

### Add Request Logging and Metrics
**MoSCoW:** Should
**User story:** As an operator I want logs and basic metrics so that routing decisions can be audited and optimized.
**Acceptance criteria:**
- ✅ Each request logs model, backend, latency, and cache hit.
- ✅ Metrics exposed at `/metrics` in Prometheus format.
- ✅ Logs written to stdout and rotated daily.
**Implementation hints:**
- Use Python `logging` module and `prometheus-client`.
- Configure log level via `LOG_LEVEL` env var.
**Test cases:**
- `pytest` asserts metrics counters increment.
- `curl /metrics` returns Prometheus text.
**Dependencies/blocks:** Build Router API and caching.

## Local Agent

### Provide Local LLM Service
**MoSCoW:** Must
**User story:** As a Mac user I want a lightweight HTTP service that runs a local model
so that I can process prompts offline.
**Acceptance criteria:**
- ✅ Agent starts via `python local_agent/main.py` on macOS.
- ✅ `POST /infer` accepts prompt and generation params.
- ✅ Uses PyTorch MPS to load default model `local_mistral-7b-instruct-q4`.
**Implementation hints:**
- Build FastAPI app binding to `:5000`.
- Keep dependencies minimal; rely on `torch` and `transformers`.
**Test cases:**
- `curl localhost:5000/infer` returns text.
- Unit tests mock model for fast execution.
**Dependencies/blocks:** None.

### Register Agent with Router
**MoSCoW:** Should
**User story:** As an operator I want the agent to announce available models
so that the router updates its registry automatically.
**Acceptance criteria:**
- ✅ On startup, agent POSTs model info to `router_host/register`.
- ✅ Router updates SQLite entry or marks agent offline if heartbeat fails.
- ✅ Registration retries on network error.
**Implementation hints:**
- Use `httpx` for registration calls.
- Agent reads router address from `ROUTER_URL` env var.
**Test cases:**
- `pytest` fakes router endpoint and checks registration logic.
- Stop router to verify retry behavior.
**Dependencies/blocks:** Router registry feature.

### Send Periodic Heartbeats
**MoSCoW:** Could
**User story:** As a router maintainer I want health info from agents so that routing avoids failed nodes.
**Acceptance criteria:**
- ✅ Agent sends heartbeat every N seconds with queue length.
- ✅ Router marks agent stale after timeout.
- ✅ Heartbeat interval configurable via env var.
**Implementation hints:**
- Background task with `asyncio.create_task`.
- Use `/heartbeat` endpoint on router.
**Test cases:**
- `pytest` verifies stale agents are pruned.
- Inspect router logs for heartbeat data.
**Dependencies/blocks:** Register Agent with Router.

## GPU Worker Cluster

### Deploy llm-d via Helm
**MoSCoW:** Should
**User story:** As an infra engineer I want a Helm chart for llm-d so that GPU workers can be installed on k3s easily.
**Acceptance criteria:**
- ✅ `make k3s-up` installs llm-d chart under `worker_cluster/chart`.
- ✅ Cluster exposes service `llm-d` on port 8000.
- ✅ Values file allows model selection and GPU resources.
**Implementation hints:**
- Base chart on Red Hat llm-d examples.
- Provide `values.yaml` with minimal defaults.
**Test cases:**
- `helm lint worker_cluster/chart` succeeds.
- Manual `curl` to cluster endpoint returns stub response.
**Dependencies/blocks:** None.

### Expose Cluster Endpoint to Router
**MoSCoW:** Could
**User story:** As a router admin I want llm-d reachable via a stable URL so that requests from the router succeed.
**Acceptance criteria:**
- ✅ Helm chart outputs `LLMD_ENDPOINT` for router config.
- ✅ Service is reachable from router pod or host machine.
- ✅ TLS termination optional but documented.
**Implementation hints:**
- Use Kubernetes Ingress or ClusterIP depending on environment.
- Document connection details in README.
**Test cases:**
- `kubectl get svc llm-d` shows cluster IP.
- Integration test uses env var to hit cluster from router.
**Dependencies/blocks:** Deploy llm-d via Helm.

## Shared / Infra

### Docker Compose for Dev Stack
**MoSCoW:** Should
**User story:** As a contributor I want a single command to start router, Redis, and optional agent
so that local testing is easy.
**Acceptance criteria:**
- ✅ `make docker-dev` launches services via Docker Compose.
- ✅ Env file `.env.example` documents required vars.
- ✅ Stopping the stack cleans up all containers.
**Implementation hints:**
- Compose file includes router image, Redis, and volume for SQLite.
- Mount Mac agent only when running on Darwin.
**Test cases:**
- `docker compose ps` shows all services running.
- E2E pytest uses compose stack for tests.
**Dependencies/blocks:** Router API and Local Agent implementation.

### Continuous Integration Workflow
**MoSCoW:** Should
**User story:** As a project maintainer I want automated lint and test checks
so that PRs stay stable.
**Acceptance criteria:**
- ✅ GitHub Actions runs `make lint` and `make test` on every PR.
- ✅ Docker images build successfully in CI.
- ✅ Failures block merge until resolved.
**Implementation hints:**
- Add `.github/workflows/ci.yml` using the provided make targets.
- Cache Python deps to speed up builds.
**Test cases:**
- Open a dummy PR and verify all checks execute.
**Dependencies/blocks:** Docker Compose for Dev Stack.

### Documentation Site with MkDocs
**MoSCoW:** Could
**User story:** As a new developer I want browsable docs
so that onboarding is quick.
**Acceptance criteria:**
- ✅ `docs/` contains MkDocs config and markdown pages.
- ✅ `make docs-serve` launches local preview on `:8001`.
- ✅ Deployment workflow publishes to GitHub Pages.
**Implementation hints:**
- Base config on `mkdocs-material` theme.
- Include PRD and FEATURES in the nav.
**Test cases:**
- `mkdocs build` runs without errors.
- Preview site loads root page.
**Dependencies/blocks:** Continuous Integration Workflow.

