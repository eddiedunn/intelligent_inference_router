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

If `ROUTER_SHARED_SECRET` is configured, include an Authorization header:

```bash
curl -H 'Authorization: Bearer mysecret' ...
```

Requests for models prefixed with `local` are forwarded to the Local Agent.
