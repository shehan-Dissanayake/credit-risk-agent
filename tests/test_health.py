from fastapi.testclient import TestClient

from credit_risk_agent import __version__
from credit_risk_agent.api.main import app


def test_health_ok() -> None:
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__
