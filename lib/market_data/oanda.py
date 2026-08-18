import os
from datetime import datetime

import requests

from lib.market_data.provider import Candle
from lib.schemas import Timeframe

_GRANULARITY_MAP: dict[Timeframe, str] = {
    "15m": "M15",
    "1H": "H1",
    "4H": "H4",
    "1D": "D",
}

_BASE_URL = {
    "practice": "https://api-fxpractice.oanda.com",
    "live": "https://api-fxtrade.oanda.com",
}


class OandaProvider:
    """Requires OANDA_API_KEY (Section 3.3 — free practice/demo account).
    Doubles as the Phase 8 paper-trading broker."""

    name = "oanda"

    def get_candles(
        self, asset: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[Candle]:
        api_key = os.environ.get("OANDA_API_KEY")
        if not api_key:
            raise RuntimeError("OANDA_API_KEY is not set — see .streamlit/secrets.toml.example")

        env = os.environ.get("OANDA_ENVIRONMENT", "practice")
        instrument = asset.replace("/", "_")
        url = f"{_BASE_URL[env]}/v3/instruments/{instrument}/candles"

        res = requests.get(
            url,
            headers={"Authorization": f"Bearer {api_key}"},
            params={
                "granularity": _GRANULARITY_MAP[timeframe],
                "from": start.isoformat() + "Z",
                "to": end.isoformat() + "Z",
                "price": "M",
            },
            timeout=10,
        )
        res.raise_for_status()

        return [
            Candle(
                time=datetime.fromisoformat(c["time"].replace("Z", "+00:00")),
                open=float(c["mid"]["o"]),
                high=float(c["mid"]["h"]),
                low=float(c["mid"]["l"]),
                close=float(c["mid"]["c"]),
                volume=float(c["volume"]),
            )
            for c in res.json()["candles"]
        ]


oanda_provider = OandaProvider()
