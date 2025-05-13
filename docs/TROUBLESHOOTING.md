# Troubleshooting: IIR MVP Phase 1a

> **Documentation Map:**
> - **Setup Guide:** See `SETUP.md`
> - **Developer Onboarding:** See `DEVELOPER_ONBOARDING.md`
> - **API Reference:** See `API.md`
> - **Configuration:** See `CONFIGURATION.md` for environment variables and config troubleshooting
> - **Monitoring:** See `MONITORING.md` for metrics and dashboard setup

## Common Issues
- **Docker fails to build:** Check NVIDIA drivers, toolkit, and Docker versions
- **vLLM not starting:** Check model ID, GPU availability, and logs
- **502: 'dict' object has no attribute 'chat_completions':** This means the provider router returned a config dict, not a client instance. Fix: ensure `select_provider` returns the client instance from `PROVIDER_CLIENTS`.
- **Redis connection errors:** Verify Redis service is running and `REDIS_URL` is correct
- **API returns 401/403:** Confirm API key in `.env` and request headers
- **Rate limiting (429):** Increase `rate_limit_rpm` in config if needed
- **Classifier errors (503):** Check RAM/VRAM, model download, and logs

## Debugging Steps
- View logs: `docker compose logs -f router`
- Health check: `curl http://localhost:8000/health`
- Check metrics: Prometheus at `http://localhost:9090`
- Dashboard: Grafana at `http://localhost:3000`
