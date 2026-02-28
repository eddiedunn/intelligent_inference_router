# Intelligent Inference Router v2

Smart LLM routing layer on top of [Bifrost](https://github.com/maximhq/bifrost).

**Bifrost handles the plumbing** (provider APIs, failover, load balancing, caching).
**This router is the brain** (classifies prompts, picks the optimal model based on cost/quality/capability).

## Architecture

```
Client Request
     │
┌──────────────────────────┐
│  Intelligent Router (Py) │  classifies prompt, picks model
└───────────┬──────────────┘
            │
┌──────────────────────────┐
│  Bifrost (Go)            │  provider APIs, <100µs overhead
└───────────┬──────────────┘
            │
   ┌────┬────────┬─────────┬───────┐
   Ollama  OpenAI  Anthropic  Groq
```

## Quick Start

```bash
# 1. Copy env file
cp .env.example .env
# Edit .env with your API keys

# 2. Start with Podman
cd podman && podman-compose up -d

# 3. Test
curl http://localhost:8000/health
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer $IIR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "Hello!"}]}'
```

## Routing Strategies

| Strategy | Behavior |
|----------|----------|
| `cost-optimized` (default) | Simple tasks → local Ollama (free), complex → cheapest capable cloud model |
| `quality-first` | Best model regardless of cost |
| `local-only` | Never use cloud |
| `pass-through` | Specify model explicitly, router doesn't override |

Override per-request with `X-Routing-Strategy` header.

## Development

```bash
pip install -e ".[test,dev]"
pytest
```

## Response Headers

Every response includes routing metadata:
- `X-Route-Model` — model that handled the request
- `X-Route-Provider` — provider (ollama, openai, anthropic, groq)
- `X-Classification` — prompt classification (coding, math, simple_chat, etc.)
- `X-Route-Reason` — why this model was chosen
