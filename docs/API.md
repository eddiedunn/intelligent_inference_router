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

Copy the generated key into your `.env` file as `ROUTER_API_KEY` (or add to `ROUTER_ALLOWED_API_KEYS` for multiple keys).

## Endpoints
- `GET /health`: Health check
- `GET /v1/models`: List available models
- `POST /v1/chat/completions`: Generate chat completion (OpenAI-compatible)

## OpenAPI Documentation
- The FastAPI app provides interactive OpenAPI docs at `/docs` and the raw schema at `/openapi.json`.
- All endpoints use JSON request/response bodies, with OpenAI-compatible schemas for `/v1/models` and `/v1/chat/completions`.

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
