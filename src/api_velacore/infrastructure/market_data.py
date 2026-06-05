from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, NoReturn, cast

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

TWELVE_DATA_INTERVALS = frozenset(
    {
        "1min",
        "5min",
        "15min",
        "30min",
        "45min",
        "1h",
        "2h",
        "4h",
        "1day",
        "1week",
        "1month",
    }
)

TWELVE_DATA_ASSET_TYPES = frozenset({"stock", "etf"})
TWELVE_DATA_TYPE_BY_ASSET = {
    "stock": "Common Stock",
    "etf": "ETF",
}


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


class MarketDataProviderError(Exception):
    def __init__(self, message: str, status_code: int) -> None:
        """Create a normalized market data provider error."""
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


def _parse_twelve_data_datetime(value: object) -> datetime:
    if not isinstance(value, str):
        raise MarketDataProviderError(
            "Twelve Data returned malformed time series data", 502
        )
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MarketDataProviderError(
            "Twelve Data returned malformed time series data", 502
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, str | int | float):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _float_at(values: list[Any], index: int) -> float | None:
    if index >= len(values):
        return None
    return _float_or_none(values[index])


class YahooFinanceClient:
    base_url = "https://query1.finance.yahoo.com/v8/finance/chart"

    def fetch_chart(
        self,
        request: YahooChartRequest,
        *,
        timeout: float = 10.0,
    ) -> MarketDataResponse:
        params = self._build_params(request)
        data = self._get_json(request.symbol, params=params, timeout=timeout)
        return self._normalize(request=request, data=data)

    def _build_params(self, request: YahooChartRequest) -> dict[str, str | int | bool]:
        params: dict[str, str | int | bool] = {
            "interval": request.interval,
            "includePrePost": request.prepost,
        }
        if request.events is not None:
            params["events"] = request.events
        if request.start is None and request.end is None:
            params["range"] = request.period or "1mo"
            return params
        if request.start is None or request.end is None:
            raise MarketDataProviderError(
                "Both start and end are required when using explicit dates",
                422,
            )
        params["period1"] = _datetime_to_epoch_seconds(request.start)
        params["period2"] = _datetime_to_epoch_seconds(request.end)
        return params

    def _get_json(
        self,
        symbol: str,
        *,
        params: Mapping[str, str | int | bool],
        timeout: float,
    ) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(f"{self.base_url}/{symbol}", params=params)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise MarketDataProviderError(
                "Yahoo Finance request timed out", 504
            ) from exc
        except httpx.HTTPStatusError as exc:
            self._raise_http_error(exc)
        except httpx.HTTPError as exc:
            raise MarketDataProviderError("Yahoo Finance request failed", 502) from exc
        return cast(dict[str, Any], response.json())

    def _raise_http_error(self, exc: httpx.HTTPStatusError) -> NoReturn:
        if exc.response.status_code == 429:
            raise MarketDataProviderError(
                "Yahoo Finance rate limit exceeded", 429
            ) from exc
        raise MarketDataProviderError("Yahoo Finance request failed", 502) from exc

    def _normalize(
        self,
        *,
        request: YahooChartRequest,
        data: Mapping[str, Any],
    ) -> MarketDataResponse:
        result = self._extract_result(data)
        quote = self._extract_quote(result)
        timestamps = cast(list[Any], result.get("timestamp") or [])
        candles = self._build_candles(timestamps=timestamps, quote=quote)
        return MarketDataResponse(
            provider="yahoo",
            symbol=request.symbol.upper(),
            interval=request.interval,
            range=request.period,
            candles=candles,
        )

    def _extract_result(self, data: Mapping[str, Any]) -> Mapping[str, Any]:
        chart = cast(Mapping[str, Any], data.get("chart", {}))
        self._raise_chart_error(chart)
        results = cast(list[Any], chart.get("result") or [])
        if not results:
            raise MarketDataProviderError("Yahoo Finance returned no chart data", 404)
        return cast(Mapping[str, Any], results[0])

    def _raise_chart_error(self, chart: Mapping[str, Any]) -> None:
        error = chart.get("error")
        if error is None:
            return
        error_data = cast(Mapping[str, Any], error)
        description = str(error_data.get("description", "Yahoo Finance error"))
        raise MarketDataProviderError(description, 404)

    def _extract_quote(self, result: Mapping[str, Any]) -> Mapping[str, Any]:
        timestamps = cast(list[Any], result.get("timestamp") or [])
        indicators = cast(Mapping[str, Any], result.get("indicators", {}))
        quotes = cast(list[Any], indicators.get("quote") or [])
        if not timestamps or not quotes:
            raise MarketDataProviderError("Yahoo Finance returned no candles", 404)
        return cast(Mapping[str, Any], quotes[0])

    def _build_candles(
        self,
        *,
        timestamps: list[Any],
        quote: Mapping[str, Any],
    ) -> list[MarketDataCandle]:
        candles: list[MarketDataCandle] = []
        for index, timestamp in enumerate(timestamps):
            candle = self._build_candle(index=index, timestamp=timestamp, quote=quote)
            if candle is not None:
                candles.append(candle)
        return candles

    def _build_candle(
        self,
        *,
        index: int,
        timestamp: object,
        quote: Mapping[str, Any],
    ) -> MarketDataCandle | None:
        if not isinstance(timestamp, int):
            return None
        values = self._quote_values(index=index, quote=quote)
        if values is None:
            return None
        open_price, high, low, close, volume = values
        return MarketDataCandle(
            timestamp=_datetime_from_seconds(timestamp),
            open=open_price,
            high=high,
            low=low,
            close=close,
            volume=volume,
        )

    def _quote_values(
        self,
        *,
        index: int,
        quote: Mapping[str, Any],
    ) -> tuple[float, float, float, float, float] | None:
        values = (
            _float_at(cast(list[Any], quote.get("open") or []), index),
            _float_at(cast(list[Any], quote.get("high") or []), index),
            _float_at(cast(list[Any], quote.get("low") or []), index),
            _float_at(cast(list[Any], quote.get("close") or []), index),
            _float_at(cast(list[Any], quote.get("volume") or []), index),
        )
        if any(value is None for value in values):
            return None
        return cast(tuple[float, float, float, float, float], values)


