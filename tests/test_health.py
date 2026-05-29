from fastapi.testclient import TestClient

from api_velacore.main import app
from api_velacore.schemas.health import HealthResponse
from api_velacore.services.health import get_health_status


def test_health_returns_ok() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"status": "ok"}


def test_openapi_schema_is_available() -> None:
    client = TestClient(app)

    response = client.get("/openapi.json")

    assert response.status_code == 200
    schema = response.json()
    assert schema["info"] == {"title": "api_velacore", "version": "0.1.0"}
    assert schema["paths"]["/health"]["get"]["responses"]["200"]["content"] == {
        "application/json": {"schema": {"$ref": "#/components/schemas/HealthResponse"}}
    }


def test_health_service_returns_typed_ok_response() -> None:
    health = get_health_status()

    assert isinstance(health, HealthResponse)
    assert health.status == "ok"
