"""Unit tests for the Weather Information App.

All external HTTP calls are mocked so the suite runs without internet access.
"""

from __future__ import annotations

import io
import json
import unittest
import urllib.error
from unittest import mock

import weather_service
from app import app
from weather_service import (
    CityNotFoundError,
    EmptyCityError,
    WeatherServiceError,
    celsius_to_fahrenheit,
    describe_weather_code,
    find_city,
    get_weather,
    get_weather_for_city,
)

GEOCODE_RESPONSE = {
    "results": [
        {
            "name": "Hyderabad",
            "admin1": "Telangana",
            "country": "India",
            "latitude": 17.385,
            "longitude": 78.4867,
        }
    ]
}

WEATHER_RESPONSE = {
    "timezone": "Asia/Kolkata",
    "current": {
        "time": "2026-11-10T14:00",
        "temperature_2m": 28.5,
        "relative_humidity_2m": 65,
        "apparent_temperature": 31.2,
        "is_day": 1,
        "precipitation": 0.0,
        "weather_code": 2,
        "cloud_cover": 45,
        "wind_speed_10m": 12.3,
    },
    "daily": {
        "time": ["2026-11-10", "2026-11-11"],
        "weather_code": [2, 61],
        "temperature_2m_max": [30.0, 29.0],
        "temperature_2m_min": [22.0, 21.0],
    },
}

LOCATION = {
    "name": "Hyderabad",
    "admin1": "Telangana",
    "country": "India",
    "latitude": 17.385,
    "longitude": 78.4867,
}


def _fake_response(payload):
    body = json.dumps(payload).encode("utf-8")
    return io.BytesIO(body)


class FakeHTTP:
    """Context-manager stand-in for urllib.request.urlopen."""

    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return _fake_response(self.payload)

    def __exit__(self, *args):
        return False


class GeocodingTests(unittest.TestCase):
    def test_valid_city_search(self):
        with mock.patch.object(weather_service.urllib.request, "urlopen", return_value=FakeHTTP(GEOCODE_RESPONSE)):
            loc = find_city("Hyderabad")
        self.assertEqual(loc["name"], "Hyderabad")
        self.assertEqual(loc["country"], "India")
        self.assertAlmostEqual(loc["latitude"], 17.385)

    def test_city_with_spaces_and_special_chars(self):
        with mock.patch.object(weather_service.urllib.request, "urlopen", return_value=FakeHTTP(GEOCODE_RESPONSE)) as m:
            find_city("  New York  ")
        url = m.call_args[0][0].full_url
        self.assertIn("name=New+York", url)

    def test_empty_input(self):
        with self.assertRaises(EmptyCityError):
            find_city("   ")

    def test_invalid_city(self):
        with mock.patch.object(weather_service.urllib.request, "urlopen", return_value=FakeHTTP({"results": []})):
            with self.assertRaises(CityNotFoundError):
                find_city("Nowhereville")

    def test_malformed_response(self):
        with mock.patch.object(weather_service.urllib.request, "urlopen", return_value=FakeHTTP({"unexpected": True})):
            with self.assertRaises(CityNotFoundError):
                find_city("Somewhere")


class WeatherParsingTests(unittest.TestCase):
    def test_successful_weather_parsing(self):
        with mock.patch.object(weather_service.urllib.request, "urlopen", return_value=FakeHTTP(WEATHER_RESPONSE)):
            result = get_weather(LOCATION)
        cur = result["current"]
        self.assertEqual(cur["temperature"], 28.5)
        self.assertEqual(cur["humidity"], 65)
        self.assertEqual(cur["condition"], "Partly cloudy")
        self.assertEqual(cur["icon"], "partly-cloudy")
        self.assertEqual(result["location"]["name"], "Hyderabad")
        self.assertEqual(len(result["daily"]), 2)
        self.assertEqual(result["daily"][1]["condition"], "Light rain")

    def test_missing_weather_fields(self):
        sparse = {"current": {"temperature_2m": 20.0, "weather_code": None}}
        with mock.patch.object(weather_service.urllib.request, "urlopen", return_value=FakeHTTP(sparse)):
            result = get_weather(LOCATION)
        cur = result["current"]
        self.assertEqual(cur["temperature"], 20.0)
        self.assertEqual(cur["humidity"], "Not available")
        self.assertEqual(cur["condition"], "Not available")

    def test_unexpected_structure(self):
        with mock.patch.object(weather_service.urllib.request, "urlopen", return_value=FakeHTTP({"foo": 1})):
            with self.assertRaises(WeatherServiceError):
                get_weather(LOCATION)

    def test_end_to_end_city_weather(self):
        responses = iter([GEOCODE_RESPONSE, WEATHER_RESPONSE])

        def fake_urlopen(request, timeout=None):
            return FakeHTTP(next(responses))

        with mock.patch.object(weather_service.urllib.request, "urlopen", side_effect=fake_urlopen):
            result = get_weather_for_city("Hyderabad")
        self.assertEqual(result["location"]["name"], "Hyderabad")
        self.assertEqual(result["current"]["wind_speed"], 12.3)


