import requests
import json
from datetime import datetime
from pathlib import Path

# ─── USTAWIENIA ───────────────────────────────────────────────────────────────

CITIES = {
    "Warsaw": "Warsaw",
    "Kraków": "Krakow",
    "Gdańsk": "Gdansk"
}

CURRENCY_PAIRS = ["USD", "EUR", "GBP", "CHF", "JPY", "AUD", "CAD", "CNY"]
INDICES = ["^WIG20", "^GSPC", "^GDAXI"]

GITHUB_RAW_URL = (
    "https://raw.githubusercontent.com/MatteoBarzotto/"
    "bot-pogodowy-automatyzacja/gh-pages/history.json"
)

HISTORY_FILE = Path("history.json")
OUTPUT_HTML  = Path("index.html")

# ─── FUNKCJE ───────────────────────────────────────────────────────────────────

def fetch_weather(city_code):
    # format=%l:+%t zwraca "City: +XX°C"
    resp = requests.get(f"https://wttr.in/{city_code}?format=%l:+%t")
    return resp.text.strip()

def fetch_rates():
    rates = {}
    for cur in CURRENCY_PAIRS:
        resp = requests.get(f"http://api.nbp.pl/api/exchangerates/rates/a/{cur}/?format=json")
        if resp.status_code == 200:
            try:
                data = resp.json()
                rates[cur] = data["rates"][0]["mid"]
            except:
                pass
    return rates

def fetch_indices():
    try:
        resp = requests.get(
            f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={','.join(INDICES)}",
            timeout=5
        )
        if resp.status_code != 200:
            return {}
        data = resp.json().get("quoteResponse", {}).get("result", [])
        return {
            q["symbol"]: q["regularMarketPrice"]
            for q in data
            if q.get("symbol") and q.get("regularMarketPrice") is not None
        }
    except:
        return {}

# ─── HISTORIA ─────────────────────────────────────────────────────────────────

# Jeśli istnieje lokalny plik history.json, odczytaj go,
# w przeciwnym razie zacznij od pustej listy.
if HISTORY_FILE.exists():
    try:
        history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except Exception:
        history = []
else:
    history = []


now = datetime.now()  # lokalny czas systemowy (Polska)
timestamp = now.strftime("%Y-%m-%d %H:%M:%S")
date_part = now.strftime("%Y-%m-%d")
time_part = now.strftime("%H:%M:%S")

entry = {
    "timestamp": timestamp,
    "date": date_part,
    "time": time_part,
    "weather": {city: fetch_weather(code) for city, code in CITIES.items()},
    "rates": fetch_rates(),
    "indices": fetch_indices()
}

history.append(entry)
HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

# ─── GENEROWANIE DANYCH DLA HTML ───────────────────────────────────────────────

weather_list = "".join(
    f"<li><strong>{city}:</strong> {w}</li>\n"
    for city, w in entry["weather"].items()
)
rates_list = "".join(
    f"<li><strong>{cur}:</strong> {r:.2f} PLN</li>\n"
    for cur, r in entry["rates"].items()
)
indices_list = "".join(
    f"<li><strong>{idx}:</strong> {val:.2f}</li>\n"
    for idx, val in entry["indices"].items()
)

conversion = {
    a: {b: (ra / rb if rb else None)
        for b, rb in entry["rates"].items()}
    for a, ra in entry["rates"].items()
}
conv_header = "".join(f"<th>{c}</th>" for c in CURRENCY_PAIRS)
conv_rows = "".join(
    f"<tr><th>{a}</th>" + "".join(f"<td>{conversion[a][b]:.4f}</td>" for b in CURRENCY_PAIRS) + "</tr>\n"
    for a in CURRENCY_PAIRS
)

rows_history = ""
for e in history:
    date = e.get("date", "")
    time = e.get("time", e.get("timestamp", "").split(" ")[1] if "timestamp" in e else "")
    we = "<br>".join(e["weather"].values())
    rr = " | ".join(f"{k}: {v:.2f}" for k, v in e["rates"].items())
    ii = " | ".join(f"{k}: {v:.2f}" for k, v in e["indices"].items())
    rows_history += (
        f"<tr><td>{date}</td><td>{time}</td><td>{we}</td><td>{rr}</td><td>{ii}</td></tr>\n"
    )

history_json = json.dumps(history, ensure_ascii=False)
today_json   = json.dumps(entry, ensure_ascii=False)

# ─── GENEROWANIE HTML ─────────────────────────────────────────────────────────

