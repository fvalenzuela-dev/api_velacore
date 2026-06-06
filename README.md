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

## Docker

Build the runtime image:

```bash
docker build -t api-velacore:local .
```

Run the API container locally with the tracked sample environment:

```bash
docker run --rm \
  --name api-velacore \
  --env-file example.env \
  -p 8091:8000 \
  api-velacore:local
```

For real credentials, copy `example.env` to the ignored `.env` file and edit
that local file instead of committing secrets:

```bash
cp example.env .env
```

Or use Docker Compose, which loads `example.env` and then optional local `.env`
overrides:

```bash
docker compose up --build
```

Verify the container health endpoint on port `8091`:

```bash
curl http://127.0.0.1:8091/health
```

Publish the image to a registry by tagging and pushing it:

```bash
docker tag api-velacore:local <registry>/<image>:<tag>
docker push <registry>/<image>:<tag>
```

The repository also includes GCP deployment workflows that build from
`Dockerfile` on `develop` and `main` pushes.

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

| Group | Method | Path | Purpose |
|-------|--------|------|---------|
| Health | `GET` | `/health` | Returns service health status. |
| Binance | `GET` | `/market-data/binance/exchange-info` | Lists normalized Binance Spot trading symbols/pairs. |
| Binance | `GET` | `/market-data/binance/{symbol}` | Returns normalized Binance Spot OHLCV candles for crypto pairs. |
| Yahoo | `GET` | `/market-data/yahoo/{symbol}` | Returns normalized Yahoo Finance OHLCV candles for stocks and ETFs. |
| Indicators | `GET` | `/indicators/ema/{symbol}` | Returns chart-ready EMA points derived from selected provider source candle closes. |
| Twelve Data | `GET` | `/market-data/twelve-data/stocks` | Lists normalized Twelve Data stock assets. |
| Twelve Data | `GET` | `/market-data/twelve-data/forex-pairs` | Lists normalized Twelve Data Forex pairs. |
| Twelve Data | `GET` | `/market-data/twelve-data/etfs` | Lists normalized Twelve Data ETF assets. |
| Twelve Data | `GET` | `/market-data/twelve-data/{symbol}` | Returns normalized Twelve Data OHLCV candles for stocks and ETFs. |
| OpenAPI | `GET` | `/openapi.json` | Returns the OpenAPI schema. |

Swagger groups provider-backed endpoints under `binance`, `yahoo`, and
`twelve-data`. Technical indicators appear under `indicators` and select their
source with a `provider` query parameter.

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
| `events` | Yahoo corporate events filter | For example `div\|split\|earn`. |

Twelve Data market data example:

```bash
VELACORE_TWELVE_DATA_API_KEY="your-api-key" uvicorn api_velacore.main:app --reload
curl "http://127.0.0.1:8000/market-data/twelve-data/QQQ?interval=1day&outputsize=100&asset_type=etf"
```

Supported Twelve Data query parameters:

| Parameter | Purpose | Values / notes |
|-----------|---------|----------------|
| `interval` | Candle interval | `1min`, `5min`, `15min`, `30min`, `45min`, `1h`, `2h`, `4h`, `1day`, `1week`, `1month` |
| `outputsize` | Maximum candles | Default `500`, maximum `5000`. |
| `start_date` / `end_date` | Explicit date range | Use together; forwarded to Twelve Data. |
| `exchange` | Exchange filter | Example: `NASDAQ`. |
| `asset_type` | Provider instrument selector | `stock` maps to `Common Stock`; `etf` maps to `ETF`. |
| `prepost` | Include pre/post-market data | Boolean, default `false`; requires a supported Twelve Data plan. |

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

Asset listing examples:

```bash
curl "http://127.0.0.1:8000/market-data/binance/exchange-info?symbolStatus=TRADING"
VELACORE_TWELVE_DATA_API_KEY="your-api-key" uvicorn api_velacore.main:app --reload
curl "http://127.0.0.1:8000/market-data/twelve-data/stocks?exchange=NASDAQ&country=United%20States&type=Common%20Stock"
curl "http://127.0.0.1:8000/market-data/twelve-data/forex-pairs?currency_group=Major"
curl "http://127.0.0.1:8000/market-data/twelve-data/etfs?exchange=NYSE&country=United%20States"
```

