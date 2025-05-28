# Router API Quickstart

> **For the authoritative MVP/post-MVP feature list, see [IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md).**

---

## MVP Support Summary

This API currently supports the following:
- OpenAI-compatible endpoint: `/v1/chat/completions`
- Local agent forwarding (only vllm, Docker-based workers)
- Proxying to OpenAI
- Forwarding to additional providers: Anthropic, Google, OpenRouter, Grok, Venice

**Note:** Features such as Redis caching, rate limiting, smart routing, and llm-d worker types are still planned for a future release.

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

Set the relevant keys before starting the server. Models for each provider must
be added to the registry using `router.cli add-model` or `refresh-openai` for
OpenAI.

---

## Post-MVP Roadmap

The following features are planned for future releases:
- Redis caching
- Rate limiting
- Smart routing
- Request logging and metrics
- Additional inference worker types (llm-d)
- Provider integrations: Anthropic, Google, OpenRouter, Grok, Venice

See [IMPLEMENTATION_STATUS.md](../IMPLEMENTATION_STATUS.md) for the up-to-date status.
