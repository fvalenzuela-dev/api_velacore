import unittest

from fastapi import FastAPI

from api_velacore.core.config import get_settings
from api_velacore.main import create_app

_CHECK = unittest.TestCase()


def test_create_app_uses_configured_metadata(monkeypatch) -> None:
    monkeypatch.setenv("VELACORE_APP_NAME", "custom-api")
    monkeypatch.setenv("VELACORE_APP_VERSION", "9.8.7")
    get_settings.cache_clear()

    try:
        app = create_app()

        _CHECK.assertIsInstance(app, FastAPI)
        _CHECK.assertEqual(app.title, "custom-api")
        _CHECK.assertEqual(app.version, "9.8.7")
        _CHECK.assertTrue(any(route.path == "/health" for route in app.routes))
    finally:
        get_settings.cache_clear()