html_template = f"""<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Dashboard bota</title>
  <style>
    html, body {{ margin:0; padding:0; background:#eef4fc; font-family:'Segoe UI',sans-serif; color:#333; }}
    .container {{ max-width:900px; margin:30px auto; background:#fff; padding:20px; border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,0.1); }}
    h1,h2 {{ color:#2c3e50; }}
    h2 {{ margin-top:30px; border-bottom:1px solid #ddd; padding-bottom:5px; }}
    ul {{ list-style:none; padding:0; }}
    li {{ margin:4px 0; }}
    table {{ width:100%; border-collapse:collapse; margin-top:15px; }}
    th, td {{ border:1px solid #ccc; padding:6px; text-align:center; }}
    th {{ background:#2c3e50; color:#fff; }}
    tr:nth-child(even) {{ background:#f9f9f9; }}
    #toggle-dark {{ position:fixed; top:10px; right:10px; padding:6px 10px; background:#2c3e50; color:#fff; border:none; border-radius:4px; cursor:pointer; z-index:1; }}
    #city-input {{ padding:5px; border:1px solid #ccc; border-radius:4px; width:200px; }}
    button#city-btn {{ padding:6px 10px; border:none; border-radius:4px; background:#2c3e50; color:#fff; cursor:pointer; }}
  </style>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css"/>
  <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
</head>
<body>
  <button id="toggle-dark">🌓</button>
  <div class="container">
    <h1>Dashboard bota</h1>
    <p><em>Ostatni pomiar: {timestamp}</em></p>

    <h2>Pogoda</h2>
    <ul>{weather_list}</ul>

    <h2>Kursy walut</h2>
    <ul>{rates_list}</ul>

    <h2>Tablica przeliczeń</h2>
    <table>
      <tr><th></th>{conv_header}</tr>
      {conv_rows}
    </table>

    <h2>Indeksy giełdowe</h2>
    <ul>{indices_list}</ul>

    <h2>Sprawdź pogodę</h2>
    <input id="city-input" placeholder="miasto"/><button id="city-btn">Sprawdź</button>
    <p id="city-weather"></p>

    <h2>Mapa miast</h2>
    <div id="map" style="height:250px; margin-top:10px;"></div>

    <h2>Wykresy historii (7 dni)</h2>
    <canvas id="chart-temp" height="150"></canvas>
    <canvas id="chart-rates" height="150" style="margin-top:20px;"></canvas>

    <h2>Historia pomiarów co 5 minut</h2>
    <table>
      <tr><th>Data</th><th>Godzina</th><th>Pogoda</th><th>Kursy</th><th>Indeksy</th></tr>
      {rows_history}
    </table>
  </div>

  <script>
    // Dark mode toggle
    const btn = document.getElementById('toggle-dark');
    btn.onclick = () => {{ document.body.classList.toggle('dark'); localStorage.setItem('dark', document.body.classList.contains('dark')); }};
    if (localStorage.getItem('dark') === 'true') {{ document.body.classList.add('dark'); }}

    // Custom city weather
    document.getElementById('city-btn').onclick = async () => {{
      const c = document.getElementById('city-input').value || 'Warsaw';
      const r = await fetch(`https://wttr.in/${{c}}?format=%l:+%t`);
      document.getElementById('city-weather').textContent = await r.text();
    }};

    // Map
    const map = L.map('map').setView([52.23,21.01],6);
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{ maxZoom:18 }}).addTo(map);
    const today = {today_json};
    const coords = {json.dumps({"Warsaw":[52.23,21.01],"Kraków":[50.06,19.94],"Gdańsk":[54.35,18.65]})};
    Object.entries(coords).forEach(([city,c]) => {{ 
      L.marker(c).addTo(map)
       .bindPopup(`<strong>${{city}}:</strong> ${{today.weather[city]}}`);
    }});

    // Charts with history
    const history = {history_json};
    const labels = history.map(d => d.timestamp);
    const tempDatasets = Object.keys(history[0].weather).map(city => ({{
      label: city,
      data: history.map(d => parseInt(d.weather[city].match(/[-+]\d+/)[0])),
      fill: false, tension: 0.3
    }}));
    new Chart(document.getElementById('chart-temp'), {{ type:'line', data:{{ labels, datasets: tempDatasets }} }});
    const rateDatasets = Object.keys(history[0].rates).map(cur => ({{
      label: cur,
      data: history.map(d => d.rates[cur] || null),
      fill: false, tension: 0.3
    }}));
    new Chart(document.getElementById('chart-rates'), {{ type:'line', data:{{ labels, datasets: rateDatasets }} }});
  </script>
</body>
</html>
"""

OUTPUT_HTML.write_text(html_template, encoding="utf-8")
