import unittest
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any, Literal

import httpx
import pytest
from fastapi.testclient import TestClient

import api_velacore.api.routes.market_data as market_data_routes
from api_velacore.infrastructure.market_data import (
    BinanceKlineRequest,
    BinanceMarketDataClient,
    MarketDataProviderError,
    YahooChartRequest,
    YahooFinanceClient,
    _datetime_to_epoch_seconds,
    _float_at,
    _float_or_none,
)
from api_velacore.main import app
from api_velacore.schemas.market_data import MarketDataCandle, MarketDataResponse
from api_velacore.services.market_data import (
    get_binance_market_data,
    get_yahoo_market_data,
)

_CHECK = unittest.TestCase()


def _sample_response(
    provider: Literal["yahoo", "binance"],
    symbol: str,
) -> MarketDataResponse:
    return MarketDataResponse(
        provider=provider,
        symbol=symbol,
        interval="1d",
        range="1mo" if provider == "yahoo" else None,
        candles=[
            MarketDataCandle(
                timestamp=datetime(2026, 5, 1, tzinfo=UTC),
                open=100.0,
                high=105.0,
                low=99.0,
                close=103.0,
                volume=1234.0,
            )
        ],
    )


def test_yahoo_endpoint_returns_normalized_market_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get_yahoo_market_data(**kwargs: object) -> MarketDataResponse:
        _CHECK.assertEqual(kwargs["symbol"], "AAPL")
        _CHECK.assertEqual(kwargs["period"], "1mo")
        _CHECK.assertEqual(kwargs["interval"], "1d")
        return _sample_response("yahoo", "AAPL")

    monkeypatch.setattr(
        market_data_routes,
        "get_yahoo_market_data",
        fake_get_yahoo_market_data,
    )
    client = TestClient(app)

    response = client.get("/market-data/yahoo/AAPL?period=1mo&interval=1d")

    _CHECK.assertEqual(response.status_code, 200)
    body = response.json()
    _CHECK.assertEqual(body["provider"], "yahoo")
    _CHECK.assertEqual(body["symbol"], "AAPL")
    _CHECK.assertEqual(body["candles"][0]["close"], 103.0)


def test_binance_endpoint_returns_normalized_market_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get_binance_market_data(**kwargs: object) -> MarketDataResponse:
        _CHECK.assertEqual(kwargs["symbol"], "BTCUSDT")
        _CHECK.assertEqual(kwargs["interval"], "1h")
        _CHECK.assertEqual(kwargs["limit"], 100)
        return _sample_response("binance", "BTCUSDT")

    monkeypatch.setattr(
        market_data_routes,
        "get_binance_market_data",
        fake_get_binance_market_data,
    )
    client = TestClient(app)

    response = client.get("/market-data/binance/BTCUSDT?interval=1h&limit=100")

    _CHECK.assertEqual(response.status_code, 200)
    body = response.json()
    _CHECK.assertEqual(body["provider"], "binance")
    _CHECK.assertEqual(body["symbol"], "BTCUSDT")
    _CHECK.assertEqual(body["candles"][0]["volume"], 1234.0)


def test_provider_errors_are_mapped_to_http_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get_yahoo_market_data(**kwargs: object) -> MarketDataResponse:
        raise MarketDataProviderError("Unsupported Yahoo interval", 422)

    monkeypatch.setattr(
        market_data_routes,
        "get_yahoo_market_data",
        fake_get_yahoo_market_data,
    )
    client = TestClient(app)

    response = client.get("/market-data/yahoo/AAPL?interval=2h")

    _CHECK.assertEqual(response.status_code, 422)
    _CHECK.assertEqual(response.json(), {"detail": "Unsupported Yahoo interval"})


def test_yahoo_service_validates_period_and_interval() -> None:
    try:
        get_yahoo_market_data(
            symbol="AAPL",
            period="bad",
            interval="1d",
            start=None,
            end=None,
            prepost=False,
            events=None,
            client=YahooFinanceClient(),
        )
    except MarketDataProviderError as exc:
        _CHECK.assertEqual(exc.status_code, 422)
        _CHECK.assertEqual(exc.message, "Unsupported Yahoo period")
    else:
        _CHECK.fail("Expected MarketDataProviderError")


def test_binance_service_validates_limit() -> None:
    try:
        get_binance_market_data(
            symbol="BTCUSDT",
            interval="1h",
            start_time=None,
            end_time=None,
            time_zone=None,
            limit=1001,
            client=BinanceMarketDataClient(),
        )
    except MarketDataProviderError as exc:
        _CHECK.assertEqual(exc.status_code, 422)
        _CHECK.assertEqual(exc.message, "Binance limit must be between 1 and 1000")
    else:
        _CHECK.fail("Expected MarketDataProviderError")


def test_yahoo_service_requires_start_and_end_together() -> None:
    try:
        get_yahoo_market_data(
            symbol="AAPL",
            period=None,
            interval="1d",
            start="2026-01-01",
            end=None,
            prepost=False,
            events=None,
            client=YahooFinanceClient(),
        )
    except MarketDataProviderError as exc:
        _CHECK.assertEqual(exc.status_code, 422)
        _CHECK.assertEqual(
            exc.message,
            "Both start and end are required when using explicit dates",
        )
    else:
        _CHECK.fail("Expected MarketDataProviderError")


