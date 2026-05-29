from fastapi import FastAPI

from api_velacore.core.config import get_settings
from api_velacore.main import create_app


def test_create_app_uses_configured_metadata(monkeypatch) -> None:
    monkeypatch.setenv("VELACORE_APP_NAME", "custom-api")
    monkeypatch.setenv("VELACORE_APP_VERSION", "9.8.7")
    get_settings.cache_clear()

    try:
        app = create_app()

        assert isinstance(app, FastAPI)
        assert app.title == "custom-api"
        assert app.version == "9.8.7"
        assert any(route.path == "/health" for route in app.routes)
    finally:
        get_settings.cache_clear()
