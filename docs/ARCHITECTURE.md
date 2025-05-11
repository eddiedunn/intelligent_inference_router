# Architecture: IIR MVP Phase 1a

> **Documentation Map:**
> - **Setup Guide:** See `SETUP.md`
> - **Developer Onboarding:** See `DEVELOPER_ONBOARDING.md`
> - **API Reference:** See `API.md`
> - **Troubleshooting:** See `TROUBLESHOOTING.md`
> - **System Patterns:** See `memory-bank/systemPatterns.md` for deep dives on architecture/design patterns.

## Overview
- FastAPI router service (auth, rate limiting, cache, classifier, routing)
- Local vLLM backend (Llama-3-8B-Instruct)
- Redis (cache)
- Prometheus (metrics)
- Grafana (dashboard)

## Request Lifecycle
```mermaid
sequenceDiagram
    participant Client
    participant Router API (FastAPI)
    participant Auth/RateLimit
    participant Cache (Redis)
    participant Classifier (MNLI)
    participant Local Provider (vLLM)

    Client->>+Router API: POST /v1/chat/completions (Req, Auth Header)
    Router API->>+Auth/RateLimit: Verify Key & Limit
    alt Invalid Key or Limit Exceeded
        Auth/RateLimit-->>-Router API: Failure (401/403/429)
        Router API-->>-Client: Error Response
    else Valid Request
        Auth/RateLimit-->>-Router API: OK
        Router API->>+Cache: Check Cache(key based on prompt/model)
        alt Cache Hit
            Cache-->>-Router API: Cached Response Data
            Router API-->>-Client: Cached Response
        else Cache Miss
            Cache-->>-Router API: Not Found
            Router API->>+Classifier: Classify(prompt)
            alt Classifier Fails
                 Classifier-->>-Router API: Failure Indication
                 Router API-->>-Client: Error Response (503)
            else Classifier OK
                Classifier-->>-Router API: Decision ("local" / "remote")
                alt Decision == "local" AND Model == LocalModelID
                    Router API->>+Local Provider: generate_local(payload)
                    alt vLLM Fails
                        Local Provider-->>-Router API: Error Indication
                        Router API-->>-Client: Error Response (502)
                    else vLLM OK
                        Local Provider-->>-Router API: Response Data
                        Router API->>+Cache: Set Cache(key, Response Data)
                        Cache-->>-Router API: OK
                        Router API-->>-Client: Final Response
                    end
                else Decision == "remote" OR Model != LocalModelID
                    Router API-->>-Client: Error Response (501 Not Implemented)
                end
            end
        end
    end
```

See `memory-bank/systemPatterns.md` for more on design patterns and technical decisions, including:
- Async cache initialization and dependency injection (ProviderRouter DI)
- Provider interface abstraction
- Middleware for authentication, rate limiting, and logging
- Error handling and standardized JSON responses
- Metrics instrumentation

For the most up-to-date and detailed architectural decisions, always check `memory-bank/systemPatterns.md`.
