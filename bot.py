import requests
import json
import time
from datetime import datetime, timezone
from pathlib import Path

# ─── USTAWIENIA ───────────────────────────────────────────────────────────────
CITIES = {
    "Warsaw": "Warsaw",
    "Kraków": "Krakow",
    "Gdańsk": "Gdansk"
}
# Rozszerzona lista walut
CURRENCY_PAIRS = ["USD", "EUR", "GBP", "CHF", "JPY", "AUD", "CAD", "CNY"]
INDICES = ["^WIG20", "^GSPC", "^GDAXI"]

GITHUB_RAW_URL = (
    "https://raw.githubusercontent.com/MatteoBarzotto/"
    "bot-pogodowy-automatyzacja/gh-pages/history.json"
)
HISTORY_FILE = Path("history.json")
OUTPUT_HTML  = Path("index.html")

# ─── FUNKCJE POBIERAJĄCE ─────────────────────────────────────────────────────
def fetch_weather(city_code):
    resp = requests.get(f"https://wttr.in/{city_code}?format=3")
    return resp.text.strip()

def fetch_rates():
    rates = {}
    for cur in CURRENCY_PAIRS:
        url = f"http://api.nbp.pl/api/exchangerates/rates/a/{cur}/?format=json"
        resp = requests.get(url)
        if resp.status_code != 200:
            print(f"⚠️ HTTP {resp.status_code} przy kursie {cur}")
            continue
        try:
            data = resp.json()
            rates[cur] = data["rates"][0]["mid"]
        except Exception as e:
            print(f"⚠️ Błąd parsowania {cur}:", e)
    return rates

def fetch_indices():
    """Pobiera ceny indeksów, zwraca pusty słownik przy błędzie (w tym 429)."""
    url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={','.join(INDICES)}"
    try:
        resp = requests.get(url, timeout=5)
        if resp.status_code != 200:
            print(f"⚠️ Ostrzeżenie: HTTP {resp.status_code} przy pobieraniu indeksów")
            return {}
        data = resp.json()
    except Exception as e:
        print(f"⚠️ Ostrzeżenie: błąd przy pobieraniu indeksów: {e}")
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

# ─── HISTORIA ─────────────────────────────────────────────────────────────────
try:
    history = requests.get(GITHUB_RAW_URL).json()
except:
    history = []

today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
today = {
    "date": today_str,
    "weather": {city: fetch_weather(code) for city,code in CITIES.items()},
    "rates":  fetch_rates(),
    "indices": fetch_indices()
}
history = [h for h in history if h.get("date") != today_str]
history.insert(0, today)
history = history[:7]
HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

# ─── PRZYGOTOWANIE LIST HTML ────────────────────────────────────────────────
weather_list = "".join(f"<li><strong>{c}:</strong> {w}</li>\n"
                       for c,w in today["weather"].items())
rates_list   = "".join(f"<li><strong>{c}:</strong> {r:.2f} PLN</li>\n"
                       for c,r in today["rates"].items())
indices_list = "".join(f"<li><strong>{i}:</strong> {v:.2f}</li>\n"
                       for i,v in today["indices"].items())

# ─── PRZELICZENIA WALUT ──────────────────────────────────────────────────────
conversion = {}
for a,ra in today["rates"].items():
    conversion[a] = {}
    for b,rb in today["rates"].items():
        conversion[a][b] = ra/rb if rb else None

conv_header = "".join(f"<th>{c}</th>" for c in CURRENCY_PAIRS)
conv_rows = ""
for a in CURRENCY_PAIRS:
    row = "".join(f"<td>{conversion[a][b]:.4f}</td>" for b in CURRENCY_PAIRS)
    conv_rows += f"<tr><th>{a}</th>{row}</tr>\n"

# ─── TABELKA HISTORYCZNA ─────────────────────────────────────────────────────
rows_history = ""
for e in history:
    we = "<br>".join(e["weather"].values())
    rr = " | ".join(f"{k}: {v:.2f}" for k,v in e["rates"].items())
    ii = " | ".join(f"{k}: {v:.2f}" for k,v in e["indices"].items())
    rows_history += f"<tr><td>{e['date']}</td><td>{we}</td><td>{rr}</td><td>{ii}</td></tr>\n"

# ─── DANE DLA JS ─────────────────────────────────────────────────────────────
history_json = json.dumps(history, ensure_ascii=False)
today_json   = json.dumps(today, ensure_ascii=False)

