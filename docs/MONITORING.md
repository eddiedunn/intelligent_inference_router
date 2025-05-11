# Monitoring: IIR MVP Phase 1a

> **Documentation Map:**
> - **Setup Guide:** See `SETUP.md`
> - **Developer Onboarding:** See `DEVELOPER_ONBOARDING.md`
> - **API Reference:** See `API.md`
> - **Troubleshooting:** See `TROUBLESHOOTING.md` for debugging steps and common issues.
> - **Configuration:** See `CONFIGURATION.md` for environment variables and config options.

## Prometheus
- Router exposes metrics at `/metrics`
- Prometheus scrapes `router:8000`
- See `docker/prometheus.yml` for config
- Monitor key metrics: request rate, latency, error rate, cache hit ratio, and rate limiting events
- Monitor Redis health and FastAPI-Limiter status for rate limiting issues

## Grafana
- Access at `http://localhost:3000` (admin/admin)
- Add Prometheus data source: `http://prometheus:9090`
- Create dashboards for: Requests/sec, P95 latency, Error rate, Cache hit ratio
- Example dashboard JSON: `docs/grafana_dashboard.json`

## Logging
- JSON logs to stdout (docker logs)
- Default: metadata only; enable full content with `ROUTER_LOG_FULL_CONTENT=true`
