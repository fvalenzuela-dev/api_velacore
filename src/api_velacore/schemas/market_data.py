from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

MarketDataProvider = Literal["yahoo", "binance", "twelve-data"]


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


class BinanceExchangeSymbol(BaseModel):
    symbol: str
    baseAsset: str
    quoteAsset: str
    status: str
    permissions: list[str] = Field(default_factory=list)
    permissionSets: list[list[str]] = Field(default_factory=list)
    isSpotTradingAllowed: bool | None = None
    isMarginTradingAllowed: bool | None = None
    orderTypes: list[str] = Field(default_factory=list)


class BinanceExchangeInfoResponse(BaseModel):
    provider: Literal["binance"] = "binance"
    symbols: list[BinanceExchangeSymbol] = Field(default_factory=list)


class TwelveDataStock(BaseModel):
    symbol: str
    name: str | None = None
    currency: str | None = None
    exchange: str | None = None
    mic_code: str | None = None
    country: str | None = None
    type: str | None = None


class TwelveDataStocksResponse(BaseModel):
    provider: Literal["twelve-data"] = "twelve-data"
    stocks: list[TwelveDataStock] = Field(default_factory=list)


class TwelveDataForexPair(BaseModel):
    symbol: str
    currency_group: str | None = None
    currency_base: str | None = None
    currency_quote: str | None = None


class TwelveDataForexPairsResponse(BaseModel):
    provider: Literal["twelve-data"] = "twelve-data"
    forex_pairs: list[TwelveDataForexPair] = Field(default_factory=list)


class TwelveDataEtf(BaseModel):
    symbol: str
    name: str | None = None
    currency: str | None = None
    exchange: str | None = None
    mic_code: str | None = None
    country: str | None = None
    figi_code: str | None = None
    cfi_code: str | None = None
    isin: str | None = None
    cusip: str | None = None


class TwelveDataEtfsResponse(BaseModel):
    provider: Literal["twelve-data"] = "twelve-data"
    etfs: list[TwelveDataEtf] = Field(default_factory=list)
