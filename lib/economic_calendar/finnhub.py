"""Economic Calendar Service (README_forex.md Section 4.10), via Finnhub's
economic calendar endpoint.

NOT usable on Finnhub's free tier — verified live (2026-08-19) against a
real key: `403 "You don't have access to this resource."`. Same pattern as
FMP (Section 11) — requiring an API key is not the same as free-tier
inclusion. Kept here only for anyone with a paid Finnhub plan. The default
provider is now `lib/economic_calendar/static.py` (no API required at all).
Requires FINNHUB_API_KEY.
"""

from datetime import datetime

import requests

from lib.schemas import EconomicEvent, EventImpact
from lib.secrets import get_secret

_BASE_URL = "https://finnhub.io/api/v1/calendar/economic"

_IMPACT_MAP: dict[str, EventImpact] = {
    "high": "HIGH",
    "medium": "MEDIUM",
    "low": "LOW",
}


def get_calendar(start: datetime, end: datetime) -> list[EconomicEvent]:
    api_key = get_secret("FINNHUB_API_KEY")
    if not api_key:
        raise RuntimeError("FINNHUB_API_KEY is not set — see .streamlit/secrets.toml.example")

    res = requests.get(
        _BASE_URL,
        params={
            "from": start.strftime("%Y-%m-%d"),
            "to": end.strftime("%Y-%m-%d"),
            "token": api_key,
        },
        timeout=10,
    )
    res.raise_for_status()
    rows = res.json().get("economicCalendar", [])

    events = []
    for row in rows:
        impact_raw = str(row.get("impact") or "").strip().lower()
        events.append(
            EconomicEvent(
                date=datetime.fromisoformat(row["time"]),
                country=row.get("country", ""),
                event=row.get("event", ""),
                impact=_IMPACT_MAP.get(impact_raw, "LOW"),
                actual=str(row["actual"]) if row.get("actual") is not None else None,
                forecast=str(row["estimate"]) if row.get("estimate") is not None else None,
                previous=str(row["prev"]) if row.get("prev") is not None else None,
            )
        )
    return events
