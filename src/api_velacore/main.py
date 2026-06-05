from fastapi import FastAPI

from api_velacore.api.routes.health import router as health_router
from api_velacore.api.routes.indicators import router as indicators_router
from api_velacore.api.routes.market_data import router as market_data_router
from api_velacore.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
    )
    app.include_router(health_router)
    app.include_router(market_data_router)
    app.include_router(indicators_router)
    return app


app = create_app()
