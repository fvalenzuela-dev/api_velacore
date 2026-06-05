import unittest

import pytest
from fastapi import FastAPI

from api_velacore.core.config import get_settings
from api_velacore.main import create_app

_CHECK = unittest.TestCase()


def test_create_app_uses_configured_metadata(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VELACORE_APP_NAME", "custom-api")
    monkeypatch.setenv("VELACORE_APP_VERSION", "9.8.7")
    get_settings.cache_clear()

    try:
        app = create_app()

        _CHECK.assertIsInstance(app, FastAPI)
        _CHECK.assertEqual(app.title, "custom-api")
        _CHECK.assertEqual(app.version, "9.8.7")
        route_paths = {getattr(route, "path", "") for route in app.routes}
        _CHECK.assertIn("/health", route_paths)
        _CHECK.assertIn("/market-data/yahoo/{symbol}", route_paths)
        _CHECK.assertIn("/market-data/binance/{symbol}", route_paths)
        openapi = app.openapi()
        _CHECK.assertEqual(
            [tag["name"] for tag in openapi["tags"]],
            ["binance", "yahoo", "twelve-data", "indicators"],
        )
        _CHECK.assertEqual(
            openapi["paths"]["/market-data/yahoo/{symbol}"]["get"]["tags"],
            ["yahoo"],
        )
        _CHECK.assertEqual(
            openapi["paths"]["/indicators/ema/{symbol}"]["get"]["tags"],
            ["indicators"],
        )
        _CHECK.assertEqual(
            openapi["paths"]["/market-data/binance/{symbol}"]["get"]["tags"],
            ["binance"],
        )
        _CHECK.assertEqual(
            openapi["paths"]["/market-data/twelve-data/{symbol}"]["get"]["tags"],
            ["twelve-data"],
        )
    finally:
        get_settings.cache_clear()
