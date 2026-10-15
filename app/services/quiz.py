"""
Quiz mode service.
Generates 5 MCQ questions via the LLM and tracks the session state.
Sessions are stored in-memory (reset on server restart).
"""
from __future__ import annotations

import uuid
from typing import Any

from app.services.llm.gemini import GeminiProvider

_provider: GeminiProvider | None = None
_sessions: dict[str, dict[str, Any]] = {}  # session_id → session state


def _get_provider() -> GeminiProvider:
    global _provider
    if _provider is None:
        _provider = GeminiProvider()
    return _provider


FALLBACK_QUIZZES = {
    "football": [
        {
            "question": "Which country won the FIFA World Cup in 2022?",
            "options": ["A. France", "B. Argentina", "C. Brazil", "D. Croatia"],
            "answer_index": 1
        },
        {
            "question": "Who holds the record for the most Ballon d'Or awards in football history?",
            "options": ["A. Cristiano Ronaldo", "B. Lionel Messi", "C. Johan Cruyff", "D. Pelé"],
            "answer_index": 1
        },
        {
            "question": "What is the standard regulation duration of a professional football match (excluding extra time)?",
            "options": ["A. 80 minutes", "B. 90 minutes", "C. 100 minutes", "D. 70 minutes"],
            "answer_index": 1
        },
        {
            "question": "Which club has won the most UEFA Champions League titles?",
            "options": ["A. Real Madrid", "B. AC Milan", "C. Bayern Munich", "D. Liverpool"],
            "answer_index": 0
        },
        {
            "question": "What happens when a defender deliberately handles the ball inside their own penalty area?",
            "options": ["A. Corner kick", "B. Penalty kick", "C. Indirect free kick", "D. Drop ball"],
            "answer_index": 1
        }
    ],
    "cricket": [
        {
            "question": "Which batsman scored the first double century in Men's ODI cricket history?",
            "options": ["A. Virender Sehwag", "B. Rohit Sharma", "C. Sachin Tendulkar", "D. Chris Gayle"],
            "answer_index": 2
        },
        {
            "question": "How many players from one team are on the field during a cricket match?",
            "options": ["A. 10", "B. 11", "C. 12", "D. 9"],
            "answer_index": 1
        },
        {
            "question": "What does LBW stand for in cricket?",
            "options": ["A. Leg Before Wicket", "B. Long Ball Wide", "C. Line Boundary Wicket", "D. Low Bouncing Wicket"],
            "answer_index": 0
        },
        {
            "question": "Who won the inaugural ICC Men's T20 World Cup in 2007?",
            "options": ["A. Pakistan", "B. India", "C. Australia", "D. West Indies"],
            "answer_index": 1
        },
        {
            "question": "How many legal balls are bowled in a single standard cricket over?",
            "options": ["A. 5", "B. 6", "C. 8", "D. 10"],
            "answer_index": 1
        }
    ]
}


async def start_quiz(sport: str) -> dict[str, Any]:
    """Generate a quiz session and return the first question."""
    sport_key = sport.lower().strip()
    try:
        questions = await _get_provider().generate_quiz(sport_key)
    except Exception:
        questions = FALLBACK_QUIZZES.get(sport_key, FALLBACK_QUIZZES["football"])
    session_id = str(uuid.uuid4())
    _sessions[session_id] = {
        "questions": questions,
        "current": 0,
        "score": 0,
        "sport": sport,
    }
    return {
        "session_id": session_id,
        "total": len(questions),
        **_format_question(session_id),
    }


def _format_question(session_id: str) -> dict[str, Any]:
    session = _sessions[session_id]
    q = session["questions"][session["current"]]
    return {
        "question_number": session["current"] + 1,
        "question": q["question"],
        "options": q["options"],
        "done": False,
    }


def answer_question(session_id: str, answer_index: int) -> dict[str, Any]:
    """Process an answer and return next question or final score."""
    if session_id not in _sessions:
        return {"error": "Quiz session not found. Start a new quiz."}

    session = _sessions[session_id]
    q = session["questions"][session["current"]]
    correct = q["answer_index"]
    is_correct = answer_index == correct

    if is_correct:
        session["score"] += 1

    session["current"] += 1

    if session["current"] >= len(session["questions"]):
        # Quiz finished
        score = session["score"]
        total = len(session["questions"])
        del _sessions[session_id]  # clean up
        return {
            "done": True,
            "correct": is_correct,
            "correct_option": q["options"][correct],
            "score": score,
            "total": total,
            "message": _score_message(score, total),
        }

    return {
        "done": False,
        "correct": is_correct,
        "correct_option": q["options"][correct],
        **_format_question(session_id),
    }


def _score_message(score: int, total: int) -> str:
    pct = score / total
    if pct == 1.0:
        return "🏆 Perfect score! You're a sports genius!"
    if pct >= 0.8:
        return "🥇 Excellent! You really know your sport!"
    if pct >= 0.6:
        return "🥈 Good effort! Keep watching those matches!"
    if pct >= 0.4:
        return "🥉 Not bad — a bit more practice and you'll be unstoppable!"
    return "📚 Tough round! Try again — every expert was once a beginner."
