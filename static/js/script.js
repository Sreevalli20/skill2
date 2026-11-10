"use strict";

const ICONS = {
  "clear": "☀️",
  "partly-cloudy": "⛅",
  "overcast": "☁️",
  "fog": "🌫️",
  "drizzle": "🌦️",
  "rain": "🌧️",
  "rain-shower": "🌧️",
  "snow": "🌨️",
  "snow-shower": "🌨️",
  "thunderstorm": "⛈️",
  "unknown": "🌡️",
};

const HISTORY_KEY = "weatherAppHistory";
const MAX_HISTORY = 8;

let currentWeather = null;
let unit = "C";

const $ = (id) => document.getElementById(id);
const form = $("search-form");
const input = $("city-input");
const statusEl = $("status");
const errorEl = $("error");
const card = $("weather-card");

function showStatus(msg) {
  statusEl.textContent = msg || "";
}

function showError(msg) {
  errorEl.textContent = msg || "";
  errorEl.hidden = !msg;
}

function toDisplayTemp(celsius) {
  if (celsius === null || celsius === undefined || typeof celsius !== "number") {
    return "Not available";
  }
  const value = unit === "F" ? (celsius * 9) / 5 + 32 : celsius;
  return `${value.toFixed(1)}°${unit}`;
}

function fmtNumber(value, suffix = "") {
  return typeof value === "number" ? `${value}${suffix}` : "Not available";
}

function renderWeather(data) {
  const cur = data.current;
  const loc = data.location;

  $("location-name").textContent = [loc.name, loc.region, loc.country]
    .filter((v) => v && v !== "Not available")
    .join(", ");
  $("location-detail").textContent = `${loc.name}${loc.region ? ` · ${loc.region}` : ""}`;

  const timeStr = cur.time
    ? `${cur.time.replace("T", " ")} (${cur.timezone || "local time"})`
    : "Not available";
  $("observed-time").textContent = `Updated: ${timeStr}`;

  $("weather-icon").textContent = ICONS[cur.icon] || ICONS.unknown;
  $("temperature").textContent = toDisplayTemp(cur.temperature);
  $("condition").textContent = cur.condition || "Not available";

  $("feels-like").textContent = toDisplayTemp(cur.feels_like);
  $("humidity").textContent = fmtNumber(cur.humidity, "%");
  $("wind").textContent = fmtNumber(cur.wind_speed, " km/h");
  $("cloud-cover").textContent = fmtNumber(cur.cloud_cover, "%");
  $("precipitation").textContent = fmtNumber(cur.precipitation, " mm");

  renderForecast(data.daily || []);
  card.hidden = false;
}

function renderForecast(days) {
  const wrap = $("forecast");
  const list = $("forecast-list");
  list.innerHTML = "";

  if (!days.length) {
    wrap.hidden = true;
    return;
  }

  for (const day of days) {
    const el = document.createElement("div");
    el.className = "forecast-day";
    const dateLabel = day.date ? day.date.slice(5).replace("-", "/") : "—";
    el.innerHTML = `
      <span>${dateLabel}</span>
      <span class="forecast-icon">${ICONS[day.icon] || ICONS.unknown}</span>
      <span>${day.condition || "Not available"}</span>
      <span class="forecast-temps">${toDisplayTemp(day.temp_max)} / ${toDisplayTemp(day.temp_min)}</span>
    `;
    list.appendChild(el);
  }
  wrap.hidden = false;
}

function getHistory() {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY)) || [];
  } catch {
    return [];
  }
}

function addToHistory(city) {
  const name = city.trim();
  if (!name) return;
  let history = getHistory().filter((c) => c.toLowerCase() !== name.toLowerCase());
  history.unshift(name);
  history = history.slice(0, MAX_HISTORY);
  localStorage.setItem(HISTORY_KEY, JSON.stringify(history));
  renderHistory();
}

function renderHistory() {
  const section = $("history");
  const list = $("history-list");
  list.innerHTML = "";
  const history = getHistory();
  section.hidden = history.length === 0;
  for (const city of history) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.textContent = city;
    btn.addEventListener("click", () => {
      input.value = city;
      search(city);
    });
    list.appendChild(btn);
  }
}

async function search(city) {
  const trimmed = (city || input.value).trim();
  if (!trimmed) {
    showError("Please enter a city name.");
    return;
  }

  showError(null);
  card.hidden = true;
  showStatus("Loading weather...");

  try {
    const res = await fetch(`/api/weather?city=${encodeURIComponent(trimmed)}`);
    const data = await res.json();
    showStatus(null);

    if (!res.ok) {
      showError(data.error || "Could not fetch the weather. Please try again.");
      return;
    }

    currentWeather = data;
    renderWeather(data);
    addToHistory(trimmed);
  } catch (err) {
    showStatus(null);
    showError("Network error. Check your internet connection and try again.");
  }
}

form.addEventListener("submit", (e) => {
  e.preventDefault();
  search(input.value);
});

$("unit-c").addEventListener("click", () => setUnit("C"));
$("unit-f").addEventListener("click", () => setUnit("F"));

function setUnit(next) {
  unit = next;
  $("unit-c").classList.toggle("active", unit === "C");
  $("unit-c").setAttribute("aria-pressed", String(unit === "C"));
  $("unit-f").classList.toggle("active", unit === "F");
  $("unit-f").setAttribute("aria-pressed", String(unit === "F"));
  if (currentWeather) renderWeather(currentWeather);
}

renderHistory();
