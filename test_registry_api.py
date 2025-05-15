import requests

import os

def test_registry_refresh(main_api_server):
    BASE = os.environ["IIR_API_URL"]
    resp = requests.post(f"{BASE}/v1/registry/refresh")
    print("/v1/registry/refresh:", resp.status_code, resp.json())
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"

def test_registry_status(main_api_server):
    BASE = os.environ["IIR_API_URL"]
    resp = requests.get(f"{BASE}/v1/registry/status")
    print("/v1/registry/status:", resp.status_code, resp.json())
    assert resp.status_code == 200
    assert "hardware" in resp.json()
    assert "last_refresh" in resp.json()

def test_models(main_api_server):
    BASE = os.environ["IIR_API_URL"]
    resp = requests.get(f"{BASE}/v1/models")
    print("/v1/models:", resp.status_code, resp.json())
    assert resp.status_code == 200
    assert resp.json()["object"] == "list"
    assert isinstance(resp.json()["data"], list)

if __name__ == "__main__":
    test_registry_refresh()
    test_registry_status()
    test_models()
    print("All registry API tests passed!")
