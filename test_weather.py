from io import BytesIO
from urllib.error import HTTPError

import pytest

from app.weather import WeatherServiceError, fetch_current_weather, fetch_current_weather_from_env


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict, reason: str = "OK") -> None:
        self.status = status_code
        self._payload = payload
        self.reason = reason

    def read(self) -> bytes:
        import json

        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_fetch_current_weather_success(monkeypatch: pytest.MonkeyPatch) -> None:
    payload = {
        "name": "Chennai",
        "sys": {"country": "IN"},
        "dt": 1711944000,
        "main": {"temp": 31.4, "feels_like": 37.1, "humidity": 73},
        "weather": [{"main": "Clouds", "description": "scattered clouds"}],
    }

    def fake_get(*_args, **_kwargs):
        return _FakeResponse(status_code=200, payload=payload)

    monkeypatch.setattr("app.weather.urlopen", fake_get)

    result = fetch_current_weather(city="Chennai", api_key="test-key", units="metric")

    assert result["city"] == "Chennai"
    assert result["country"] == "IN"
    assert result["temperature_c"] == 31.4
    assert result["humidity_percent"] == 73
    assert result["condition"] == "Clouds"


def test_fetch_current_weather_city_not_found(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get(*_args, **_kwargs):
        error_payload = b"{\"message\": \"city not found\"}"
        raise HTTPError(
            url="https://api.openweathermap.org/data/2.5/weather",
            code=404,
            msg="Not Found",
            hdrs=None,
            fp=BytesIO(error_payload),
        )

    monkeypatch.setattr("app.weather.urlopen", fake_get)

    with pytest.raises(WeatherServiceError, match="City not found") as exc:
        fetch_current_weather(city="NoSuchCity", api_key="test-key")

    assert exc.value.status_code == 404


def test_fetch_current_weather_requires_api_key_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENWEATHER_API_KEY", raising=False)

    with pytest.raises(WeatherServiceError, match="Missing OPENWEATHER_API_KEY") as exc:
        fetch_current_weather_from_env(city="Chennai")

    assert exc.value.status_code == 500
