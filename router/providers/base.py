# Base provider interface (optional for future phases)
class BaseProvider:
    async def generate(self, payload: dict) -> dict:
        raise NotImplementedError
