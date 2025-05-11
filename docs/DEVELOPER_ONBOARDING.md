# Developer Onboarding Guide: Intelligent Inference Router (IIR)

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
- See `docs/SETUP.md` for Python, Docker, and Redis setup instructions.
- Copy `.env.example` to `.env` and fill in required secrets.
- Install dependencies: `pip install -r requirements.txt`
- Start services: `docker-compose up`

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
