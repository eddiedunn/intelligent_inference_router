from __future__ import annotations

import asyncio

from router.providers.huggingface import HuggingFaceProvider
from router.schemas import ChatCompletionRequest, Message


class DummyPipe:
    def __call__(
        self,
        prompt: str,
        max_new_tokens: int,
        temperature: float,
        return_full_text: bool,
    ):
        return [{"generated_text": f"HF: {prompt}"}]


def test_forward(monkeypatch) -> None:
    provider = HuggingFaceProvider()
    monkeypatch.setattr(provider, "_get_pipeline", lambda m: DummyPipe())
    payload = ChatCompletionRequest(
        model="dummy-model",
        messages=[Message(role="user", content="hello")],
    )
    data = asyncio.run(provider.forward(payload, base_url="unused"))
    assert data["choices"][0]["message"]["content"] == "HF: hello"
