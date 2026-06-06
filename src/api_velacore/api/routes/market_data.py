from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status

from api_velacore.infrastructure.market_data import MarketDataProviderError
from api_velacore.schemas.market_data import (
    BinanceExchangeInfoResponse,
    MarketDataResponse,
    TwelveDataEtfsResponse,
    TwelveDataForexPairsResponse,
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

router = APIRouter(prefix="/market-data")


@router.get(
    "/yahoo/{symbol}",
    response_model=MarketDataResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch Yahoo Finance market data",
    tags=["yahoo"],
)
def get_yahoo_market_data_endpoint(
    symbol: Annotated[str, Path(min_length=1, description="Yahoo ticker symbol")],
    period: Annotated[
        str | None,
        Query(description="Yahoo time range, for example 1mo, 1y, ytd, max"),
    ] = None,
    interval: Annotated[
        str,
        Query(description="Yahoo candle interval, for example 1d, 1h, 5m"),
    ] = "1d",
    start: Annotated[
        str | None,
        Query(description="ISO start date/time used instead of period"),
    ] = None,
    end: Annotated[
        str | None,
        Query(description="ISO end date/time used instead of period"),
    ] = None,
    prepost: Annotated[
        bool,
        Query(description="Include pre-market and post-market data"),
    ] = False,
    events: Annotated[
        str | None,
        Query(description="Yahoo event filter such as div|split|earn"),
    ] = None,
) -> MarketDataResponse:
    try:
        return get_yahoo_market_data(
            symbol=symbol,
            period=period,
            interval=interval,
            start=start,
            end=end,
            prepost=prepost,
            events=events,
        )
    except MarketDataProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get(
    "/binance/exchange-info",
    response_model=BinanceExchangeInfoResponse,
    status_code=status.HTTP_200_OK,
    summary="List Binance Spot trading symbols from exchange info",
    tags=["binance"],
)
def get_binance_exchange_info_endpoint(
    symbol: Annotated[
        str | None,
        Query(description="Optional Binance Spot symbol filter"),
    ] = None,
    symbols: Annotated[
        list[str] | None,
        Query(description="Optional repeated Binance Spot symbol filters"),
    ] = None,
    permissions: Annotated[
        list[str] | None,
        Query(description="Optional repeated Binance permission filters"),
    ] = None,
    show_permission_sets: Annotated[
        bool,
        Query(
            alias="showPermissionSets",
            description="Include Binance permission set metadata",
        ),
    ] = False,
    symbol_status: Annotated[
        str | None,
        Query(alias="symbolStatus", description="Optional Binance symbol status"),
    ] = "TRADING",
) -> BinanceExchangeInfoResponse:
    try:
        return get_binance_exchange_info(
            symbol=symbol,
            symbols=symbols,
            permissions=permissions,
            show_permission_sets=show_permission_sets,
            symbol_status=symbol_status,
        )
    except MarketDataProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get(
    "/twelve-data/stocks",
    response_model=TwelveDataStocksResponse,
    status_code=status.HTTP_200_OK,
    summary="List Twelve Data stock assets",
    tags=["twelve-data"],
)
def get_twelve_data_stocks_endpoint(
    symbol: Annotated[
        str | None,
        Query(description="Optional stock symbol filter"),
    ] = None,
    exchange: Annotated[
        str,
        Query(description="Stock exchange filter"),
    ] = "NASDAQ",
    mic_code: Annotated[
        str | None,
        Query(description="Optional market identifier code filter"),
    ] = None,
    country: Annotated[
        str,
        Query(description="Stock country filter"),
    ] = "United States",
    stock_type: Annotated[
        str,
        Query(alias="type", description="Twelve Data stock type filter"),
    ] = "Common Stock",
) -> TwelveDataStocksResponse:
    try:
        return get_twelve_data_stocks(
            options=TwelveDataStockListOptions(
                symbol=symbol,
                exchange=exchange,
                mic_code=mic_code,
                country=country,
                type=stock_type,
            ),
        )
    except MarketDataProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get(
    "/twelve-data/forex-pairs",
    response_model=TwelveDataForexPairsResponse,
    status_code=status.HTTP_200_OK,
    summary="List Twelve Data Forex pairs",
    tags=["twelve-data"],
)
def get_twelve_data_forex_pairs_endpoint(
    symbol: Annotated[
        str | None,
        Query(description="Optional Forex pair filter such as EUR/USD"),
    ] = None,
    currency_base: Annotated[
        str | None,
        Query(description="Optional base currency filter"),
    ] = None,
    currency_quote: Annotated[
        str | None,
        Query(description="Optional quote currency filter"),
    ] = None,
    currency_group: Annotated[
        str,
        Query(description="Twelve Data currency group filter"),
    ] = "Major",
) -> TwelveDataForexPairsResponse:
    try:
        return get_twelve_data_forex_pairs(
            options=TwelveDataForexPairsOptions(
                symbol=symbol,
                currency_base=currency_base,
                currency_quote=currency_quote,
                currency_group=currency_group,
            ),
        )
    except MarketDataProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get(
    "/twelve-data/etfs",
    response_model=TwelveDataEtfsResponse,
    status_code=status.HTTP_200_OK,
    summary="List Twelve Data ETF assets",
    tags=["twelve-data"],
)
def get_twelve_data_etfs_endpoint(
    symbol: Annotated[
        str | None,
        Query(description="Optional ETF symbol filter"),
    ] = None,
    exchange: Annotated[
        str,
        Query(description="ETF exchange filter"),
    ] = "NYSE",
    mic_code: Annotated[
        str | None,
        Query(description="Optional market identifier code filter"),
    ] = None,
    country: Annotated[
        str,
        Query(description="ETF country filter"),
    ] = "United States",
) -> TwelveDataEtfsResponse:
    try:
        return get_twelve_data_etfs(
            options=TwelveDataEtfListOptions(
                symbol=symbol,
                exchange=exchange,
                mic_code=mic_code,
                country=country,
            ),
        )
    except MarketDataProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get(
    "/twelve-data/{symbol}",
    response_model=MarketDataResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch Twelve Data market data for stocks and ETFs",
    tags=["twelve-data"],
)
def get_twelve_data_market_data_endpoint(
    symbol: Annotated[str, Path(min_length=1, description="Stock or ETF symbol")],
    interval: Annotated[
        str,
        Query(description="Twelve Data interval, for example 1min, 1h, 1day"),
    ] = "1day",
    outputsize: Annotated[
        int,
        Query(ge=1, le=5000, description="Maximum candles"),
    ] = 500,
    start_date: Annotated[
        str | None,
        Query(description="Twelve Data start date/time; requires end_date"),
    ] = None,
    end_date: Annotated[
        str | None,
        Query(description="Twelve Data end date/time; requires start_date"),
    ] = None,
    exchange: Annotated[
        str | None,
        Query(description="Optional exchange filter such as NASDAQ"),
    ] = None,
    asset_type: Annotated[
        str | None,
        Query(description="Optional asset selector: stock or etf"),
    ] = None,
    prepost: Annotated[
        bool,
        Query(description="Include pre-market and post-market data when supported"),
    ] = False,
) -> MarketDataResponse:
    try:
        return get_twelve_data_market_data(
            options=TwelveDataMarketDataOptions(
                symbol=symbol,
                interval=interval,
                outputsize=outputsize,
                start_date=start_date,
                end_date=end_date,
                exchange=exchange,
                asset_type=asset_type,
                prepost=prepost,
            ),
        )
    except MarketDataProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get(
    "/binance/{symbol}",
    response_model=MarketDataResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch Binance Spot market data",
    tags=["binance"],
)
def get_binance_market_data_endpoint(
    symbol: Annotated[str, Path(min_length=1, description="Binance Spot symbol")],
    interval: Annotated[
        str,
        Query(description="Binance candle interval, for example 1m, 1h, 1d"),
    ] = "1h",
    start_time: Annotated[
        int | None,
        Query(alias="startTime", description="UTC start timestamp in milliseconds"),
    ] = None,
    end_time: Annotated[
        int | None,
        Query(alias="endTime", description="UTC end timestamp in milliseconds"),
    ] = None,
    time_zone: Annotated[
        str | None,
        Query(alias="timeZone", description="Kline timezone such as 0, 8, -1:00"),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=1000, description="Maximum candles")] = 500,
) -> MarketDataResponse:
    try:
        return get_binance_market_data(
            symbol=symbol,
            interval=interval,
            start_time=start_time,
            end_time=end_time,
            time_zone=time_zone,
            limit=limit,
        )
    except MarketDataProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
