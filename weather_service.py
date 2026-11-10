"""Weather data service backed by the Open-Meteo API (no API key required)."""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
REQUEST_TIMEOUT = 10

# WMO weather interpretation codes -> human-readable condition + icon key.
WEATHER_CODES: dict[int, tuple[str, str]] = {
    0: ("Clear sky", "clear"),
    1: ("Mainly clear", "clear"),
    2: ("Partly cloudy", "partly-cloudy"),
    3: ("Overcast", "overcast"),
    45: ("Fog", "fog"),
    48: ("Rime fog", "fog"),
    51: ("Light drizzle", "drizzle"),
    53: ("Drizzle", "drizzle"),
    55: ("Heavy drizzle", "drizzle"),
    56: ("Freezing drizzle", "drizzle"),
    57: ("Freezing drizzle", "drizzle"),
    61: ("Light rain", "rain"),
    63: ("Rain", "rain"),
    65: ("Heavy rain", "rain"),
    66: ("Freezing rain", "rain"),
    67: ("Freezing rain", "rain"),
    71: ("Light snow", "snow"),
    73: ("Snow", "snow"),
    75: ("Heavy snow", "snow"),
    77: ("Snow grains", "snow"),
    80: ("Rain showers", "rain-shower"),
    81: ("Rain showers", "rain-shower"),
    82: ("Violent rain showers", "rain-shower"),
    85: ("Snow showers", "snow-shower"),
    86: ("Heavy snow showers", "snow-shower"),
    95: ("Thunderstorm", "thunderstorm"),
    96: ("Thunderstorm with hail", "thunderstorm"),
    99: ("Thunderstorm with hail", "thunderstorm"),
}

CURRENT_VARIABLES = (
    "temperature_2m,relative_humidity_2m,apparent_temperature,is_day,"
    "precipitation,weather_code,cloud_cover,wind_speed_10m"
)
DAILY_VARIABLES = "weather_code,temperature_2m_max,temperature_2m_min"


class WeatherServiceError(Exception):
    """Base error raised by the weather service."""


class CityNotFoundError(WeatherServiceError):
    """Raised when the geocoding API cannot resolve a city name."""


class EmptyCityError(WeatherServiceError):
    """Raised when the requested city name is empty."""


def _http_get_json(url: str, timeout: int = REQUEST_TIMEOUT) -> Any:
    """Perform an HTTPS GET request and parse the JSON response."""
    request = urllib.request.Request(url, headers={"User-Agent": "weather-app/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise WeatherServiceError(f"Weather API returned HTTP error {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise WeatherServiceError("Could not reach the weather service. Check your internet connection.") from exc
    except json.JSONDecodeError as exc:
        raise WeatherServiceError("The weather service returned an unexpected response.") from exc
    except TimeoutError as exc:
        raise WeatherServiceError("The weather service timed out. Please try again.") from exc


def _value_or_na(value: Any) -> Any:
    return "Not available" if value is None else value


def describe_weather_code(code: int | None) -> tuple[str, str]:
    """Map a WMO weather code to (label, icon key)."""
    if code is None:
        return ("Not available", "unknown")
    return WEATHER_CODES.get(code, ("Unknown", "unknown"))


def celsius_to_fahrenheit(celsius: float) -> float:
    """Convert Celsius to Fahrenheit."""
    return celsius * 9 / 5 + 32


def find_city(query: str) -> dict[str, Any]:
    """Resolve a city name to a location using the Open-Meteo geocoding API."""
    query = query.strip()
    if not query:
        raise EmptyCityError("Please enter a city name.")

    params = urllib.parse.urlencode({"name": query, "count": 1, "language": "en", "format": "json"})
    data = _http_get_json(f"{GEOCODING_URL}?{params}")

    results = data.get("results") if isinstance(data, dict) else None
    if not results:
        raise CityNotFoundError(f"No location found for '{query}'. Try a different city name.")

    location = results[0]
    return {
        "name": location.get("name"),
        "admin1": location.get("admin1"),
        "country": location.get("country"),
        "latitude": location.get("latitude"),
        "longitude": location.get("longitude"),
    }


def get_weather(location: dict[str, Any]) -> dict[str, Any]:
    """Fetch current weather and a 5-day forecast for a resolved location."""
    params = {
        "latitude": location["latitude"],
        "longitude": location["longitude"],
        "current": CURRENT_VARIABLES,
        "daily": DAILY_VARIABLES,
        "timezone": "auto",
        "forecast_days": 5,
    }
    url = f"{FORECAST_URL}?{urllib.parse.urlencode(params)}"
    data = _http_get_json(url)

    if not isinstance(data, dict) or not isinstance(data.get("current"), dict):
        raise WeatherServiceError("The weather service returned an unexpected response.")

    current = data["current"]
    condition, icon = describe_weather_code(current.get("weather_code"))
    forecast = []
    daily = data.get("daily")
    if isinstance(daily, dict):
        for index, day_code in enumerate(daily.get("weather_code") or []):
            day_condition, day_icon = describe_weather_code(day_code)
            forecast.append(
                {
                    "date": (daily.get("time") or [None] * (index + 1))[index],
                    "condition": day_condition,
                    "icon": day_icon,
                    "temp_max": _value_or_na((daily.get("temperature_2m_max") or [None] * (index + 1))[index]),
                    "temp_min": _value_or_na((daily.get("temperature_2m_min") or [None] * (index + 1))[index]),
                }
            )

    return {
        "location": {
            "name": _value_or_na(location.get("name")),
            "region": _value_or_na(location.get("admin1")),
            "country": _value_or_na(location.get("country")),
        },
        "current": {
            "temperature": _value_or_na(current.get("temperature_2m")),
            "feels_like": _value_or_na(current.get("apparent_temperature")),
            "humidity": _value_or_na(current.get("relative_humidity_2m")),
            "wind_speed": _value_or_na(current.get("wind_speed_10m")),
            "cloud_cover": _value_or_na(current.get("cloud_cover")),
            "precipitation": _value_or_na(current.get("precipitation")),
            "condition": condition,
            "icon": icon,
            "is_day": current.get("is_day"),
            "time": current.get("time"),
            "timezone": data.get("timezone"),
        },
        "daily": forecast,
    }


def get_weather_for_city(city: str) -> dict[str, Any]:
    """End-to-end lookup: resolve the city, then fetch its weather."""
    location = find_city(city)
    return get_weather(location)
