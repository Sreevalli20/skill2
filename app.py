"""Flask application for the Weather Information App."""

from __future__ import annotations

import logging

from flask import Flask, jsonify, render_template, request

from weather_service import (
    CityNotFoundError,
    EmptyCityError,
    WeatherServiceError,
    get_weather_for_city,
)

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@app.get("/")
def index() -> str:
    return render_template("index.html")


@app.get("/api/weather")
def api_weather() -> tuple:
    city = request.args.get("city", "")
    try:
        return jsonify(get_weather_for_city(city))
    except EmptyCityError as exc:
        return jsonify({"error": str(exc)}), 400
    except CityNotFoundError as exc:
        return jsonify({"error": str(exc)}), 404
    except WeatherServiceError as exc:
        return jsonify({"error": str(exc)}), 502
    except Exception:
        logger.exception("Unexpected error while fetching weather")
        return jsonify({"error": "Something went wrong while fetching the weather. Please try again."}), 500


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
