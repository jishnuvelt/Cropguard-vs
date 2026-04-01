import pytest

pytest.importorskip("httpx")

from app.main import app


def test_weather_endpoint_missing_api_key_returns_server_error(monkeypatch):
    from fastapi.testclient import TestClient

    monkeypatch.delenv("OPENWEATHER_API_KEY", raising=False)

    client = TestClient(app)
    response = client.get("/api/weather/current", params={"city": "Chennai"})

    assert response.status_code == 500
    assert "OPENWEATHER_API_KEY" in response.json()["detail"]


def test_weather_endpoint_city_not_found_maps_to_404(monkeypatch):
    from fastapi.testclient import TestClient
    from app import main as main_module
    from app.weather import WeatherServiceError

    def fake_fetch(city: str, units: str = "metric"):
        raise WeatherServiceError("City not found. Check spelling and try again.", status_code=404)

    monkeypatch.setattr(main_module, "fetch_current_weather_from_env", fake_fetch)

    client = TestClient(app)
    response = client.get("/api/weather/current", params={"city": "NoSuchCity"})

    assert response.status_code == 404
    assert "City not found" in response.json()["detail"]
