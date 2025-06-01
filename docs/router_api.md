# Router API Quickstart

> **For the authoritative MVP/post-MVP feature list, see [IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md).**

---

## MVP Support Summary

This API currently supports the following:
- OpenAI-compatible endpoint: `/v1/chat/completions`
- Local agent forwarding (only vllm, Docker-based workers)
- Proxying to OpenAI
- SQLite-backed model registry


**Note:** Features such as caching, rate limiting, smart routing,
additional worker types (llm-d), and the planned Hugging Face provider
integration remain post-MVP.

---

The router exposes an OpenAI-compatible endpoint at `/v1/chat/completions`.

Start the server locally:

```bash
make dev
```

Send a test request:

```bash
curl -X POST http://localhost:8000/v1/chat/completions \
    -H 'Content-Type: application/json' \
    -d '{"model":"dummy","messages":[{"role":"user","content":"hi"}]}'
```

The response contains a placeholder completion:

```json
{
  "id": "cmpl-...",
  "object": "chat.completion",
  "model": "dummy",
  "choices": [{
    "index": 0,
    "message": {"role": "assistant", "content": "Hello world"},
    "finish_reason": "stop"
  }]
}
```

### Local Agent Forwarding

If the `model` field begins with `local`, the router forwards the request to the Local Agent running on port `5000`:

```bash
uvicorn local_agent.main:app --port 5000
```

The router relays the agent's JSON response back to the client.

### Routing Logic

When a request hits `/v1/chat/completions` the router first looks up the
requested model in the SQLite registry. If the model exists the request is
forwarded to the provider specified by the `type` column. Unknown models fall
back to simple prefix heuristics:

- `local*` → Local Agent
- `gpt-*` → OpenAI
- `llmd-*` → llm-d cluster (when `LLMD_ENDPOINT` is set)
- `claude*` → Anthropic
- `google*` → Google
- `openrouter*` → OpenRouter
- `grok*` → Grok
- `venice*` → Venice

This basic scheme will be replaced by smart routing in a future release.

### Configuration

The router reads its configuration from environment variables. A sample `.env`
might look like:

```bash
SQLITE_DB_PATH=data/models.db
# caching uses an in-memory TTL dictionary
LOCAL_AGENT_URL=http://local_agent:5000
OPENAI_BASE_URL=https://api.openai.com
EXTERNAL_OPENAI_KEY=sk-...
LLMD_ENDPOINT=
ANTHROPIC_BASE_URL=https://api.anthropic.com
EXTERNAL_ANTHROPIC_KEY=...
GOOGLE_BASE_URL=https://generativelanguage.googleapis.com
EXTERNAL_GOOGLE_KEY=...
OPENROUTER_BASE_URL=https://openrouter.ai
EXTERNAL_OPENROUTER_KEY=...
GROK_BASE_URL=https://api.groq.com
EXTERNAL_GROK_KEY=...
VENICE_BASE_URL=https://api.venice.ai
EXTERNAL_VENICE_KEY=...
HF_CACHE_DIR=data/hf_models
HF_DEVICE=cpu
HUGGING_FACE_HUB_TOKEN=
RATE_LIMIT_REQUESTS=60
```


`GOOGLE_BASE_URL` sets the base endpoint for the Gemini API while
`EXTERNAL_GOOGLE_KEY` holds your Google API token.


For OpenRouter, both `OPENROUTER_BASE_URL` and `EXTERNAL_OPENROUTER_KEY` must be
set before the router can forward requests to the service.

The code defines a few tuning variables reserved for future smart routing.
They can be set as environment variables or placed under `[tool.router]` in
`pyproject.toml`:

```bash
ROUTER_COST_WEIGHT=1.0      # weight applied to request cost
ROUTER_LATENCY_WEIGHT=1.0   # weight applied to measured backend latency
ROUTER_COST_THRESHOLD=1000  # route locally if cost exceeds this value
```

If omitted, the router falls back to the values defined in the project config.

### Provider Architecture

Version&nbsp;0.2 introduced a unified provider layer. Every backend now derives
from one of two base classes:

- **`ApiProvider`** – forwards requests to a remote HTTP API.
- **`WeightProvider`** – loads model weights locally and performs inference.

Provider implementations live under `router/providers/`. The router looks at the
`kind` column of the model registry to decide which class to instantiate.

Weight providers such as `huggingface` download and cache models in
`HF_CACHE_DIR` and respect `HF_DEVICE`. API providers (OpenAI, Anthropic,
Google, OpenRouter, Grok and Venice) simply forward the request with the
appropriate API key.

Set the relevant keys before starting the server. Models for each provider must
be added to the registry using `router.cli add-model` (pass `kind=api` or
`kind=weight`) or via `refresh-openai` for OpenAI models.

#### Registering Weight-Based Models

Use the CLI to register models that run locally:

```bash
python -m router.cli add-model local_mistral local http://localhost:5000 weight
python -m router.cli add-model meta-llama/Llama-3 huggingface https://huggingface.co weight
```

Valid model types are `local`, `openai`, `llm-d`, `anthropic`, `google`,
`openrouter`, `grok`, and `venice`.

### Agent Registration & Heartbeats

Agents announce themselves to the router using the `/register` and `/heartbeat`
endpoints. A registration payload has the form:

```json
{
  "name": "local-agent",
  "endpoint": "http://localhost:5000",
  "models": ["local_mistral-7b-instruct-q4"]
}
```

After registration, agents should periodically `POST` to `/heartbeat` with

```json
{"name": "local-agent"}
```

The router stores this data in SQLite and updates the model registry
accordingly.

---

### In-Memory Caching

Responses are cached in-process using a simple TTL dictionary. This avoids the
need for Redis during development. Future versions may support an external
cache.


---

## Post-MVP Roadmap

The following features are planned for future releases:
- External cache integration (e.g., Redis)
- Rate limiting
- Smart routing
- Forwarding to llm-d cluster
- Deploying llm-d via Helm
- Exposing the cluster endpoint to the router
- Additional inference worker types (llm-d)
- Provider integration: Hugging Face

See [IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md) for the up-to-date status.

---

## Monitoring

The router exposes Prometheus metrics at `/metrics`. Basic counters
track request volume, latency and cache hits. Logs are written to
`logs/router.log` and rotated daily. Configure the log level via the
`LOG_LEVEL` environment variable.
