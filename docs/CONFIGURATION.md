# Configuration Reference: IIR MVP Phase 1a

> For setup and .env creation, see `SETUP.md`. For common issues, see `TROUBLESHOOTING.md`.

## .env Variables
- `IIR_API_KEY`: Required API key for authentication
- `REDIS_URL`: Redis connection string (must include password if Redis requires auth, e.g., `redis://:password@host:6379/0`)
- `LOG_LEVEL`: Logging level (e.g., `INFO`, `DEBUG`)
- `ROUTER_LOG_FULL_CONTENT`: Enable full prompt/response logging (set to `1` to enable)
- `HF_TOKEN`: Hugging Face access token for gated models
- `REMOTE_LOG_SINK`: (Optional) UDP address for log forwarding
- `FASTAPI_LIMITER_ENABLED`: Enable rate limiting (set to `1` to enable)
- (Phase 1b+) External provider keys, e.g., `OPENAI_API_KEY`, etc.

## config.defaults.yaml
- `classifier_model_id`, `classifier_device`: Prompt classifier config
- `local_model_id`, `vllm_base_url`: Local model and vLLM backend config
- `cache_ttl_seconds`: Cache time-to-live (in seconds)
- `rate_limit_rpm`, `max_request_tokens`: Rate limiting and payload size controls
- (Future) `provider_priority`, `external_providers`: Provider routing config

See file comments for details. All config options are loaded at startup.

### Troubleshooting Configuration
- **Redis Authentication Error:** Ensure your `REDIS_URL` includes the password if required by your Redis instance.
- **Missing API Key:** Make sure `IIR_API_KEY` is set in both `.env` and your client config.
- **Rate Limiting Not Working:** Check `FASTAPI_LIMITER_ENABLED` and ensure Redis is running and accessible.
- **Hugging Face Model Download Issues:** Make sure `HF_TOKEN` is set and valid for gated models.

For more, see `TROUBLESHOOTING.md`.
