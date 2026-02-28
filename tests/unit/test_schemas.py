"""Tests for API schemas."""

import pytest
from pydantic import ValidationError

from iir.api.schemas import ChatCompletionRequest


def test_valid_request():
    req = ChatCompletionRequest(
        model="openai/gpt-4o",
        messages=[{"role": "user", "content": "Hello"}],
    )
    assert req.model == "openai/gpt-4o"
    assert len(req.messages) == 1


def test_no_model_defaults_none():
    req = ChatCompletionRequest(messages=[{"role": "user", "content": "Hello"}])
    assert req.model is None


def test_stream_default_false():
    req = ChatCompletionRequest(messages=[{"role": "user", "content": "Hi"}])
    assert req.stream is False


def test_missing_messages():
    with pytest.raises(ValidationError):
        ChatCompletionRequest()


def test_extra_fields_allowed():
    req = ChatCompletionRequest(
        messages=[{"role": "user", "content": "Hi"}],
        custom_field="value",
    )
    assert req.messages[0].content == "Hi"
