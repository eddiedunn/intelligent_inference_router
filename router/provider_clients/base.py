import abc
from typing import Any, Dict, Optional

class ProviderResponse:
    def __init__(self, content: Any, raw_response: Any = None, status_code: int = 200):
        self.content = content
        self.raw_response = raw_response
        self.status_code = status_code

class ProviderClient(abc.ABC):
    """Abstract base class for all provider clients."""
    @abc.abstractmethod
    async def chat_completions(self, payload: Dict[str, Any], model: str, **kwargs) -> ProviderResponse:
        pass

    @abc.abstractmethod
    async def completions(self, payload: Dict[str, Any], model: str, **kwargs) -> ProviderResponse:
        pass
