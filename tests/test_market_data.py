import unittest
from datetime import UTC, datetime
from typing import Literal

import pytest
from fastapi.testclient import TestClient

import api_velacore.api.routes.market_data as market_data_routes
from api_velacore.infrastructure.market_data import (
    BinanceMarketDataClient,
    MarketDataProviderError,
    YahooFinanceClient,
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

    result = YahooFinanceClient()._normalize(
        symbol="aapl",
        interval="1d",
        data=payload,
        period="1mo",
    )

    _CHECK.assertEqual(result.provider, "yahoo")
    _CHECK.assertEqual(result.symbol, "AAPL")
    _CHECK.assertEqual(result.range, "1mo")
    _CHECK.assertEqual(result.candles[0].close, 103.0)
