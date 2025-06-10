# Router Environment Variables

The router service reads its configuration from environment variables. The
`router.config.Settings` class centralises these options. All variables are
optional unless noted.

| Variable | Default | Description |
|----------|---------|-------------|
| `SQLITE_DB_PATH` | `data/models.db` | Path to the model registry database. |
| `LOCAL_AGENT_URL` | `http://localhost:5000` | Base URL for the local agent. |
| `OPENAI_BASE_URL` | `https://api.openai.com` | OpenAI API endpoint. |
| `EXTERNAL_OPENAI_KEY` | unset | API key for OpenAI. |
| `LLMD_ENDPOINT` | unset | Base URL for a llm-d cluster. |
| `ANTHROPIC_BASE_URL` | `https://api.anthropic.com` | Anthropic API endpoint. |
| `EXTERNAL_ANTHROPIC_KEY` | unset | API key for Anthropic. |
| `GOOGLE_BASE_URL` | `https://generativelanguage.googleapis.com` | Google Gemini API base URL. |
| `EXTERNAL_GOOGLE_KEY` | unset | API key for Google. |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai` | OpenRouter API endpoint. |
| `EXTERNAL_OPENROUTER_KEY` | unset | API key for OpenRouter. |
| `GROK_BASE_URL` | `https://api.groq.com` | Grok API endpoint. |
| `EXTERNAL_GROK_KEY` | unset | API key for Grok. |
| `VENICE_BASE_URL` | `https://api.venice.ai` | Venice API endpoint. |
| `EXTERNAL_VENICE_KEY` | unset | API key for Venice. |
| `HF_CACHE_DIR` | `data/hf_models` | Directory for Hugging Face model cache. |
| `HF_DEVICE` | `cpu` | Device for Hugging Face pipelines. |
| `HUGGING_FACE_HUB_TOKEN` | unset | Token for private Hugging Face repos. |
| `LOG_LEVEL` | `INFO` | Logging level for the router. |
| `LOG_PATH` | `logs/router.log` | Log file path. |
| `CACHE_TTL` | `300` | In-memory cache time‑to‑live (seconds). |
| `RATE_LIMIT_REQUESTS` | `60` | Allowed requests per window. |
| `RATE_LIMIT_WINDOW` | `60` | Window size in seconds for rate limiting. |
| `ROUTER_COST_WEIGHT` | `1.0` | Smart routing cost weight. |
| `ROUTER_LATENCY_WEIGHT` | `1.0` | Smart routing latency weight. |
| `ROUTER_COST_THRESHOLD` | `1000` | Token threshold before routing locally. |
