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
from api_velacore.services.market_data import TwelveDataMarketDataOptions

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


def _sample_candles() -> list[MarketDataCandle]:
    return [_candle(1, 10.0), _candle(2, 11.0), _candle(3, 12.0)]


def test_ema_endpoint_returns_chart_ready_points(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get_ema_indicator(**kwargs: object) -> list[IndicatorPoint]:
        options = cast(EmaIndicatorOptions, kwargs["options"])
        _CHECK.assertEqual(options.symbol, "AAPL")
        _CHECK.assertEqual(options.provider, "yahoo")
        _CHECK.assertEqual(options.period, 3)
        _CHECK.assertEqual(options.range, "1mo")
        _CHECK.assertEqual(options.interval, "1d")
        _CHECK.assertEqual(options.outputsize, 500)
        _CHECK.assertEqual(options.limit, 500)
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
        "/indicators/ema/AAPL?provider=yahoo&period=3&range=1mo&interval=1d"
    )

    _CHECK.assertEqual(response.status_code, 200)
    _CHECK.assertEqual(
        response.json(),
        [{"time": "2026-01-03T00:00:00Z", "value": 11.0}],
    )


def test_ema_endpoint_uses_default_yahoo_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get_ema_indicator(**kwargs: object) -> list[IndicatorPoint]:
        options = cast(EmaIndicatorOptions, kwargs["options"])
        _CHECK.assertEqual(options.provider, "yahoo")
        _CHECK.assertEqual(options.period, 20)
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


def test_ema_endpoint_accepts_binance_provider_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get_ema_indicator(**kwargs: object) -> list[IndicatorPoint]:
        options = cast(EmaIndicatorOptions, kwargs["options"])
        _CHECK.assertEqual(options.provider, "binance")
        _CHECK.assertEqual(options.limit, 100)
        return [IndicatorPoint(time=datetime(2026, 1, 3, tzinfo=UTC), value=11.0)]

    monkeypatch.setattr(indicator_routes, "get_ema_indicator", fake_get_ema_indicator)
    client = TestClient(app)

    response = client.get("/indicators/ema/BTCUSDT?provider=binance&period=3&limit=100")

    _CHECK.assertEqual(response.status_code, 200)


def test_ema_endpoint_accepts_twelve_data_provider_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get_ema_indicator(**kwargs: object) -> list[IndicatorPoint]:
        options = cast(EmaIndicatorOptions, kwargs["options"])
        _CHECK.assertEqual(options.provider, "twelve-data")
        _CHECK.assertEqual(options.outputsize, 100)
        _CHECK.assertEqual(options.asset_type, "etf")
        return [IndicatorPoint(time=datetime(2026, 1, 3, tzinfo=UTC), value=11.0)]

    monkeypatch.setattr(indicator_routes, "get_ema_indicator", fake_get_ema_indicator)
    client = TestClient(app)

    response = client.get(
        "/indicators/ema/QQQ?provider=twelve-data&period=3&outputsize=100&asset_type=etf"
    )

    _CHECK.assertEqual(response.status_code, 200)


def test_ema_endpoint_rejects_invalid_provider() -> None:
    client = TestClient(app)

    response = client.get("/indicators/ema/AAPL?provider=forex")

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


def test_ema_service_routes_yahoo_provider(
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
            candles=_sample_candles(),
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
            provider="yahoo",
            range="1mo",
            interval="1d",
            outputsize=500,
            limit=500,
            asset_type=None,
        )
    )

    _CHECK.assertEqual(
        points, [IndicatorPoint(time=_candle(3, 12.0).timestamp, value=11.0)]
    )


def test_ema_service_routes_binance_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get_binance_market_data(**kwargs: object) -> MarketDataResponse:
        _CHECK.assertEqual(kwargs["symbol"], "BTCUSDT")
        _CHECK.assertEqual(kwargs["interval"], "1d")
        _CHECK.assertEqual(kwargs["limit"], 100)
        return MarketDataResponse(
            provider="binance",
            symbol="BTCUSDT",
            interval="1d",
            candles=_sample_candles(),
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
            provider="binance",
            range="1mo",
            interval="1d",
            outputsize=500,
            limit=100,
            asset_type=None,
        )
    )

    _CHECK.assertEqual(
        points, [IndicatorPoint(time=_candle(3, 12.0).timestamp, value=11.0)]
    )


def test_ema_service_routes_twelve_data_provider(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get_twelve_data_market_data(**kwargs: object) -> MarketDataResponse:
        options = cast(TwelveDataMarketDataOptions, kwargs["options"])
        _CHECK.assertEqual(options.symbol, "QQQ")
        _CHECK.assertEqual(options.interval, "1day")
        _CHECK.assertEqual(options.outputsize, 100)
        _CHECK.assertEqual(options.asset_type, "etf")
        return MarketDataResponse(
            provider="twelve-data",
            symbol="QQQ",
            interval="1day",
            candles=_sample_candles(),
        )

    monkeypatch.setattr(
        indicator_services,
        "get_twelve_data_market_data",
        fake_get_twelve_data_market_data,
    )

    points = get_ema_indicator(
        options=EmaIndicatorOptions(
            symbol="QQQ",
            period=3,
            provider="twelve-data",
            range="1mo",
            interval="1d",
            outputsize=100,
            limit=500,
            asset_type="etf",
        )
    )

    _CHECK.assertEqual(
        points, [IndicatorPoint(time=_candle(3, 12.0).timestamp, value=11.0)]
    )


def test_ema_service_rejects_binance_period_larger_than_limit() -> None:
    with pytest.raises(MarketDataProviderError) as exc_info:
        get_ema_indicator(
            options=EmaIndicatorOptions(
                symbol="BTCUSDT",
                period=1001,
                provider="binance",
                range="1mo",
                interval="1d",
                outputsize=500,
                limit=1000,
                asset_type=None,
            )
        )

    _CHECK.assertEqual(exc_info.value.status_code, 422)
    _CHECK.assertEqual(
        exc_info.value.message,
        "Binance source limit must be greater than or equal to EMA period",
    )


def test_ema_service_rejects_twelve_data_period_larger_than_outputsize() -> None:
    with pytest.raises(MarketDataProviderError) as exc_info:
        get_ema_indicator(
            options=EmaIndicatorOptions(
                symbol="QQQ",
                period=501,
                provider="twelve-data",
                range="1mo",
                interval="1d",
                outputsize=500,
                limit=500,
                asset_type="etf",
            )
        )

    _CHECK.assertEqual(exc_info.value.status_code, 422)
    _CHECK.assertEqual(
        exc_info.value.message,
        "Twelve Data outputsize must be greater than or equal to EMA period",
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
                provider="yahoo",
                range="1mo",
                interval="1d",
                outputsize=500,
                limit=500,
                asset_type=None,
            )
        )

    _CHECK.assertEqual(exc_info.value.status_code, 502)
    _CHECK.assertEqual(exc_info.value.message, "Yahoo Finance request failed")
