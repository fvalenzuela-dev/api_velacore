from typing import Annotated

from fastapi import APIRouter, HTTPException, Path, Query, status

from api_velacore.infrastructure.market_data import MarketDataProviderError
from api_velacore.schemas.indicators import IndicatorAssetType, IndicatorPoint
from api_velacore.services.indicators import EmaIndicatorOptions, get_ema_indicator

router = APIRouter(prefix="/indicators", tags=["indicators"])


@router.get(
    "/ema/{symbol}",
    response_model=list[IndicatorPoint],
    status_code=status.HTTP_200_OK,
    summary="Calculate EMA indicator points for chart overlays",
)
def get_ema_indicator_endpoint(
    symbol: Annotated[str, Path(min_length=1, description="Market symbol")],
    period: Annotated[
        int,
        Query(ge=1, le=5000, description="EMA length; defaults to 20"),
    ] = 20,
    asset_type: Annotated[
        IndicatorAssetType | None,
        Query(description="Optional asset selector: equity, etf, or crypto"),
    ] = None,
    range_: Annotated[
        str | None,
        Query(
            alias="range",
            description="Source market-data range where supported, for example 1mo",
        ),
    ] = "1mo",
    interval: Annotated[
        str,
        Query(description="Source candle interval, for example 1d, 1h, or 5m"),
    ] = "1d",
) -> list[IndicatorPoint]:
    try:
        return get_ema_indicator(
            options=EmaIndicatorOptions(
                symbol=symbol,
                period=period,
                asset_type=asset_type,
                range=range_,
                interval=interval,
            ),
        )
    except MarketDataProviderError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
