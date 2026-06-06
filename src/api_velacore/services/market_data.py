from dataclasses import dataclass

from api_velacore.core.config import get_settings
from api_velacore.infrastructure.constants import (
    BINANCE_INTERVALS,
    TWELVE_DATA_ASSET_TYPES,
    TWELVE_DATA_INTERVALS,
    YAHOO_INTERVALS,
    YAHOO_PERIODS,
)
from api_velacore.infrastructure.errors import MarketDataProviderError
from api_velacore.infrastructure.market_data import (
    BinanceMarketDataClient,
    TwelveDataMarketDataClient,
    YahooFinanceClient,
)
from api_velacore.infrastructure.requests import (
    BinanceExchangeInfoRequest,
    BinanceKlineRequest,
    BinanceSymbolSearchRequest,
    TwelveDataEtfListRequest,
    TwelveDataForexPairsRequest,
    TwelveDataStockListRequest,
    TwelveDataSymbolSearchRequest,
    TwelveDataTimeSeriesRequest,
    YahooChartRequest,
)
from api_velacore.schemas.market_data import (
    BinanceExchangeInfoResponse,
    BinanceSymbolSearchResponse,
    MarketDataResponse,
    TwelveDataEtfsResponse,
    TwelveDataForexPairsResponse,
    TwelveDataStocksResponse,
    TwelveDataSymbolSearchResponse,
)


def get_yahoo_market_data(
    *,
    symbol: str,
    period: str | None,
    interval: str,
    start: str | None,
    end: str | None,
    prepost: bool,
    events: str | None,
    client: YahooFinanceClient | None = None,
) -> MarketDataResponse:
    if interval not in YAHOO_INTERVALS:
        raise MarketDataProviderError("Unsupported Yahoo interval", 422)
    if period is not None and period not in YAHOO_PERIODS:
        raise MarketDataProviderError("Unsupported Yahoo period", 422)
    if period is not None and (start is not None or end is not None):
        raise MarketDataProviderError(
            "Use either period or start/end, not both",
            422,
        )
    yahoo_client = client or YahooFinanceClient()
    request = YahooChartRequest(
        symbol=symbol,
        period=period,
        interval=interval,
        start=start,
        end=end,
        prepost=prepost,
        events=events,
    )
    return yahoo_client.fetch_chart(request)


def get_binance_market_data(
    *,
    symbol: str,
    interval: str,
    start_time: int | None,
    end_time: int | None,
    time_zone: str | None,
    limit: int,
    client: BinanceMarketDataClient | None = None,
) -> MarketDataResponse:
    if interval not in BINANCE_INTERVALS:
        raise MarketDataProviderError("Unsupported Binance interval", 422)
    if limit < 1 or limit > 1000:
        raise MarketDataProviderError("Binance limit must be between 1 and 1000", 422)
    binance_client = client or BinanceMarketDataClient()
    request = BinanceKlineRequest(
        symbol=symbol,
        interval=interval,
        start_time=start_time,
        end_time=end_time,
        time_zone=time_zone,
        limit=limit,
    )
    return binance_client.fetch_klines(request)


def get_binance_exchange_info(
    *,
    symbol: str | None,
    symbols: list[str] | None,
    permissions: list[str] | None,
    show_permission_sets: bool,
    symbol_status: str | None,
    client: BinanceMarketDataClient | None = None,
) -> BinanceExchangeInfoResponse:
    normalized_symbol = _optional_string(symbol)
    normalized_symbols = _optional_strings(symbols)
    normalized_permissions = _optional_strings(permissions)
    _validate_binance_exchange_info_filters(
        symbol=normalized_symbol,
        symbols=normalized_symbols,
        permissions=normalized_permissions,
    )
    request = BinanceExchangeInfoRequest(
        symbol=normalized_symbol,
        symbols=tuple(normalized_symbols),
        permissions=tuple(normalized_permissions),
        show_permission_sets=show_permission_sets,
        symbol_status=_binance_exchange_info_symbol_status(
            symbol=normalized_symbol,
            symbols=normalized_symbols,
            symbol_status=symbol_status,
        ),
    )
    binance_client = client or BinanceMarketDataClient()
    return binance_client.fetch_exchange_info(request)