class ErrorHandlingTests(unittest.TestCase):
    def test_timeout(self):
        with mock.patch.object(
            weather_service.urllib.request,
            "urlopen",
            side_effect=TimeoutError("timed out"),
        ):
            with self.assertRaises(WeatherServiceError):
                find_city("Paris")

    def test_network_failure(self):
        with mock.patch.object(
            weather_service.urllib.request,
            "urlopen",
            side_effect=urllib.error.URLError("no route"),
        ):
            with self.assertRaises(WeatherServiceError):
                find_city("Paris")

    def test_invalid_json(self):
        class BadJSON:
            def __enter__(self):
                return io.BytesIO(b"not json{{{")

            def __exit__(self, *args):
                return False

        with mock.patch.object(weather_service.urllib.request, "urlopen", return_value=BadJSON()):
            with self.assertRaises(WeatherServiceError):
                find_city("Paris")

    def test_http_error(self):
        with mock.patch.object(
            weather_service.urllib.request,
            "urlopen",
            side_effect=urllib.error.HTTPError("http://x", 500, "err", {}, None),
        ):
            with self.assertRaises(WeatherServiceError):
                find_city("Paris")


class MappingTests(unittest.TestCase):
    def test_temperature_conversion(self):
        self.assertAlmostEqual(celsius_to_fahrenheit(0), 32.0)
        self.assertAlmostEqual(celsius_to_fahrenheit(100), 212.0)
        self.assertAlmostEqual(celsius_to_fahrenheit(28.5), 83.3, places=1)

    def test_weather_code_mapping(self):
        cases = {
            0: ("Clear sky", "clear"),
            1: ("Mainly clear", "clear"),
            2: ("Partly cloudy", "partly-cloudy"),
            3: ("Overcast", "overcast"),
            45: ("Fog", "fog"),
            61: ("Light rain", "rain"),
            71: ("Light snow", "snow"),
            95: ("Thunderstorm", "thunderstorm"),
        }
        for code, expected in cases.items():
            self.assertEqual(describe_weather_code(code), expected)
        self.assertEqual(describe_weather_code(None), ("Not available", "unknown"))
        self.assertEqual(describe_weather_code(999), ("Unknown", "unknown"))


class RouteTests(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_index_route(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Weather", resp.data)

    def test_api_empty_city(self):
        resp = self.client.get("/api/weather?city=")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("error", resp.get_json())

    def test_api_city_not_found(self):
        with mock.patch.object(
            weather_service.urllib.request,
            "urlopen",
            return_value=FakeHTTP({"results": []}),
        ):
            resp = self.client.get("/api/weather?city=Nowhereville")
        self.assertEqual(resp.status_code, 404)
        self.assertIn("error", resp.get_json())

    def test_api_success(self):
        responses = iter([GEOCODE_RESPONSE, WEATHER_RESPONSE])

        def fake_urlopen(request, timeout=None):
            return FakeHTTP(next(responses))

        with mock.patch.object(weather_service.urllib.request, "urlopen", side_effect=fake_urlopen):
            resp = self.client.get("/api/weather?city=Hyderabad")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertEqual(data["location"]["name"], "Hyderabad")
        self.assertEqual(data["current"]["temperature"], 28.5)

    def test_api_service_error(self):
        with mock.patch.object(
            weather_service.urllib.request,
            "urlopen",
            side_effect=urllib.error.URLError("down"),
        ):
            resp = self.client.get("/api/weather?city=Paris")
        self.assertEqual(resp.status_code, 502)
        self.assertIn("error", resp.get_json())


if __name__ == "__main__":
    unittest.main()
