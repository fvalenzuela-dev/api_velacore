import unittest
from datetime import UTC, datetime, timedelta
from typing import cast

import pytest
from fastapi.testclient import TestClient

import api_velacore.api.routes.indicators as indicator_routes
import api_velacore.services.indicators as indicator_services
from api_velacore.infrastructure.market_data import MarketDataProviderError
from api_velacore.main import app
from api_velacore.schemas.indicators import IndicatorPoint
from api_velacore.schemas.market_data import MarketDataCandle, MarketDataResponse
from api_velacore.services.indicators import (
    EmaIndicatorOptions,
    calculate_ema_points,
    get_ema_indicator,
)

_CHECK = unittest.TestCase()


def _candle(day: int, close: float) -> MarketDataCandle:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=day - 1)
    return MarketDataCandle(
        timestamp=timestamp,
        open=close - 1,
        high=close + 1,
        low=close - 2,
        close=close,
        volume=1000.0,
    )


def test_ema_endpoint_returns_chart_ready_points(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get_ema_indicator(**kwargs: object) -> list[IndicatorPoint]:
        options = cast(EmaIndicatorOptions, kwargs["options"])
        _CHECK.assertEqual(options.symbol, "AAPL")
        _CHECK.assertEqual(options.period, 3)
        _CHECK.assertEqual(options.asset_type, "equity")
        _CHECK.assertEqual(options.range, "1mo")
        _CHECK.assertEqual(options.interval, "1d")
        return [
            IndicatorPoint(
                time=datetime(2026, 1, 3, tzinfo=UTC),
                value=11.0,
            )
        ]

    monkeypatch.setattr(
        indicator_routes,
        "get_ema_indicator",
        fake_get_ema_indicator,
    )
    client = TestClient(app)

    response = client.get(
        "/indicators/ema/AAPL?period=3&asset_type=equity&range=1mo&interval=1d"
    )

    _CHECK.assertEqual(response.status_code, 200)
    _CHECK.assertEqual(
        response.json(),
        [{"time": "2026-01-03T00:00:00Z", "value": 11.0}],
    )


def test_ema_endpoint_uses_default_period_and_asset_routing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get_ema_indicator(**kwargs: object) -> list[IndicatorPoint]:
        options = cast(EmaIndicatorOptions, kwargs["options"])
        _CHECK.assertEqual(options.period, 20)
        _CHECK.assertIsNone(options.asset_type)
        _CHECK.assertEqual(options.range, "1mo")
        _CHECK.assertEqual(options.interval, "1d")
        return [
            IndicatorPoint(
                time=datetime(2026, 1, 20, tzinfo=UTC),
                value=20.0,
            )
        ]

    monkeypatch.setattr(
        indicator_routes,
        "get_ema_indicator",
        fake_get_ema_indicator,
    )
    client = TestClient(app)

    response = client.get("/indicators/ema/AAPL")

    _CHECK.assertEqual(response.status_code, 200)
    _CHECK.assertEqual(
        response.json(),
        [{"time": "2026-01-20T00:00:00Z", "value": 20.0}],
    )


def test_ema_endpoint_rejects_invalid_asset_type() -> None:
    client = TestClient(app)

    response = client.get("/indicators/ema/AAPL?asset_type=forex")

    _CHECK.assertEqual(response.status_code, 422)


def test_ema_endpoint_maps_provider_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get_ema_indicator(**kwargs: object) -> list[IndicatorPoint]:
        raise MarketDataProviderError("Not enough candles to calculate EMA", 422)

    monkeypatch.setattr(
        indicator_routes,
        "get_ema_indicator",
        fake_get_ema_indicator,
    )
    client = TestClient(app)

    response = client.get("/indicators/ema/AAPL?period=20")

    _CHECK.assertEqual(response.status_code, 422)
    _CHECK.assertEqual(
        response.json(), {"detail": "Not enough candles to calculate EMA"}
    )


def test_ema_endpoint_rejects_invalid_period() -> None:
    client = TestClient(app)

    response = client.get("/indicators/ema/AAPL?period=0")

    _CHECK.assertEqual(response.status_code, 422)


def test_calculate_ema_points_uses_close_prices_and_omits_warmup() -> None:
    candles = [
        _candle(1, 10.0),
        _candle(2, 11.0),
        _candle(3, 12.0),
        _candle(4, 13.0),
        _candle(5, 14.0),
    ]

    points = calculate_ema_points(candles=candles, period=3)

    _CHECK.assertEqual(
        [point.time for point in points],
        [candles[2].timestamp, candles[3].timestamp, candles[4].timestamp],
    )
    _CHECK.assertEqual([point.value for point in points], [11.0, 12.0, 13.0])


def test_calculate_ema_points_sorts_candles_chronologically() -> None:
    candles = [_candle(3, 12.0), _candle(1, 10.0), _candle(2, 11.0)]

    points = calculate_ema_points(candles=candles, period=3)

    _CHECK.assertEqual(
        points, [IndicatorPoint(time=_candle(3, 12.0).timestamp, value=11.0)]
    )


def test_calculate_ema_points_rejects_invalid_period() -> None:
    with pytest.raises(MarketDataProviderError) as exc_info:
        calculate_ema_points(candles=[_candle(1, 10.0)], period=0)

    _CHECK.assertEqual(exc_info.value.status_code, 422)
    _CHECK.assertEqual(exc_info.value.message, "EMA period must be greater than 0")


def test_calculate_ema_points_rejects_insufficient_data() -> None:
    with pytest.raises(MarketDataProviderError) as exc_info:
        calculate_ema_points(candles=[_candle(1, 10.0), _candle(2, 11.0)], period=3)

    _CHECK.assertEqual(exc_info.value.status_code, 422)
    _CHECK.assertEqual(exc_info.value.message, "Not enough candles to calculate EMA")


def test_ema_service_routes_equity_to_yahoo_market_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get_yahoo_market_data(**kwargs: object) -> MarketDataResponse:
        _CHECK.assertEqual(kwargs["symbol"], "AAPL")
        _CHECK.assertEqual(kwargs["period"], "1mo")
        _CHECK.assertEqual(kwargs["interval"], "1d")
        return MarketDataResponse(
            provider="yahoo",
            symbol="AAPL",
            interval="1d",
            range="1mo",
            candles=[_candle(1, 10.0), _candle(2, 11.0), _candle(3, 12.0)],
        )

    monkeypatch.setattr(
        indicator_services,
        "get_yahoo_market_data",
        fake_get_yahoo_market_data,
    )

    points = get_ema_indicator(
        options=EmaIndicatorOptions(
            symbol="AAPL",
            period=3,
            asset_type="equity",
            range="1mo",
            interval="1d",
        )
    )

    _CHECK.assertEqual(
        points, [IndicatorPoint(time=_candle(3, 12.0).timestamp, value=11.0)]
    )


def test_ema_service_routes_etf_to_yahoo_market_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get_yahoo_market_data(**kwargs: object) -> MarketDataResponse:
        _CHECK.assertEqual(kwargs["symbol"], "QQQ")
        _CHECK.assertEqual(kwargs["period"], "3mo")
        _CHECK.assertEqual(kwargs["interval"], "1d")
        return MarketDataResponse(
            provider="yahoo",
            symbol="QQQ",
            interval="1d",
            range="3mo",
            candles=[_candle(1, 10.0), _candle(2, 11.0), _candle(3, 12.0)],
        )

    monkeypatch.setattr(
        indicator_services,
        "get_yahoo_market_data",
        fake_get_yahoo_market_data,
    )

    points = get_ema_indicator(
        options=EmaIndicatorOptions(
            symbol="QQQ",
            period=3,
            asset_type="etf",
            range="3mo",
            interval="1d",
        )
    )

    _CHECK.assertEqual(
        points, [IndicatorPoint(time=_candle(3, 12.0).timestamp, value=11.0)]
    )


def test_ema_service_routes_crypto_to_binance_market_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get_binance_market_data(**kwargs: object) -> MarketDataResponse:
        _CHECK.assertEqual(kwargs["symbol"], "BTCUSDT")
        _CHECK.assertEqual(kwargs["interval"], "1d")
        _CHECK.assertEqual(kwargs["limit"], 500)
        return MarketDataResponse(
            provider="binance",
            symbol="BTCUSDT",
            interval="1d",
            candles=[_candle(1, 10.0), _candle(2, 11.0), _candle(3, 12.0)],
        )

    monkeypatch.setattr(
        indicator_services,
        "get_binance_market_data",
        fake_get_binance_market_data,
    )

    points = get_ema_indicator(
        options=EmaIndicatorOptions(
            symbol="BTCUSDT",
            period=3,
            asset_type="crypto",
            range="1mo",
            interval="1d",
        )
    )

    _CHECK.assertEqual(
        points, [IndicatorPoint(time=_candle(3, 12.0).timestamp, value=11.0)]
    )


def test_ema_service_preserves_provider_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get_yahoo_market_data(**kwargs: object) -> MarketDataResponse:
        raise MarketDataProviderError("Yahoo Finance request failed", 502)

    monkeypatch.setattr(
        indicator_services,
        "get_yahoo_market_data",
        fake_get_yahoo_market_data,
    )

    with pytest.raises(MarketDataProviderError) as exc_info:
        get_ema_indicator(
            options=EmaIndicatorOptions(
                symbol="AAPL",
                period=3,
                asset_type="equity",
                range="1mo",
                interval="1d",
            )
        )

    _CHECK.assertEqual(exc_info.value.status_code, 502)
    _CHECK.assertEqual(exc_info.value.message, "Yahoo Finance request failed")
