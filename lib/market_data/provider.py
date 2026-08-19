from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol

from lib.schemas import Timeframe


@dataclass
class Candle:
    time: datetime  # naive, but always UTC — see epoch_to_utc_naive()
    open: float
    high: float
    low: float
    close: float
    volume: float


def epoch_to_utc_naive(epoch_seconds: float) -> datetime:
    """Convert a Unix epoch timestamp to a naive UTC datetime.

    `datetime.fromtimestamp(epoch)` without a `tz` argument converts to the
    *server's local timezone*, not UTC — it silently produced a wrong time
    (confirmed a full hour off on a non-UTC test machine) despite the
    Candle.time contract requiring UTC (README_forex.md Section 6.7). It
    happened to look correct in production only because Streamlit Community
    Cloud's containers default to UTC — coincidence, not correctness. Every
    provider should build Candle.time through this function, not
    datetime.fromtimestamp() directly.
    """
    return datetime.fromtimestamp(epoch_seconds, tz=UTC).replace(tzinfo=None)


class MarketDataProvider(Protocol):
    """Every data source (OANDA, Binance, future providers) implements this
    so downstream engines never depend on a specific vendor's response shape."""

    name: str

    def get_candles(
        self, asset: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[Candle]: ...
