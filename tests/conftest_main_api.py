import pytest
import subprocess
import time
import os
import socket
import requests
import signal

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

@pytest.fixture(scope="session")
def main_api_server():
    port = get_free_port()
    env = os.environ.copy()
    env["IIR_API_URL"] = f"http://localhost:{port}"
    command = [
        "uvicorn",
        "router.main:create_app",
        "--factory",
        "--host", "127.0.0.1",
        "--port", str(port),
        "--lifespan", "on"
    ]
    proc = subprocess.Popen(
        command,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid
    )
    # Wait for the service to be ready
    for _ in range(30):
        try:
            r = requests.get(f"http://localhost:{port}/health", timeout=0.5)
            if r.status_code == 200:
                break
        except Exception:
            time.sleep(0.5)
    else:
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        raise RuntimeError("Main API did not start in time")
    yield port
    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
