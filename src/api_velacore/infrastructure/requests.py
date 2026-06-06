from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class YahooChartRequest:
    symbol: str
    period: str | None
    interval: str
    start: str | None
    end: str | None
    prepost: bool
    events: str | None


@dataclass(frozen=True, slots=True)
class BinanceKlineRequest:
    symbol: str
    interval: str
    start_time: int | None
    end_time: int | None
    time_zone: str | None
    limit: int


@dataclass(frozen=True, slots=True)
class BinanceExchangeInfoRequest:
    symbol: str | None
    symbols: tuple[str, ...]
    permissions: tuple[str, ...]
    show_permission_sets: bool
    symbol_status: str | None


@dataclass(frozen=True, slots=True)
class BinanceSymbolSearchRequest:
    q: str
    permissions: tuple[str, ...]
    show_permission_sets: bool
    symbol_status: str | None
    limit: int | None


@dataclass(frozen=True, slots=True)
class TwelveDataTimeSeriesRequest:
    symbol: str
    interval: str
    outputsize: int
    start_date: str | None
    end_date: str | None
    exchange: str | None
    asset_type: str | None
    prepost: bool
    api_key: str


@dataclass(frozen=True, slots=True)
class TwelveDataStockListRequest:
    symbol: str | None
    exchange: str
    mic_code: str | None
    country: str
    type: str
    api_key: str


@dataclass(frozen=True, slots=True)
class TwelveDataForexPairsRequest:
    symbol: str | None
    currency_base: str | None
    currency_quote: str | None
    currency_group: str
    api_key: str


@dataclass(frozen=True, slots=True)
class TwelveDataEtfListRequest:
    symbol: str | None
    exchange: str
    mic_code: str | None
    country: str
    api_key: str


@dataclass(frozen=True, slots=True)
class TwelveDataSymbolSearchRequest:
    symbol: str
    api_key: str
