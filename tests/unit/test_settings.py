from router.settings import get_settings
import os

def test_settings_load():
    s = get_settings()
    assert s.local_model_id
    assert s.vllm_base_url
    assert s.classifier_model_id
    assert s.max_request_tokens > 0
