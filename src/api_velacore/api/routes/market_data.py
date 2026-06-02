from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status

from api_velacore.infrastructure.market_data import MarketDataProviderError
from api_velacore.schemas.market_data import MarketDataResponse
from api_velacore.services.market_data import (
    get_binance_market_data,
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
