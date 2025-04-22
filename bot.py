import requests
import json
import time
from datetime import datetime, timezone
from pathlib import Path

# ─── USTAWIENIA ───────────────────────────────────────────────────────────────

# Miasta do pobrania pogody
CITIES = {
    "Warsaw": "Warsaw",
    "Kraków": "Krakow",
    "Gdańsk": "Gdansk"
}

# Waluty do pobrania kursów (PLN → …)
CURRENCY_PAIRS = ["USD", "EUR"]

# Indeksy giełdowe (Yahoo Finance)
INDICES = ["^WIG20", "^GSPC", "^GDAXI"]

# URL do pobierania historii z gałęzi gh‑pages
GITHUB_RAW_URL = (
    "https://raw.githubusercontent.com/MatteoBarzotto/"
    "bot-pogodowy-automatyzacja/gh-pages/history.json"
)

HISTORY_FILE = Path("history.json")
OUTPUT_HTML  = Path("index.html")

# ─── FUNKCJE POBIERAJĄCE ─────────────────────────────────────────────────────

def fetch_weather(city_code):
    url = f"https://wttr.in/{city_code}?format=3"
    resp = requests.get(url)
    return resp.text.strip()

def fetch_rates():
    rates = {}
    for cur in CURRENCY_PAIRS:
        url = f"http://api.nbp.pl/api/exchangerates/rates/a/{cur}/?format=json"
        resp = requests.get(url)
        if resp.status_code != 200:
            print(f"⚠️ Ostrzeżenie: HTTP {resp.status_code} przy pobieraniu kursu {cur}")
            continue
        try:
            data = resp.json()
            mid = data["rates"][0]["mid"]
            rates[cur] = mid
        except Exception as e:
            print(f"⚠️ Błąd parsowania kursu {cur}:", e)
    return rates

def fetch_indices():
    url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={','.join(INDICES)}"
    max_attempts = 3
    backoff = 5

    for attempt in range(1, max_attempts + 1):
        resp = requests.get(url)
        if resp.status_code == 200:
            try:
                data = resp.json()
            except ValueError:
                print("⚠️ Ostrzeżenie: odpowiedź z indeksów nie jest JSON-em")
                return {}
            qr = data.get("quoteResponse", {})
            results = qr.get("result", [])
            out = {}
            for q in results:
                sym = q.get("symbol")
                price = q.get("regularMarketPrice")
                if sym and price is not None:
                    out[sym] = price
            return out

        elif resp.status_code == 429:
            if attempt < max_attempts:
                print(f"⚠️ 429 limit prób {attempt}, czekam {backoff}s...")
                time.sleep(backoff)
                backoff *= 2
                continue
            else:
                print("⚠️ Osiągnięto limit 429, zwracam pusty zestaw.")
                return {}

        else:
            print(f"⚠️ Ostrzeżenie: HTTP {resp.status_code} przy pobieraniu indeksów")
            return {}

    return {}

# ─── ŁADOWANIE HISTORII ────────────────────────────────────────────────────────

try:
    resp = requests.get(GITHUB_RAW_URL)
    resp.raise_for_status()
    history = resp.json()
except Exception:
    history = []

# ─── ZBIERANIE DZIŚSZYCH DANYCH ───────────────────────────────────────────────

today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
today = {
    "date": today_str,
    "weather": {city: fetch_weather(code) for city, code in CITIES.items()},
    "rates": fetch_rates(),
    "indices": fetch_indices()
}

# Aktualizujemy historię
history = [h for h in history if h.get("date") != today_str]
history.insert(0, today)
history = history[:7]
HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

# ─── PRZYGOTOWANIE HTML-LIST ────────────────────────────────────────────────

weather_list = "".join(
    f"<li><strong>{city}:</strong> {w}</li>\n"
    for city, w in today["weather"].items()
)

rates_list = "".join(
    f"<li><strong>{cur}:</strong> {rate:.2f}</li>\n"
    for cur, rate in today["rates"].items()
)

indices_list = "".join(
    f"<li><strong>{idx}:</strong> {val:.2f}</li>\n"
    for idx, val in today["indices"].items()
)

# ─── GENEROWANIE TABELKI HISTORYCZNEJ ────────────────────────────────────────

rows_history = ""
for entry in history:
    weas_str   = "<br>".join(entry["weather"].values())
    rates_str  = " | ".join(f"{k}: {v:.2f}" for k, v in entry["rates"].items())
    inds_str   = " | ".join(f"{k}: {v:.2f}" for k, v in entry["indices"].items())
    rows_history += (
        f"<tr>"
        f"<td>{entry['date']}</td>"
        f"<td>{weas_str}</td>"
        f"<td>{rates_str}</td>"
        f"<td>{inds_str}</td>"
        f"</tr>\n"
    )

# ─── DANE DLA JS ─────────────────────────────────────────────────────────────

