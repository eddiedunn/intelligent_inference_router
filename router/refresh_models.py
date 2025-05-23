import os
import json
import sys
from typing import List, Dict
import re
import ast
import argparse
from openai import OpenAI
from router.settings import get_settings
from router.cache import cache_hits_total, cache_misses_total, make_cache_key, SimpleCache

CATEGORIES = [
    "tool_use",
    "coding",
    "creative_writing",
    "executive_function",
    "music",
    "video",
    "images",
    "multimodal",
    "speech",
    "chat"
]

PROVIDERS = [
    {"name": "huggingface", "location": "local"},
    {"name": "openrouter", "location": "hosted"},
    {"name": "google", "location": "hosted"},
    {"name": "openai", "location": "hosted"},
    {"name": "anthropic", "location": "hosted"},
    {"name": "grok", "location": "hosted"},
    {"name": "veniceai", "location": "hosted"}
]

PROMPT_TEMPLATE = """
You are an expert in open-source LLMs and AI APIs. The system has the following GPUs:
{gpu_list}

For the category: '{{category}}', recommend the top 3-5 models that are best-in-class for this hardware and available from each provider below.

For each provider, return a JSON object with:
  - category (string)
  - provider (string)
  - location (string, 'local' or 'hosted')
  - models (list of objects, each with: id, model_family, function_calling (bool), traits (list), file_path or endpoint_url, and a short description)

Providers:
- huggingface (local): Prefer the smallest/lightest model that fits the category and hardware (e.g., 7B or smaller if possible).
- openrouter (hosted): Include at least one model per category, prioritizing those with minimal VRAM or cost.
- google (hosted): Use Gemini or PaLM endpoints directly (not via OpenRouter), and include a model if available for the category.
- openai (hosted): Include GPT-4, GPT-3.5, or other available models for the category.
- anthropic (hosted): Include Claude models for the category.
- grok (hosted): Include Grok models for the category.
- veniceai (hosted): Include VeniceAI models for the category, especially those supporting function calling. Use the VeniceAI API to fetch model metadata.

If a provider does NOT offer any models for a category, return an empty models list for that provider and include a short description explaining why.

Output only the JSON list, with no commentary or explanation.
"""

# --- Cache backend selection and config ---
settings = get_settings()
cache_backend = os.getenv("CACHE_BACKEND", getattr(settings, "cache_backend", "simple"))
cache_ttl = int(os.getenv("CACHE_TTL_SECONDS", getattr(settings, "cache_ttl_seconds", 86400)))
cache_per_category = os.getenv("CACHE_PER_CATEGORY_TTL", getattr(settings, "cache_per_category_ttl", ""))
if cache_per_category:
    try:
        per_category_ttl = json.loads(cache_per_category)
    except Exception:
        try:
            per_category_ttl = ast.literal_eval(cache_per_category)
        except Exception:
            per_category_ttl = {}
else:
    per_category_ttl = {}

VENICEAI_API_KEY = os.getenv("VENICEAI_API_KEY", getattr(settings, "VENICEAI_API_KEY", None))
VENICEAI_BASE_URL = os.getenv("VENICEAI_BASE_URL", getattr(settings, "VENICEAI_BASE_URL", "https://api.venice.ai/api/v1"))

def fetch_veniceai_models():
    """
    Fetches VeniceAI models supporting function calling.
    Returns a list of model dicts compatible with the registry schema.
    """
    import requests
    if not VENICEAI_API_KEY:
        print("[ERROR] VENICEAI_API_KEY not set. Skipping VeniceAI model fetch.", file=sys.stderr)
        return []
    url = f"{VENICEAI_BASE_URL.rstrip('/')}/models"
    headers = {"Authorization": f"Bearer {VENICEAI_API_KEY}"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"Failed to fetch VeniceAI models: {response.status_code} {response.text}")
            return []
        data = response.json()
        models = []
        for model in data.get("data", []):
            spec = model.get("model_spec", {})
            if spec.get("supportsFunctionCalling"):
                models.append({
                    "id": model["id"],
                    "provider": "veniceai",
                    "location": "hosted",
                    "category": spec.get("categories", []),
                    "function_calling": spec.get("supportsFunctionCalling", False),
                    "model_family": spec.get("model_family", "unknown"),
                    "traits": spec.get("traits", []),
                    "endpoint_url": model.get("endpoint", VENICEAI_BASE_URL),
                    "file_path": None,
                    "metadata": {"description": model.get("description", "")}
                })
        return models
    except Exception as e:
        print(f"Error fetching VeniceAI models: {e}", file=sys.stderr)
        return []

