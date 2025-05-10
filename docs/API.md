# API Reference: IIR MVP Phase 1a

## Authentication
- All endpoints except `/health` and `/metrics` require: `Authorization: Bearer <API_KEY>`

## API Key Generation

To generate a secure API key for use with the Intelligent Inference Router, use the provided script:

```sh
npm run generate-api-key
# or directly:
python generate_api_key.py --length 40 --prefix myservice
```

Copy the generated key into your `.env` file as `IIR_API_KEY` (or add to `IIR_ALLOWED_KEYS` for multiple keys).

## Endpoints

| Method | Path                                         | Description                                                   | Auth Required |
|--------|----------------------------------------------|---------------------------------------------------------------|---------------|
| GET    | `/health`                                   | Health check                                                  | No            |
| GET    | `/v1/models`                                | List available models (OpenAI format)                         | Yes           |
| POST   | `/v1/chat/completions`                      | Generate chat completion (OpenAI-compatible)                  | Yes           |
| POST   | `/v1/async/chat/completions`                | Submit async chat completion job                              | Yes           |
| GET    | `/v1/async/chat/completions/{job_id}`       | Poll async chat completion job status/result                  | Yes           |
| POST   | `/infer`                                    | Direct model inference with secret scrubbing                  | Yes           |
| GET    | `/v1/registry/status`                       | Get model registry status/hardware info                       | Yes           |
| POST   | `/v1/registry/refresh`                      | Refresh/rebuild model registry                                | Yes           |
| GET    | `/metrics`                                  | Prometheus metrics                                            | No            |
| GET    | `/version`                                  | Returns version info                                          | No            |

---

### Endpoint Details

#### `GET /health`
- Returns `{ "status": "ok" }` if the service is up.

#### `GET /v1/models`
- Lists available models in OpenAI-compatible format.
- Example response:
```json
{
  "object": "list",
  "data": [
    { "id": "openai/gpt-4o", "object": "model", "owned_by": "openai", "permission": [] },
    { "id": "anthropic/claude-3-sonnet", ... }
  ]
}
```

#### `POST /v1/chat/completions`
- OpenAI-compatible chat completion endpoint.
- See example request/response below.

#### `POST /v1/async/chat/completions`
- Submit a chat completion job for asynchronous processing.
- Request body: same as `/v1/chat/completions`.
- Response:
```json
{ "job_id": "...", "status": "pending" }
```

#### `GET /v1/async/chat/completions/{job_id}`
- Poll for the result of an async chat completion job.
- Response:
  - If pending: `{ "job_id": "...", "status": "pending" }`
  - If complete: OpenAI-compatible chat completion result.

#### `POST /infer`
- Direct inference endpoint for calling a specific model.
- Request body:
```json
{
  "model": "openai/gpt-4o", // provider/model
  "input": { ... },
  "async_": false // optional
}
```
- Response: Model-specific output. All secrets are scrubbed from input/output.

#### `GET /v1/registry/status`
- Returns the current status of the model registry (e.g., discovered models, hardware info).

#### `POST /v1/registry/refresh`
- Triggers a refresh/rebuild of the model registry. Returns status and registry info.

#### `GET /metrics`
- Prometheus metrics endpoint for monitoring.

#### `GET /version`
- Returns the current application version, e.g. `{ "version": "0.1.0" }`.

---

## OpenAPI Documentation
- The FastAPI app provides interactive OpenAPI docs at `/docs` and the raw schema at `/openapi.json`.
- All endpoints use JSON request/response bodies, with OpenAI-compatible schemas for `/v1/models` and `/v1/chat/completions`.

---

## Secret Scrubbing
All incoming requests and outgoing responses for `/infer`, `/v1/chat/completions`, and async endpoints are automatically scrubbed for secrets (API keys, tokens, passwords, etc). This is done using a hybrid utility that detects and redacts secrets from both environment variables and payloads.

- **What is scrubbed?**
  - Any value matching known secret patterns or environment secrets is replaced with `REDACTED`.
- **Why?**
  - To prevent accidental leakage of sensitive information in logs, errors, or responses.
- **How?**
  - The utility scans payloads recursively and replaces detected secrets before further processing or returning data to the client.

---

## Supported Providers & Model Naming
- Supported providers include: OpenAI, Anthropic, Grok, OpenRouter, OpenLLaMA (see README for details).
- Model names must be provided as `<provider>/<model>`, e.g. `openai/gpt-4o`, `anthropic/claude-3-sonnet`.
- Use `/v1/models` to discover the full list of available models.

---

## Example Request/Response
### POST /v1/chat/completions
Request:
```json
{
  "model": "meta-llama/Meta-Llama-3-8B-Instruct",
  "messages": [
    {"role": "user", "content": "Hello!"}
  ]
}
```
Response (success):
```json
{
  "id": "...",
  "object": "chat.completion",
  "created": 1710000000,
  "model": "meta-llama/Meta-Llama-3-8B-Instruct",
  "choices": [
    {"index": 0, "message": {"role": "assistant", "content": "Hi!"}, "finish_reason": "stop"}
  ],
  "usage": {"prompt_tokens": 3, "completion_tokens": 2, "total_tokens": 5}
}
```
Response (error):
```json
{"detail": "Classifier error: ..."}
```

## Error Codes
- 400: Bad request
- 401: Unauthorized
- 403: Forbidden
- 404: Model not found
- 413: Payload too large
- 429: Rate limit exceeded
- 500: Internal error
- 501: Not implemented (remote path)
- 502: vLLM backend error
- 503: Classifier error

## Error Response Schema
- All errors return a JSON body with at least a `detail` field describing the error.
- Example:
```json
{"detail": "Request exceeds max token limit"}
```
- For future: consider `{ "error": { "code": "ERROR_CODE", "message": "..." } }` for more structured errors.

## Rate Limiting
- Exceeding per-IP limit returns 429 with body `{ "detail": "Rate limit exceeded" }`

## Common Pitfalls & Troubleshooting

- **401 Unauthorized / 403 Forbidden:**
  - Did you set `IIR_API_KEY` in your `.env` and client config?
  - Are you passing the correct `Authorization: Bearer <API_KEY>` header?
- **429 Too Many Requests:**
  - Rate limit exceeded. Wait and retry, or check your per-IP rate limit settings.
- **Connection Refused / Port in Use:**
  - Is another stack running on the same ports? Use Docker Compose override files and unique project names.
- **Redis Not Connecting:**
  - Double-check your `REDIS_URL` and that the right Redis container is running.
- **Log Forwarding Not Working:**
  - Is `REMOTE_LOG_SINK` set in your `.env`? Is your UDP listener running and accessible?

See `docs/TROUBLESHOOTING.md` for more.

## Remote Log Debugging

To forward all logs to a remote UDP listener for debugging:

1. Set `REMOTE_LOG_SINK` in your `.env`:
   ```
   REMOTE_LOG_SINK=1.2.3.4:9999
   ```
2. Start your log listener on the remote host:
   ```python
   import socket
   sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
   sock.bind(("0.0.0.0", 9999))
   while True:
       data, addr = sock.recvfrom(4096)
       print(data.decode(), end="")
   ```
3. Run `make deploy-test` or `make logs` in your project. Logs will be streamed to the remote listener.

**Note:** The sender (log forwarder) is implemented in `forward_logs_udp.py` and does not require any third-party packages—just Python 3.6+ standard library. The listener is also pure Python and can be run as shown above.

**Security Note:** Only use this for debugging in trusted environments, as logs may contain sensitive information.

## Metrics
- Prometheus metrics available at `/metrics` (see Monitoring doc)

See OpenAPI spec at `/docs` when running.
