from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

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
    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    symbol: str
    base_asset: str = Field(alias="baseAsset")
    quote_asset: str = Field(alias="quoteAsset")
    status: str
    permissions: list[str] = Field(default_factory=list)
    permission_sets: list[list[str]] = Field(
        default_factory=list,
        alias="permissionSets",
    )
    is_spot_trading_allowed: bool | None = Field(
        default=None,
        alias="isSpotTradingAllowed",
    )
    is_margin_trading_allowed: bool | None = Field(
        default=None,
        alias="isMarginTradingAllowed",
    )
    order_types: list[str] = Field(default_factory=list, alias="orderTypes")


class BinanceExchangeInfoResponse(BaseModel):
    provider: Literal["binance"] = "binance"
    symbols: list[BinanceExchangeSymbol] = Field(default_factory=list)


class BinanceSymbolSearchResponse(BaseModel):
    provider: Literal["binance"] = "binance"
    symbols: list[BinanceExchangeSymbol] = Field(default_factory=list)


class TwelveDataSymbolSearchResult(BaseModel):
    symbol: str
    name: str | None = None
    instrument_name: str | None = None
    exchange: str | None = None
    mic_code: str | None = None
    country: str | None = None
    currency: str | None = None
    type: str | None = None


class TwelveDataSymbolSearchResponse(BaseModel):
    provider: Literal["twelve-data"] = "twelve-data"
    symbols: list[TwelveDataSymbolSearchResult] = Field(default_factory=list)


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