class BinanceMarketDataClient:
    base_url = "https://api.binance.com"

    def fetch_klines(
        self,
        request: BinanceKlineRequest,
        *,
        timeout: float = 10.0,
    ) -> MarketDataResponse:
        params = self._build_params(request)
        rows = self._get_json_rows(params=params, timeout=timeout)
        return MarketDataResponse(
            provider="binance",
            symbol=request.symbol.upper(),
            interval=request.interval,
            candles=[self._normalize_row(row) for row in rows],
        )

    def _build_params(self, request: BinanceKlineRequest) -> dict[str, str | int]:
        params: dict[str, str | int] = {
            "symbol": request.symbol.upper(),
            "interval": request.interval,
            "limit": request.limit,
        }
        optional_params = {
            "startTime": request.start_time,
            "endTime": request.end_time,
            "timeZone": request.time_zone,
        }
        for key, value in optional_params.items():
            if value is not None:
                params[key] = value
        return params

    def _get_json_rows(
        self,
        *,
        params: Mapping[str, str | int],
        timeout: float,
    ) -> list[Any]:
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(f"{self.base_url}/api/v3/klines", params=params)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise MarketDataProviderError("Binance request timed out", 504) from exc
        except httpx.HTTPStatusError as exc:
            self._raise_http_error(exc)
        except httpx.HTTPError as exc:
            raise MarketDataProviderError("Binance request failed", 502) from exc
        return cast(list[Any], response.json())

    def _raise_http_error(self, exc: httpx.HTTPStatusError) -> NoReturn:
        if exc.response.status_code == 429:
            raise MarketDataProviderError("Binance rate limit exceeded", 429) from exc
        if exc.response.status_code == 400:
            raise MarketDataProviderError(
                "Invalid Binance symbol or parameters", 422
            ) from exc
        raise MarketDataProviderError("Binance request failed", 502) from exc

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


