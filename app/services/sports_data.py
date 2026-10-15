"""
TheSportsDB API wrapper.
Free test key: "3"  (v1 endpoints, no sign-up needed).
Full key available at https://www.thesportsdb.com/api.php

NOTE on cricket: TheSportsDB has limited cricket data (no ball-by-ball).
For richer cricket live scores, Cricbuzz / CricAPI (https://cricapi.com/)
or the ESPN Cricinfo API are better free alternatives. The code is
structured so you can add a CricketDataService alongside this one.
"""
from __future__ import annotations

import httpx

from app.config import get_sports_db_key

BASE_V1 = "https://www.thesportsdb.com/api/v1/json"


def _url(endpoint: str) -> str:
    key = get_sports_db_key()
    return f"{BASE_V1}/{key}/{endpoint}"


async def _get(endpoint: str, params: dict | None = None) -> dict:
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(_url(endpoint), params=params)
        r.raise_for_status()
        if not r.content or not r.content.strip():
            return {}
        try:
            return r.json()
        except Exception:
            return {}


# ── Live scores ────────────────────────────────────────────────────────────────

async def get_live_scores(league_id: str | None = None) -> str:
    """Return a formatted string of live scores (all sports or filtered)."""
    try:
        data = await _get("livescore.php")
        events = data.get("events") or []
        if not events:
            return "No live matches found at the moment."
        lines = ["**Live Scores**"]
        for e in events[:10]:
            home = e.get("strHomeTeam", "?")
            away = e.get("strAwayTeam", "?")
            hs = e.get("intHomeScore", "-")
            as_ = e.get("intAwayScore", "-")
            sport = e.get("strSport", "")
            lines.append(f"- {sport}: {home} {hs} – {as_} {away}")
        return "\n".join(lines)
    except Exception as exc:
        return f"Live scores unavailable: {exc}"


# ── Upcoming fixtures ──────────────────────────────────────────────────────────

async def get_upcoming_fixtures(league_id: str) -> str:
    """Return next 5 fixtures for a given league ID."""
    try:
        data = await _get("eventsnextleague.php", {"id": league_id})
        events = data.get("events") or []
        if not events:
            return "No upcoming fixtures found."
        lines = ["**Upcoming Fixtures**"]
        for e in events[:5]:
            home = e.get("strHomeTeam", "?")
            away = e.get("strAwayTeam", "?")
            date = e.get("dateEvent", "?")
            time = e.get("strTime", "")
            lines.append(f"- {date} {time}  {home} vs {away}")
        return "\n".join(lines)
    except Exception as exc:
        return f"Fixtures unavailable: {exc}"


# ── League table / standings ───────────────────────────────────────────────────

async def get_standings(league_id: str, season: str = "") -> str:
    """Return league table for a given league. season format: '2023-2024'."""
    try:
        params: dict = {"id": league_id}
        if season:
            params["s"] = season
        data = await _get("lookuptable.php", params)
        rows = data.get("table") or []
        if not rows:
            return "Standings not available for this league/season."
        lines = ["**League Standings**", "| # | Team | P | W | D | L | GD | Pts |",
                 "|---|------|---|---|---|---|----|-----|"]
        for r in rows[:10]:
            lines.append(
                f"| {r.get('intRank','-')} | {r.get('strTeam','-')} "
                f"| {r.get('intPlayed','-')} | {r.get('intWin','-')} "
                f"| {r.get('intDraw','-')} | {r.get('intLoss','-')} "
                f"| {r.get('intGoalDifference','-')} | {r.get('intPoints','-')} |"
            )
        return "\n".join(lines)
    except Exception as exc:
        return f"Standings unavailable: {exc}"


# ── Team search ────────────────────────────────────────────────────────────────

async def search_team(team_name: str) -> str:
    """Return basic info about a team."""
    try:
        data = await _get("searchteams.php", {"t": team_name})
        teams = data.get("teams") or []
        if not teams:
            return f"No team found for '{team_name}'."
        t = teams[0]
        return (
            f"**{t.get('strTeam')}** ({t.get('strSport', '')}, {t.get('strLeague', '')})\n"
            f"Country: {t.get('strCountry', 'N/A')}\n"
            f"Founded: {t.get('intFormedYear', 'N/A')}\n"
            f"Stadium: {t.get('strStadium', 'N/A')}\n"
            f"Description: {(t.get('strDescriptionEN') or '')[:300]}..."
        )
    except Exception as exc:
        return f"Team search failed: {exc}"


