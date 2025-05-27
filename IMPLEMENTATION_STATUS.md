# Implementation Status Checklist

This document tracks which features from `docs/FEATURES.md` are actually implemented in the repository. Items are checked once their functionality exists in the codebase.

## Router
- [x] Build OpenAI-compatible API
- [x] Connect Router to Local Agent
- [x] Proxy External API Calls
- [ ] Enable Redis Caching
- [x] Implement SQLite Model Registry
- [ ] Forward to llm-d Cluster
- [ ] Add Request Logging and Metrics

## Local Agent
- [x] Provide Local LLM Service
- [ ] Register Agent with Router
- [ ] Send Periodic Heartbeats

## GPU Worker Cluster
- [ ] Deploy llm-d via Helm
- [ ] Expose Cluster Endpoint to Router

## Shared / Infra
- [ ] Docker Compose for Dev Stack
- [ ] Continuous Integration Workflow
- [ ] Documentation Site with MkDocs
