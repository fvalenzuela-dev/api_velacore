# api_velacore

FastAPI backend base for Velacore.

## Runtime

This project strictly targets Python `3.14.5`.

The runtime is declared in:

- `.python-version`
- `pyproject.toml` with `requires-python = "==3.14.5"`

## Setup

Create and activate a virtual environment with Python `3.14.5`, then install the project with development tools:

```bash
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

## Run Locally

```bash
uvicorn api_velacore.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

## Health Check

```bash
curl http://127.0.0.1:8000/health
```

Expected response:

```json
{"status":"ok"}
```

## Swagger and OpenAPI

FastAPI interactive documentation is enabled with the default endpoints:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`

## Tests and Quality Checks

Run the test suite:

```bash
pytest
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

## Architecture Guidelines

The project uses a `src/` layout and separates FastAPI concerns by responsibility:

- `src/api_velacore/main.py`: FastAPI application factory and app instance.
- `src/api_velacore/api/routes/`: HTTP route definitions.
- `src/api_velacore/core/`: application configuration and core settings.
- `src/api_velacore/schemas/`: Pydantic request and response schemas.
- `src/api_velacore/services/`: business logic independent from HTTP details.
- `src/api_velacore/infrastructure/`: external systems such as databases, queues, or HTTP clients.
- `src/api_velacore/utils/`: small shared helpers with no framework coupling.
- `tests/`: automated tests mirroring externally visible behavior.

Keep route handlers thin: validate input, delegate behavior to services, and return typed schemas. Avoid placing business rules or infrastructure access directly in route modules.
