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
