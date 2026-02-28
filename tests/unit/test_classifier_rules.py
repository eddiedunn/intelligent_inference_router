"""Tests for rules-based classifier."""

import pytest

from iir.classifier.categories import TaskCategory
from iir.classifier.rules import RulesClassifier


@pytest.fixture
def classifier():
    return RulesClassifier()


def _msgs(text: str) -> list[dict]:
    return [{"role": "user", "content": text}]


def _msgs_with_image() -> list[dict]:
    return [{"role": "user", "content": [
        {"type": "text", "text": "What is in this image?"},
        {"type": "image_url", "image_url": {"url": "https://example.com/img.png"}},
    ]}]


@pytest.mark.asyncio
async def test_greeting(classifier):
    assert await classifier.classify(_msgs("Hello!")) == TaskCategory.SIMPLE_CHAT


@pytest.mark.asyncio
async def test_greeting_hey(classifier):
    assert await classifier.classify(_msgs("hey")) == TaskCategory.SIMPLE_CHAT


@pytest.mark.asyncio
async def test_coding_python(classifier):
    assert await classifier.classify(_msgs("Write a Python function to sort a list")) == TaskCategory.CODING


@pytest.mark.asyncio
async def test_coding_backticks(classifier):
    assert await classifier.classify(_msgs("Fix this bug:\n```python\ndef foo(): pass\n```")) == TaskCategory.CODING


@pytest.mark.asyncio
async def test_coding_debug(classifier):
    assert await classifier.classify(_msgs("I'm getting a traceback in my Flask app")) == TaskCategory.CODING


@pytest.mark.asyncio
async def test_math(classifier):
    assert await classifier.classify(_msgs("Calculate the integral of x^2 from 0 to 5")) == TaskCategory.MATH


@pytest.mark.asyncio
async def test_math_arithmetic(classifier):
    assert await classifier.classify(_msgs("What is 2 + 2")) == TaskCategory.MATH


@pytest.mark.asyncio
async def test_translation(classifier):
    assert await classifier.classify(_msgs("Translate this to Spanish: Hello world")) == TaskCategory.TRANSLATION


@pytest.mark.asyncio
async def test_summarize(classifier):
    assert await classifier.classify(_msgs("Summarize this article for me")) == TaskCategory.SUMMARIZATION


@pytest.mark.asyncio
async def test_creative(classifier):
    assert await classifier.classify(_msgs("Write a poem about the ocean")) == TaskCategory.CREATIVE_WRITING


@pytest.mark.asyncio
async def test_vision(classifier):
    assert await classifier.classify(_msgs_with_image()) == TaskCategory.VISION


@pytest.mark.asyncio
async def test_function_calling(classifier):
    result = await classifier.classify(_msgs("Get the weather"), tools=[{"type": "function"}])
    assert result == TaskCategory.FUNCTION_CALLING


@pytest.mark.asyncio
async def test_long_context(classifier):
    long_text = "word " * 15_000
    assert await classifier.classify(_msgs(long_text)) == TaskCategory.LONG_CONTEXT


@pytest.mark.asyncio
async def test_ambiguous_returns_none(classifier):
    result = await classifier.classify(_msgs("Tell me about the history of Rome"))
    assert result is None
