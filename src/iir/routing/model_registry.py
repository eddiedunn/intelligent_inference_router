"""Model capabilities registry loaded from YAML config."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from iir.classifier.categories import TaskCategory

logger = logging.getLogger("iir.routing.registry")


@dataclass
class ModelInfo:
    id: str
    provider: str
    capabilities: list[str] = field(default_factory=list)
    context_length: int = 128_000
    cost_per_1m_input: float = 0.0
    cost_per_1m_output: float = 0.0
    quality_tier: str = "good"  # good | great | excellent
    supports_vision: bool = False
    supports_tools: bool = False


class ModelRegistry:
    def __init__(self) -> None:
        self._models: dict[str, ModelInfo] = {}
        self._task_defaults: dict[str, str] = {}

    def load_from_yaml(self, path: str | Path) -> None:
        path = Path(path)
        if not path.exists():
            logger.warning("Model config not found: %s", path)
            return
        with open(path) as f:
            data = yaml.safe_load(f) or {}

        for model_id, info in data.get("models", {}).items():
            self._models[model_id] = ModelInfo(
                id=model_id,
                provider=info.get("provider", model_id.split("/")[0]),
                capabilities=info.get("capabilities", []),
                context_length=info.get("context_length", 128_000),
                cost_per_1m_input=info.get("cost_per_1m_input_tokens", 0.0),
                cost_per_1m_output=info.get("cost_per_1m_output_tokens", 0.0),
                quality_tier=info.get("quality_tier", "good"),
                supports_vision=info.get("supports_vision", False),
                supports_tools=info.get("supports_tools", False),
            )

        self._task_defaults = data.get("task_routing", {})
        logger.info("Loaded %d models from %s", len(self._models), path)

    def get_model(self, model_id: str) -> ModelInfo | None:
        return self._models.get(model_id)

    def get_models_for_task(self, category: TaskCategory) -> list[ModelInfo]:
        return [m for m in self._models.values() if category.value in m.capabilities]

    def get_default_model_for_task(self, category: TaskCategory) -> str | None:
        return self._task_defaults.get(category.value)

    def list_models(self) -> list[ModelInfo]:
        return list(self._models.values())

    def model_exists(self, model_id: str) -> bool:
        return model_id in self._models
