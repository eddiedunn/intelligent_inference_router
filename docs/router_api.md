# Router API Quickstart

> **For the authoritative MVP/post-MVP feature list, see [IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md).**

---

## MVP Support Summary

This API currently supports the following:
- OpenAI-compatible endpoint: `/v1/chat/completions`
- Local agent forwarding (only vllm, Docker-based workers)
- Proxying to OpenAI
- Forwarding to additional providers: Anthropic, Google, OpenRouter, Grok, Venice
- Local inference via Hugging Face models


**Note:** Features such as rate limiting, smart routing, additional worker types (llm-d), and other providers (Anthropic, Google, OpenRouter, Grok, Venice, Hugging Face) are planned for post-MVP.


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

### Smart Routing Logic

`/v1/chat/completions` requests are routed based on model type, estimated
request cost, and recent backend latency metrics. When a `gpt-*` model is
requested, the router weighs the measured latency of the OpenAI backend against
the local agent. If the request cost (roughly the combined prompt length)
exceeds `ROUTER_COST_THRESHOLD`, the request is sent to the local agent to save
API usage. Otherwise, the backend with the lowest weighted score—computed from
`ROUTER_COST_WEIGHT` and `ROUTER_LATENCY_WEIGHT`—is selected.

### Configuration

The router reads API keys for each provider from environment variables. A sample
`.env` file might look like:

```bash
OPENAI_BASE_URL=https://api.openai.com
EXTERNAL_OPENAI_KEY=sk-...
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
```


`GOOGLE_BASE_URL` sets the base endpoint for the Gemini API while
`EXTERNAL_GOOGLE_KEY` holds your Google API token.


For OpenRouter, both `OPENROUTER_BASE_URL` and `EXTERNAL_OPENROUTER_KEY` must be
set before the router can forward requests to the service.

Routing decisions also depend on a few tuning variables. These may be set as
environment variables or placed under `[tool.router]` in `pyproject.toml`:

```bash
ROUTER_COST_WEIGHT=1.0      # weight applied to request cost
ROUTER_LATENCY_WEIGHT=1.0   # weight applied to measured backend latency
ROUTER_COST_THRESHOLD=1000  # route locally if cost exceeds this value
```

If omitted, the router falls back to the values defined in the project config.



Set the relevant keys before starting the server. Models for each provider must
be added to the registry using `router.cli add-model` or `refresh-openai` for
OpenAI.

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

### Redis Caching

Set `REDIS_URL` to point to your Redis instance and `CACHE_TTL` to the desired
expiration (in seconds). When a request is received, the router checks Redis for
a cached response before forwarding to a backend. Non-streaming responses are
stored in Redis using the TTL.


---

## Post-MVP Roadmap

The following features are planned for future releases:
- Rate limiting
- Smart routing
- Additional inference worker types (llm-d)
- Provider integrations: Anthropic, Google, OpenRouter, Grok, Venice, Hugging Face

See [IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md) for the up-to-date status.

---

## Monitoring

The router exposes Prometheus metrics at `/metrics`. Basic counters
track request volume, latency and cache hits. Logs are written to
`logs/router.log` and rotated daily. Configure the log level via the
`LOG_LEVEL` environment variable.
