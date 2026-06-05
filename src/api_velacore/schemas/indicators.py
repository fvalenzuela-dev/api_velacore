from datetime import datetime
from typing import Literal

from pydantic import BaseModel

IndicatorProvider = Literal["yahoo", "binance", "twelve-data"]
TwelveDataIndicatorAssetType = Literal["stock", "etf"]


class IndicatorPoint(BaseModel):
    time: datetime
    value: float
