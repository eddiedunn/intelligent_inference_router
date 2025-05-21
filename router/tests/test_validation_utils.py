import pytest
from router.validation_utils import (
    validate_required_fields,
    validate_model_format,
    validate_messages,
    validate_token_limit,
    validate_model_registry,
    InvalidPayloadError,
    InvalidModelFormatError,
    UnknownProviderError,
    InvalidMessagesError,
    TokenLimitExceededError,
    RegistryUnavailableError,
)

def test_validate_required_fields_valid():
    payload = {"model": "openai/gpt-3.5-turbo", "messages": [{"role": "user", "content": "hi"}]}
    validate_required_fields(payload)  # Should not raise

def test_validate_required_fields_missing_model():
    payload = {"messages": [{"role": "user", "content": "hi"}]}
    with pytest.raises(InvalidPayloadError):
        validate_required_fields(payload)

def test_validate_required_fields_missing_messages():
    payload = {"model": "openai/gpt-3.5-turbo"}
    with pytest.raises(InvalidPayloadError):
        validate_required_fields(payload)

def test_validate_model_format_valid():
    provider, model = validate_model_format("openai/gpt-3.5-turbo")
    assert provider == "openai"
    assert model == "gpt-3.5-turbo"

def test_validate_model_format_invalid():
    with pytest.raises(InvalidModelFormatError):
        validate_model_format("gpt-3.5-turbo")
    with pytest.raises(InvalidModelFormatError):
        validate_model_format(123)
    with pytest.raises(UnknownProviderError):
        validate_model_format("/")
    with pytest.raises(UnknownProviderError):
        validate_model_format("openai/")
    with pytest.raises(UnknownProviderError):
        validate_model_format("/gpt-3.5-turbo")

def test_validate_messages_valid():
    messages = [{"role": "user", "content": "hi"}]
    assert validate_messages(messages) == messages

def test_validate_messages_invalid():
    with pytest.raises(InvalidMessagesError):
        validate_messages(None)
    with pytest.raises(InvalidMessagesError):
        validate_messages("notalist")

def test_validate_token_limit_ok():
    messages = [{"role": "user", "content": "a"*500}]
    validate_token_limit(messages, token_limit=1000)  # Should not raise

def test_validate_token_limit_exceeded():
    messages = [{"role": "user", "content": "a"*1001}]
    with pytest.raises(TokenLimitExceededError):
        validate_token_limit(messages, token_limit=1000)

def test_validate_model_registry_success():
    def list_models_func():
        return {"data": [
            {"id": "openai/gpt-3.5-turbo"},
            {"id": "anthropic/claude-3"}
        ]}
    validate_model_registry("openai/gpt-3.5-turbo", list_models_func)  # Should not raise

def test_validate_model_registry_unknown():
    def list_models_func():
        return {"data": [
            {"id": "openai/gpt-3.5-turbo"}
        ]}
    with pytest.raises(UnknownProviderError):
        validate_model_registry("anthropic/claude-3", list_models_func)

def test_validate_model_registry_unavailable():
    def list_models_func():
        raise Exception("db error")
    with pytest.raises(RegistryUnavailableError):
        validate_model_registry("openai/gpt-3.5-turbo", list_models_func)
