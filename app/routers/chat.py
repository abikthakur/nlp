"""
Chat and Quiz API routers.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.classifier import NOT_SPORTS_REPLY, is_sports_topic
from app.services.sports_data import fetch_context_for_query
from app.services.llm.gemini import GeminiProvider
from app.services import quiz as quiz_service

router = APIRouter(prefix="/api")

_llm: GeminiProvider | None = None


def _get_llm() -> GeminiProvider:
    global _llm
    if _llm is None:
        _llm = GeminiProvider()
    return _llm


# ── Request / response models ──────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    history: list[dict[str, Any]] = []


class ChatResponse(BaseModel):
    reply: str
    blocked: bool = False


class QuizStartRequest(BaseModel):
    sport: str = "football"


class QuizAnswerRequest(BaseModel):
    session_id: str
    answer_index: int


# ── Chat endpoint ──────────────────────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """
    Main chat endpoint:
    1. Classify the topic.
    2. If sports, fetch live data if applicable.
    3. Send to LLM with context.
    """
    message = req.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    # Layer 1: Topic classifier
    is_sports = await is_sports_topic(message)
    if not is_sports:
        return ChatResponse(reply=NOT_SPORTS_REPLY, blocked=True)

    # Fetch live data context if the query seems to need it
    context = await fetch_context_for_query(message)

    # Layer 2: LLM with hardened system prompt
    reply = await _get_llm().chat(
        user_message=message,
        context=context,
        history=req.history,
    )

    return ChatResponse(reply=reply, blocked=False)


# ── Quiz endpoints ─────────────────────────────────────────────────────────────

@router.post("/quiz/start")
async def quiz_start(req: QuizStartRequest) -> dict[str, Any]:
    """Start a new quiz session for the given sport."""
    return await quiz_service.start_quiz(req.sport)


@router.post("/quiz/answer")
async def quiz_answer(req: QuizAnswerRequest) -> dict[str, Any]:
    """Submit an answer for the current quiz question."""
    result = quiz_service.answer_question(req.session_id, req.answer_index)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result
