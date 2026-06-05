from datetime import datetime
from typing import Literal

from pydantic import BaseModel

IndicatorAssetType = Literal["equity", "etf", "crypto"]


class IndicatorPoint(BaseModel):
    time: datetime
    value: float
