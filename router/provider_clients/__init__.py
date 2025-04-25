# Provider client base and registry for external LLM routing

from .base import ProviderClient, ProviderResponse
from .openai import OpenAIClient
from .anthropic import AnthropicClient
from .grok import GrokClient
from .openrouter import OpenRouterClient
from .openllama import OpenLLaMAClient

# Registry for provider clients (by provider key)
PROVIDER_CLIENTS = {
    "openai": OpenAIClient(),
    "anthropic": AnthropicClient(),
    "grok": GrokClient(),
    "openrouter": OpenRouterClient(),
    "openllama": OpenLLaMAClient(),
}

__all__ = [
    "ProviderClient", "ProviderResponse",
    "OpenAIClient", "AnthropicClient", "GrokClient", "OpenRouterClient", "OpenLLaMAClient",
    "PROVIDER_CLIENTS"
]
