# Usage

The router exposes an OpenAI compatible API at `/v1/chat/completions`.

Start the services locally:
```bash
make dev
```

Then send a completion request:
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
     -H 'Content-Type: application/json' \
     -d '{"model":"local_mistral","messages":[{"role":"user","content":"hello"}]}'
```

Requests for models prefixed with `local` are forwarded to the Local Agent.

## External Cache Service

The router uses an in-memory cache by default. When the optional
`CACHE_ENDPOINT` environment variable points to the cache service, all cache
operations go through that HTTP API. Build and run the service with:

```bash
make cache-service
```

The service exposes simple `GET /<key>` and `PUT /<key>?ttl=SECONDS` endpoints
and listens on port `8600` by default.
