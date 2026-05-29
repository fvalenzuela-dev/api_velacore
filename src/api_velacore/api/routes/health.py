from fastapi import APIRouter, status

from api_velacore.schemas.health import HealthResponse
from api_velacore.services.health import get_health_status

router = APIRouter(tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Check API health",
)
def health_check() -> HealthResponse:
    return get_health_status()
