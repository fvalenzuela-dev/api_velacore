from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, cast

import httpx

from api_velacore.schemas.market_data import MarketDataCandle, MarketDataResponse

BINANCE_INTERVALS = frozenset(
    {
        "1s",
        "1m",
        "3m",
        "5m",
        "15m",
        "30m",
        "1h",
        "2h",
        "4h",
        "6h",
        "8h",
        "12h",
        "1d",
        "3d",
        "1w",
        "1M",
    }
)

YAHOO_INTERVALS = frozenset(
    {
        "1m",
        "2m",
        "5m",
        "15m",
        "30m",
        "60m",
        "90m",
        "1h",
        "1d",
        "5d",
        "1wk",
        "1mo",
        "3mo",
    }
)

YAHOO_PERIODS = frozenset(
    {"1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"}
)


class MarketDataProviderError(Exception):
    def __init__(self, message: str, status_code: int) -> None:
        self.message = message
        self.status_code = status_code
        super().__init__(message)


def _datetime_to_epoch_seconds(value: str) -> int:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        msg = "Dates must use ISO format, for example 2026-01-31"
        raise MarketDataProviderError(msg, 422) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return int(parsed.timestamp())


def _datetime_from_milliseconds(value: int) -> datetime:
    return datetime.fromtimestamp(value / 1000, tz=UTC)


def _datetime_from_seconds(value: int) -> datetime:
    return datetime.fromtimestamp(value, tz=UTC)


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, str | int | float):
        try:
            return float(value)
        except ValueError:
            return None
    return None


class YahooFinanceClient:
    base_url = "https://query1.finance.yahoo.com/v8/finance/chart"

    def fetch_chart(
        self,
        *,
        symbol: str,
        period: str | None,
        interval: str,
        start: str | None,
        end: str | None,
        prepost: bool,
        events: str | None,
        timeout: float = 10.0,
    ) -> MarketDataResponse:
        params: dict[str, str | int | bool] = {
            "interval": interval,
            "includePrePost": prepost,
        }
        if events is not None:
            params["events"] = events
        if start is not None or end is not None:
            if start is None or end is None:
                raise MarketDataProviderError(
                    "Both start and end are required when using explicit dates",
                    422,
                )
            params["period1"] = _datetime_to_epoch_seconds(start)
            params["period2"] = _datetime_to_epoch_seconds(end)
        else:
            params["range"] = period or "1mo"

        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(f"{self.base_url}/{symbol}", params=params)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise MarketDataProviderError(
                "Yahoo Finance request timed out", 504
            ) from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                raise MarketDataProviderError(
                    "Yahoo Finance rate limit exceeded", 429
                ) from exc
            raise MarketDataProviderError("Yahoo Finance request failed", 502) from exc
        except httpx.HTTPError as exc:
            raise MarketDataProviderError("Yahoo Finance request failed", 502) from exc

        data = cast(dict[str, Any], response.json())
        return self._normalize(
            symbol=symbol, interval=interval, data=data, period=period
        )

    def _normalize(
        self,
        *,
        symbol: str,
        interval: str,
        data: Mapping[str, Any],
        period: str | None,
    ) -> MarketDataResponse:
        chart = cast(Mapping[str, Any], data.get("chart", {}))
        error = chart.get("error")
        if error is not None:
            error_data = cast(Mapping[str, Any], error)
            description = str(error_data.get("description", "Yahoo Finance error"))
            raise MarketDataProviderError(description, 404)

        results = cast(list[Any], chart.get("result") or [])
        if not results:
            raise MarketDataProviderError("Yahoo Finance returned no chart data", 404)

        result = cast(Mapping[str, Any], results[0])
        timestamps = cast(list[Any], result.get("timestamp") or [])
        indicators = cast(Mapping[str, Any], result.get("indicators", {}))
        quotes = cast(list[Any], indicators.get("quote") or [])
        if not timestamps or not quotes:
            raise MarketDataProviderError("Yahoo Finance returned no candles", 404)

        quote = cast(Mapping[str, Any], quotes[0])
        opens = cast(list[Any], quote.get("open") or [])
        highs = cast(list[Any], quote.get("high") or [])
        lows = cast(list[Any], quote.get("low") or [])
        closes = cast(list[Any], quote.get("close") or [])
        volumes = cast(list[Any], quote.get("volume") or [])

        candles: list[MarketDataCandle] = []
        for index, timestamp in enumerate(timestamps):
            if not isinstance(timestamp, int):
                continue
            values = (
                _float_or_none(opens[index] if index < len(opens) else None),
                _float_or_none(highs[index] if index < len(highs) else None),
                _float_or_none(lows[index] if index < len(lows) else None),
                _float_or_none(closes[index] if index < len(closes) else None),
                _float_or_none(volumes[index] if index < len(volumes) else None),
            )
            if any(value is None for value in values):
                continue
            open_price, high, low, close, volume = cast(
                tuple[float, float, float, float, float], values
            )
            candles.append(
                MarketDataCandle(
                    timestamp=_datetime_from_seconds(timestamp),
                    open=open_price,
                    high=high,
                    low=low,
                    close=close,
                    volume=volume,
                )
            )

        return MarketDataResponse(
            provider="yahoo",
            symbol=symbol.upper(),
            interval=interval,
            range=period,
            candles=candles,
        )


class BinanceMarketDataClient:
    base_url = "https://api.binance.com"

    def fetch_klines(
        self,
        *,
        symbol: str,
        interval: str,
        start_time: int | None,
        end_time: int | None,
        time_zone: str | None,
        limit: int,
        timeout: float = 10.0,
    ) -> MarketDataResponse:
        params: dict[str, str | int] = {
            "symbol": symbol.upper(),
            "interval": interval,
            "limit": limit,
        }
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time
        if time_zone is not None:
            params["timeZone"] = time_zone

        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(f"{self.base_url}/api/v3/klines", params=params)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise MarketDataProviderError("Binance request timed out", 504) from exc
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 429:
                raise MarketDataProviderError(
                    "Binance rate limit exceeded", 429
                ) from exc
            if exc.response.status_code == 400:
                raise MarketDataProviderError(
                    "Invalid Binance symbol or parameters", 422
                ) from exc
            raise MarketDataProviderError("Binance request failed", 502) from exc
        except httpx.HTTPError as exc:
            raise MarketDataProviderError("Binance request failed", 502) from exc

        rows = cast(list[Any], response.json())
        candles = [self._normalize_row(row) for row in rows]
        return MarketDataResponse(
            provider="binance",
            symbol=symbol.upper(),
            interval=interval,
            candles=candles,
        )

    def _normalize_row(self, row: Any) -> MarketDataCandle:
        values = cast(list[Any], row)
        if len(values) < 6:
            raise MarketDataProviderError("Binance returned malformed kline data", 502)
        try:
            timestamp = int(cast(str | int | float, values[0]))
            return MarketDataCandle(
                timestamp=_datetime_from_milliseconds(timestamp),
                open=float(cast(str | int | float, values[1])),
                high=float(cast(str | int | float, values[2])),
                low=float(cast(str | int | float, values[3])),
                close=float(cast(str | int | float, values[4])),
                volume=float(cast(str | int | float, values[5])),
            )
        except (TypeError, ValueError) as exc:
            raise MarketDataProviderError(
                "Binance returned malformed kline data", 502
            ) from exc