class TwelveDataMarketDataClient:
    base_url = "https://api.twelvedata.com"

    def fetch_time_series(
        self,
        request: TwelveDataTimeSeriesRequest,
        *,
        timeout: float = 10.0,
    ) -> MarketDataResponse:
        params = self._build_params(request)
        data = self._get_json(params=params, timeout=timeout)
        return self._normalize(request=request, data=data)

    def _build_params(
        self,
        request: TwelveDataTimeSeriesRequest,
    ) -> dict[str, str | int | bool]:
        params: dict[str, str | int | bool] = {
            "symbol": request.symbol.upper(),
            "interval": request.interval,
            "outputsize": request.outputsize,
            "prepost": request.prepost,
            "apikey": request.api_key,
        }
        optional_params = {
            "start_date": request.start_date,
            "end_date": request.end_date,
            "exchange": request.exchange,
            "type": self._provider_type(request.asset_type),
        }
        for key, value in optional_params.items():
            if value is not None:
                params[key] = value
        return params

    def _provider_type(self, asset_type: str | None) -> str | None:
        if asset_type is None:
            return None
        return TWELVE_DATA_TYPE_BY_ASSET[asset_type]

    def _get_json(
        self,
        *,
        params: Mapping[str, str | int | bool],
        timeout: float,
    ) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(f"{self.base_url}/time_series", params=params)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            message = "Twelve Data request timed out"
            raise MarketDataProviderError(message, 504) from exc
        except httpx.HTTPStatusError as exc:
            self._raise_http_error(exc)
        except httpx.HTTPError as exc:
            raise MarketDataProviderError("Twelve Data request failed", 502) from exc
        return cast(dict[str, Any], response.json())

    def _raise_http_error(self, exc: httpx.HTTPStatusError) -> NoReturn:
        if exc.response.status_code == 429:
            raise MarketDataProviderError(
                "Twelve Data rate limit exceeded", 429
            ) from exc
        if exc.response.status_code in {400, 401, 403, 404}:
            raise MarketDataProviderError(
                "Invalid Twelve Data symbol, API key, or parameters", 422
            ) from exc
        raise MarketDataProviderError("Twelve Data request failed", 502) from exc

    def _normalize(
        self,
        *,
        request: TwelveDataTimeSeriesRequest,
        data: Mapping[str, Any],
    ) -> MarketDataResponse:
        self._raise_api_error(data)
        meta = cast(Mapping[str, Any], data.get("meta", {}))
        values = cast(list[Any], data.get("values") or [])
        if not values:
            raise MarketDataProviderError("Twelve Data returned no candles", 404)
        symbol = str(meta.get("symbol", request.symbol)).upper()
        interval = str(meta.get("interval", request.interval))
        return MarketDataResponse(
            provider="twelve-data",
            symbol=symbol,
            interval=interval,
            candles=[self._normalize_row(row) for row in values],
        )

    def _raise_api_error(self, data: Mapping[str, Any]) -> None:
        if data.get("status") != "error":
            return
        message = str(data.get("message", "Twelve Data request failed"))
        code_value = data.get("code", 0)
        try:
            code = int(cast(int | str, code_value) or 0)
        except (TypeError, ValueError):
            code = 0
        status_code = 429 if code == 429 else 422
        raise MarketDataProviderError(message, status_code)

    def _normalize_row(self, row: Any) -> MarketDataCandle:
        if not isinstance(row, Mapping):
            raise MarketDataProviderError(
                "Twelve Data returned malformed time series data", 502
            )
        try:
            return MarketDataCandle(
                timestamp=_parse_twelve_data_datetime(row.get("datetime")),
                open=float(cast(str | int | float, row.get("open"))),
                high=float(cast(str | int | float, row.get("high"))),
                low=float(cast(str | int | float, row.get("low"))),
                close=float(cast(str | int | float, row.get("close"))),
                volume=float(cast(str | int | float, row.get("volume"))),
            )
        except (TypeError, ValueError) as exc:
            raise MarketDataProviderError(
                "Twelve Data returned malformed time series data", 502
            ) from exc
