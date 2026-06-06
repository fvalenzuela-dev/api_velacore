import unittest
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, cast

import httpx
import pytest
from fastapi.testclient import TestClient
from starlette.routing import Route

import api_velacore.api.routes.market_data as market_data_routes
from api_velacore.core.config import get_settings
from api_velacore.infrastructure.errors import MarketDataProviderError
from api_velacore.infrastructure.market_data import (
    BinanceMarketDataClient,
    TwelveDataMarketDataClient,
    YahooFinanceClient,
    _datetime_to_epoch_seconds,
    _float_at,
    _float_or_none,
)
from api_velacore.infrastructure.requests import (
    BinanceExchangeInfoRequest,
    BinanceKlineRequest,
    TwelveDataEtfListRequest,
    TwelveDataForexPairsRequest,
    TwelveDataStockListRequest,
    TwelveDataTimeSeriesRequest,
    YahooChartRequest,
)
from api_velacore.main import app
from api_velacore.schemas.market_data import (
    BinanceExchangeInfoResponse,
    BinanceExchangeSymbol,
    MarketDataCandle,
    MarketDataResponse,
    TwelveDataEtf,
    TwelveDataEtfsResponse,
    TwelveDataForexPair,
    TwelveDataForexPairsResponse,
    TwelveDataStock,
    TwelveDataStocksResponse,
)
from api_velacore.services.market_data import (
    TwelveDataEtfListOptions,
    TwelveDataForexPairsOptions,
    TwelveDataMarketDataOptions,
    TwelveDataStockListOptions,
    get_binance_exchange_info,
    get_binance_market_data,
    get_twelve_data_etfs,
    get_twelve_data_forex_pairs,
    get_twelve_data_market_data,
    get_twelve_data_stocks,
    get_yahoo_market_data,
)

_CHECK = unittest.TestCase()


def _twelve_data_options(
    *,
    interval: str = "1day",
    outputsize: int = 10,
    start_date: str | None = None,
    end_date: str | None = None,
    asset_type: str | None = "stock",
) -> TwelveDataMarketDataOptions:
    return TwelveDataMarketDataOptions(
        symbol="AAPL",
        interval=interval,
        outputsize=outputsize,
        start_date=start_date,
        end_date=end_date,
        exchange=None,
        asset_type=asset_type,
        prepost=False,
    )


