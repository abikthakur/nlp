"""
Abstract base class for LLM providers.
Swap providers by subclassing this and updating config.
"""
from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """All LLM providers must implement this interface."""

    @abstractmethod
    async def classify(self, user_message: str) -> str:
        """
        Lightweight topic classification.
        Must return exactly 'SPORTS' or 'NOT_SPORTS'.
        """
        ...

    @abstractmethod
    async def chat(
        self,
        user_message: str,
        context: str = "",
        history: list[dict[str, Any]] | None = None,
    ) -> str:
        """
        Main chat completion.
        context: extra live data injected from the sports API.
        history: list of {"role": "user"|"model", "content": "..."} dicts.
        """
        ...

    @abstractmethod
    async def generate_quiz(self, sport: str) -> list[dict[str, Any]]:
        """
        Generate 5 multiple-choice quiz questions for the given sport.
        Returns list of dicts:
          {"question": str, "options": [str, str, str, str], "answer_index": int}
        """
        ...
