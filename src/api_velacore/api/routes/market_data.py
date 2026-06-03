from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status

from api_velacore.infrastructure.market_data import MarketDataProviderError
from api_velacore.schemas.market_data import MarketDataResponse
from api_velacore.services.market_data import (
    get_binance_market_data,
    get_twelve_data_market_data,
    get_yahoo_market_data,
)

router = APIRouter(prefix="/market-data", tags=["market-data"])


@router.get(
    "/yahoo/{symbol}",
    response_model=MarketDataResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch Yahoo Finance market data",
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
    "/twelve-data/{symbol}",
    response_model=MarketDataResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch Twelve Data market data for stocks and ETFs",
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
            symbol=symbol,
            interval=interval,
            outputsize=outputsize,
            start_date=start_date,
            end_date=end_date,
            exchange=exchange,
            asset_type=asset_type,
            prepost=prepost,
        )
    except MarketDataProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.get(
    "/binance/{symbol}",
    response_model=MarketDataResponse,
    status_code=status.HTTP_200_OK,
    summary="Fetch Binance Spot market data",
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
