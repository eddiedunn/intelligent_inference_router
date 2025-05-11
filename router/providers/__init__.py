
def parse_provider_and_model(model_id: str):
    """
    Splits a model_id into provider and model name.
    Example: 'openai/gpt-4' -> ('openai', 'gpt-4')
    """
    if '/' not in model_id:
        raise ValueError("Model name must be in the format <provider>/<model_name>")
    provider, model_name = model_id.split('/', 1)
    return provider, model_name