history_json = json.dumps(history, ensure_ascii=False)
today_json   = json.dumps(today, ensure_ascii=False)

# ─── GENEROWANIE STRONY HTML ─────────────────────────────────────────────────

html_template = f"""<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="utf-8">
  <title>Dashboard bota</title>
  <style>
    body {{
      margin: 0; padding: 0;
      background: linear-gradient(to bottom, #a1c4fd, #c2e9fb);
      font-family: 'Segoe UI', sans-serif; color: #333;
    }}
    .container {{
      max-width: 800px; margin: 40px auto;
      background: rgba(255,255,255,0.85);
      padding: 20px 30px; border-radius: 10px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }}
    header {{ text-align: center; margin-bottom: 30px; }}
    h1 {{ margin:0; color:#2c3e50; font-size:2em; }}
    h2 {{ color:#34495e; margin-top:30px; border-bottom:2px solid #eee; padding-bottom:5px; }}
    ul {{ list-style:none; padding-left:0; }}
    li {{ margin:5px 0; }}
    table {{ width:100%; border-collapse:collapse; margin-top:20px; }}
    th,td {{ border:1px solid #ddd; padding:8px; text-align:left; vertical-align:top; }}
    th {{ background-color:#2c3e50; color:#fff; }}
    tr:nth-child(even) {{ background-color:#f9f9f9; }}
    #map {{ height:300px; margin-top:20px; }}
    #toggle-dark {{ position:fixed; top:10px; right:10px; padding:8px; border:none; background:#2c3e50; color:#fff; border-radius:4px; cursor:pointer; }}
    body.dark {{ background:#222; color:#ddd; }}
    body.dark .container {{ background:rgba(0,0,0,0.8); }}
    body.dark th {{ background-color:#444; }}
    body.dark tr:nth-child(even) {{ background-color:#333; }}
  </style>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
</head>
<body>
  <button id="toggle-dark">🌓</button>
  <div class="container">
    <header>
      <h1>Dashboard bota</h1>
      <p>Aktualne dane ({today_str})</p>
    </header>

    <h2>Pogoda</h2>
    <ul>
      {weather_list}
    </ul>

    <h2>Kursy walut (PLN → ...)</h2>
    <ul>
      {rates_list}
    </ul>

    <h2>Indeksy giełdowe</h2>
    <ul>
      {indices_list}
    </ul>

    <h2>Mapa miast</h2>
    <div id="map"></div>

    <h2>Wykres temperatury</h2>
    <canvas id="chart-temp" height="200"></canvas>

    <h2>Wykres kursów walut</h2>
    <canvas id="chart-rates" height="200"></canvas>

    <h2>Historia (max 7 dni)</h2>
    <table>
      <tr><th>Data</th><th>Pogoda</th><th>Kursy</th><th>Indeksy</th></tr>
      {rows_history}
    </table>

    <footer>
      Strona wygenerowana automatycznie: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
    </footer>
  </div>

  <script>
    // Dark mode toggle
    const btn = document.getElementById('toggle-dark');
    btn.onclick = () => {{
      document.body.classList.toggle('dark');
      localStorage.setItem('dark', document.body.classList.contains('dark'));
    }};
    if (localStorage.getItem('dark') === 'true') {{
      document.body.classList.add('dark');
    }}

    // Dane dla JS
    const history = {history_json};
    const todayData = {today_json};

    // Chart.js – temperatura
    const labels = history.map(d => d.date);
    const datasetsTemp = Object.keys(todayData.weather).map(city => ({{
      label: city,
      data: history.map(d => parseInt(d.weather[city].match(/[-+]\d+/)[0])),
      fill: false,
      tension: 0.3
    }}));
    new Chart(
      document.getElementById('chart-temp'),
      {{ type: 'line', data: {{ labels, datasets: datasetsTemp }} }}
    );

    // Chart.js – kursy walut
    const datasetsRates = Object.keys(todayData.rates).map(cur => ({{
      label: cur,
      data: history.map(d => d.rates[cur] || null),
      fill: false,
      tension: 0.3
    }}));
    new Chart(
      document.getElementById('chart-rates'),
      {{ type: 'line', data: {{ labels, datasets: datasetsRates }} }}
    );

    // Leaflet – mapa miast
    const map = L.map('map').setView([52.23, 21.01], 6);
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      maxZoom: 18
    }}).addTo(map);
    const coords = {{
      "Warsaw": [52.23, 21.01],
      "Kraków": [50.06, 19.94],
      "Gdańsk": [54.35, 18.65]
    }};
    Object.entries(coords).forEach(([city, c]) => {{
      L.marker(c).addTo(map).bindPopup(`<strong>${{city}}:</strong> ${{todayData.weather[city]}}`);
    }});
  </script>
</body>
</html>
"""

OUTPUT_HTML.write_text(html_template, encoding="utf-8")
