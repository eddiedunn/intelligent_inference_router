# API Examples

Example request for a dummy completion:
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
     -H 'Content-Type: application/json' \
     -d '{"model":"dummy","messages":[{"role":"user","content":"hi"}]}'
```

Example request to the local agent:
```bash
curl -X POST http://localhost:8000/v1/chat/completions \
     -H 'Content-Type: application/json' \
     -d '{"model":"local_mistral","messages":[{"role":"user","content":"hi"}]}'
```
