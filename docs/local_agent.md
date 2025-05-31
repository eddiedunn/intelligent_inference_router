# Local Agent

The Local Agent runs on macOS and forwards completion requests to a local model. It registers with the Router so the gateway knows which models are available.

## Environment Variables

Set these variables in your shell or a `.env` file before starting the service. Defaults are shown in parentheses.

| Variable | Default | Description |
|---------|---------|-------------|
| `ROUTER_URL` | `http://localhost:8000` | Router base URL used for registration and heartbeats |
| `HEARTBEAT_INTERVAL` | `30` | Seconds between heartbeat pings |
| `AGENT_NAME` | `local-agent` | Name reported to the Router |
| `AGENT_ENDPOINT` | `http://localhost:5000` | Public URL where the agent listens |
| `MODEL_LIST` | `local_mistral-7b-instruct-q4` | Comma-separated models served |

Start the agent with:

```bash
uvicorn local_agent.main:app --port 5000
```

For example, to register under a different name:

```bash
export AGENT_NAME=my-macos-agent
uvicorn local_agent.main:app --port 5000
```
