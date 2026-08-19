from datetime import UTC, datetime, timedelta

import requests

from lib.market_data.provider import Candle
from lib.schemas import Timeframe
from lib.secrets import get_secret


def _to_oanda_timestamp(dt: datetime) -> str:
    """OANDA wants an RFC3339 UTC string with a literal 'Z' suffix. Naively
    appending "Z" to `dt.isoformat()` is only safe for a *naive* datetime —
    an aware one already ends in an offset like "+00:00", producing an
    invalid double-marked string ("...+00:00Z"). Callers now consistently
    pass timezone-aware UTC datetimes (lib/data.py uses datetime.now(UTC)),
    so this normalizes either case explicitly rather than assuming one.
    """
    if dt.tzinfo is not None:
        dt = dt.astimezone(UTC).replace(tzinfo=None)
    return dt.isoformat() + "Z"

_GRANULARITY_MAP: dict[Timeframe, str] = {
    "15m": "M15",
    "1H": "H1",
    "4H": "H4",
    "1D": "D",
}

_GRANULARITY_SECONDS: dict[Timeframe, int] = {
    "15m": 900,
    "1H": 3600,
    "4H": 14400,
    "1D": 86400,
}

_BASE_URL = {
    "practice": "https://api-fxpractice.oanda.com",
    "live": "https://api-fxtrade.oanda.com",
}

# OANDA caps each candles response at 5000, so a wide (start, end) window at
# a fine granularity (e.g. 15m over 90 days = 8640 candles) needs paging —
# same class of bug as the Binance provider's original 1000-candle cap
# (lib/market_data/binance.py), caught proactively here before hitting it live.
_MAX_CANDLES_PER_REQUEST = 5000


def is_configured() -> bool:
    return bool(get_secret("OANDA_API_KEY"))


class OandaProvider:
    """Requires OANDA_API_KEY (Section 3.3 — free practice/demo account).
    Doubles as the Phase 8 paper-trading broker."""

    name = "oanda"

    def get_candles(
        self, asset: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[Candle]:
        api_key = get_secret("OANDA_API_KEY")
        if not api_key:
            raise RuntimeError("OANDA_API_KEY is not set — see .streamlit/secrets.toml.example")

        env = get_secret("OANDA_ENVIRONMENT", "practice")
        instrument = asset.replace("/", "_")
        url = f"{_BASE_URL[env]}/v3/instruments/{instrument}/candles"
        window = timedelta(seconds=_GRANULARITY_SECONDS[timeframe] * _MAX_CANDLES_PER_REQUEST)

        candles: list[Candle] = []
        cursor = start
        while cursor < end:
            chunk_end = min(cursor + window, end)
            res = requests.get(
                url,
                headers={"Authorization": f"Bearer {api_key}"},
                params={
                    "granularity": _GRANULARITY_MAP[timeframe],
                    "from": _to_oanda_timestamp(cursor),
                    "to": _to_oanda_timestamp(chunk_end),
                    "price": "M",
                },
                timeout=10,
            )
            res.raise_for_status()
            rows = res.json()["candles"]

            candles.extend(
                Candle(
                    time=datetime.fromisoformat(c["time"].replace("Z", "+00:00"))
                    .astimezone(UTC)
                    .replace(tzinfo=None),
                    open=float(c["mid"]["o"]),
                    high=float(c["mid"]["h"]),
                    low=float(c["mid"]["l"]),
                    close=float(c["mid"]["c"]),
                    volume=float(c["volume"]),
                )
                for c in rows
                if c.get("complete", True)
            )

            cursor = chunk_end

        return candles


oanda_provider = OandaProvider()
