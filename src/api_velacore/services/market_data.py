from api_velacore.core.config import get_settings
from api_velacore.infrastructure.market_data import (
    BINANCE_INTERVALS,
    TWELVE_DATA_ASSET_TYPES,
    TWELVE_DATA_INTERVALS,
    YAHOO_INTERVALS,
    YAHOO_PERIODS,
    BinanceKlineRequest,
    BinanceMarketDataClient,
    MarketDataProviderError,
    TwelveDataMarketDataClient,
    TwelveDataTimeSeriesRequest,
    YahooChartRequest,
    YahooFinanceClient,
)
from api_velacore.schemas.market_data import MarketDataResponse


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


def get_twelve_data_market_data(
    *,
    symbol: str,
    interval: str,
    outputsize: int,
    start_date: str | None,
    end_date: str | None,
    exchange: str | None,
    asset_type: str | None,
    prepost: bool,
    api_key: str | None = None,
    client: TwelveDataMarketDataClient | None = None,
) -> MarketDataResponse:
    if interval not in TWELVE_DATA_INTERVALS:
        raise MarketDataProviderError("Unsupported Twelve Data interval", 422)
    if outputsize < 1 or outputsize > 5000:
        raise MarketDataProviderError(
            "Twelve Data outputsize must be between 1 and 5000", 422
        )
    if start_date is None and end_date is not None:
        raise MarketDataProviderError(
            "Both start_date and end_date are required when using explicit dates",
            422,
        )
    if start_date is not None and end_date is None:
        raise MarketDataProviderError(
            "Both start_date and end_date are required when using explicit dates",
            422,
        )
    if asset_type is not None and asset_type not in TWELVE_DATA_ASSET_TYPES:
        raise MarketDataProviderError("Unsupported Twelve Data asset_type", 422)
    resolved_api_key = api_key or get_settings().twelve_data_api_key
    if not resolved_api_key:
        raise MarketDataProviderError("Twelve Data API key is not configured", 503)
    twelve_data_client = client or TwelveDataMarketDataClient()
    request = TwelveDataTimeSeriesRequest(
        symbol=symbol,
        interval=interval,
        outputsize=outputsize,
        start_date=start_date,
        end_date=end_date,
        exchange=exchange,
        asset_type=asset_type,
        prepost=prepost,
        api_key=resolved_api_key,
    )
    return twelve_data_client.fetch_time_series(request)
