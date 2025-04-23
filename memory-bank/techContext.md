# Tech Context: IIR MVP Phase 1a

## Technologies Used
- **Language:** Python 3.9+
- **API Framework:** FastAPI
- **Model Serving:** vLLM (Llama-3-8B-Instruct)
- **ML Libraries:** transformers, torch, accelerate, bitsandbytes (optional)
- **Caching:** Redis 7+ (redis-py[hiredis])
- **Monitoring:** prometheus_client, Prometheus, Grafana
- **Deployment:** Docker, Docker Compose
- **Config:** PyYAML, python-dotenv, pydantic-settings
- **Rate Limiting:** fastapi-limiter
- **Testing:** pytest, httpx

## Development Setup
- Target OS: Debian 12
- Target hardware: NVIDIA RTX 4090, >=16-core CPU, >=64GB RAM
- NVIDIA drivers and container toolkit required
- All services run via Docker Compose

## Technical Constraints
- Classifier and router must fit in system RAM/VRAM with vLLM
- All config must be externalized (no hardcoded secrets)
- OpenAI-compatible API contract

## Dependencies
- All Python and system dependencies listed in requirements.txt and docs/SETUP.md
