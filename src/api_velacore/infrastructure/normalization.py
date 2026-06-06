from collections.abc import Mapping
from typing import Any, cast

from api_velacore.schemas.market_data import BinanceExchangeSymbol

from .errors import MarketDataProviderError

_BINANCE_EXCHANGE_INFO_ERROR = "Binance returned malformed exchange info data"


def normalize_binance_exchange_symbol(row: object) -> BinanceExchangeSymbol:
    if not isinstance(row, Mapping):
        raise MarketDataProviderError(_BINANCE_EXCHANGE_INFO_ERROR, 502)
    typed_row = cast(Mapping[str, Any], row)
    return BinanceExchangeSymbol.model_validate(
        {
            "symbol": _required_string(typed_row, "symbol"),
            "baseAsset": _required_string(typed_row, "baseAsset"),
            "quoteAsset": _required_string(typed_row, "quoteAsset"),
            "status": _required_string(typed_row, "status"),
            "permissions": _string_list(typed_row.get("permissions")),
            "permissionSets": _string_matrix(typed_row.get("permissionSets")),
            "isSpotTradingAllowed": cast(
                bool | None,
                typed_row.get("isSpotTradingAllowed"),
            ),
            "isMarginTradingAllowed": cast(
                bool | None,
                typed_row.get("isMarginTradingAllowed"),
            ),
            "orderTypes": _string_list(typed_row.get("orderTypes")),
        }
    )


def _required_string(row: Mapping[str, Any], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value:
        raise MarketDataProviderError(_BINANCE_EXCHANGE_INFO_ERROR, 502)
    return value


def _string_list(value: object) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise MarketDataProviderError(_BINANCE_EXCHANGE_INFO_ERROR, 502)
    if not all(isinstance(item, str) for item in value):
        raise MarketDataProviderError(_BINANCE_EXCHANGE_INFO_ERROR, 502)
    return value


def _string_matrix(value: object) -> list[list[str]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise MarketDataProviderError(_BINANCE_EXCHANGE_INFO_ERROR, 502)
    return [_string_list(row) for row in value]
