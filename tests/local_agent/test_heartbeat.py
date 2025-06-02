import asyncio
import pytest
import local_agent.main as agent


async def dummy_post(path: str, payload: dict) -> None:
    dummy_post.calls.append((path, payload))
    if len(dummy_post.calls) >= 2:
        raise asyncio.CancelledError()


dummy_post.calls = []


def test_heartbeat_loop(monkeypatch):
    monkeypatch.setattr(agent, "_post_with_retry", dummy_post)
    monkeypatch.setattr(agent, "HEARTBEAT_INTERVAL", 0)
    original_sleep = asyncio.sleep
    monkeypatch.setattr(agent.asyncio, "sleep", lambda s: original_sleep(0))

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(agent.heartbeat_loop())

    assert dummy_post.calls[0] == ("/heartbeat", {"name": agent.AGENT_NAME})
    assert len(dummy_post.calls) >= 2
