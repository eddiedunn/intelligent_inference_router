# System Patterns: IIR MVP Phase 1a

> For a high-level system diagram and request lifecycle, see `docs/ARCHITECTURE.md`.

## Architecture
- Containerized microservice design (Docker Compose)
- FastAPI for API ingress, modular Python package layout
- Redis for caching, Prometheus for metrics, Grafana for visualization
- Pydantic for configuration management

## Key Technical Decisions
- Prompt classification determines routing path (local only)
- Local path fully implemented; remote path is not supported in this deployment
- All configuration externalized via YAML + env vars
- API key auth and rate limiting at ingress
- Structured JSON logging (metadata by default)

## Design Patterns
- Dependency injection for config, cache, and classifier
- Provider interface for model backends (local/external)
- Provider client registry pattern: `PROVIDER_CLIENTS` holds singleton client instances, and all routing uses these for API calls. `select_provider` must return the client instance, not the config dict.
- Middleware for auth, rate limiting, logging
- Error handling via standardized JSON responses

## Component Relationships
- Router orchestrates all flows: auth → cache → classifier → provider
- Metrics instrumented at each major step
- Stateless router; state managed in Redis
