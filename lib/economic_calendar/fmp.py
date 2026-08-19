"""Economic Calendar Service (README_forex.md Section 4.10), via Financial
Modeling Prep's economic-calendar endpoint.

NOT usable on FMP's free tier — verified live (2026-08-19): the endpoint
returns `402 Restricted Endpoint`, i.e. it requires a paid plan. Kept here,
correctly pointed at FMP's current `/stable/` API (the old `/v3/` path is a
retired legacy endpoint that also 403s), only for anyone who has or wants a
paid FMP plan. The default provider is `lib/economic_calendar/finnhub.py`.
Requires FMP_API_KEY.
"""

from datetime import datetime

import requests

from lib.schemas import EconomicEvent, EventImpact
from lib.secrets import get_secret

_BASE_URL = "https://financialmodelingprep.com/stable/economic-calendar"

_IMPACT_MAP: dict[str, EventImpact] = {
    "high": "HIGH",
    "medium": "MEDIUM",
    "low": "LOW",
}


def get_calendar(start: datetime, end: datetime) -> list[EconomicEvent]:
    api_key = get_secret("FMP_API_KEY")
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
