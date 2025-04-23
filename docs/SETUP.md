# Setup Guide: IIR MVP Phase 1a

## Prerequisites
- Debian 12
- NVIDIA RTX 4090 with drivers (≥535)
- NVIDIA Container Toolkit
- Docker & Docker Compose
- Git

## Steps
1. Clone the repo
2. `cd intelligent_inference_router`
3. Copy `.env.example` to `.env` and set `ROUTER_API_KEY`
4. `docker compose build`
5. `docker compose up -d`
6. Check `docker compose ps` for service status
7. Access API at `http://localhost:8000/health`
8. View logs with `docker compose logs -f router`

See `docs/TROUBLESHOOTING.md` for common issues.
