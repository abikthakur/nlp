"""
Topic classifier service — thin wrapper so the router stays clean.
"""
from app.services.llm.gemini import GeminiProvider

NOT_SPORTS_REPLY = (
    "I can only help with sports-related questions. "
    "Ask me about scores, players, rules, or teams!"
)

_provider: GeminiProvider | None = None


def _get_provider() -> GeminiProvider:
    global _provider
    if _provider is None:
        _provider = GeminiProvider()
    return _provider


async def is_sports_topic(message: str) -> bool:
    """Returns True if the message is sports-related."""
    label = await _get_provider().classify(message)
    return label == "SPORTS"
