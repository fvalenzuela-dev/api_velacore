from api_velacore.infrastructure.market_data import (
    BINANCE_INTERVALS,
    YAHOO_INTERVALS,
    YAHOO_PERIODS,
    BinanceKlineRequest,
    BinanceMarketDataClient,
    MarketDataProviderError,
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