@dataclass(frozen=True)
class BinanceSymbolSearchOptions:
    q: str
    permissions: list[str] | None
    show_permission_sets: bool
    symbol_status: str | None
    limit: int | None


def get_binance_symbol_search(
    *,
    options: BinanceSymbolSearchOptions,
    client: BinanceMarketDataClient | None = None,
) -> BinanceSymbolSearchResponse:
    normalized_query = _required_search_query(options.q, "Binance q is required")
    if options.limit is not None and options.limit < 1:
        raise MarketDataProviderError(
            "Binance symbol search limit must be positive",
            422,
        )
    request = BinanceSymbolSearchRequest(
        q=normalized_query,
        permissions=tuple(_optional_strings(options.permissions)),
        show_permission_sets=options.show_permission_sets,
        symbol_status=_optional_string(options.symbol_status),
        limit=options.limit,
    )
    binance_client = client or BinanceMarketDataClient()
    return binance_client.fetch_symbol_search(request)


def _validate_binance_exchange_info_filters(
    *,
    symbol: str | None,
    symbols: list[str],
    permissions: list[str],
) -> None:
    if symbol is not None and symbols:
        raise MarketDataProviderError("Use either symbol or symbols, not both", 422)
    if permissions and (symbol is not None or symbols):
        raise MarketDataProviderError(
            "Use permissions without symbol or symbols filters",
            422,
        )


def _binance_exchange_info_symbol_status(
    *,
    symbol: str | None,
    symbols: list[str],
    symbol_status: str | None,
) -> str | None:
    if symbol is not None or symbols:
        return None
    return _optional_string(symbol_status)


@dataclass(frozen=True)
class TwelveDataMarketDataOptions:
    symbol: str
    interval: str
    outputsize: int
    start_date: str | None
    end_date: str | None
    exchange: str | None
    asset_type: str | None
    prepost: bool


@dataclass(frozen=True)
class TwelveDataStockListOptions:
    symbol: str | None
    exchange: str
    mic_code: str | None
    country: str
    type: str


@dataclass(frozen=True)
class TwelveDataForexPairsOptions:
    symbol: str | None
    currency_base: str | None
    currency_quote: str | None
    currency_group: str


@dataclass(frozen=True)
class TwelveDataEtfListOptions:
    symbol: str | None
    exchange: str
    mic_code: str | None
    country: str


@dataclass(frozen=True)
class TwelveDataSymbolSearchOptions:
    symbol: str


def get_twelve_data_market_data(
    *,
    options: TwelveDataMarketDataOptions,
    api_key: str | None = None,
    client: TwelveDataMarketDataClient | None = None,
) -> MarketDataResponse:
    _validate_twelve_data_options(options)
    resolved_api_key = _resolve_twelve_data_api_key(api_key)
    request = _build_twelve_data_request(options, resolved_api_key)
    twelve_data_client = client or TwelveDataMarketDataClient()
    return twelve_data_client.fetch_time_series(request)


def get_twelve_data_stocks(
    *,
    options: TwelveDataStockListOptions,
    api_key: str | None = None,
    client: TwelveDataMarketDataClient | None = None,
) -> TwelveDataStocksResponse:
    resolved_api_key = _resolve_twelve_data_api_key(api_key)
    request = TwelveDataStockListRequest(
        symbol=_optional_string(options.symbol),
        exchange=options.exchange,
        mic_code=_optional_string(options.mic_code),
        country=options.country,
        type=options.type,
        api_key=resolved_api_key,
    )
    twelve_data_client = client or TwelveDataMarketDataClient()
    return twelve_data_client.fetch_stocks(request)


