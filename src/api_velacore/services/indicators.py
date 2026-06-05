from dataclasses import dataclass

from api_velacore.infrastructure.market_data import MarketDataProviderError
from api_velacore.schemas.indicators import (
    IndicatorPoint,
    IndicatorProvider,
    TwelveDataIndicatorAssetType,
)
from api_velacore.schemas.market_data import MarketDataCandle, MarketDataResponse
from api_velacore.services.market_data import (
    TwelveDataMarketDataOptions,
    get_binance_market_data,
    get_twelve_data_market_data,
    get_yahoo_market_data,
)

_DEFAULT_SOURCE_CANDLE_LIMIT = 500
_BINANCE_INTERVAL_BY_COMMON_INTERVAL = {
    "1m": "1m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "1d": "1d",
    "1wk": "1w",
    "1mo": "1M",
}
_TWELVE_DATA_INTERVAL_BY_COMMON_INTERVAL = {
    "1m": "1min",
    "5m": "5min",
    "15m": "15min",
    "30m": "30min",
    "1h": "1h",
    "1d": "1day",
    "1wk": "1week",
    "1mo": "1month",
}


@dataclass(frozen=True)
class EmaIndicatorOptions:
    symbol: str
    period: int
    provider: IndicatorProvider
    range: str | None
    interval: str
    outputsize: int
    limit: int
    asset_type: TwelveDataIndicatorAssetType | None


def get_ema_indicator(*, options: EmaIndicatorOptions) -> list[IndicatorPoint]:
    candles = _fetch_source_candles(options)
    return calculate_ema_points(candles=candles, period=options.period)


def calculate_ema_points(
    *,
    candles: list[MarketDataCandle],
    period: int,
) -> list[IndicatorPoint]:
    if period < 1:
        raise MarketDataProviderError("EMA period must be greater than 0", 422)

    chronological_candles = sorted(candles, key=lambda candle: candle.timestamp)
    if len(chronological_candles) < period:
        raise MarketDataProviderError("Not enough candles to calculate EMA", 422)

    multiplier = 2 / (period + 1)
    seed_candles = chronological_candles[:period]
    ema = sum(candle.close for candle in seed_candles) / period
    points = [
        IndicatorPoint(
            time=chronological_candles[period - 1].timestamp,
            value=ema,
        )
    ]

    for candle in chronological_candles[period:]:
        ema = ((candle.close - ema) * multiplier) + ema
        points.append(IndicatorPoint(time=candle.timestamp, value=ema))

    return points


def _fetch_source_candles(options: EmaIndicatorOptions) -> list[MarketDataCandle]:
    response = _fetch_source_market_data(options)
    return response.candles


def _fetch_source_market_data(options: EmaIndicatorOptions) -> MarketDataResponse:
    if options.provider == "binance":
        if options.period > options.limit:
            raise MarketDataProviderError(
                "Binance source limit must be greater than or equal to EMA period",
                422,
            )
        return get_binance_market_data(
            symbol=options.symbol,
            interval=_binance_interval(options.interval),
            start_time=None,
            end_time=None,
            time_zone=None,
            limit=options.limit,
        )

    if options.provider == "twelve-data":
        if options.period > options.outputsize:
            raise MarketDataProviderError(
                "Twelve Data outputsize must be greater than or equal to EMA period",
                422,
            )
        return get_twelve_data_market_data(
            options=TwelveDataMarketDataOptions(
                symbol=options.symbol,
                interval=_twelve_data_interval(options.interval),
                outputsize=options.outputsize,
                start_date=None,
                end_date=None,
                exchange=None,
                asset_type=options.asset_type,
                prepost=False,
            ),
        )

    return get_yahoo_market_data(
        symbol=options.symbol,
        period=options.range,
        interval=options.interval,
        start=None,
        end=None,
        prepost=False,
        events=None,
    )


def _binance_interval(interval: str) -> str:
    return _BINANCE_INTERVAL_BY_COMMON_INTERVAL.get(interval, interval)


def _twelve_data_interval(interval: str) -> str:
    return _TWELVE_DATA_INTERVAL_BY_COMMON_INTERVAL.get(interval, interval)


def default_source_limit(period: int) -> int:
    return min(max(period * 3, _DEFAULT_SOURCE_CANDLE_LIMIT), 1000)
