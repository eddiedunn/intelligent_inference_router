# Settings loader for IIR MVP
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import os

class Settings(BaseSettings):
    classifier_model_id: str = Field(...)
    classifier_device: int = Field(...)
    local_model_id: str = Field(...)
    vllm_base_url: str = Field(...)
    cache_ttl_seconds: int = Field(...)
    rate_limit_rpm: int = Field(...)
    max_request_tokens: int = Field(...)
    REDIS_URL: str = Field(...)
    LOG_LEVEL: str = Field(default="INFO")
    IIR_API_KEY: str = Field(..., env="IIR_API_KEY")
    ROUTER_LOG_FULL_CONTENT: bool = Field(default=False)
    REMOTE_LOG_SINK: str = Field(default=None)
    HF_TOKEN: str = Field(default=None)
    # Optionally include these if needed in codebase:
    # OPENAI_API_KEY: str = Field(default=None)
    # ANTHROPIC_API_KEY: str = Field(default=None)
    model_config = SettingsConfigDict(env_prefix="", env_file=".env")

    @classmethod
    def from_yaml(cls, path="config.defaults.yaml"):
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls(**data)

# Always use env-based loading by default
def get_settings():
    settings = Settings()
    # Fail fast if IIR_API_KEY is missing
    if not settings.IIR_API_KEY:
        raise RuntimeError("IIR_API_KEY environment variable must be set! (Check your .env and deployment)")
    return settings

# Only use from_yaml for explicit local/testing scenarios
# def get_settings_from_yaml(path="config.defaults.yaml"):
#     return Settings.from_yaml(path)
