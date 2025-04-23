# System Patterns: IIR MVP Phase 1a

## Architecture
- Containerized microservice design (Docker Compose)
- FastAPI for API ingress, modular Python package layout
- Redis for caching, Prometheus for metrics, Grafana for visualization
- Pydantic for configuration management

## Key Technical Decisions
- Prompt classification determines routing path (local vs remote)
- Local path fully implemented, remote path stubbed for MVP
- All configuration externalized via YAML + env vars
- API key auth and rate limiting at ingress
- Structured JSON logging (metadata by default)

## Design Patterns
- Dependency injection for config, cache, and classifier
- Provider interface for model backends (local/external)
- Middleware for auth, rate limiting, logging
- Error handling via standardized JSON responses

## Component Relationships
- Router orchestrates all flows: auth → cache → classifier → provider
- Metrics instrumented at each major step
- Stateless router; state managed in Redis