Supported Binance exchange-info listing parameters:

| Parameter | Purpose | Values / notes |
|-----------|---------|----------------|
| `symbol` | Single trading symbol filter | Optional; mutually exclusive with `symbols` and `permissions`. |
| `symbols` | Repeated trading symbol filters | Optional; use repeated query params such as `symbols=BTCUSDT&symbols=ETHUSDT`; mutually exclusive with `symbol` and `permissions`. |
| `permissions` | Repeated Binance permission filters | Optional; forwarded to Binance as a list; cannot be combined with `symbol` or `symbols`. |
| `showPermissionSets` | Include Binance permission set metadata | Boolean, default `true`. |
| `symbolStatus` | Symbol status filter | Default `TRADING`. |

Supported Twelve Data listing parameters:

| Endpoint | Parameters |
|----------|------------|
| `/market-data/twelve-data/stocks` | `symbol`, `exchange` default `NASDAQ`, `mic_code`, `country` default `United States`, `type` default `Common Stock`. |
| `/market-data/twelve-data/forex-pairs` | `symbol`, `currency_base`, `currency_quote`, `currency_group` default `Major`. |
| `/market-data/twelve-data/etfs` | `symbol`, `exchange` default `NYSE`, `mic_code`, `country` default `United States`. |

Market data responses are normalized and stateless; the backend does not persist
candles in the database or local storage.

EMA indicator examples:

```bash
curl "http://127.0.0.1:8000/indicators/ema/AAPL?provider=yahoo&period=20&range=1mo&interval=1d"
curl "http://127.0.0.1:8000/indicators/ema/BTCUSDT?provider=binance&period=20&interval=1d&limit=500"
curl "http://127.0.0.1:8000/indicators/ema/QQQ?provider=twelve-data&period=20&interval=1d&outputsize=500&asset_type=etf"
```

Supported EMA query parameters:

| Parameter | Purpose | Values / notes |
|-----------|---------|----------------|
| `provider` | Source market-data provider | Default `yahoo`; allowed values: `yahoo`, `binance`, `twelve-data`. |
| `period` | EMA length | Default `20`; must be greater than `0`. |
| `range` | Yahoo source market-data range | Default `1mo`; used by Yahoo where supported. |
| `interval` | Source candle interval | Default `1d`; common aliases map to Binance and Twelve Data intervals where needed. |
| `limit` | Binance candle count | Default derives from `period`; maximum `1000`; must be greater than or equal to `period`. |
| `outputsize` | Twelve Data candle count | Default `500`; maximum `5000`; must be greater than or equal to `period`. |
| `asset_type` | Twelve Data instrument selector | Optional: `stock` or `etf`. |

Provider-specific parameters that do not apply to the selected provider are
ignored. Twelve Data EMA requires `VELACORE_TWELVE_DATA_API_KEY` to be
configured.

EMA responses are stateless and omit warm-up candles; a shared calculation uses
normalized candle `close` prices from the selected provider. The first returned
point is the seed EMA at the `period`th candle.

```json
[
  {"time":"2026-01-01T00:00:00Z","value":123.45}
]
```

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

Runtime settings live in `src/api_velacore/core/config.py`, use the
`VELACORE_` environment variable prefix, and are loaded from environment
variables plus a local `.env` file in the current working directory.

| Setting | Environment variable | Default |
|---------|----------------------|---------|
| `app_name` | `VELACORE_APP_NAME` | `api_velacore` |
| `app_version` | `VELACORE_APP_VERSION` | `0.1.0` |
| `twelve_data_api_key` | `VELACORE_TWELVE_DATA_API_KEY` | `None` |

Environment variable example:

```bash
VELACORE_APP_NAME="Velacore API" uvicorn api_velacore.main:app --reload
```

Local `.env` example:

```bash
cat > .env <<'EOF'
VELACORE_TWELVE_DATA_API_KEY=your-api-key
EOF

.venv/bin/python -m uvicorn api_velacore.main:app --reload --port 8766
```

The `.env` file is ignored by Git; do not commit real provider API keys.

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
