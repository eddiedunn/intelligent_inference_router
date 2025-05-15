# Developer Onboarding

## Testing Strategy: Unit vs Integration

### Unit Tests (FastAPI TestClient)
- Unit tests use FastAPI's `TestClient` to run the app in-process, without starting a real HTTP server.
- Use these for endpoint validation, input/output checks, and logic that does not require real network calls.
- Example usage:
  ```python
  from fastapi.testclient import TestClient
  from router.main import create_app
  client = TestClient(create_app())
  def test_health():
      r = client.get("/health")
      assert r.status_code == 200
  ```

### Integration Tests (Real HTTP API)
- Integration tests spin up the actual API server (and/or model registry) on a random port using pytest fixtures.
- Use these for tests that:
  - Use `requests`/`httpx` to make real HTTP calls
  - Need to test startup/shutdown hooks, background tasks, or cross-service communication
- Fixtures:
  - `main_api_server`: starts the main API and sets `IIR_API_URL`
  - `model_registry_server`: starts the model registry and sets `MODEL_REGISTRY_URL`
- Example usage:
  ```python
  import os, requests
  def test_registry_refresh(main_api_server):
      api_url = os.environ["IIR_API_URL"]
      r = requests.post(f"{api_url}/v1/registry/refresh")
      assert r.status_code == 200
  ```
- Always use the dynamic URLs from environment variables, never hardcode ports.

### Best Practices
- Use `TestClient` for fast, isolated unit tests.
- Use the provided fixtures for integration/E2E tests that require real HTTP/network.
- Ensure all new integration tests depend on the appropriate fixture and use dynamic URLs.
- All test servers are started on random ports and cleaned up automatically—no port conflicts or orphaned processes.
 Guide: Intelligent Inference Router (IIR)

> **Documentation Map:**
> - **Setup Guide:** Basic installation & running the stack (see `SETUP.md`).
> - **Developer Onboarding (this doc):** Dev setup, contribution, API key system.
> - **API Reference:** See `API.md` for all endpoints.
> - **Troubleshooting:** See `TROUBLESHOOTING.md` for common errors.
> - **Architecture:** See `ARCHITECTURE.md` for system overview.

> **For basic installation and running the stack, see `SETUP.md`.**

Welcome to the IIR codebase! This guide will help you get productive quickly, understand the core features, and interact with the API using Python and JavaScript/TypeScript.

---

## Table of Contents
- [Project Overview](#project-overview)
- [Environment Setup](#environment-setup)
- [Key Features](#key-features)
- [API Key System](#api-key-system)
  - [Registering an API Key](#registering-an-api-key)
  - [Using Your API Key](#using-your-api-key)
  - [Revoking and Listing Keys](#revoking-and-listing-keys)
- [Model Registry](#model-registry)
  - [Listing Models](#listing-models)
  - [Refreshing Registry](#refreshing-registry)
- [Example API Usage](#example-api-usage)
  - [Python Example](#python-example)
  - [JavaScript/TypeScript Example](#javascripttypescript-example)
- [Testing & Contribution](#testing--contribution)
- [Troubleshooting](#troubleshooting)

---

## Project Overview
IIR is a containerized, OpenAI-compatible inference gateway that routes LLM requests to local or remote models, supports prompt classification, and provides robust monitoring and caching. All endpoints are protected by a production-grade API key system.

## Environment Setup
- **See `docs/SETUP.md` for all Python, Docker, Redis, and Hugging Face setup instructions.**
- After following SETUP.md, install any additional dev dependencies as needed: `pip install -r requirements.txt`
- Start services as described in SETUP.md (`docker compose up -d`).

## Key Features
- **OpenAI-compatible REST endpoints**: `/v1/chat/completions`, `/v1/models`, `/infer`, etc.
- **API key authentication**: All protected endpoints require a valid API key (see below).
- **Dynamic model registry**: Discover and route to available models, both local and remote.
- **Redis caching**: Fast response caching for repeated queries.
- **Prometheus/Grafana monitoring**: Built-in metrics for ops.

---

## API Key System

### Registration
Register an API key by POSTing to `/api/v1/apikeys`:
- Only allowed from trusted IPs (default: local network, see `is_allowed_ip`).
- Keys are stored in the database and are immediately valid for all protected endpoints.

#### Example (Python)
```python
import requests
payload = {"description": "dev test key", "priority": 10}
r = requests.post("http://localhost:8000/api/v1/apikeys", json=payload)
print(r.json())  # {'api_key': '...', 'priority': 10}
```

#### Example (curl)
```bash
curl -X POST http://localhost:8000/api/v1/apikeys \
  -H "Content-Type: application/json" \
  -d '{"description":"dev test key","priority":10}'
```

### Usage
Include your API key in the `Authorization` header for all protected endpoints:

#### Example (Python)
```python
headers = {"Authorization": f"Bearer {api_key}"}
r = requests.post("http://localhost:8000/infer", json={"model": "musicgen", "input": {"prompt": "hello"}}, headers=headers)
print(r.json())
```

#### Example (JavaScript/TypeScript)
```js
const apiKey = "YOUR_API_KEY";
fetch("http://localhost:8000/infer", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
    "Authorization": `Bearer ${apiKey}`
  },
  body: JSON.stringify({ model: "musicgen", input: { prompt: "hello" } })
})
  .then(res => res.json())
  .then(console.log)
  .catch(console.error);
```

### Revoking and Listing Keys
- Use the admin DB or future API endpoints to revoke or list keys.
- Only active keys in the DB are accepted by the API.

---

## Model Registry

### Listing Models
Get all available models:
```python
import requests
headers = {"Authorization": f"Bearer {api_key}"}
r = requests.get("http://localhost:8000/v1/models", headers=headers)
print(r.json())
```

#### Example (curl)
```bash
curl -X GET http://localhost:8000/v1/models \
  -H "Authorization: Bearer YOUR_API_KEY"
```
Replace `YOUR_API_KEY` with your actual API key.

### Refreshing Registry
Trigger hardware/model discovery and registry refresh:
```python
r = requests.post("http://localhost:8000/v1/registry/refresh", headers=headers)
print(r.json())
```

---

## Example API Usage

### Python Example: Chat Completion
```python
import requests
headers = {"Authorization": f"Bearer {api_key}"}
payload = {"model": "local/llama-3-8b-instruct", "messages": [{"role": "user", "content": "Hello!"}]}
r = requests.post("http://localhost:8000/v1/chat/completions", json=payload, headers=headers)
print(r.json())
```

### JavaScript/TypeScript Example: Model Listing
```js
const apiKey = "YOUR_API_KEY";
fetch("http://localhost:8000/v1/models", {
  headers: { "Authorization": `Bearer ${apiKey}` }
})
  .then(res => res.json())
  .then(console.log);
```

---

## Testing & Contribution
- Run tests: `pytest router/tests/`
- All tests use the same DB-backed API key logic as production.
- See `README.md` and `docs/SETUP.md` for more.

## Troubleshooting
- See `docs/TROUBLESHOOTING.md` for common issues.
- For API key issues, ensure your key is active in the DB and sent in the `Authorization` header.
- For registry/model issues, refresh the registry and check logs for errors.

---

Welcome aboard, and happy hacking!