def get_twelve_data_forex_pairs(
    *,
    options: TwelveDataForexPairsOptions,
    api_key: str | None = None,
    client: TwelveDataMarketDataClient | None = None,
) -> TwelveDataForexPairsResponse:
    resolved_api_key = _resolve_twelve_data_api_key(api_key)
    request = TwelveDataForexPairsRequest(
        symbol=_optional_string(options.symbol),
        currency_base=_optional_string(options.currency_base),
        currency_quote=_optional_string(options.currency_quote),
        currency_group=options.currency_group,
        api_key=resolved_api_key,
    )
    twelve_data_client = client or TwelveDataMarketDataClient()
    return twelve_data_client.fetch_forex_pairs(request)


def get_twelve_data_etfs(
    *,
    options: TwelveDataEtfListOptions,
    api_key: str | None = None,
    client: TwelveDataMarketDataClient | None = None,
) -> TwelveDataEtfsResponse:
    resolved_api_key = _resolve_twelve_data_api_key(api_key)
    request = TwelveDataEtfListRequest(
        symbol=_optional_string(options.symbol),
        exchange=options.exchange,
        mic_code=_optional_string(options.mic_code),
        country=options.country,
        api_key=resolved_api_key,
    )
    twelve_data_client = client or TwelveDataMarketDataClient()
    return twelve_data_client.fetch_etfs(request)


def get_twelve_data_symbol_search(
    *,
    options: TwelveDataSymbolSearchOptions,
    api_key: str | None = None,
    client: TwelveDataMarketDataClient | None = None,
) -> TwelveDataSymbolSearchResponse:
    resolved_symbol = _required_search_query(
        options.symbol,
        "Twelve Data symbol search query is required",
    )
    resolved_api_key = _resolve_twelve_data_api_key(api_key)
    request = TwelveDataSymbolSearchRequest(
        symbol=resolved_symbol,
        api_key=resolved_api_key,
    )
    twelve_data_client = client or TwelveDataMarketDataClient()
    return twelve_data_client.fetch_symbol_search(request)


def _validate_twelve_data_options(options: TwelveDataMarketDataOptions) -> None:
    if options.interval not in TWELVE_DATA_INTERVALS:
        raise MarketDataProviderError("Unsupported Twelve Data interval", 422)
    if options.outputsize < 1 or options.outputsize > 5000:
        raise MarketDataProviderError(
            "Twelve Data outputsize must be between 1 and 5000", 422
        )
    if (options.start_date is None) != (options.end_date is None):
        raise MarketDataProviderError(
            "Both start_date and end_date are required when using explicit dates",
            422,
        )
    if (
        options.asset_type is not None
        and options.asset_type not in TWELVE_DATA_ASSET_TYPES
    ):
        raise MarketDataProviderError("Unsupported Twelve Data asset_type", 422)


def _resolve_twelve_data_api_key(api_key: str | None) -> str:
    resolved_api_key = api_key or get_settings().twelve_data_api_key
    if not resolved_api_key:
        raise MarketDataProviderError("Twelve Data API key is not configured", 503)
    return resolved_api_key


def _build_twelve_data_request(
    options: TwelveDataMarketDataOptions,
    api_key: str,
) -> TwelveDataTimeSeriesRequest:
    return TwelveDataTimeSeriesRequest(
        symbol=options.symbol,
        interval=options.interval,
        outputsize=options.outputsize,
        start_date=options.start_date,
        end_date=options.end_date,
        exchange=options.exchange,
        asset_type=options.asset_type,
        prepost=options.prepost,
        api_key=api_key,
    )


def _required_search_query(value: str, message: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise MarketDataProviderError(message, 422)
    return stripped


def _optional_string(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _optional_strings(values: list[str] | None) -> list[str]:
    if values is None:
        return []
    return [stripped for value in values if (stripped := value.strip())]
