from __future__ import annotations

import asyncio
import sys
import types

# Stub optional dependencies so the provider can be imported
hub_stub = types.ModuleType("huggingface_hub")
hub_stub.snapshot_download = lambda *args, **kwargs: None
trans_stub = types.ModuleType("transformers")
trans_stub.pipeline = lambda *args, **kwargs: None
sys.modules.setdefault("huggingface_hub", hub_stub)
sys.modules.setdefault("transformers", trans_stub)

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


def test_get_pipeline_download_and_cache(monkeypatch, tmp_path) -> None:
    provider = HuggingFaceProvider()
    provider.cache_dir = str(tmp_path)

    calls = {"download": 0, "pipeline": 0}

    def fake_exists(path: str) -> bool:
        return False

    def fake_snapshot_download(repo_id: str, local_dir: str, local_dir_use_symlinks: bool) -> None:
        calls["download"] += 1
        assert repo_id == "test/model"
        assert local_dir == str(tmp_path / "test_model")
        assert local_dir_use_symlinks is False

    dummy_pipe = object()

    def fake_pipeline(task: str, model: str, tokenizer: str, device: int):
        calls["pipeline"] += 1
        assert task == "text-generation"
        assert model == str(tmp_path / "test_model")
        assert tokenizer == str(tmp_path / "test_model")
        assert device == -1
        return dummy_pipe

    monkeypatch.setattr("router.providers.huggingface.os.path.exists", fake_exists)
    monkeypatch.setattr("router.providers.huggingface.snapshot_download", fake_snapshot_download)
    monkeypatch.setattr("router.providers.huggingface.pipeline", fake_pipeline)

    pipe1 = provider._get_pipeline("test/model")
    assert pipe1 is dummy_pipe
    assert calls == {"download": 1, "pipeline": 1}

    pipe2 = provider._get_pipeline("test/model")
    assert pipe2 is dummy_pipe
    assert calls == {"download": 1, "pipeline": 1}
