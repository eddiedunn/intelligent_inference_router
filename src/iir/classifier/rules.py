"""Rules-based fast classifier. Handles ~60-70% of requests in <1ms."""

from __future__ import annotations

import re
from typing import Any

from iir.classifier.base import Classifier
from iir.classifier.categories import TaskCategory

_CODE_KEYWORDS = re.compile(
    r"\b(def |class |import |function |const |let |var |return |async |await |"
    r"print\(|console\.log|\.py\b|\.js\b|\.ts\b|\.rs\b|\.go\b|\.java\b|"
    r"traceback|stacktrace|exception|error:|bug|debug|refactor|"
    r"```|dockerfile|makefile|yaml|json|sql|regex|api endpoint|http request|"
    r"git |npm |pip |cargo |docker )",
    re.IGNORECASE,
)

_MATH_KEYWORDS = re.compile(
    r"\b(calculate|solve|equation|integral|derivative|matrix|probability|"
    r"statistics|algebra|geometry|trigonometry|factorial|logarithm|"
    r"\d+\s*[\+\-\*\/\^]\s*\d+)",
    re.IGNORECASE,
)

_CREATIVE_KEYWORDS = re.compile(
    r"\b(write a (story|poem|essay|song|script|letter|blog)|"
    r"creative writing|fiction|narrative|once upon|imagine|"
    r"compose|draft a|rewrite this.*tone)",
    re.IGNORECASE,
)

_SUMMARIZE_KEYWORDS = re.compile(
    r"\b(summarize|summary|tldr|tl;dr|brief overview|key points|"
    r"main ideas|condense|shorten this)",
    re.IGNORECASE,
)

_TRANSLATE_KEYWORDS = re.compile(
    r"\b(translate|translation|in (spanish|french|german|chinese|japanese|korean|"
    r"portuguese|italian|russian|arabic|hindi)|to (spanish|french|german|chinese|"
    r"japanese|korean|portuguese|italian|russian|arabic|hindi))",
    re.IGNORECASE,
)

_GREETING_PATTERNS = re.compile(
    r"^(hi|hello|hey|howdy|good (morning|afternoon|evening)|what'?s up|yo|sup)\s*[!?.]?$",
    re.IGNORECASE,
)


def _last_user_message(messages: list[dict[str, Any]]) -> str:
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            return content if isinstance(content, str) else ""
    return ""


def _has_images(messages: list[dict[str, Any]]) -> bool:
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "image_url":
                    return True
    return False


def _total_content_length(messages: list[dict[str, Any]]) -> int:
    total = 0
    for msg in messages:
        content = msg.get("content", "")
        if isinstance(content, str):
            total += len(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    total += len(block.get("text", ""))
    return total


class RulesClassifier(Classifier):
    async def classify(self, messages: list[dict[str, Any]], **kwargs: Any) -> TaskCategory | None:
        # Check for tool/function calling in the request
        if kwargs.get("tools") or kwargs.get("functions"):
            return TaskCategory.FUNCTION_CALLING

        # Vision: images present
        if _has_images(messages):
            return TaskCategory.VISION

        # Long context
        if _total_content_length(messages) > 50_000:
            return TaskCategory.LONG_CONTEXT

        text = _last_user_message(messages)
        if not text:
            return None

        # Simple greetings
        if len(text) < 60 and _GREETING_PATTERNS.match(text.strip()):
            return TaskCategory.SIMPLE_CHAT

        # Code detection
        if _CODE_KEYWORDS.search(text) or "```" in text:
            return TaskCategory.CODING

        # Math
        if _MATH_KEYWORDS.search(text):
            return TaskCategory.MATH

        # Translation
        if _TRANSLATE_KEYWORDS.search(text):
            return TaskCategory.TRANSLATION

        # Summarization
        if _SUMMARIZE_KEYWORDS.search(text):
            return TaskCategory.SUMMARIZATION

        # Creative writing
        if _CREATIVE_KEYWORDS.search(text):
            return TaskCategory.CREATIVE_WRITING

        # No rule matched — return None so hybrid can fall through to LLM
        return None
