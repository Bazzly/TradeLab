from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from lib.schemas import Timeframe


@dataclass
class Candle:
    time: datetime  # UTC
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketDataProvider(Protocol):
    """Every data source (OANDA, Binance, future providers) implements this
    so downstream engines never depend on a specific vendor's response shape."""

    name: str

    def get_candles(
        self, asset: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> list[Candle]: ...