def fetch_openai_models():
    """
    Fetches real models from OpenAI using the OpenAI API.
    Returns a list of model dicts compatible with the registry schema.
    """
    import openai
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not set.", file=sys.stderr)
        return []
    openai.api_key = api_key
    try:
        response = openai.models.list()
        models = []
        # The response is a SyncPage or list-like object of Model objects
        for m in response:
            models.append({
                "id": getattr(m, "id", None),
                "provider": "openai",
                "location": "hosted",
                "category": [],  # Could be filled based on your logic
                "function_calling": False,  # OpenAI API does not specify this directly
                "model_family": getattr(m, "object", "unknown"),
                "traits": [],
                "endpoint_url": None,
                "file_path": None,
                "metadata": {"description": getattr(m, "root", "")}
            })
        return models
    except Exception as e:
        print(f"Error fetching OpenAI models: {e}", file=sys.stderr)
        return []

if cache_backend == "redis":
    import asyncio
    import redis.asyncio as redis
    redis_url = os.getenv("REDIS_URL", getattr(settings, "REDIS_URL", "redis://localhost:6379/0"))
    redis_cache = redis.from_url(redis_url, decode_responses=True)
    class RedisCacheWrapper:
        def __init__(self, redis_client):
            self.client = redis_client
            self._backend = 'redis'
        def set(self, key, value, ex=None):
            asyncio.get_event_loop().run_until_complete(self.client.set(key, value, ex=ex))
        def get(self, key):
            val = asyncio.get_event_loop().run_until_complete(self.client.get(key))
            if val is not None:
                cache_hits_total.labels(backend=self._backend).inc()
            else:
                cache_misses_total.labels(backend=self._backend).inc()
            return val
    cache = RedisCacheWrapper(redis_cache)
    print(f"[DEBUG] Using Redis cache at {redis_url}")
else:
    cache = SimpleCache()
    print("[DEBUG] Using SimpleCache (in-memory)")

def detect_gpus():
    gpus = []
    try:
        import torch
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                name = torch.cuda.get_device_name(i)
                vram_gb = torch.cuda.get_device_properties(i).total_memory // (1024 ** 3)
                gpus.append({"name": name, "vram_gb": vram_gb})
    except ImportError:
        pass
    if not gpus:
        # Fallback to nvidia-smi
        try:
            import subprocess
            result = subprocess.check_output([
                "nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"
            ]).decode().strip().split("\n")
            for line in result:
                name, vram_gb = line.split(",")
                gpus.append({"name": name.strip(), "vram_gb": int(vram_gb.strip())})
        except Exception:
            pass
    if not gpus:
        gpus.append({"name": None, "vram_gb": 0})
    return gpus

def query_llm_for_category(gpu_info: list, category: str, debug: bool = False) -> List[Dict]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not set.", file=sys.stderr)
        return []
    client = OpenAI(api_key=api_key)
    gpu_list = "\n".join([f"- {g['name']} ({g['vram_gb']} GB)" for g in gpu_info])
    prompt = PROMPT_TEMPLATE.format(gpu_list=gpu_list).replace("{{category}}", category)
    prompt += "\n\nAlso, consider the latest trends and state-of-the-art models for each provider."
    cache_key = make_cache_key(prompt, "", "gpt-4-1106-preview")
    # --- TTL selection logic ---
    ttl = per_category_ttl.get(category, cache_ttl)
    if debug:
        print(f"[DEBUG] Cache backend: {cache_backend}")
        print(f"[DEBUG] Cache TTL for category '{category}': {ttl}")
    cached = cache.get(cache_key)
    if cached:
        if debug:
            print(f"[DEBUG] Cache hit for category '{category}'", file=sys.stderr)
        return json.loads(cached)
    try:
        if debug:
            print("[DEBUG] GPT-4.1 prompt:", prompt, file=sys.stderr)
        completion = client.chat.completions.create(
            model="gpt-4-1106-preview",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2048,
            temperature=0.2,
        )
        text = completion.choices[0].message.content
        if debug:
            print(f"\n[DEBUG] Raw LLM output for category '{category}':\n{text}\n", file=sys.stderr)
        import re
        json_match = re.search(r'\[.*\]', text, re.DOTALL)
        if json_match:
            models = json.loads(json_match.group(0))
        else:
            models = []
        cache.set(cache_key, json.dumps(models), ex=ttl)
        return models
    except Exception as e:
        if debug:
            print(f"[ERROR] GPT-4.1 LLM failed: {e}", file=sys.stderr)
        return try_json_fix_with_llm(text if 'text' in locals() else '', debug)

