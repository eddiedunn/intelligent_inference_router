# Registry status and hardware info persistence for IIR
import os
import json
import time
import platform
from pathlib import Path

STATUS_PATH = os.path.expanduser("~/.agent_coder/registry_status.json")

def get_hardware_info():
    info = {
        "platform": platform.platform(),
        "python_version": platform.python_version(),
        "cpu": platform.processor(),
        "machine": platform.machine(),
        "gpu": None,
        "cuda": False,
    }
    try:
        import torch
        info["cuda"] = torch.cuda.is_available()
        if info["cuda"]:
            info["gpu"] = torch.cuda.get_device_name(0)
    except Exception:
        pass
    try:
        import subprocess
        result = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True, text=True)
        if result.returncode == 0:
            info["gpu"] = result.stdout.strip()
    except Exception:
        pass
    return info

def save_registry_status():
    status = {
        "last_refresh": int(time.time()),
        "hardware": get_hardware_info(),
    }
    Path(os.path.dirname(STATUS_PATH)).mkdir(parents=True, exist_ok=True)
    with open(STATUS_PATH, "w") as f:
        json.dump(status, f, indent=2)
    return status

def load_registry_status():
    if not os.path.exists(STATUS_PATH):
        return None
    with open(STATUS_PATH, "r") as f:
        return json.load(f)
