from api_velacore.core.config import get_settings


def test_settings_use_velacore_environment_prefix(monkeypatch) -> None:
    monkeypatch.setenv("VELACORE_APP_NAME", "env-api")
    monkeypatch.setenv("VELACORE_APP_VERSION", "1.2.3")
    get_settings.cache_clear()

    try:
        settings = get_settings()

        assert settings.app_name == "env-api"
        assert settings.app_version == "1.2.3"
    finally:
        get_settings.cache_clear()
