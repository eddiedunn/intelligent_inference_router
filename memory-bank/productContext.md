# Product Context: Intelligent Inference Router (IIR)

## Why This Project Exists
Modern AI workflows require cost-effective, high-performance, and flexible access to LLMs. Current solutions are either expensive (external APIs) or complex to self-host. The IIR bridges this gap by enabling intelligent, policy-driven routing between local LLM backends, optimizing for cost, latency, and reliability.

## Problems Solved
- Reduces LLM inference costs by leveraging local hardware when possible
- Optimizes latency and throughput for high-volume inference
- Provides a unified API for multiple local LLM backends
- Enables caching, monitoring, and operational observability out-of-the-box

## How It Should Work
- User sends a request to a single endpoint
- Router authenticates, rate-limits, checks cache
- Classifies prompt as "local"
- Routes to local vLLM
- Returns response, caching when appropriate
- Exposes metrics for monitoring

## User Experience Goals
- Easy setup (Docker Compose, clear docs)
- OpenAI-compatible API for drop-in usage
- Transparent routing and logging
- Secure by default, with opt-in full-content logging
- Clear error handling and feedback
