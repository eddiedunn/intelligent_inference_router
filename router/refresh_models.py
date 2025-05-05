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
    {"name": "grok", "location": "hosted"}
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
    out_path = os.path.expanduser("~/.agent_coder/model_recommendations.json")
    with open(out_path, "w") as f:
        json.dump(models, f, indent=2)
    if debug:
        print(f"Saved model recommendations to {out_path}")

def run_discovery(debug=False):
    gpus = detect_gpus()
    all_models = []
    for category in CATEGORIES:
        cat_models = query_llm_for_category(gpus, category, debug)
        if isinstance(cat_models, list):
            all_models.extend(cat_models)
        else:
            # Defensive: if LLM returns a dict or other type
            all_models.append(cat_models)
    save_models(all_models, debug)
    return all_models

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()
    run_discovery(debug=args.debug)