# ─── SZABLON HTML ────────────────────────────────────────────────────────────
html = f"""<!DOCTYPE html>
<html lang="pl">
<head>
<meta charset="utf-8"><title>Dashboard bota</title>
<style>
  body{{margin:0;padding:0;background:#eef4fc;font-family:sans-serif;color:#333}}
  .container{{max-width:900px;margin:30px auto;background:#fff;padding:20px;border-radius:8px;box-shadow:0 2px 8px rgba(0,0,0,0.1)}}
  h1,h2{{color:#2c3e50}}
  h2{{margin-top:30px;border-bottom:1px solid #ddd;padding-bottom:5px}}
  ul{{padding:0;list-style:none}}
  li{{margin:4px 0}}
  table{{width:100%;border-collapse:collapse;margin-top:15px}}
  th,td{{border:1px solid #ccc;padding:6px;text-align:center}}
  th{{background:#2c3e50;color:#fff}}
  tr:nth-child(even){{background:#f9f9f9}}
  #map{{height:250px;margin-top:20px}}
  #toggle-dark{{
    position:fixed;top:10px;right:10px;padding:6px 10px;
    background:#2c3e50;color:#fff;border:none;border-radius:4px;cursor:pointer
  }}
  body.dark{{background:#333;color:#ddd}}
  body.dark .container{{background:#444}}
  body.dark th{{background:#555}}
  body.dark tr:nth-child(even){{background:#444}}
  #city-input{{
    width:200px;padding:5px;border:1px solid #ccc;border-radius:4px;
    margin-right:6px;
  }}
</style>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
</head>
<body>
<button id="toggle-dark">🌓</button>
<div class="container">
  <h1>Dashboard bota</h1>
  <p><em>Aktualne dane ({today_str})</em></p>

  <h2>Pogoda</h2>
  <ul>{weather_list}</ul>

  <h2>Kursy walut (PLN → ...)</h2>
  <ul>{rates_list}</ul>

  <h2>Tablica przeliczeń walut</h2>
  <table>
    <tr><th></th>{conv_header}</tr>
    {conv_rows}
  </table>

  <h2>Indeksy giełdowe</h2>
  <ul>{indices_list}</ul>

  <h2>Sprawdź pogodę dla swojej miejscowości</h2>
  <input id="city-input" placeholder="Wpisz miasto"/><button id="city-btn">Sprawdź</button>
  <p id="city-weather"></p>

  <h2>Mapa miast</h2>
  <div id="map"></div>

  <h2>Wykresy historii (7 dni)</h2>
  <canvas id="chart-temp" height="150"></canvas>
  <canvas id="chart-rates" height="150" style="margin-top:20px;"></canvas>

  <h2>Historia (max 7 dni)</h2>
  <table>
    <tr><th>Data</th><th>Pogoda</th><th>Kursy</th><th>Indeksy</th></tr>
    {rows_history}
  </table>

  <footer style="text-align:center;margin-top:20px;font-size:0.9em;color:#666">
    Strona wygenerowana: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
  </footer>
</div>

<script>
  // dark mode
  const btn = document.getElementById('toggle-dark');
  btn.onclick = () => {{
    document.body.classList.toggle('dark');
    localStorage.dark = document.body.classList.contains('dark');
  }};
  if(localStorage.dark==='true') document.body.classList.add('dark');

  // user‐input pogoda
  document.getElementById('city-btn').onclick = async () => {{
    const city = document.getElementById('city-input').value || 'Warsaw';
    const res  = await fetch(`https://wttr.in/${{city}}?format=3`);
    document.getElementById('city-weather').textContent = await res.text();
  }};

  // mapka
  const map = L.map('map').setView([52.23,21.01],6);
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{maxZoom:18}}).addTo(map);

  const coords = {json.dumps({"Warsaw":[52.23,21.01],"Kraków":[50.06,19.94],"Gdańsk":[54.35,18.65]})};
  Object.entries(coords).forEach(([city,c]) => {{
    L.marker(c).addTo(map).bindPopup(`<strong>${{city}}:</strong> ${{today_json.weather[city]||''}}`);
  }});

  // wykresy
  const history = {history_json}, todayData = {today_json};
  const labels = history.map(d=>d.date);
  // temp
  new Chart(
    document.getElementById('chart-temp'),
    {{
      type:'line',
      data:{{
        labels,
        datasets: Object.keys(todayData.weather).map(c=>({{
          label:c,
          data:history.map(d=>parseInt(d.weather[c].match(/[-+]\d+/)[0])),
          fill:false, tension:0.3
        }}))
      }}
    }}
  );
  // kursy
  new Chart(
    document.getElementById('chart-rates'),
    {{
      type:'line',
      data:{{
        labels,
        datasets: Object.keys(todayData.rates).map(c=>({{
          label:c,
          data:history.map(d=>d.rates[c]||null),
          fill:false, tension:0.3
        }}))
      }}
    }}
  );
</script>
</body>
</html>
"""

OUTPUT_HTML.write_text(html, encoding="utf-8")
