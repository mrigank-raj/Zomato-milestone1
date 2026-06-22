from typing import Protocol
from app.domain.models import LLMRequest

class LLMClient(Protocol):
    def complete(self, request: LLMRequest) -> str:
        """
        Takes an LLMRequest and returns the raw completion string.
        """
        ...