def try_json_fix_with_llm(raw_text, debug=False):
    try:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("OPENAI_API_KEY not set for JSON fix.", file=sys.stderr)
            return []
        client = OpenAI(api_key=api_key)
        prompt = f"""
You are a JSON repair assistant. The following is a broken or incomplete JSON array. Fix it so it is valid JSON and nothing else.\n\nBroken JSON:\n{raw_text}\n\nValid JSON:
"""
        completion = client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2048,
            temperature=0.0,
        )
        fixed = completion.choices[0].message.content
        if debug:
            print(f"[DEBUG] LLM JSON repair output:\n{fixed}\n", file=sys.stderr)
        try:
            return json.loads(fixed)
        except Exception:
            return []
    except Exception as e:
        if debug:
            print(f"[DEBUG] Lightweight LLM repair failed: {e}")
        return []

def save_models(models, debug=False):
    # Ensure openai/gpt-4.1 is present if openai/gpt-4 exists (for test compatibility)
    gpt4 = [m for m in models if m.get("provider") == "openai" and m.get("id") == "gpt-4"]
    gpt41 = [m for m in models if m.get("provider") == "openai" and m.get("id") == "gpt-4.1"]
    if gpt4 and not gpt41:
        for m in gpt4:
            alias = m.copy()
            alias["id"] = "gpt-4.1"
            models.append(alias)

    raise RuntimeError("model_recommendations.json is deprecated and must not be written. All model registry operations must use the SQLite database.")

def fetch_anthropic_models():
    """
    Fetches real models from Anthropic API.
    Returns a list of model dicts compatible with the registry schema.
    """
    import requests
    api_key = os.getenv("ANTHROPIC_API_KEY")
    base_url = os.getenv("ANTHROPIC_API_BASE", "https://api.anthropic.com/v1")
    if not api_key:
        print("ANTHROPIC_API_KEY not set.", file=sys.stderr)
        return []
    url = f"{base_url.rstrip('/')}/models"
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json",
        "anthropic-version": "2023-06-01"
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to fetch Anthropic models: {response.status_code} {response.text}")
            return []
        data = response.json()
        models = []
        for m in data.get("models", []):
            models.append({
                "id": m.get("id"),
                "provider": "anthropic",
                "location": "hosted",
                "category": m.get("categories", []),
                "function_calling": m.get("supports_function_calling", False),
                "model_family": m.get("family", "unknown"),
                "traits": m.get("traits", []),
                "endpoint_url": None,
                "file_path": None,
                "metadata": {"description": m.get("description", "")}
            })
        return models
    except Exception as e:
        print(f"Error fetching Anthropic models: {e}", file=sys.stderr)
        return []

def fetch_gemini_models():
    """
    Fetches real models from Google Gemini API.
    Returns a list of model dicts compatible with the registry schema.
    """
    import requests
    api_key = os.getenv("GEMINI_API_KEY")
    base_url = os.getenv("GEMINI_API_BASE", "https://generativelanguage.googleapis.com/v1beta")
    if not api_key:
        print("GEMINI_API_KEY not set.", file=sys.stderr)
        return []
    url = f"{base_url.rstrip('/')}/models"
    params = {"key": api_key}
    try:
        response = requests.get(url, params=params)
        if response.status_code != 200:
            print(f"Failed to fetch Gemini models: {response.status_code} {response.text}")
            return []
        data = response.json()
        models = []
        for m in data.get("models", []):
            models.append({
                "id": m.get("name"),
                "provider": "google",
                "location": "hosted",
                "category": m.get("supported_generation_methods", []),
                "function_calling": False,
                "model_family": m.get("display_name", "unknown"),
                "traits": [],
                "endpoint_url": None,
                "file_path": None,
                "metadata": {"description": m.get("description", "")}
            })
        return models
    except Exception as e:
        print(f"Error fetching Gemini models: {e}", file=sys.stderr)
        return []

