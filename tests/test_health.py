import unittest

from fastapi.testclient import TestClient

from api_velacore.main import app
from api_velacore.schemas.health import HealthResponse
from api_velacore.services.health import get_health_status

_CHECK = unittest.TestCase()


def test_health_returns_ok() -> None:
    client = TestClient(app)

    response = client.get("/health")

    _CHECK.assertEqual(response.status_code, 200)
    _CHECK.assertTrue(response.headers["content-type"].startswith("application/json"))
    _CHECK.assertEqual(response.json(), {"status": "ok"})


def test_openapi_schema_is_available() -> None:
    client = TestClient(app)

    response = client.get("/openapi.json")

    _CHECK.assertEqual(response.status_code, 200)
    schema = response.json()
    _CHECK.assertEqual(schema["info"], {"title": "api_velacore", "version": "0.1.0"})
    _CHECK.assertEqual(
        schema["paths"]["/health"]["get"]["responses"]["200"]["content"],
        {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/HealthResponse"}
            }
        },
    )


def test_health_service_returns_typed_ok_response() -> None:
    health = get_health_status()

    _CHECK.assertIsInstance(health, HealthResponse)
    _CHECK.assertEqual(health.status, "ok")
