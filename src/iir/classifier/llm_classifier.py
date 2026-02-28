"""LLM-based classifier via Ollama for ambiguous prompts."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from iir.classifier.base import Classifier
from iir.classifier.categories import TaskCategory

logger = logging.getLogger("iir.classifier.llm")

_CLASSIFICATION_PROMPT = """Classify this user request into exactly one category.

Categories: general_chat, coding, analysis, creative_writing, summarization, translation, math

User request: {message}

Respond with ONLY the category name, nothing else."""

_CATEGORY_MAP = {v.value: v for v in TaskCategory if v not in (TaskCategory.VISION, TaskCategory.FUNCTION_CALLING, TaskCategory.LONG_CONTEXT, TaskCategory.SIMPLE_CHAT)}


class LLMClassifier(Classifier):
    def __init__(self, ollama_url: str, model: str = "llama3.2:1b") -> None:
        self.ollama_url = ollama_url.rstrip("/")
        self.model = model

    async def classify(self, messages: list[dict[str, Any]], **kwargs: Any) -> TaskCategory | None:
        last_user = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                last_user = content if isinstance(content, str) else str(content)
                break

        if not last_user:
            return None

        prompt = _CLASSIFICATION_PROMPT.format(message=last_user[:500])

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={"model": self.model, "prompt": prompt, "stream": False},
                )
                resp.raise_for_status()
                result = resp.json().get("response", "").strip().lower()
                return _CATEGORY_MAP.get(result)
        except Exception:
            logger.warning("LLM classification failed, falling back", exc_info=True)
            return None
