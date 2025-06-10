from router.config import Settings


def test_settings_defaults():
    s = Settings()
    assert s.sqlite_db_path == "data/models.db"
    assert s.local_agent_url == "http://localhost:5000"
    assert s.openai_base_url == "https://api.openai.com"
    assert s.anthropic_base_url == "https://api.anthropic.com"
    assert s.google_base_url == "https://generativelanguage.googleapis.com"
    assert s.openrouter_base_url == "https://openrouter.ai"
    assert s.grok_base_url == "https://api.groq.com"
    assert s.venice_base_url == "https://api.venice.ai"
    assert s.log_level == "INFO"
    assert s.log_path == "logs/router.log"
    assert s.cache_ttl == 300
    assert s.rate_limit_requests == 60
    assert s.rate_limit_window == 60
    assert s.router_cost_weight == 1.0
    assert s.router_latency_weight == 1.0
    assert s.router_cost_threshold == 1000
    assert s.hf_cache_dir == "data/hf_models"
    assert s.hf_device == "cpu"
