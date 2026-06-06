import json
from collections.abc import Mapping
from typing import Any, NoReturn, cast

import httpx

from api_velacore.schemas.market_data import (
    BinanceExchangeInfoResponse,
    BinanceExchangeSymbol,
    MarketDataCandle,
    MarketDataResponse,
)

from .errors import MarketDataProviderError as MarketDataProviderError
from .market_data_common import _datetime_from_milliseconds
from .normalization import normalize_binance_exchange_symbol
from .requests import BinanceExchangeInfoRequest, BinanceKlineRequest


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

    def fetch_exchange_info(
        self,
        request: BinanceExchangeInfoRequest,
        *,
        timeout: float = 10.0,
    ) -> BinanceExchangeInfoResponse:
        params = self._build_exchange_info_params(request)
        data = self._get_json_object(
            "/api/v3/exchangeInfo",
            params=params,
            timeout=timeout,
        )
        return self._normalize_exchange_info(data)

    def _build_exchange_info_params(
        self,
        request: BinanceExchangeInfoRequest,
    ) -> dict[str, str | bool]:
        params: dict[str, str | bool] = {
            "showPermissionSets": request.show_permission_sets,
        }
        optional_params = {
            "symbol": request.symbol.upper() if request.symbol is not None else None,
            "symbols": json.dumps([symbol.upper() for symbol in request.symbols])
            if request.symbols
            else None,
            "permissions": json.dumps(list(request.permissions))
            if request.permissions
            else None,
            "symbolStatus": request.symbol_status,
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

    def _get_json_object(
        self,
        path: str,
        *,
        params: Mapping[str, str | bool],
        timeout: float,
    ) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(f"{self.base_url}{path}", params=params)
                response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise MarketDataProviderError("Binance request timed out", 504) from exc
        except httpx.HTTPStatusError as exc:
            self._raise_http_error(exc)
        except httpx.HTTPError as exc:
            raise MarketDataProviderError("Binance request failed", 502) from exc
        return cast(dict[str, Any], response.json())

    def _normalize_exchange_info(
        self,
        data: Mapping[str, Any],
    ) -> BinanceExchangeInfoResponse:
        symbols = data.get("symbols")
        if not isinstance(symbols, list):
            raise MarketDataProviderError(
                "Binance returned malformed exchange info data", 502
            )
        return BinanceExchangeInfoResponse(
            symbols=[self._normalize_exchange_symbol(row) for row in symbols]
        )

    def _normalize_exchange_symbol(self, row: object) -> BinanceExchangeSymbol:
        return normalize_binance_exchange_symbol(row)

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