def _sample_response(
    provider: Literal["yahoo", "binance", "twelve-data"],
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


def _sample_binance_exchange_info_response() -> BinanceExchangeInfoResponse:
    return BinanceExchangeInfoResponse(
        symbols=[
            BinanceExchangeSymbol(
                symbol="BTCUSDT",
                baseAsset="BTC",
                quoteAsset="USDT",
                status="TRADING",
                permissions=["SPOT"],
                permissionSets=[["SPOT"]],
                isSpotTradingAllowed=True,
                isMarginTradingAllowed=False,
                orderTypes=["LIMIT", "MARKET"],
            )
        ]
    )


def _sample_twelve_data_stocks_response() -> TwelveDataStocksResponse:
    return TwelveDataStocksResponse(
        stocks=[
            TwelveDataStock(
                symbol="AAPL",
                name="Apple Inc",
                currency="USD",
                exchange="NASDAQ",
                mic_code="XNAS",
                country="United States",
                type="Common Stock",
            )
        ]
    )


def _sample_twelve_data_forex_pairs_response() -> TwelveDataForexPairsResponse:
    return TwelveDataForexPairsResponse(
        forex_pairs=[
            TwelveDataForexPair(
                symbol="EUR/USD",
                currency_group="Major",
                currency_base="Euro",
                currency_quote="US Dollar",
            )
        ]
    )


def _sample_twelve_data_etfs_response() -> TwelveDataEtfsResponse:
    return TwelveDataEtfsResponse(
        etfs=[
            TwelveDataEtf(
                symbol="SPY",
                name="SPDR S&P 500 ETF Trust",
                currency="USD",
                exchange="NYSE",
                mic_code="XNYS",
                country="United States",
                figi_code="BBG000BDTBL9",
                cfi_code="CEOJLS",
                isin="US78462F1030",
                cusip="78462F103",
            )
        ]
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


def test_twelve_data_endpoint_returns_normalized_market_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get_twelve_data_market_data(**kwargs: object) -> MarketDataResponse:
        options = kwargs["options"]
        _CHECK.assertIsInstance(options, TwelveDataMarketDataOptions)
        typed_options = cast(TwelveDataMarketDataOptions, options)
        _CHECK.assertEqual(typed_options.symbol, "QQQ")
        _CHECK.assertEqual(typed_options.interval, "1day")
        _CHECK.assertEqual(typed_options.outputsize, 10)
        _CHECK.assertEqual(typed_options.asset_type, "etf")
        return _sample_response("twelve-data", "QQQ")

    monkeypatch.setattr(
        market_data_routes,
        "get_twelve_data_market_data",
        fake_get_twelve_data_market_data,
    )
    client = TestClient(app)

    response = client.get(
        "/market-data/twelve-data/QQQ?interval=1day&outputsize=10&asset_type=etf"
    )

    _CHECK.assertEqual(response.status_code, 200)
    body = response.json()
    _CHECK.assertEqual(body["provider"], "twelve-data")
    _CHECK.assertEqual(body["symbol"], "QQQ")
    _CHECK.assertEqual(body["candles"][0]["open"], 100.0)


def test_binance_exchange_info_endpoint_uses_defaults_and_returns_symbols(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get_binance_exchange_info(**kwargs: object) -> BinanceExchangeInfoResponse:
        _CHECK.assertIsNone(kwargs["symbol"])
        _CHECK.assertIsNone(kwargs["symbols"])
        _CHECK.assertIsNone(kwargs["permissions"])
        _CHECK.assertEqual(kwargs["show_permission_sets"], False)
        _CHECK.assertEqual(kwargs["symbol_status"], "TRADING")
        return _sample_binance_exchange_info_response()

    monkeypatch.setattr(
        market_data_routes,
        "get_binance_exchange_info",
        fake_get_binance_exchange_info,
    )
    client = TestClient(app)

    response = client.get("/market-data/binance/exchange-info")

    _CHECK.assertEqual(response.status_code, 200)
    body = response.json()
    _CHECK.assertEqual(body["provider"], "binance")
    _CHECK.assertEqual(body["symbols"][0]["symbol"], "BTCUSDT")
    _CHECK.assertEqual(body["symbols"][0]["baseAsset"], "BTC")


def test_binance_exchange_info_endpoint_forwards_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get_binance_exchange_info(**kwargs: object) -> BinanceExchangeInfoResponse:
        _CHECK.assertIsNone(kwargs["symbol"])
        _CHECK.assertEqual(kwargs["symbols"], ["BTCUSDT", "ETHUSDT"])
        _CHECK.assertIsNone(kwargs["permissions"])
        _CHECK.assertEqual(kwargs["show_permission_sets"], False)
        _CHECK.assertEqual(kwargs["symbol_status"], "BREAK")
        return _sample_binance_exchange_info_response()

    monkeypatch.setattr(
        market_data_routes,
        "get_binance_exchange_info",
        fake_get_binance_exchange_info,
    )
    client = TestClient(app)

    response = client.get(
        "/market-data/binance/exchange-info"
        "?symbols=BTCUSDT&symbols=ETHUSDT"
        "&showPermissionSets=false&symbolStatus=BREAK"
    )

    _CHECK.assertEqual(response.status_code, 200)


def test_twelve_data_stocks_endpoint_uses_defaults_and_returns_normalized_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get_twelve_data_stocks(**kwargs: object) -> TwelveDataStocksResponse:
        options = cast(TwelveDataStockListOptions, kwargs["options"])
        _CHECK.assertIsNone(options.symbol)
        _CHECK.assertEqual(options.exchange, "NASDAQ")
        _CHECK.assertIsNone(options.mic_code)
        _CHECK.assertEqual(options.country, "United States")
        _CHECK.assertEqual(options.type, "Common Stock")
        return _sample_twelve_data_stocks_response()

    monkeypatch.setattr(
        market_data_routes,
        "get_twelve_data_stocks",
        fake_get_twelve_data_stocks,
    )
    client = TestClient(app)

    response = client.get("/market-data/twelve-data/stocks")

    _CHECK.assertEqual(response.status_code, 200)
    body = response.json()
    _CHECK.assertEqual(body["provider"], "twelve-data")
    _CHECK.assertEqual(body["stocks"][0]["symbol"], "AAPL")
    _CHECK.assertEqual(body["stocks"][0]["mic_code"], "XNAS")


def test_twelve_data_forex_pairs_endpoint_forwards_filters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get_twelve_data_forex_pairs(
        **kwargs: object,
    ) -> TwelveDataForexPairsResponse:
        options = cast(TwelveDataForexPairsOptions, kwargs["options"])
        _CHECK.assertEqual(options.symbol, "EUR/USD")
        _CHECK.assertEqual(options.currency_base, "EUR")
        _CHECK.assertEqual(options.currency_quote, "USD")
        _CHECK.assertEqual(options.currency_group, "Minor")
        return _sample_twelve_data_forex_pairs_response()

    monkeypatch.setattr(
        market_data_routes,
        "get_twelve_data_forex_pairs",
        fake_get_twelve_data_forex_pairs,
    )
    client = TestClient(app)

    response = client.get(
        "/market-data/twelve-data/forex-pairs"
        "?symbol=EUR/USD&currency_base=EUR&currency_quote=USD&currency_group=Minor"
    )

    _CHECK.assertEqual(response.status_code, 200)
    body = response.json()
    _CHECK.assertEqual(body["forex_pairs"][0]["currency_base"], "Euro")


def test_twelve_data_etfs_endpoint_uses_defaults_and_returns_normalized_list(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get_twelve_data_etfs(**kwargs: object) -> TwelveDataEtfsResponse:
        options = cast(TwelveDataEtfListOptions, kwargs["options"])
        _CHECK.assertIsNone(options.symbol)
        _CHECK.assertEqual(options.exchange, "NYSE")
        _CHECK.assertIsNone(options.mic_code)
        _CHECK.assertEqual(options.country, "United States")
        return _sample_twelve_data_etfs_response()

    monkeypatch.setattr(
        market_data_routes,
        "get_twelve_data_etfs",
        fake_get_twelve_data_etfs,
    )
    client = TestClient(app)

    response = client.get("/market-data/twelve-data/etfs")

    _CHECK.assertEqual(response.status_code, 200)
    body = response.json()
    _CHECK.assertEqual(body["etfs"][0]["symbol"], "SPY")
    _CHECK.assertEqual(body["etfs"][0]["figi_code"], "BBG000BDTBL9")


def test_twelve_data_listing_endpoints_return_missing_api_key_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("VELACORE_TWELVE_DATA_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    try:
        client = TestClient(app)
        for path in (
            "/market-data/twelve-data/stocks",
            "/market-data/twelve-data/forex-pairs",
            "/market-data/twelve-data/etfs",
        ):
            response = client.get(path)
            _CHECK.assertEqual(response.status_code, 503)
            _CHECK.assertEqual(
                response.json(), {"detail": "Twelve Data API key is not configured"}
            )
    finally:
        get_settings.cache_clear()


def test_static_listing_routes_are_not_captured_by_dynamic_symbol_routes() -> None:
    paths = [route.path for route in app.routes if isinstance(route, Route)]

    _CHECK.assertLess(
        paths.index("/market-data/binance/exchange-info"),
        paths.index("/market-data/binance/{symbol}"),
    )
    _CHECK.assertLess(
        paths.index("/market-data/twelve-data/stocks"),
        paths.index("/market-data/twelve-data/{symbol}"),
    )
    _CHECK.assertLess(
        paths.index("/market-data/twelve-data/forex-pairs"),
        paths.index("/market-data/twelve-data/{symbol}"),
    )
    _CHECK.assertLess(
        paths.index("/market-data/twelve-data/etfs"),
        paths.index("/market-data/twelve-data/{symbol}"),
    )


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


def test_twelve_data_service_rejects_unsupported_interval() -> None:
    try:
        get_twelve_data_market_data(
            options=_twelve_data_options(interval="1d"),
            api_key="test-key",
            client=TwelveDataMarketDataClient(),
        )
    except MarketDataProviderError as exc:
        _CHECK.assertEqual(exc.status_code, 422)
        _CHECK.assertEqual(exc.message, "Unsupported Twelve Data interval")
    else:
        _CHECK.fail("Expected MarketDataProviderError")


def test_twelve_data_service_rejects_invalid_outputsize() -> None:
    try:
        get_twelve_data_market_data(
            options=_twelve_data_options(outputsize=5001),
            api_key="test-key",
            client=TwelveDataMarketDataClient(),
        )
    except MarketDataProviderError as exc:
        _CHECK.assertEqual(exc.status_code, 422)
        _CHECK.assertEqual(
            exc.message, "Twelve Data outputsize must be between 1 and 5000"
        )
    else:
        _CHECK.fail("Expected MarketDataProviderError")


def test_twelve_data_service_requires_start_and_end_dates_together() -> None:
    try:
        get_twelve_data_market_data(
            options=_twelve_data_options(start_date="2026-01-01"),
            api_key="test-key",
            client=TwelveDataMarketDataClient(),
        )
    except MarketDataProviderError as exc:
        _CHECK.assertEqual(exc.status_code, 422)
        _CHECK.assertEqual(
            exc.message,
            "Both start_date and end_date are required when using explicit dates",
        )
    else:
        _CHECK.fail("Expected MarketDataProviderError")


def test_twelve_data_service_rejects_unsupported_asset_type() -> None:
    try:
        get_twelve_data_market_data(
            options=_twelve_data_options(asset_type="fund"),
            api_key="test-key",
            client=TwelveDataMarketDataClient(),
        )
    except MarketDataProviderError as exc:
        _CHECK.assertEqual(exc.status_code, 422)
        _CHECK.assertEqual(exc.message, "Unsupported Twelve Data asset_type")
    else:
        _CHECK.fail("Expected MarketDataProviderError")


def test_twelve_data_service_requires_api_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("VELACORE_TWELVE_DATA_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    try:
        _assert_twelve_data_service_requires_api_key()
    finally:
        get_settings.cache_clear()


def test_twelve_data_listing_services_require_api_key(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("VELACORE_TWELVE_DATA_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    try:
        _assert_twelve_data_listing_services_require_api_key()
    finally:
        get_settings.cache_clear()


def _assert_twelve_data_listing_services_require_api_key() -> None:
    service_calls: list[Callable[[], object]] = [
        lambda: get_twelve_data_stocks(
            options=TwelveDataStockListOptions(
                symbol=None,
                exchange="NASDAQ",
                mic_code=None,
                country="United States",
                type="Common Stock",
            ),
            api_key=None,
            client=TwelveDataMarketDataClient(),
        ),
        lambda: get_twelve_data_forex_pairs(
            options=TwelveDataForexPairsOptions(
                symbol=None,
                currency_base=None,
                currency_quote=None,
                currency_group="Major",
            ),
            api_key=None,
            client=TwelveDataMarketDataClient(),
        ),
        lambda: get_twelve_data_etfs(
            options=TwelveDataEtfListOptions(
                symbol=None,
                exchange="NYSE",
                mic_code=None,
                country="United States",
            ),
            api_key=None,
            client=TwelveDataMarketDataClient(),
        ),
    ]
    for service_call in service_calls:
        try:
            service_call()
        except MarketDataProviderError as exc:
            _CHECK.assertEqual(exc.status_code, 503)
            _CHECK.assertEqual(exc.message, "Twelve Data API key is not configured")
        else:
            _CHECK.fail("Expected MarketDataProviderError")


def test_binance_exchange_info_service_validates_exclusive_symbol_filters() -> None:
    invalid_cases: list[tuple[str | None, list[str] | None, list[str] | None, str]] = [
        (
            "BTCUSDT",
            ["ETHUSDT"],
            None,
            "Use either symbol or symbols, not both",
        ),
        (
            "BTCUSDT",
            None,
            ["SPOT"],
            "Use permissions without symbol or symbols filters",
        ),
        (
            None,
            ["BTCUSDT"],
            ["SPOT"],
            "Use permissions without symbol or symbols filters",
        ),
    ]
    for symbol, symbols, permissions, expected_message in invalid_cases:
        try:
            get_binance_exchange_info(
                symbol=symbol,
                symbols=symbols,
                permissions=permissions,
                show_permission_sets=True,
                symbol_status="TRADING",
                client=BinanceMarketDataClient(),
            )
        except MarketDataProviderError as exc:
            _CHECK.assertEqual(exc.status_code, 422)
            _CHECK.assertEqual(exc.message, expected_message)
        else:
            _CHECK.fail("Expected MarketDataProviderError")


class _StubBinanceExchangeInfoClient(BinanceMarketDataClient):
    def __init__(self) -> None:
        self.request: BinanceExchangeInfoRequest | None = None

    def fetch_exchange_info(
        self,
        request: BinanceExchangeInfoRequest,
        *,
        timeout: float = 10.0,
    ) -> BinanceExchangeInfoResponse:
        self.request = request
        return _sample_binance_exchange_info_response()


class _StubTwelveDataListingClient(TwelveDataMarketDataClient):
    def __init__(self) -> None:
        self.stock_request: TwelveDataStockListRequest | None = None
        self.forex_request: TwelveDataForexPairsRequest | None = None
        self.etf_request: TwelveDataEtfListRequest | None = None

    def fetch_stocks(
        self,
        request: TwelveDataStockListRequest,
        *,
        timeout: float = 10.0,
    ) -> TwelveDataStocksResponse:
        self.stock_request = request
        return _sample_twelve_data_stocks_response()

    def fetch_forex_pairs(
        self,
        request: TwelveDataForexPairsRequest,
        *,
        timeout: float = 10.0,
    ) -> TwelveDataForexPairsResponse:
        self.forex_request = request
        return _sample_twelve_data_forex_pairs_response()

    def fetch_etfs(
        self,
        request: TwelveDataEtfListRequest,
        *,
        timeout: float = 10.0,
    ) -> TwelveDataEtfsResponse:
        self.etf_request = request
        return _sample_twelve_data_etfs_response()


def test_listing_services_forward_binance_request() -> None:
    binance_client = _StubBinanceExchangeInfoClient()
    get_binance_exchange_info(
        symbol=" ",
        symbols=["btcusdt", ""],
        permissions=None,
        show_permission_sets=False,
        symbol_status="TRADING",
        client=binance_client,
    )
    _CHECK.assertIsNotNone(binance_client.request)
    binance_request = cast(BinanceExchangeInfoRequest, binance_client.request)
    _CHECK.assertEqual(binance_request.symbols, ("btcusdt",))
    _CHECK.assertEqual(binance_request.permissions, ())
    _CHECK.assertEqual(binance_request.show_permission_sets, False)
    _CHECK.assertIsNone(binance_request.symbol_status)


def test_listing_services_forward_twelve_data_requests() -> None:
    twelve_data_client = _StubTwelveDataListingClient()
    get_twelve_data_stocks(
        options=TwelveDataStockListOptions(
            symbol="aapl",
            exchange="NASDAQ",
            mic_code="XNAS",
            country="United States",
            type="Common Stock",
        ),
        api_key="test-key",
        client=twelve_data_client,
    )
    get_twelve_data_forex_pairs(
        options=TwelveDataForexPairsOptions(
            symbol="eur/usd",
            currency_base="eur",
            currency_quote="usd",
            currency_group="Major",
        ),
        api_key="test-key",
        client=twelve_data_client,
    )
    get_twelve_data_etfs(
        options=TwelveDataEtfListOptions(
            symbol="spy",
            exchange="NYSE",
            mic_code="XNYS",
            country="United States",
        ),
        api_key="test-key",
        client=twelve_data_client,
    )
    _CHECK.assertIsNotNone(twelve_data_client.stock_request)
    stock_request = cast(TwelveDataStockListRequest, twelve_data_client.stock_request)
    _CHECK.assertEqual(stock_request.symbol, "aapl")
    _CHECK.assertEqual(stock_request.api_key, "test-key")
    _CHECK.assertIsNotNone(twelve_data_client.forex_request)
    forex_request = cast(TwelveDataForexPairsRequest, twelve_data_client.forex_request)
    _CHECK.assertEqual(forex_request.currency_base, "eur")
    _CHECK.assertIsNotNone(twelve_data_client.etf_request)
    etf_request = cast(TwelveDataEtfListRequest, twelve_data_client.etf_request)
    _CHECK.assertEqual(etf_request.mic_code, "XNYS")


def _assert_twelve_data_service_requires_api_key() -> None:
    try:
        get_twelve_data_market_data(
            options=_twelve_data_options(),
            api_key=None,
            client=TwelveDataMarketDataClient(),
        )
    except MarketDataProviderError as exc:
        _CHECK.assertEqual(exc.status_code, 503)
        _CHECK.assertEqual(exc.message, "Twelve Data API key is not configured")
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
        """Create a Yahoo client stub with a fixed payload."""
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
        """Create a Binance client stub with fixed kline rows."""
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


class StubTwelveDataMarketDataClient(TwelveDataMarketDataClient):
    def __init__(self, payload: dict[str, Any]) -> None:
        """Create a Twelve Data client stub with a fixed payload."""
        self.payload = payload
        self.seen_params: Mapping[str, str | int | bool] = {}
        self.seen_timeout = 0.0

    def _get_json(
        self,
        *,
        params: Mapping[str, str | int | bool],
        timeout: float,
    ) -> dict[str, Any]:
        self.seen_params = params
        self.seen_timeout = timeout
        return self.payload


def _http_status_error(status_code: int) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://example.test")
    response = httpx.Response(status_code, request=request)
    return httpx.HTTPStatusError("provider failed", request=request, response=response)


def test_binance_fetch_exchange_info_uses_params_and_normalizes_response() -> None:
    class StubBinanceExchangeInfoClient(BinanceMarketDataClient):
        def __init__(self, payload: dict[str, Any]) -> None:
            self.payload = payload
            self.seen_path = ""
            self.seen_params: Mapping[str, str | bool] = {}
            self.seen_timeout = 0.0

        def _get_json_object(
            self,
            path: str,
            *,
            params: Mapping[str, str | bool],
            timeout: float,
        ) -> dict[str, Any]:
            self.seen_path = path
            self.seen_params = params
            self.seen_timeout = timeout
            return self.payload

    client = StubBinanceExchangeInfoClient(
        {
            "symbols": [
                {
                    "symbol": "BTCUSDT",
                    "baseAsset": "BTC",
                    "quoteAsset": "USDT",
                    "status": "TRADING",
                    "permissions": ["SPOT"],
                    "permissionSets": [["SPOT"]],
                    "isSpotTradingAllowed": True,
                    "isMarginTradingAllowed": False,
                    "orderTypes": ["LIMIT", "MARKET"],
                }
            ]
        }
    )
    request = BinanceExchangeInfoRequest(
        symbol=None,
        symbols=("btcusdt", "ethusdt"),
        permissions=(),
        show_permission_sets=False,
        symbol_status=None,
    )

    response = client.fetch_exchange_info(request, timeout=2.0)

    _CHECK.assertEqual(client.seen_path, "/api/v3/exchangeInfo")
    _CHECK.assertEqual(client.seen_params["symbols"], '["BTCUSDT", "ETHUSDT"]')
    _CHECK.assertNotIn("permissions", client.seen_params)
    _CHECK.assertEqual(client.seen_params["showPermissionSets"], False)
    _CHECK.assertNotIn("symbolStatus", client.seen_params)
    _CHECK.assertEqual(client.seen_timeout, 2.0)
    _CHECK.assertEqual(response.symbols[0].base_asset, "BTC")
    _CHECK.assertEqual(response.symbols[0].permission_sets, [["SPOT"]])


class _StubTwelveDataListingHttpClient(TwelveDataMarketDataClient):
    def __init__(self, payloads: dict[str, dict[str, Any]]) -> None:
        self.payloads = payloads
        self.seen: list[tuple[str, Mapping[str, str | int | bool], float]] = []

    def _get_json_from_path(
        self,
        path: str,
        *,
        params: Mapping[str, str | int | bool],
        timeout: float,
    ) -> dict[str, Any]:
        self.seen.append((path, params, timeout))
        return self.payloads[path]


def _twelve_data_listing_payloads() -> dict[str, dict[str, Any]]:
    return {
        "/stocks": {
            "data": [{"symbol": "AAPL", "name": "Apple Inc", "type": "Common Stock"}],
            "status": "ok",
        },
        "/forex_pairs": {
            "data": [
                {
                    "symbol": "EUR/USD",
                    "currency_group": "Major",
                    "currency_base": "Euro",
                    "currency_quote": "US Dollar",
                }
            ],
            "status": "ok",
        },
        "/etf": {
            "data": [
                {
                    "symbol": "SPY",
                    "name": "SPDR S&P 500 ETF Trust",
                    "isin": "US78462F1030",
                }
            ],
            "status": "ok",
        },
    }


def test_twelve_data_stock_listing_client_uses_path_params_and_normalizes() -> None:
    client = _StubTwelveDataListingHttpClient(_twelve_data_listing_payloads())

    stocks = client.fetch_stocks(
        TwelveDataStockListRequest(
            "aapl", "NASDAQ", "XNAS", "United States", "Common Stock", "key"
        ),
        timeout=3.0,
    )

    _CHECK.assertEqual(client.seen[0][0], "/stocks")
    _CHECK.assertEqual(client.seen[0][1]["symbol"], "AAPL")
    _CHECK.assertEqual(client.seen[0][1]["apikey"], "key")
    _CHECK.assertEqual(client.seen[0][2], 3.0)
    _CHECK.assertEqual(stocks.stocks[0].name, "Apple Inc")


def test_twelve_data_forex_listing_client_uses_path_params_and_normalizes() -> None:
    client = _StubTwelveDataListingHttpClient(_twelve_data_listing_payloads())

    forex_pairs = client.fetch_forex_pairs(
        TwelveDataForexPairsRequest("eur/usd", "eur", "usd", "Major", "key"),
        timeout=4.0,
    )

    _CHECK.assertEqual(client.seen[0][0], "/forex_pairs")
    _CHECK.assertEqual(client.seen[0][1]["currency_base"], "EUR")
    _CHECK.assertEqual(forex_pairs.forex_pairs[0].currency_quote, "US Dollar")


def test_twelve_data_etf_listing_client_uses_path_params_and_normalizes() -> None:
    client = _StubTwelveDataListingHttpClient(_twelve_data_listing_payloads())

    etfs = client.fetch_etfs(
        TwelveDataEtfListRequest("spy", "NYSE", "XNYS", "United States", "key"),
        timeout=5.0,
    )

    _CHECK.assertEqual(client.seen[0][0], "/etf")
    _CHECK.assertEqual(client.seen[0][1]["symbol"], "SPY")
    _CHECK.assertEqual(etfs.etfs[0].isin, "US78462F1030")


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


def test_twelve_data_client_normalizes_time_series_payload() -> None:
    payload = {
        "meta": {"symbol": "aapl", "interval": "1day", "type": "Common Stock"},
        "values": [
            {
                "datetime": "2026-05-01",
                "open": "100.0",
                "high": "105.0",
                "low": "99.0",
                "close": "103.0",
                "volume": "1234",
            }
        ],
        "status": "ok",
    }
    request = TwelveDataTimeSeriesRequest(
        symbol="aapl",
        interval="1day",
        outputsize=10,
        start_date=None,
        end_date=None,
        exchange=None,
        asset_type="stock",
        prepost=False,
        api_key="test-key",
    )

    result = TwelveDataMarketDataClient()._normalize(request=request, data=payload)

    _CHECK.assertEqual(result.provider, "twelve-data")
    _CHECK.assertEqual(result.symbol, "AAPL")
    _CHECK.assertEqual(result.interval, "1day")
    _CHECK.assertEqual(result.candles[0].timestamp, datetime(2026, 5, 1, tzinfo=UTC))
    _CHECK.assertEqual(result.candles[0].close, 103.0)


def test_twelve_data_fetch_time_series_uses_params_and_normalizes_response() -> None:
    payload = {
        "meta": {"symbol": "QQQ", "interval": "1day", "type": "ETF"},
        "values": [
            {
                "datetime": "2026-05-01 15:59:00",
                "open": "1",
                "high": "2",
                "low": "0.5",
                "close": "1.5",
                "volume": "10",
            }
        ],
        "status": "ok",
    }
    client = StubTwelveDataMarketDataClient(payload)
    request = TwelveDataTimeSeriesRequest(
        symbol="qqq",
        interval="1day",
        outputsize=10,
        start_date="2026-01-01",
        end_date="2026-02-01",
        exchange="NASDAQ",
        asset_type="etf",
        prepost=True,
        api_key="secret-key",
    )

    response = client.fetch_time_series(request, timeout=5.0)

    _CHECK.assertEqual(client.seen_params["symbol"], "QQQ")
    _CHECK.assertEqual(client.seen_params["outputsize"], 10)
    _CHECK.assertEqual(client.seen_params["start_date"], "2026-01-01")
    _CHECK.assertEqual(client.seen_params["end_date"], "2026-02-01")
    _CHECK.assertEqual(client.seen_params["exchange"], "NASDAQ")
    _CHECK.assertEqual(client.seen_params["type"], "ETF")
    _CHECK.assertEqual(client.seen_params["prepost"], True)
    _CHECK.assertEqual(client.seen_params["apikey"], "secret-key")
    _CHECK.assertEqual(client.seen_timeout, 5.0)
    _CHECK.assertEqual(response.candles[0].close, 1.5)


def test_twelve_data_client_rejects_error_and_malformed_payloads() -> None:
    client = TwelveDataMarketDataClient()
    request = TwelveDataTimeSeriesRequest(
        "AAPL", "1day", 10, None, None, None, "stock", False, "test-key"
    )

    try:
        client._normalize(
            request=request,
            data={"status": "error", "message": "Invalid API key", "code": 401},
        )
    except MarketDataProviderError as exc:
        _CHECK.assertEqual(exc.status_code, 422)
        _CHECK.assertEqual(exc.message, "Invalid API key")
    else:
        _CHECK.fail("Expected MarketDataProviderError")

    try:
        client._normalize(request=request, data={"status": "ok", "values": []})
    except MarketDataProviderError as exc:
        _CHECK.assertEqual(exc.status_code, 404)
        _CHECK.assertEqual(exc.message, "Twelve Data returned no candles")
    else:
        _CHECK.fail("Expected MarketDataProviderError")

    try:
        client._normalize_row(
            {
                "datetime": "2026-05-01",
                "open": "bad",
                "high": "2",
                "low": "0.5",
                "close": "1.5",
                "volume": "10",
            }
        )
    except MarketDataProviderError as exc:
        _CHECK.assertEqual(exc.status_code, 502)
        _CHECK.assertEqual(
            exc.message, "Twelve Data returned malformed time series data"
        )
    else:
        _CHECK.fail("Expected MarketDataProviderError")

    try:
        client._normalize_row(["not", "a", "mapping"])
    except MarketDataProviderError as exc:
        _CHECK.assertEqual(exc.status_code, 502)
        _CHECK.assertEqual(
            exc.message, "Twelve Data returned malformed time series data"
        )
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

    try:
        TwelveDataMarketDataClient()._raise_http_error(_http_status_error(400))
    except MarketDataProviderError as exc:
        _CHECK.assertEqual(exc.status_code, 422)
        _CHECK.assertEqual(
            exc.message, "Invalid Twelve Data symbol, API key, or parameters"
        )
    else:
        _CHECK.fail("Expected MarketDataProviderError")

    try:
        TwelveDataMarketDataClient()._raise_http_error(_http_status_error(429))
    except MarketDataProviderError as exc:
        _CHECK.assertEqual(exc.status_code, 429)
        _CHECK.assertEqual(exc.message, "Twelve Data rate limit exceeded")
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
