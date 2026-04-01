from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

OPENWEATHER_CURRENT_URL = "https://api.openweathermap.org/data/2.5/weather"
ALLOWED_UNITS = {"standard", "metric", "imperial"}


class WeatherServiceError(Exception):
    """Raised when weather data cannot be fetched or parsed."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.status_code = status_code


def _parse_observed_at(value: Any) -> str | None:
    if not isinstance(value, (int, float)):
        return None
    return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()


def _normalize_weather_payload(payload: dict[str, Any]) -> dict[str, Any]:
    main = payload.get("main") if isinstance(payload.get("main"), dict) else {}
    sys_data = payload.get("sys") if isinstance(payload.get("sys"), dict) else {}
    weather_list = payload.get("weather") if isinstance(payload.get("weather"), list) else []
    weather_first = weather_list[0] if weather_list and isinstance(weather_list[0], dict) else {}

    return {
        "city": payload.get("name") or "Unknown",
        "country": sys_data.get("country"),
        "observed_at_utc": _parse_observed_at(payload.get("dt")),
        "temperature_c": main.get("temp"),
        "feels_like_c": main.get("feels_like"),
        "humidity_percent": main.get("humidity"),
        "condition": weather_first.get("main"),
        "condition_detail": weather_first.get("description"),
    }


def fetch_current_weather(city: str, api_key: str, units: str = "metric") -> dict[str, Any]:
    cleaned_city = city.strip()
    cleaned_key = api_key.strip()
    cleaned_units = units.strip().lower()

    if not cleaned_city:
        raise WeatherServiceError("City is required.", status_code=400)
    if not cleaned_key:
        raise WeatherServiceError("OpenWeather API key is required.", status_code=500)
    if cleaned_units not in ALLOWED_UNITS:
        raise WeatherServiceError("Units must be one of: standard, metric, imperial.", status_code=400)

    params = {
        "q": cleaned_city,
        "appid": cleaned_key,
        "units": cleaned_units,
    }

    try:
        query = urlencode(params)
        url = f"{OPENWEATHER_CURRENT_URL}?{query}"
        with urlopen(url, timeout=10) as response:
            status_code = response.status if hasattr(response, "status") else response.getcode()
            raw_body = response.read().decode("utf-8")
    except HTTPError as exc:
        status_code = exc.code
        raw_body = exc.read().decode("utf-8", errors="replace")
    except URLError as exc:
        raise WeatherServiceError("Unable to reach weather provider right now.", status_code=503) from exc

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError as exc:
        raise WeatherServiceError("Weather provider returned an invalid response.", status_code=502) from exc

    if status_code == 401:
        raise WeatherServiceError("Invalid OpenWeather API key.", status_code=500)
    if status_code == 404:
        raise WeatherServiceError("City not found. Check spelling and try again.", status_code=404)
    if status_code != 200:
        detail = payload.get("message") if isinstance(payload, dict) else None
        raise WeatherServiceError(f"Weather API request failed: {detail or status_code}.", status_code=502)

    return _normalize_weather_payload(payload)


def fetch_current_weather_from_env(city: str, units: str = "metric") -> dict[str, Any]:
    api_key = os.getenv("OPENWEATHER_API_KEY", "").strip()
    if not api_key:
        raise WeatherServiceError("Missing OPENWEATHER_API_KEY environment variable.", status_code=500)
    return fetch_current_weather(city=city, api_key=api_key, units=units)
