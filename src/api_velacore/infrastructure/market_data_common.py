from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from .errors import MarketDataProviderError as MarketDataProviderError


def _datetime_to_epoch_seconds(value: str) -> int:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        msg = "Dates must use ISO format, for example 2026-01-31"
        raise MarketDataProviderError(msg, 422) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return int(parsed.timestamp())


def _datetime_from_milliseconds(value: int) -> datetime:
    return datetime.fromtimestamp(value / 1000, tz=UTC)


def _datetime_from_seconds(value: int) -> datetime:
    return datetime.fromtimestamp(value, tz=UTC)


def _parse_twelve_data_datetime(value: object) -> datetime:
    if not isinstance(value, str):
        raise MarketDataProviderError(
            "Twelve Data returned malformed time series data", 502
        )
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MarketDataProviderError(
            "Twelve Data returned malformed time series data", 502
        ) from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _float_or_none(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, str | int | float):
        try:
            return float(value)
        except ValueError:
            return None
    return None


def _float_at(values: list[Any], index: int) -> float | None:
    if index >= len(values):
        return None
    return _float_or_none(values[index])


def _string_or_none(value: object) -> str | None:
    if isinstance(value, str) and value:
        return value
    return None


def _required_string(
    row: Mapping[str, Any],
    key: str,
    *,
    provider_message: str,
) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value:
        raise MarketDataProviderError(provider_message, 502)
    return value