def test_binance_client_rejects_malformed_numeric_values() -> None:
    try:
        BinanceMarketDataClient()._normalize_row(
            [1499040000000, "bad", "0.80000000", "0.01575800", "0.01577100", "1"]
        )
    except MarketDataProviderError as exc:
        _CHECK.assertEqual(exc.status_code, 502)
        _CHECK.assertEqual(exc.message, "Binance returned malformed kline data")
    else:
        _CHECK.fail("Expected MarketDataProviderError")


def test_binance_client_normalizes_kline_rows() -> None:
    candle = BinanceMarketDataClient()._normalize_row(
        [
            1499040000000,
            "0.01634790",
            "0.80000000",
            "0.01575800",
            "0.01577100",
            "148976.11427815",
        ]
    )

    _CHECK.assertEqual(candle.timestamp, datetime(2017, 7, 3, tzinfo=UTC))
    _CHECK.assertEqual(candle.open, 0.01634790)
    _CHECK.assertEqual(candle.high, 0.8)
    _CHECK.assertEqual(candle.low, 0.015758)
    _CHECK.assertEqual(candle.close, 0.015771)
    _CHECK.assertEqual(candle.volume, 148976.11427815)


def test_yahoo_client_normalizes_chart_payload() -> None:
    payload = {
        "chart": {
            "result": [
                {
                    "timestamp": [1777593600],
                    "indicators": {
                        "quote": [
                            {
                                "open": [100.0],
                                "high": [105.0],
                                "low": [99.0],
                                "close": [103.0],
                                "volume": [1234],
                            }
                        ]
                    },
                }
            ],
            "error": None,
        }
    }

    request = YahooChartRequest(
        symbol="aapl",
        period="1mo",
        interval="1d",
        start=None,
        end=None,
        prepost=False,
        events=None,
    )
    result = YahooFinanceClient()._normalize(request=request, data=payload)

    _CHECK.assertEqual(result.provider, "yahoo")
    _CHECK.assertEqual(result.symbol, "AAPL")
    _CHECK.assertEqual(result.range, "1mo")
    _CHECK.assertEqual(result.candles[0].close, 103.0)


class StubYahooFinanceClient(YahooFinanceClient):
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload
        self.seen_symbol = ""
        self.seen_params: Mapping[str, str | int | bool] = {}
        self.seen_timeout = 0.0

    def _get_json(
        self,
        symbol: str,
        *,
        params: Mapping[str, str | int | bool],
        timeout: float,
    ) -> dict[str, Any]:
        self.seen_symbol = symbol
        self.seen_params = params
        self.seen_timeout = timeout
        return self.payload


class StubBinanceMarketDataClient(BinanceMarketDataClient):
    def __init__(self, rows: list[Any]) -> None:
        self.rows = rows
        self.seen_params: Mapping[str, str | int] = {}
        self.seen_timeout = 0.0

    def _get_json_rows(
        self,
        *,
        params: Mapping[str, str | int],
        timeout: float,
    ) -> list[Any]:
        self.seen_params = params
        self.seen_timeout = timeout
        return self.rows


def _http_status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://example.test")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError("provider failed", request=request, response=response)


def test_market_data_low_level_conversion_helpers() -> None:
    _CHECK.assertEqual(_datetime_to_epoch_seconds("2026-01-01"), 1767225600)
    _CHECK.assertEqual(_datetime_to_epoch_seconds("2026-01-01T00:00:00Z"), 1767225600)
    _CHECK.assertEqual(_float_or_none("1.5"), 1.5)
    _CHECK.assertIsNone(_float_or_none("bad"))
    _CHECK.assertIsNone(_float_or_none(object()))
    _CHECK.assertEqual(_float_at(["2.5"], 0), 2.5)
    _CHECK.assertIsNone(_float_at([], 0))


def test_datetime_helper_rejects_invalid_iso_dates() -> None:
    try:
        _datetime_to_epoch_seconds("not-a-date")
    except MarketDataProviderError as exc:
        _CHECK.assertEqual(exc.status_code, 422)
        _CHECK.assertEqual(
            exc.message, "Dates must use ISO format, for example 2026-01-31"
        )
    else:
        _CHECK.fail("Expected MarketDataProviderError")


def test_yahoo_build_params_supports_events_and_explicit_dates() -> None:
    request = YahooChartRequest(
        symbol="AAPL",
        period=None,
        interval="1d",
        start="2026-01-01",
        end="2026-01-02",
        prepost=True,
        events="div|split|earn",
    )

    params = YahooFinanceClient()._build_params(request)

    _CHECK.assertEqual(params["interval"], "1d")
    _CHECK.assertEqual(params["includePrePost"], True)
    _CHECK.assertEqual(params["events"], "div|split|earn")
    _CHECK.assertEqual(params["period1"], 1767225600)
    _CHECK.assertEqual(params["period2"], 1767312000)


