# Configuration Reference: IIR MVP Phase 1a

## .env Variables
- `IIR_API_KEY`: Required API key for authentication
- `REDIS_URL`: Redis connection string
- `LOG_LEVEL`: Logging level
- `ROUTER_LOG_FULL_CONTENT`: Enable full prompt/response logging
- (Phase 1b+) External provider keys

## config.defaults.yaml
- `classifier_model_id`, `classifier_device`
- `local_model_id`, `vllm_base_url`
- `cache_ttl_seconds`
- `rate_limit_rpm`, `max_request_tokens`
- (Future) provider_priority, external_providers

See file comments for details.
