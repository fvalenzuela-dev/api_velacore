from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

MarketDataProvider = Literal["yahoo", "binance"]


class MarketDataCandle(BaseModel):
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class MarketDataResponse(BaseModel):
    provider: MarketDataProvider
    symbol: str
    interval: str
    range: str | None = None
    candles: list[MarketDataCandle] = Field(default_factory=list)
