import pytest
from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"EmeraldFlow" in response.data


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "UP"
    assert data["service"] == "emeraldflow-app"
    assert data["runtime"] == "python"


def test_db_status_disconnected_graceful(client):
    response = client.get("/db-status")
    assert response.status_code in [200, 503]
    data = response.get_json()
    assert "database" in data
