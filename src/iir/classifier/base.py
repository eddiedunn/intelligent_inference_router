"""Abstract classifier interface and hybrid coordinator."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Protocol

from iir.classifier.categories import TaskCategory

logger = logging.getLogger("iir.classifier")


class Classifier(ABC):
    @abstractmethod
    async def classify(self, messages: list[dict[str, Any]], **kwargs: Any) -> TaskCategory | None:
        ...


class HybridClassifier:
    """Two-stage classifier: rules first, then LLM for ambiguous cases."""

    def __init__(self, rules: Classifier, llm: Classifier | None = None, strategy: str = "hybrid") -> None:
        self.rules = rules
        self.llm = llm
        self.strategy = strategy

    async def classify(self, messages: list[dict[str, Any]], **kwargs: Any) -> TaskCategory:
        if self.strategy == "llm_only" and self.llm:
            result = await self.llm.classify(messages, **kwargs)
            return result or TaskCategory.GENERAL_CHAT

        result = await self.rules.classify(messages, **kwargs)
        if result is not None:
            logger.debug("Rules classifier matched: %s", result)
            return result

        if self.strategy == "hybrid" and self.llm:
            result = await self.llm.classify(messages, **kwargs)
            if result is not None:
                logger.debug("LLM classifier matched: %s", result)
                return result

        return TaskCategory.GENERAL_CHAT
