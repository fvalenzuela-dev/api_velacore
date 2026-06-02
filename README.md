# api_velacore

FastAPI backend base for Velacore. It currently exposes the application shell,
health checks, OpenAPI documentation, and the quality gates used by CI.

## Quick Start

Create the environment, install the project, and launch the local API:

```bash
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
uvicorn api_velacore.main:app --reload
```

The API runs at `http://127.0.0.1:8000`.

## Project Summary

| Topic | Details |
|-------|---------|
| Purpose | FastAPI backend foundation for Velacore services. |
| Runtime | Python `3.14.5` only. |
| Package | `api-velacore` version `0.1.0`. |
| Framework | FastAPI with Uvicorn. |
| Configuration | Pydantic Settings with `VELACORE_` environment variable prefix. |
| Validation | Pytest, Coverage, Ruff, and mypy. |
| Layout | `src/` package layout with tests in `tests/`. |

The Python version is pinned in `.python-version` and `pyproject.toml` with
`requires-python = "==3.14.5"`.

## Install

Use Python `3.14.5`, then install the application with development tools:

```bash
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Run Locally

Start the development server with reload enabled:

```bash
uvicorn api_velacore.main:app --reload
```
```bash
.venv/bin/python -m uvicorn api_velacore.main:app --reload --port 8766
```

Use an explicit host or port when needed:

```bash
uvicorn api_velacore.main:app --host 0.0.0.0 --port 8000 --reload
```

## Build and Compile Checks

Python projects are not compiled into a single binary by default. In this
project, the practical build checks are bytecode compilation, package build
validation, and the same quality gates used by CI.

Compile source and tests to Python bytecode:

```bash
python -m compileall src tests
```

Build the package distribution when the `build` frontend is installed:

```bash
python -m pip install build
python -m build
```

The package build uses Hatchling, configured in `pyproject.toml`.

## Tests and Quality Checks

Run the test suite:

```bash
pytest
```

Run tests with coverage, matching CI:

```bash
coverage run -m pytest
mkdir -p coverage
coverage lcov -o coverage/lcov.info
```

Run formatting checks:

```bash
ruff format --check .
```

Run linting:

```bash
ruff check .
```

Run type checking:

```bash
mypy
```

Run the local validation path end to end:

```bash
python -m compileall src tests
pytest
ruff check .
ruff format --check .
mypy
```

## API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/health` | Returns service health status. |
| `GET` | `/market-data/yahoo/{symbol}` | Returns normalized Yahoo Finance OHLCV candles for stocks and ETFs. |
| `GET` | `/market-data/binance/{symbol}` | Returns normalized Binance Spot OHLCV candles for crypto pairs. |
| `GET` | `/openapi.json` | Returns the OpenAPI schema. |

Health check:

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

Yahoo Finance market data example:

```bash
curl "http://127.0.0.1:8000/market-data/yahoo/AAPL?period=1mo&interval=1d"
```

Supported Yahoo query parameters:

| Parameter | Purpose | Values / notes |
|-----------|---------|----------------|
| `period` | Relative time range | `1d`, `5d`, `1mo`, `3mo`, `6mo`, `1y`, `2y`, `5y`, `10y`, `ytd`, `max` |
| `interval` | Candle temporalidad | `1m`, `2m`, `5m`, `15m`, `30m`, `60m`, `90m`, `1h`, `1d`, `5d`, `1wk`, `1mo`, `3mo` |
| `start` / `end` | Explicit ISO date range | Use instead of `period`; both are required together. |
| `prepost` | Include pre/post-market data | Boolean, default `false`. |
| `events` | Yahoo corporate events filter | For example `div|split|earn`. |

Binance market data example:

```bash
curl "http://127.0.0.1:8000/market-data/binance/BTCUSDT?interval=1h&limit=100"
```

Supported Binance query parameters:

| Parameter | Purpose | Values / notes |
|-----------|---------|----------------|
| `interval` | Candle temporalidad | `1s`, `1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `6h`, `8h`, `12h`, `1d`, `3d`, `1w`, `1M` |
| `startTime` / `endTime` | Explicit UTC range | Unix timestamps in milliseconds. |
| `timeZone` | Kline interval timezone | Examples: `0`, `8`, `-1:00`, `05:45`. |
| `limit` | Maximum candles | Default `500`, maximum `1000`. |

Market data responses are normalized and stateless; the backend does not persist
candles in the database or local storage.

Example response shape:

```json
{
  "provider": "binance",
  "symbol": "BTCUSDT",
  "interval": "1h",
  "range": null,
  "candles": [
    {
      "timestamp": "2026-05-01T00:00:00Z",
      "open": 65000.0,
      "high": 66000.0,
      "low": 64500.0,
      "close": 65500.0,
      "volume": 123.45
    }
  ]
}
```

## Swagger and OpenAPI

FastAPI interactive documentation is enabled with the default endpoints:

| UI | URL |
|----|-----|
| Swagger UI | `http://127.0.0.1:8000/docs` |
| ReDoc | `http://127.0.0.1:8000/redoc` |
| OpenAPI JSON | `http://127.0.0.1:8000/openapi.json` |

The OpenAPI title comes from `VELACORE_APP_NAME` or the default
`api_velacore` setting.

## Configuration

Runtime settings live in `src/api_velacore/core/config.py` and use the
`VELACORE_` environment variable prefix.

| Setting | Environment variable | Default |
|---------|----------------------|---------|
| `app_name` | `VELACORE_APP_NAME` | `api_velacore` |
| `app_version` | `VELACORE_APP_VERSION` | `0.1.0` |

Example:

```bash
VELACORE_APP_NAME="Velacore API" uvicorn api_velacore.main:app --reload
```

## Architecture Overview

The project uses a `src/` layout and separates FastAPI concerns by
responsibility:

| Path | Responsibility |
|------|----------------|
| `src/api_velacore/main.py` | FastAPI application factory and app instance. |
| `src/api_velacore/api/routes/` | HTTP route definitions. |
| `src/api_velacore/core/` | Application configuration and core settings. |
| `src/api_velacore/schemas/` | Pydantic request and response schemas. |
| `src/api_velacore/services/` | Business logic independent from HTTP details. |
| `src/api_velacore/infrastructure/` | External systems such as databases, queues, or HTTP clients. |
| `src/api_velacore/utils/` | Small shared helpers with no framework coupling. |
| `tests/` | Automated tests mirroring externally visible behavior. |

Keep route handlers thin: validate input, delegate behavior to services, and
return typed schemas. Avoid placing business rules or infrastructure access
directly in route modules.

## Continuous Integration

The central validation workflow installs the package with `.[dev]`, runs tests
with coverage, uploads an LCOV report, then runs Ruff and mypy.

```bash
python -m pip install -e ".[dev]"
coverage run -m pytest
mkdir -p coverage
coverage lcov -o coverage/lcov.info
ruff check .
ruff format --check .
mypy
```