def test_yahoo_fetch_chart_uses_params_and_normalizes_response() -> None:
    payload = {
        "chart": {
            "result": [
                {
                    "timestamp": [1777593600, "invalid", 1777680000],
                    "indicators": {
                        "quote": [
                            {
                                "open": [100.0, 1.0, None],
                                "high": [105.0, 1.0, 2.0],
                                "low": [99.0, 1.0, 1.0],
                                "close": [103.0, 1.0, 1.5],
                                "volume": [1234, 1, 2],
                            }
                        ]
                    },
                }
            ],
            "error": None,
        }
    }
    client = StubYahooFinanceClient(payload)
    request = YahooChartRequest(
        symbol="AAPL",
        period="1mo",
        interval="1d",
        start=None,
        end=None,
        prepost=False,
        events=None,
    )

    response = client.fetch_chart(request, timeout=3.0)

    _CHECK.assertEqual(client.seen_symbol, "AAPL")
    _CHECK.assertEqual(client.seen_params["range"], "1mo")
    _CHECK.assertEqual(client.seen_timeout, 3.0)
    _CHECK.assertEqual(len(response.candles), 1)
    _CHECK.assertEqual(response.candles[0].close, 103.0)


def test_yahoo_normalization_rejects_error_and_empty_payloads() -> None:
    client = YahooFinanceClient()
    request = YahooChartRequest("AAPL", "1mo", "1d", None, None, False, None)
    error_payload = {"chart": {"result": None, "error": {"description": "No data"}}}

    try:
        client._normalize(request=request, data=error_payload)
    except MarketDataProviderError as exc:
        _CHECK.assertEqual(exc.status_code, 404)
        _CHECK.assertEqual(exc.message, "No data")
    else:
        _CHECK.fail("Expected MarketDataProviderError")

    try:
        client._normalize(request=request, data={"chart": {"result": []}})
    except MarketDataProviderError as exc:
        _CHECK.assertEqual(exc.status_code, 404)
        _CHECK.assertEqual(exc.message, "Yahoo Finance returned no chart data")
    else:
        _CHECK.fail("Expected MarketDataProviderError")

    try:
        client._normalize(
            request=request, data={"chart": {"result": [{"timestamp": []}]}}
        )
    except MarketDataProviderError as exc:
        _CHECK.assertEqual(exc.status_code, 404)
        _CHECK.assertEqual(exc.message, "Yahoo Finance returned no candles")
    else:
        _CHECK.fail("Expected MarketDataProviderError")


def test_provider_http_error_mapping() -> None:
    try:
        YahooFinanceClient()._raise_http_error(_http_status_error(429))
    except MarketDataProviderError as exc:
        _CHECK.assertEqual(exc.status_code, 429)
        _CHECK.assertEqual(exc.message, "Yahoo Finance rate limit exceeded")
    else:
        _CHECK.fail("Expected MarketDataProviderError")

    try:
        BinanceMarketDataClient()._raise_http_error(_http_status_error(400))
    except MarketDataProviderError as exc:
        _CHECK.assertEqual(exc.status_code, 422)
        _CHECK.assertEqual(exc.message, "Invalid Binance symbol or parameters")
    else:
        _CHECK.fail("Expected MarketDataProviderError")

    try:
        BinanceMarketDataClient()._raise_http_error(_http_status_error(429))
    except MarketDataProviderError as exc:
        _CHECK.assertEqual(exc.status_code, 429)
        _CHECK.assertEqual(exc.message, "Binance rate limit exceeded")
    else:
        _CHECK.fail("Expected MarketDataProviderError")


def test_binance_fetch_klines_uses_params_and_normalizes_response() -> None:
    client = StubBinanceMarketDataClient(
        [[1499040000000, "1", "2", "0.5", "1.5", "10"]]
    )
    request = BinanceKlineRequest(
        symbol="btcusdt",
        interval="1h",
        start_time=1,
        end_time=2,
        time_zone="0",
        limit=10,
    )

    response = client.fetch_klines(request, timeout=4.0)

    _CHECK.assertEqual(client.seen_params["symbol"], "BTCUSDT")
    _CHECK.assertEqual(client.seen_params["startTime"], 1)
    _CHECK.assertEqual(client.seen_params["endTime"], 2)
    _CHECK.assertEqual(client.seen_params["timeZone"], "0")
    _CHECK.assertEqual(client.seen_timeout, 4.0)
    _CHECK.assertEqual(response.candles[0].close, 1.5)


def test_binance_build_params_omits_empty_optional_values() -> None:
    request = BinanceKlineRequest("ETHUSDT", "1d", None, None, None, 500)

    params = BinanceMarketDataClient()._build_params(request)

    _CHECK.assertEqual(params, {"symbol": "ETHUSDT", "interval": "1d", "limit": 500})


def test_binance_client_rejects_short_rows() -> None:
    try:
        BinanceMarketDataClient()._normalize_row([1, "1"])
    except MarketDataProviderError as exc:
        _CHECK.assertEqual(exc.status_code, 502)
        _CHECK.assertEqual(exc.message, "Binance returned malformed kline data")
    else:
        _CHECK.fail("Expected MarketDataProviderError")
