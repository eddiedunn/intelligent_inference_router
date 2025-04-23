# Settings loader for IIR MVP
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
import yaml
import os

class Settings(BaseSettings):
    classifier_model_id: str = Field(...)
    classifier_device: int = Field(...)
    local_model_id: str = Field(...)
    vllm_base_url: str = Field(...)
    cache_ttl_seconds: int = Field(...)
    rate_limit_rpm: int = Field(...)
    max_request_tokens: int = Field(...)
    model_config = SettingsConfigDict(env_prefix="ROUTER_", env_file=".env")

    @classmethod
    def from_yaml(cls, path="config.defaults.yaml"):
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls(**data)

def get_settings():
    return Settings.from_yaml()