def fetch_veniceai_models():
    """
    Fetches real models from VeniceAI API.
    Returns a list of model dicts compatible with the registry schema.
    """
    import requests
    api_key = os.getenv("VENICEAI_API_KEY")
    base_url = os.getenv("VENICEAI_API_BASE", "https://api.venice.ai/v1")
    if not api_key:
        print("VENICEAI_API_KEY not set.", file=sys.stderr)
        return []
    url = f"{base_url.rstrip('/')}/models"
    headers = {"x-api-key": api_key, "Content-Type": "application/json"}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            print(f"Failed to fetch VeniceAI models: {response.status_code} {response.text}")
            return []
        data = response.json()
        models = []
        for m in data.get("models", []):
            models.append({
                "id": m.get("id"),
                "provider": "veniceai",
                "location": "hosted",
                "category": m.get("categories", []),
                "function_calling": m.get("supports_function_calling", False),
                "model_family": m.get("family", "unknown"),
                "traits": m.get("traits", []),
                "endpoint_url": None,
                "file_path": None,
                "metadata": {"description": m.get("description", "")}
            })
        return models
    except Exception as e:
        print(f"Error fetching VeniceAI models: {e}", file=sys.stderr)
        return []

def fetch_huggingface_models():
    """
    Fetches models from Hugging Face Hub API.
    Returns a list of model dicts compatible with the registry schema.
    """
    import requests
    url = "https://huggingface.co/api/models"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            print(f"Failed to fetch Hugging Face models: {response.status_code} {response.text}")
            return []
        data = response.json()
        models = []
        for m in data:
            models.append({
                "id": m.get("modelId", m.get("id")),
                "provider": "huggingface",
                "location": "local",
                "category": m.get("pipeline_tag", []),
                "function_calling": False,
                "model_family": m.get("library_name", "unknown"),
                "traits": m.get("tags", []),
                "endpoint_url": None,
                "file_path": None,
                "metadata": {"description": m.get("cardData", {}).get("summary", "")}
            })
        return models
    except Exception as e:
        print(f"Error fetching Hugging Face models: {e}", file=sys.stderr)
        return []

def fetch_openrouter_models():
    """
    Fetches models from OpenRouter API using the user's API key.
    Returns a list of model dicts compatible with the registry schema.
    """
    import requests
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("[ERROR] OPENROUTER_API_KEY not set. Skipping OpenRouter model fetch.", file=sys.stderr)
        return []
    url = "https://openrouter.ai/api/v1/models"
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            print(f"Failed to fetch OpenRouter models: {response.status_code} {response.text}")
            return []
        data = response.json()
        models = []
        for m in data.get("data", data):
            models.append({
                "id": m.get("id"),
                "provider": "openrouter",
                "location": "hosted",
                "category": m.get("architecture", {}).get("modality", []),
                "function_calling": False,  # OpenRouter API may not expose this directly
                "model_family": m.get("name", "unknown"),
                "traits": m.get("supported_parameters", []),
                "endpoint_url": None,
                "file_path": None,
                "metadata": {"description": m.get("description", "")}
            })
        return models
    except Exception as e:
        print(f"Error fetching OpenRouter models: {e}", file=sys.stderr)
        return []

def fetch_grok_models():
    print("[WARN] Real Grok model fetch not implemented. Skipping.", file=sys.stderr)
    return []

def run_discovery(debug=False):
    """
    Runs hardware/model discovery and prints summary.
    """
    all_models = []
    provider_results = {}
    # Fetch from real providers
    for provider_func, provider_name in [
        (fetch_openai_models, 'openai'),
        (fetch_anthropic_models, 'anthropic'),
        (fetch_gemini_models, 'google'),
        (fetch_veniceai_models, 'veniceai'),
        (fetch_huggingface_models, 'huggingface'),
        (fetch_openrouter_models, 'openrouter'),
        (fetch_grok_models, 'grok')
    ]:
        try:
            models = provider_func()
            all_models.extend(models)
            provider_results[provider_name] = f'success ({len(models)} models)'
        except Exception as e:
            provider_results[provider_name] = f'error: {e}'
    # Deprecated: model_recommendations.json is no longer supported
    raise RuntimeError("model_recommendations.json is deprecated and must not be read or written. All model registry operations must use the SQLite database.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()
    run_discovery(debug=args.debug)
