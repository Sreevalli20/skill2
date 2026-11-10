# Weather Information App

A polished, responsive web-based weather dashboard built with Python 3.14.6, Flask, HTML5, CSS3, and JavaScript. It resolves any city name via the [Open-Meteo](https://open-meteo.com/) API — **no API key, account, or subscription required** — and displays current conditions plus a 5-day forecast.

## Features

- Search weather by city name (supports spaces and special characters)
- Displays resolved city, region/state, and country
- Current temperature, feels-like temperature, humidity, wind speed, cloud cover, precipitation
- Weather condition with icon and human-readable label (WMO weather-code mapping)
- Observation/update time and location timezone
- 5-day forecast cards
- Celsius/Fahrenheit toggle
- Recent search history stored in the browser (localStorage)
- Loading indicator and friendly error messages (empty input, city not found, network failure, timeout, API errors)
- Responsive design for desktop and mobile; no external image assets required

## Technology Stack

- **Python 3.14.6** — backend (standard library `urllib` for HTTP; no `requests` needed)
- **Flask 3.x** — web framework (only dependency)
- **HTML5 / CSS3 / JavaScript** — frontend dashboard
- **Open-Meteo REST API** — free weather data, no API key for non-commercial use

## Project Structure

```
weather-app/
├── app.py                  # Flask routes (/ and /api/weather)
├── weather_service.py      # Open-Meteo geocoding + forecast client
├── requirements.txt
├── .gitignore
├── templates/
│   └── index.html          # Dashboard markup
├── static/
│   ├── css/style.css       # Dashboard styling
│   └── js/script.js        # Search, rendering, unit toggle, history
└── tests/
    ├── __init__.py
    └── test_weather_app.py # Unit tests (HTTP fully mocked)
```

## Requirements

- Python **3.14.6** (tested on this version)
- Flask `>=3.0,<4.0`

## Installation

```bash
cd weather-app
python -m pip install -r requirements.txt
```

## Running the Application

```bash
python app.py
```

Then open <http://127.0.0.1:5000> in a browser.

Alternatively, without the debug server:

```bash
flask --app app run
```

## API Information

- Geocoding: `https://geocoding-api.open-meteo.com/v1/search` — resolves city names to latitude/longitude.
- Forecast: `https://api.open-meteo.com/v1/forecast` — current weather variables and a 5-day daily forecast.

Open-Meteo is free for non-commercial use and does **not** require an API key. All requests use HTTPS with a 10-second timeout via Python's standard-library `urllib`.

## Running Tests

```bash
cd weather-app
python -m unittest discover -s tests -v
```

All external HTTP requests are mocked, so tests run without internet access.

## Limitations

- Weather data resolution depends on Open-Meteo coverage; very small or ambiguous place names may not resolve.
- Temperature unit conversion (°C ↔ °F) is done in the browser; wind speed is always shown in km/h.
- Forecast is limited to 5 days.
- This project is intended for academic/non-commercial use per Open-Meteo's terms.

## Attribution

Weather data by [Open-Meteo.com](https://open-meteo.com/) — free open-source weather API.
