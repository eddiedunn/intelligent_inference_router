# Setup Guide: IIR MVP Phase 1a

> **Documentation Map:**
> - **Setup Guide (this doc):** Install & run IIR for all users.
> - **Developer Onboarding:** Dev setup, contribution, API key system (see `DEVELOPER_ONBOARDING.md`).
> - **API Reference:** See `API.md` for all endpoints.
> - **Troubleshooting:** See `TROUBLESHOOTING.md` for common errors.
> - **Architecture:** See `ARCHITECTURE.md` for system overview.

> **Are you a developer or contributor?** See `DEVELOPER_ONBOARDING.md` for dev-specific setup, contribution, and API key management.

## Prerequisites
- Debian 12 (or compatible Linux)
- NVIDIA RTX 4090 with drivers (≥535) for GPU inference
- NVIDIA Container Toolkit
- Docker & Docker Compose
- Git
- Python 3.7+ for utility scripts

---

## Step-by-Step Setup

1. **Clone the repository**
   ```sh
   git clone https://github.com/eddiedunn/intelligent_inference_router.git
   cd intelligent_inference_router
   ```

2. **Copy and configure your environment**
   ```sh
   cp .env.example .env
   ```

3. **Generate a secure API key for both server and client**
   ```sh
   python generate_api_key.py --set-server-env --set-client-env
   # Optionally, add --prefix myproject or --client-path path/to/client.env
   ```

## Hugging Face Token for Gated Models

Some models (such as Meta Llama 3) are gated on Hugging Face and require authentication to download.

If you see errors like `401 Unauthorized` or `Cannot access gated repo` in your logs, you must:

1. **Request access** to the model at: https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct
2. **Get your Hugging Face access token**: https://huggingface.co/settings/tokens
3. **Add your token to the `.env` file**:
   ```sh
   HF_TOKEN=your_huggingface_token_here
   ```
4. **Restart the stack**:
   ```sh
   make deploy-test
   # or
   docker compose up -d
   ```

If you do not add this token, the vLLM container will fail to start and you will see repeated authentication errors in the logs.

---

5. **Build and start the stack**
   ```sh
   docker compose build
   docker compose up -d
   ```

6. **Check service status and logs**
   ```sh
   docker compose ps
   docker compose logs -f router
   ```

7. **Test the API**
   - Health check: [http://localhost:8000/health](http://localhost:8000/health)
   - OpenAPI docs: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## Model Registry & Hardware-Aware Discovery

- The registry supports local and hosted models from multiple providers (OpenAI, Hugging Face, OpenRouter, Google Gemini/PaLM, etc.).
- To refresh the registry and run hardware-aware model discovery, call the API endpoint:

  ```bash
  curl -X POST http://localhost:8000/v1/registry/refresh
  ```
  or use the CLI:
  ```bash
  python router/refresh_models.py
  ```
- The registry and recommendations are persisted in `~/.agent_coder/`.
- To check the last refresh time and hardware info, call:
  ```bash
  curl http://localhost:8000/v1/registry/status
  ```
- Set `OPENAI_API_KEY` in your environment for model recommendations.
- Requirements: `sqlite3`, `requests`, `torch`, `openai`

---

## Redis Configuration for Local Development & Testing

- **Set `REDIS_URL=redis://localhost:6379/0` in your `.env` file** for all local development and testing.
- The application uses a lazy environment variable lookup for `REDIS_URL`, ensuring the correct Redis host is always used—even if the environment changes after import.
- This pattern prevents test failures due to import order or environment variable timing issues.
- For Docker Compose or production, set `REDIS_URL` as appropriate for your environment.

---

## Running Multiple Stacks (Dev/Test)

To run a second stack on the same host (e.g., for parallel dev/testing):

1. Copy and edit the override file:
   ```sh
   cp docker-compose.override-sample.yml docker-compose.override-stack2.yml
   # Edit ports as needed in the new file
   ```

2. Start with a unique project name:
   ```sh
   COMPOSE_PROJECT_NAME=stack2 docker compose -f docker-compose.yml -f docker-compose.override-stack2.yml up -d
   ```

---

## Troubleshooting

- See `docs/TROUBLESHOOTING.md` for common issues.
- For authentication errors, double-check your API key in `.env` and client config.
- For port conflicts, use the override file and unique `COMPOSE_PROJECT_NAME`.

---

**For more details, see:**
- [docs/API.md](docs/API.md) for endpoint and usage details
- [docs/CONFIGURATION.md](docs/CONFIGURATION.md) for environment/config options
- [docs/MONITORING.md](docs/MONITORING.md) for metrics setup
