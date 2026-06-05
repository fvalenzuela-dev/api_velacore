from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status

from api_velacore.infrastructure.market_data import MarketDataProviderError
from api_velacore.schemas.indicators import (
    IndicatorPoint,
    IndicatorProvider,
    TwelveDataIndicatorAssetType,
)
from api_velacore.services.indicators import (
    EmaIndicatorOptions,
    default_source_limit,
    get_ema_indicator,
)

router = APIRouter(prefix="/indicators", tags=["indicators"])


@router.get(
    "/ema/{symbol}",
    response_model=list[IndicatorPoint],
    status_code=status.HTTP_200_OK,
    summary="Calculate EMA indicator points for chart overlays",
)
def get_ema_indicator_endpoint(
    symbol: Annotated[str, Path(min_length=1, description="Market symbol")],
    provider: Annotated[
        IndicatorProvider,
        Query(
            description="Source market-data provider: yahoo, binance, or twelve-data"
        ),
    ] = "yahoo",
    period: Annotated[
        int,
        Query(ge=1, le=5000, description="EMA length; defaults to 20"),
    ] = 20,
    range_: Annotated[
        str | None,
        Query(
            alias="range",
            description="Yahoo source range where supported, for example 1mo",
        ),
    ] = "1mo",
    interval: Annotated[
        str,
        Query(description="Source candle interval, for example 1d, 1h, or 5m"),
    ] = "1d",
    outputsize: Annotated[
        int,
        Query(ge=1, le=5000, description="Twelve Data source candle count"),
    ] = 500,
    limit: Annotated[
        int | None,
        Query(ge=1, le=1000, description="Binance source candle count"),
    ] = None,
    asset_type: Annotated[
        TwelveDataIndicatorAssetType | None,
        Query(description="Optional Twelve Data asset selector: stock or etf"),
    ] = None,
) -> list[IndicatorPoint]:
    try:
        return get_ema_indicator(
            options=EmaIndicatorOptions(
                symbol=symbol,
                period=period,
                provider=provider,
                range=range_,
                interval=interval,
                outputsize=outputsize,
                limit=limit or default_source_limit(period),
                asset_type=asset_type,
            ),
        )
    except MarketDataProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
