"""Economic Calendar Service (README_forex.md Section 4.10), via Financial
Modeling Prep's free-tier economic_calendar endpoint.

Requires FMP_API_KEY — a free key from financialmodelingprep.com. Not yet
verified against a live key (see README_forex.md Section 11); field mapping
follows FMP's documented response shape as of this writing and may need
adjustment once tested against real data.
"""

import os
from datetime import datetime

import requests

from lib.schemas import EconomicEvent, EventImpact

_BASE_URL = "https://financialmodelingprep.com/api/v3/economic_calendar"

_IMPACT_MAP: dict[str, EventImpact] = {
    "high": "HIGH",
    "medium": "MEDIUM",
    "low": "LOW",
}


def get_calendar(start: datetime, end: datetime) -> list[EconomicEvent]:
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        raise RuntimeError("FMP_API_KEY is not set — see .streamlit/secrets.toml.example")

    res = requests.get(
        _BASE_URL,
        params={
            "from": start.strftime("%Y-%m-%d"),
            "to": end.strftime("%Y-%m-%d"),
            "apikey": api_key,
        },
        timeout=10,
    )
    res.raise_for_status()
    rows = res.json()

    events = []
    for row in rows:
        impact_raw = str(row.get("impact") or "").strip().lower()
        events.append(
            EconomicEvent(
                date=datetime.fromisoformat(row["date"]),
                country=row.get("country", ""),
                event=row.get("event", ""),
                impact=_IMPACT_MAP.get(impact_raw, "LOW"),
                actual=str(row["actual"]) if row.get("actual") is not None else None,
                forecast=str(row["estimate"]) if row.get("estimate") is not None else None,
                previous=str(row["previous"]) if row.get("previous") is not None else None,
            )
        )
    return events
