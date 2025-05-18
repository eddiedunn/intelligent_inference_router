from fastapi.responses import JSONResponse

MULTI_SLASH_PROVIDERS = {"openrouter", "groq", "openai-router", "anthropic-router"}


def validate_model_and_messages(payload, list_models_func=None, require_messages=True, token_limit=1000):
    print("[DEBUG][TEST] Payload to validate:", payload)
    if list_models_func:
        models = list_models_func()['data']
        print("[DEBUG][TEST] Models from list_models_func:", [m['id'] for m in models])
    else:
        print("[DEBUG][TEST] No list_models_func provided")
    import logging
    logger = logging.getLogger("iir.validation")
    logger.debug(f"validate_model_and_messages ENTRY: payload={payload}")
    # 1. If payload is not a dict (even if valid JSON), return 'Invalid JSON payload'
    if payload is None or not isinstance(payload, dict):
        logger.debug(f"Validation error: payload not a dict (payload={payload})")
        return JSONResponse({"error": {"type": "validation_error", "code": "invalid_payload", "message": "Invalid JSON payload"}}, status_code=400)

    # 2. Model field must exist and be a string
    model = payload.get("model", None)
    logger.debug(f"Model field: model={model}")
    # Model name must be in <provider>/<model> format (multi-slash allowed after first)
    if not isinstance(model, str) or '/' not in model:
        logger.debug(f"Validation error: invalid_model_format for model {model}")
        return JSONResponse({"error": {"type": "validation_error", "code": "invalid_model_format", "message": "Model name must be in <provider>/<model> format."}}, status_code=400)

    # 3. Model must split into two non-empty parts (first part is provider, rest is model name)
    provider, model_name = model.split("/", 1)
    logger.debug(f"Model split: provider={provider}, model_name={model_name}")
    if not provider.strip() or not model_name.strip():
        logger.debug(f"Validation error: unknown_provider for badly formatted model (model={model}, provider={provider}, model_name={model_name})")
        return JSONResponse({"error": {"type": "validation_error", "code": "unknown_provider", "message": "Unknown remote provider for model"}}, status_code=400)

    # 4. Messages validation & token limit (must be before unknown provider check)
    messages = payload.get("messages", None)
    logger.debug(f"Messages field: messages={messages}")
    if require_messages:
        if messages is None or not isinstance(messages, list):
            logger.debug(f"Validation error: missing or invalid messages field (messages={messages})")
            return JSONResponse({"error": {"type": "validation_error", "code": "invalid_payload", "message": "Missing or invalid messages field"}}, status_code=400)
        # Token limit check is always before registry lookup
        def is_token_limit_exceeded(messages, token_limit):
            total_length = sum(len(m.get('content', '')) for m in messages if isinstance(m, dict))
            return total_length > token_limit
        if is_token_limit_exceeded(messages, token_limit):
            logger.debug(f"Validation error: token_limit_exceeded (token_limit={token_limit})")
            return JSONResponse({"error": {"type": "validation_error", "code": "token_limit_exceeded", "message": "Token limit exceeded"}}, status_code=413)

    # 5. Only after all other validation, check registry for unknown provider
    if list_models_func is not None:
        try:
            models = list_models_func().get('data', [])

            logger.debug(f"Registry models: {models}")
        except Exception as e:
            logger.error(f"Model registry lookup failed: {e}")
            return JSONResponse({"error": {"type": "service_unavailable", "code": "model_registry_unavailable", "message": "Model registry unavailable: " + str(e)}}, status_code=503)
        # Robust model matching: normalize both sides (strip, lower)
        def normalize(s):
            return s.strip().lower() if isinstance(s, str) else s
        model_norm = normalize(model)
        # Accept registry models that match full model string, or match after the first slash
        def registry_match(m):
            mid = normalize(m['id'])
            if mid == model_norm:
                logger.debug(f"registry_match: direct match (mid={mid}, model_norm={model_norm})")
                return True
            if '/' not in mid and model_name and normalize(model_name) == mid:
                logger.debug(f"registry_match: model_name match (mid={mid}, model_name={model_name})")
        print("[DEBUG][TEST] Looking for model:", model)
        print("[DEBUG][TEST] All model IDs:", [m['id'] for m in models])
        print("[DEBUG][TEST] model_norm:", model_norm)
        for m in models:
            print("[DEBUG][TEST] registry_id:", m['id'], "normalized:", normalize(m['id']))
        registry_match = lambda m: m["id"] == model or normalize(m["id"]) == model_norm
        model_entry = next((m for m in models if registry_match(m) or normalize(m.get('endpoint_url')) == model_norm), None)
        logger.debug(f"Model registry lookup: model_entry={model_entry}")
        if not model_entry:
            logger.debug(f"Validation error: unknown_provider for model {model}")
            return JSONResponse({"error": {"type": "validation_error", "code": "unknown_provider", "message": "Unknown remote provider for model"}}, status_code=400)
    logger.debug("Validation passed: no error")
    return None  # No error

    # Messages validation
    messages = payload.get("messages", None)
    if require_messages:
        if messages is None or not isinstance(messages, list):
            return JSONResponse({"error": {"type": "validation_error", "code": "invalid_payload", "message": "Missing or invalid messages field"}}, status_code=400)
        if len(messages) > token_limit:
            return JSONResponse({"error": {"type": "validation_error", "code": "token_limit_exceeded", "message": "Token limit exceeded"}}, status_code=413)
    return None  # No error
