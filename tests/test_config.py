import unittest
from pathlib import Path

import pytest

from api_velacore.core.config import get_settings

_CHECK = unittest.TestCase()


def test_settings_load_twelve_data_api_key_from_dotenv(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("VELACORE_TWELVE_DATA_API_KEY", raising=False)
    monkeypatch.chdir(tmp_path)
    tmp_path.joinpath(".env").write_text(
        "VELACORE_TWELVE_DATA_API_KEY=dotenv-key\n",
        encoding="utf-8",
    )
    get_settings.cache_clear()

    try:
        settings = get_settings()

        _CHECK.assertEqual(settings.twelve_data_api_key, "dotenv-key")
    finally:
        get_settings.cache_clear()


def test_settings_use_velacore_environment_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VELACORE_APP_NAME", "env-api")
    monkeypatch.setenv("VELACORE_APP_VERSION", "1.2.3")
    monkeypatch.setenv("VELACORE_TWELVE_DATA_API_KEY", "test-key")
    get_settings.cache_clear()

    try:
        settings = get_settings()

        _CHECK.assertEqual(settings.app_name, "env-api")
        _CHECK.assertEqual(settings.app_version, "1.2.3")
        _CHECK.assertEqual(settings.twelve_data_api_key, "test-key")
    finally:
        get_settings.cache_clear()
