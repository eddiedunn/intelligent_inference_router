# Model Registry: How to Add, Refresh, and Verify Models

This guide explains how to safely update the model registry for Intelligent Inference Router (IIR) using supported tools and API endpoints.

---

## API Key Management Policy (READ THIS CAREFULLY)

There are **two completely separate types of API keys** in Intelligent Inference Router (IIR):

| Type                     | Purpose                                      | Where Stored                  | How Used / Managed                       |
|--------------------------|----------------------------------------------|-------------------------------|------------------------------------------|
| **Provider API Keys**    | Allow IIR to access external model providers | **Environment Variables**     | Set as env vars before app starts. Only used by IIR backend to talk to OpenAI, Anthropic, Hugging Face, etc. Never stored in IIR DB. |
| **IIR User/Client API Keys** | Allow users/clients to access IIR endpoints | **SQLite DB (`persistent-data/api_keys.sqlite3`)** | Managed via `router/apikey_db.py` or admin UI. Required in Authorization header (`Bearer <key>`) for all IIR API calls. |

### Provider API Keys (for OpenAI, Anthropic, etc)
- **Set as environment variables**: e.g. `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `HUGGINGFACE_API_KEY`, etc.
- **Used only by the IIR backend** to authenticate requests to external model providers.
- **Never sent by clients** and never stored in the IIR database.
- **Example:**
  ```bash
  export OPENAI_API_KEY=sk-xxxx
  export ANTHROPIC_API_KEY=sk-xxxx
  ```

### IIR User/Client API Keys (for accessing IIR itself)
- **Managed in the SQLite database**: `persistent-data/api_keys.sqlite3`.
- **Created/managed** via `router/apikey_db.py` tools, admin endpoints, or UI.
- **Required in the `Authorization: Bearer <key>` header** for all API calls to IIR (e.g., `/infer`, `/v1/models`).
- **Source of truth is the database only**. The `api_keys` section in config YAML is deprecated and ignored.
- **Environment variable `IIR_API_KEY`**: If set, is auto-imported into the DB on startup for convenience (e.g., for CI or local dev).
- **Do NOT confuse these with provider keys!**

**Summary:**
- Provider keys = env vars for IIR backend to access external APIs.
- IIR user/client keys = database for authenticating users/clients to IIR endpoints.

## 1. Adding a New Model to the Registry

**Preferred Method:** Use the `/v1/registry/refresh` endpoint or an admin script to discover and add models. Do not edit the database directly.

### **A. Using the API (Recommended for Most Users)**

- Ensure your environment variables (API keys, etc.) are set for the providers you want to add models from (e.g., `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`).
- Trigger a refresh:

```bash
curl -X POST http://localhost:8000/v1/registry/refresh \
  -H "Authorization: Bearer <your-admin-api-key>"
```

- The system will auto-discover available models for all configured providers and update the registry database.

### **B. Using an Admin Script (Advanced)**

- Run the provided admin script (if available):

```bash
python router/refresh_models.py
```

- This script will fetch models from all supported providers and update the registry.

---

## 2. Refreshing the Registry After Hardware or Model Changes

- **Whenever you change hardware (e.g., add a GPU) or update provider credentials,** you should refresh the registry to ensure all available models are detected.
- Use the same API call as above:

```bash
curl -X POST http://localhost:8000/v1/registry/refresh \
  -H "Authorization: Bearer <your-admin-api-key>"
```

---

## 3. Verifying Registry Updates

- To list all available models and verify your changes, use:

```bash
curl -X GET http://localhost:8000/v1/models \
  -H "Authorization: Bearer <your-api-key>"
```

- The response will include all models currently registered and available for inference.

- You can also check the last refresh time and hardware info:

```bash
curl -X GET http://localhost:8000/v1/registry/status
```

---

**Note:** If you need to add support for a new provider, ensure the relevant API keys and configuration are set in your environment or configuration files before running a refresh.
