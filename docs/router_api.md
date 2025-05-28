# Router API Quickstart

> **For the authoritative MVP/post-MVP feature list, see [IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md).**

---

## MVP Support Summary

This API currently supports the following for the MVP:
- OpenAI-compatible endpoint: `/v1/chat/completions`
- Local agent forwarding (only vllm, Docker-based workers)
- Proxying to OpenAI (no other providers yet)

**Note:** Features such as Redis caching, rate limiting, smart routing, additional worker types (llm-d), and other providers (Anthropic, Google, OpenRouter, Grok, Venice) are planned for post-MVP.

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

---

## Post-MVP Roadmap

The following features are planned for future releases:
- Redis caching
- Rate limiting
- Smart routing
- Additional inference worker types (llm-d)
- Provider integrations: Anthropic, Google, OpenRouter, Grok, Venice

See [IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md) for the up-to-date status.

---

## Monitoring

The router exposes Prometheus metrics at `/metrics`. Basic counters
track request volume, latency and cache hits. Logs are written to
`logs/router.log` and rotated daily. Configure the log level via the
`LOG_LEVEL` environment variable.
