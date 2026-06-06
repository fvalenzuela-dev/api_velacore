from collections.abc import Mapping
from typing import Any, NoReturn, cast

import httpx

from api_velacore.schemas.market_data import (
    MarketDataCandle,
    MarketDataResponse,
    TwelveDataEtf,
    TwelveDataEtfsResponse,
    TwelveDataForexPair,
    TwelveDataForexPairsResponse,
    TwelveDataStock,
    TwelveDataStocksResponse,
)

from .constants import TWELVE_DATA_TYPE_BY_ASSET
from .errors import MarketDataProviderError as MarketDataProviderError
from .market_data_common import (
    _parse_twelve_data_datetime,
    _required_string,
    _string_or_none,
)
from .requests import (
    TwelveDataEtfListRequest,
    TwelveDataForexPairsRequest,
    TwelveDataStockListRequest,
    TwelveDataTimeSeriesRequest,
)


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

    def fetch_stocks(
        self,
        request: TwelveDataStockListRequest,
        *,
        timeout: float = 10.0,
    ) -> TwelveDataStocksResponse:
        params = self._build_stock_list_params(request)
        data = self._get_json_from_path("/stocks", params=params, timeout=timeout)
        return self._normalize_stocks(data)

    def fetch_forex_pairs(
        self,
        request: TwelveDataForexPairsRequest,
        *,
        timeout: float = 10.0,
    ) -> TwelveDataForexPairsResponse:
        params = self._build_forex_pairs_params(request)
        data = self._get_json_from_path("/forex_pairs", params=params, timeout=timeout)
        return self._normalize_forex_pairs(data)

    def fetch_etfs(
        self,
        request: TwelveDataEtfListRequest,
        *,
        timeout: float = 10.0,
    ) -> TwelveDataEtfsResponse:
        params = self._build_etf_list_params(request)
        data = self._get_json_from_path("/etf", params=params, timeout=timeout)
        return self._normalize_etfs(data)

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

    def _build_stock_list_params(
        self,
        request: TwelveDataStockListRequest,
    ) -> dict[str, str]:
        params = {
            "exchange": request.exchange,
            "country": request.country,
            "type": request.type,
            "apikey": request.api_key,
        }
        return self._with_optional_params(
            params,
            {
                "symbol": request.symbol.upper()
                if request.symbol is not None
                else None,
                "mic_code": request.mic_code,
            },
        )

    def _build_forex_pairs_params(
        self,
        request: TwelveDataForexPairsRequest,
    ) -> dict[str, str]:
        params = {
            "currency_group": request.currency_group,
            "apikey": request.api_key,
        }
        return self._with_optional_params(
            params,
            {
                "symbol": request.symbol.upper()
                if request.symbol is not None
                else None,
                "currency_base": request.currency_base.upper()
                if request.currency_base is not None
                else None,
                "currency_quote": request.currency_quote.upper()
                if request.currency_quote is not None
                else None,
            },
        )

    def _build_etf_list_params(
        self,
        request: TwelveDataEtfListRequest,
    ) -> dict[str, str]:
        params = {
            "exchange": request.exchange,
            "country": request.country,
            "apikey": request.api_key,
        }
        return self._with_optional_params(
            params,
            {
                "symbol": request.symbol.upper()
                if request.symbol is not None
                else None,
                "mic_code": request.mic_code,
            },
        )

    def _with_optional_params(
        self,
        params: dict[str, str],
        optional_params: Mapping[str, str | None],
    ) -> dict[str, str]:
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
        return self._get_json_from_path(
            "/time_series",
            params=params,
            timeout=timeout,
        )

    def _get_json_from_path(
        self,
        path: str,
        *,
        params: Mapping[str, str | int | bool],
        timeout: float,
    ) -> dict[str, Any]:
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.get(f"{self.base_url}{path}", params=params)
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

    def _normalize_stocks(self, data: Mapping[str, Any]) -> TwelveDataStocksResponse:
        rows = self._extract_listing_rows(data)
        return TwelveDataStocksResponse(
            stocks=[self._normalize_stock(row) for row in rows]
        )

    def _normalize_forex_pairs(
        self,
        data: Mapping[str, Any],
    ) -> TwelveDataForexPairsResponse:
        rows = self._extract_listing_rows(data)
        return TwelveDataForexPairsResponse(
            forex_pairs=[self._normalize_forex_pair(row) for row in rows]
        )

    def _normalize_etfs(self, data: Mapping[str, Any]) -> TwelveDataEtfsResponse:
        rows = self._extract_listing_rows(data)
        return TwelveDataEtfsResponse(etfs=[self._normalize_etf(row) for row in rows])

    def _extract_listing_rows(self, data: Mapping[str, Any]) -> list[Any]:
        self._raise_api_error(data)
        rows = data.get("data")
        if not isinstance(rows, list):
            raise MarketDataProviderError(
                "Twelve Data returned malformed listing data", 502
            )
        return rows

    def _normalize_stock(self, row: object) -> TwelveDataStock:
        typed_row = self._typed_listing_row(row)
        return TwelveDataStock(
            symbol=_required_string(
                typed_row,
                "symbol",
                provider_message="Twelve Data returned malformed listing data",
            ),
            name=_string_or_none(typed_row.get("name")),
            currency=_string_or_none(typed_row.get("currency")),
            exchange=_string_or_none(typed_row.get("exchange")),
            mic_code=_string_or_none(typed_row.get("mic_code")),
            country=_string_or_none(typed_row.get("country")),
            type=_string_or_none(typed_row.get("type")),
        )

    def _normalize_forex_pair(self, row: object) -> TwelveDataForexPair:
        typed_row = self._typed_listing_row(row)
        return TwelveDataForexPair(
            symbol=_required_string(
                typed_row,
                "symbol",
                provider_message="Twelve Data returned malformed listing data",
            ),
            currency_group=_string_or_none(typed_row.get("currency_group")),
            currency_base=_string_or_none(typed_row.get("currency_base")),
            currency_quote=_string_or_none(typed_row.get("currency_quote")),
        )

    def _normalize_etf(self, row: object) -> TwelveDataEtf:
        typed_row = self._typed_listing_row(row)
        return TwelveDataEtf(
            symbol=_required_string(
                typed_row,
                "symbol",
                provider_message="Twelve Data returned malformed listing data",
            ),
            name=_string_or_none(typed_row.get("name")),
            currency=_string_or_none(typed_row.get("currency")),
            exchange=_string_or_none(typed_row.get("exchange")),
            mic_code=_string_or_none(typed_row.get("mic_code")),
            country=_string_or_none(typed_row.get("country")),
            figi_code=_string_or_none(typed_row.get("figi_code")),
            cfi_code=_string_or_none(typed_row.get("cfi_code")),
            isin=_string_or_none(typed_row.get("isin")),
            cusip=_string_or_none(typed_row.get("cusip")),
        )

    def _typed_listing_row(self, row: object) -> Mapping[str, Any]:
        if not isinstance(row, Mapping):
            raise MarketDataProviderError(
                "Twelve Data returned malformed listing data", 502
            )
        return cast(Mapping[str, Any], row)

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
