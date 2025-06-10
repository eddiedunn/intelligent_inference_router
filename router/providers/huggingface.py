"""Local weight-based provider using Hugging Face transformers."""

from __future__ import annotations

import os
import uuid
import time
import asyncio
from typing import Dict, Any

from huggingface_hub import snapshot_download
from transformers import pipeline

from ..schemas import ChatCompletionRequest
from .base import WeightProvider
from . import register_provider
import sys


class HuggingFaceProvider(WeightProvider):
    """Load models from the Hugging Face Hub and run inference locally."""

    def __init__(self) -> None:
        self.cache_dir = os.getenv("HF_CACHE_DIR", "data/hf_models")
        self.device = os.getenv("HF_DEVICE", "cpu")
        self._pipelines: Dict[str, Any] = {}

    def _get_pipeline(self, model_id: str):
        """Return the text-generation pipeline for ``model_id``.

        The model is downloaded from Hugging Face if it is not already
        available locally. The resulting pipeline is cached in
        ``self._pipelines`` and then returned.
        """
        pipe = self._pipelines.get(model_id)
        if pipe is None:
            local_dir = os.path.join(self.cache_dir, model_id.replace("/", "_"))
            if not os.path.exists(local_dir):
                snapshot_download(
                    repo_id=model_id,
                    local_dir=local_dir,
                    local_dir_use_symlinks=False,
                )
            pipe = pipeline(
                "text-generation",
                model=local_dir,
                tokenizer=local_dir,
                device=0 if self.device == "cuda" else -1,
            )
            self._pipelines[model_id] = pipe
        return pipe

    async def forward(self, payload: ChatCompletionRequest, base_url: str) -> dict:
        pipe = self._get_pipeline(payload.model)
        prompt = payload.messages[-1].content if payload.messages else ""
        max_tokens = payload.max_tokens or 16
        temperature = payload.temperature or 0.7
        generated = await asyncio.to_thread(
            lambda: pipe(
                prompt,
                max_new_tokens=max_tokens,
                temperature=temperature,
                return_full_text=False,
            )[0]["generated_text"]
        )
        return {
            "id": f"hf-{uuid.uuid4().hex}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": payload.model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": generated},
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        }


async def forward(payload: ChatCompletionRequest, base_url: str) -> dict:
    """Backward compatible wrapper for ``HuggingFaceProvider``."""

    provider = HuggingFaceProvider()
    return await provider.forward(payload, base_url)


register_provider("huggingface", sys.modules[__name__])
