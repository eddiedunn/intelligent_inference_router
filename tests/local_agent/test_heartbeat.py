import asyncio
import pytest
import local_agent.main as agent


calls: list[tuple[str, dict]] = []


async def dummy_post(path: str, payload: dict) -> None:
    calls.append((path, payload))
    if len(calls) >= 2:
        raise asyncio.CancelledError()


def test_heartbeat_loop(monkeypatch):
    monkeypatch.setattr(agent, "_post_with_retry", dummy_post)
    monkeypatch.setattr(agent, "HEARTBEAT_INTERVAL", 0)
    original_sleep = asyncio.sleep
    monkeypatch.setattr(agent.asyncio, "sleep", lambda s: original_sleep(0))

    with pytest.raises(asyncio.CancelledError):
        asyncio.run(agent.heartbeat_loop())

    assert calls[0] == ("/heartbeat", {"name": agent.AGENT_NAME})
    assert len(calls) >= 2
