from collections.abc import Mapping
from typing import Any, NoReturn, cast

import httpx

from api_velacore.schemas.market_data import MarketDataCandle, MarketDataResponse

from .errors import MarketDataProviderError as MarketDataProviderError
from .market_data_common import (
    _datetime_from_seconds,
    _datetime_to_epoch_seconds,
    _float_at,
)
from .requests import YahooChartRequest


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
