# Monitoring: IIR MVP Phase 1a

## Prometheus
- Router exposes metrics at `/metrics`
- Prometheus scrapes `router:8000`
- See `docker/prometheus.yml` for config

## Grafana
- Access at `http://localhost:3000` (admin/admin)
- Add Prometheus data source: `http://prometheus:9090`
- Create dashboards for: Requests/sec, P95 latency, Error rate, Cache hit ratio
- Example dashboard JSON: `docs/grafana_dashboard.json`

## Logging
- JSON logs to stdout (docker logs)
- Default: metadata only; enable full content with `ROUTER_LOG_FULL_CONTENT=true`
