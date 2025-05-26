# Intelligent Inference Router

This project provides a prototype OpenAI-compatible API that returns a dummy response.

## Development

Start the router using `make dev` and access `http://localhost:8000/v1/chat/completions`.

For local models, run the Local Agent service:

```bash
uvicorn local_agent.main:app --port 5000
```

Any request whose `model` starts with `local` will be forwarded to this agent.