# ── Player search ──────────────────────────────────────────────────────────────

async def search_player(player_name: str) -> str:
    """Return basic stats about a player."""
    try:
        data = await _get("searchplayers.php", {"p": player_name})
        players = data.get("player") or []
        if not players:
            return f"No player found for '{player_name}'."
        p = players[0]
        return (
            f"**{p.get('strPlayer')}** — {p.get('strSport', '')} | {p.get('strTeam', '')}\n"
            f"Nationality: {p.get('strNationality', 'N/A')}\n"
            f"Position: {p.get('strPosition', 'N/A')}\n"
            f"Date of Birth: {p.get('dateBorn', 'N/A')}\n"
            f"Description: {(p.get('strDescriptionEN') or '')[:300]}..."
        )
    except Exception as exc:
        return f"Player search failed: {exc}"


# ── Last event between two teams ───────────────────────────────────────────────

async def get_last_event(team1: str, team2: str) -> str:
    """Return the result of the last match between two teams."""
    try:
        # Search for team1 events and look for team2
        data = await _get("searchevents.php", {"e": f"{team1} vs {team2}"})
        events = data.get("event") or []
        if not events:
            # fallback: search the other way
            data = await _get("searchevents.php", {"e": f"{team2} vs {team1}"})
            events = data.get("event") or []
        if not events:
            return f"No recent match data found for {team1} vs {team2}."
        e = events[-1]
        return (
            f"**Last Match**: {e.get('strHomeTeam')} vs {e.get('strAwayTeam')}\n"
            f"Date: {e.get('dateEvent')}\n"
            f"Score: {e.get('intHomeScore')} – {e.get('intAwayScore')}\n"
            f"League: {e.get('strLeague')}"
        )
    except Exception as exc:
        return f"Head-to-head lookup failed: {exc}"


# ── Intent router — called by the chat endpoint ────────────────────────────────

# Map keywords in user messages to sports-DB leagues
LEAGUE_MAP: dict[str, str] = {
    "premier league": "4328",
    "epl": "4328",
    "la liga": "4335",
    "bundesliga": "4331",
    "serie a": "4332",
    "ligue 1": "4334",
    "champions league": "4346",
    "ipl": "4507",
    "bbl": "4508",   # Big Bash League
    "psl": "4644",   # Pakistan Super League
}


async def fetch_context_for_query(user_message: str) -> str:
    """
    Heuristically decide what live data (if any) to fetch based on the query.
    Returns a formatted string that is injected as context into the LLM prompt.
    """
    msg = user_message.lower()

    # Live score request
    if any(w in msg for w in ["live", "score", "scorecard", "current score", "playing now"]):
        return await get_live_scores()

    # Head-to-head / last match
    if " vs " in msg or "versus" in msg or "last match" in msg or "head to head" in msg:
        # Try to extract two team names around "vs" / "versus"
        import re
        m = re.search(r"([\w\s]+?)\s+(?:vs\.?|versus)\s+([\w\s]+)", msg)
        if m:
            t1 = m.group(1).strip()
            t2 = m.group(2).strip()
            return await get_last_event(t1, t2)

    # Fixtures / schedule
    if any(w in msg for w in ["fixture", "schedule", "next match", "upcoming"]):
        for league_name, league_id in LEAGUE_MAP.items():
            if league_name in msg:
                return await get_upcoming_fixtures(league_id)
        # Default to Premier League
        return await get_upcoming_fixtures("4328")

    # Standings / table
    if any(w in msg for w in ["standing", "table", "ranking", "points table", "top of"]):
        for league_name, league_id in LEAGUE_MAP.items():
            if league_name in msg:
                return await get_standings(league_id)
        return await get_standings("4328")

    # Player lookup
    if any(w in msg for w in ["player", "stat", "career", "goals", "wickets", "runs"]):
        import re
        # Look for quoted names or capitalize-word patterns
        m = re.search(r'"([^"]+)"', msg)
        if m:
            return await search_player(m.group(1))

    # Team lookup
    if "team" in msg or "club" in msg or "squad" in msg:
        import re
        m = re.search(r'"([^"]+)"', msg)
        if m:
            return await search_team(m.group(1))

    # No specific live data needed
    return ""
