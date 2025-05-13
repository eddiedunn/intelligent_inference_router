# Active Context: IIR MVP Phase 1a

---

> **For current debugging and monitoring practices, see:**
> - `docs/TROUBLESHOOTING.md`
> - `docs/MONITORING.md`

## Current Focus
- Integrated real external LLM API calls into `/v1/chat/completions` endpoint (OpenAI, Anthropic, etc.)
- Debugged and resolved 400 and 502 errors in provider routing
- Fixed provider client registry bug (select_provider returned config dict, not client instance)
- Ensured robust error handling and proper test coverage for 400/502 scenarios
- Docker container rebuild and test cycle validated
- Decoupling ml_ops: all references, submodules, and dependencies removed from IIR project (2025-04-24)

## Recent Changes
- Updated event loop handling in test fixtures and minimal Redis tests to use asyncio.run() for Python 3.11+ compatibility
- Added debug output to FastAPILimiter fixture for connection diagnosis
- Confirmed minimal Redis ping tests pass; FastAPILimiter tests still skipped due to connection/init issues
- Updated README and project documentation to reflect ml_ops decoupling

## Onboarding & CI/CD (2025-05-05)
- Project updated for Gaia Infra Platform onboarding (see ONBOARDING.md in gaia-infra-platform)
- Directory structure matches canonical Gaia app stack pattern (monitoring/, db-provisioning/, n8n/, .env.example, docker-compose.yml, .gitlab-ci.yml)
- Monitoring: prometheus.yml and Grafana dashboards present in monitoring/
- .env.example uses only placeholders (no secrets committed)
- .env is gitignored
- CI/CD: Now uses GitLab CE exclusively; all automation in .gitlab-ci.yml
- Pipelines: lint, test, build, push, deploy (manual for dev/prod)
- Registry: Images pushed to GitLab Container Registry
- README.md and memory-bank updated to reflect all onboarding and CI/CD requirements
- Ready for import via Gaia onboarding scripts and integration into any Gaia-managed environment

## Next Steps
- Run pytest with -s to capture all debug output from test suite
- Analyze FastAPILimiter fixture output/logs to pinpoint cause of skipped tests
- Finalize and document solution for robust Redis + FastAPILimiter test integration
- Continue monitoring for any further Redis or rate limiting issues
- Monitor for any onboarding script or pipeline errors in GitLab
- Keep README and memory-bank in sync with any further onboarding or CI/CD changes
- Periodically review Gaia ONBOARDING.md for updates to process or requirements

## Active Decisions
- Continue strict documentation-first, memory-driven workflow
- Project is now fully self-contained; ml_ops is archived/external only

## Considerations
- All context and major changes must be reflected in memory-bank for future resets
- Maintain clarity and precision in all updates, especially regarding test infra and decoupling
