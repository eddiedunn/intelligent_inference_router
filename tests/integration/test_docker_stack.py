import asyncio
import shutil
from pathlib import Path

import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]

if shutil.which("docker") is None:
    pytest.skip("docker not available", allow_module_level=True)


@pytest.fixture(scope="module")
async def docker_stack():
    compose_file = ROOT / "docker-compose.yml"
    up = await asyncio.create_subprocess_exec(
        "docker",
        "compose",
        "-f",
        str(compose_file),
        "up",
        "-d",
        cwd=str(ROOT),
    )
    await up.communicate()
    # wait for router to start
    for _ in range(30):
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "http://localhost:8000/v1/chat/completions",
                    json={
                        "model": "local_test",
                        "messages": [{"role": "user", "content": "hi"}],
                    },
                    timeout=1,
                )
            if resp.status_code == 200:
                break
        except Exception:
            await asyncio.sleep(1)
    yield
    down = await asyncio.create_subprocess_exec(
        "docker",
        "compose",
        "-f",
        str(compose_file),
        "down",
        "-v",
        cwd=str(ROOT),
    )
    await down.communicate()


@pytest.mark.asyncio
async def test_stack_basic(docker_stack):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "http://localhost:8000/v1/chat/completions",
            json={
                "model": "local_test",
                "messages": [{"role": "user", "content": "ping"}],
            },
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["choices"][0]["message"]["content"] == "Echo: ping"
