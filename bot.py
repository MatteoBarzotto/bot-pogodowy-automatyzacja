import requests
import json
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup

# ───── USTAWIENIA ─────
CITIES       = {"Warsaw": "Warsaw", "Kraków": "Krakow", "Gdańsk": "Gdansk"}
CURRENCY     = ["USD", "EUR", "GBP", "CHF", "JPY", "AUD", "CAD", "CNY"]
CRYPTO       = ["bitcoin", "ethereum", "ripple", "litecoin", "dogecoin"]
INDICES      = ["^GSPC", "^DJI", "^IXIC", "^FTSE"]
NEWS_RSS     = "https://news.google.com/rss?hl=pl&gl=PL&ceid=PL:PL"
HISTORY_FILE = Path("history.json")
OUTPUT_HTML  = Path("index.html")

# ───── POBIERANIE ─────
def fetch_weather(city):
    try:
        r = requests.get(f"https://wttr.in/{city}?m&format=%l:+%t", timeout=5)
        return r.text.strip()
    except:
        return "brak danych"

def fetch_rates():
    rates = {}
    for c in CURRENCY:
        try:
            r = requests.get(f"http://api.nbp.pl/api/exchangerates/rates/a/{c}/?format=json")
            rates[c] = r.json()["rates"][0]["mid"]
        except:
            continue
    return rates

def fetch_crypto():
    try:
        r = requests.get(
            "https://api.coingecko.com/api/v3/simple/price",
            params={"ids": ",".join(CRYPTO), "vs_currencies": "pln"}
        )
        return {k.upper(): v["pln"] for k, v in r.json().items()}
    except:
        return {}

def fetch_index_price_from_gpw(index_names):
    try:
        url = "https://www.bankier.pl/gielda/notowania/indeksy-gpw"
        r = requests.get(url, timeout=5)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        # Find the table with indices
        table = soup.find("table", {"class": "qTableFull"})
        if not table:
            table = soup.find("table", {"class": "qTable"})
        if not table:
            tables = soup.find_all("table")
            if tables:
                table = tables[0]
        if not table:
            print("ERROR: Could not find indices table on bankier.pl")
            return None
        # Find all rows
        rows = table.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 2:
                name = cols[0].text.strip()
                if any(index_name in name for index_name in index_names):
                    price_text = cols[1].text.strip()
                    price_text = price_text.replace("\xa0", "").replace(",", ".")
                    import re
                    match = re.search(r"[\d\.]+", price_text)
                    if match:
                        price = float(match.group())
                        return price
        print(f"ERROR: Could not find any of {index_names} price in indices table")
        return None
    except Exception as e:
        print(f"ERROR in fetch_index_price_from_gpw for {index_names}:", e)
        return None

def fetch_indices():
    price_map = {}
    indices_to_fetch = {
        "^WIG20": ["WIG20"],
        "^WIG30": ["WIG30"],
        "^WIG": ["WIG"],
        "^NCINDEX": ["NCIndex", "NC Index", "NC"]
    }
    for key, names in indices_to_fetch.items():
        price = fetch_index_price_from_gpw(names)
        if price is not None and price > 0:
            price_map[key] = price
    return price_map

def fetch_news():
    try:
        r = requests.get(NEWS_RSS)
        root = ET.fromstring(r.text)
        return [
            {"title": i.findtext("title"), "link": i.findtext("link")}
            for i in root.findall(".//item")[:5]
        ]
    except:
        return []

# ─── HISTORIA ─────────────────────────────────────────────────────────────

if HISTORY_FILE.exists():
    history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
else:
    history = []

now = datetime.now()
timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

weather_dict = {city: fetch_weather(code) for city, code in CITIES.items()}

entry = {
    "timestamp": timestamp,
    "weather": weather_dict,
    "rates": fetch_rates(),
    "crypto": fetch_crypto(),
    "indices": fetch_indices(),
    "news": fetch_news()
}

history.append(entry)
history = history[-50:]
HISTORY_FILE.write_text(json.dumps(history, indent=2, ensure_ascii=False), encoding="utf-8")

# ───── HTML ELEMENTY ─────
weather_html = "".join(f"<li><b>{c}:</b> {w}</li>" for c, w in entry["weather"].items())
rates_html   = "".join(f"<li><b>{k}:</b> {v:.2f} PLN</li>" for k, v in entry["rates"].items())
crypto_html  = "".join(f"<li><b>{k}:</b> {v:.2f} PLN</li>" for k, v in entry["crypto"].items())
indices_html = "".join(f"<li><b>{k}:</b> {v:.2f}</li>" for k, v in entry["indices"].items())
news_html    = "".join(f"<li><a href='{n['link']}' target='_blank'>{n['title']}</a></li>"
                       for n in entry["news"])

table_rows = ""
for h in history:
    w = "<br>".join(h["weather"].values())
    r = " | ".join(f"{k}: {v:.2f}" for k, v in h["rates"].items())
    c = " | ".join(f"{k}: {v:.2f}" for k, v in h["crypto"].items())
    i = " | ".join(f"{k}: {v:.2f}" for k, v in h["indices"].items())
    table_rows += f"<tr><td>{h['timestamp']}</td><td>{w}</td><td>{r}</td><td>{c}</td><td>{i}</td></tr>"

# ───── WYKRESY ─────
labels        = [h["timestamp"] for h in history]
weather_data  = [{
    "label": city,
    "data": [
        int(x.split()[-1].replace("°C","").replace("+","")) if "°C" in x else None
        for x in (h["weather"].get(city,"") for h in history)
    ],
    "fill": False, "tension": 0.3
} for city in CITIES]
currency_data = [{
    "label": cur,
    "data": [h["rates"].get(cur) for h in history],
    "fill": False, "tension": 0.3
} for cur in CURRENCY]
crypto_data   = [{
    "label": k,
    "data": [h["crypto"].get(k) for h in history],
    "fill": False, "tension": 0.3
} for k in entry["crypto"].keys()]
indices_data = [{
    "label": k,
    "data": [h["indices"].get(k) for h in history],
    "fill": False, "tension": 0.3
} for k in entry["indices"].keys()]

labels_js    = json.dumps(labels)
weather_js   = json.dumps(weather_data, ensure_ascii=False)
currency_js  = json.dumps(currency_data, ensure_ascii=False)
crypto_js    = json.dumps(crypto_data, ensure_ascii=False)
indices_js   = json.dumps(indices_data, ensure_ascii=False)

# ───── GENERUJ HTML ─────
html = f"""<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>Dashboard Bota</title>
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chartjs-plugin-zoom@2.1.1/dist/chartjs-plugin-zoom.min.js"></script>
  <style>
    body {{ font-family: 'Roboto', sans-serif; background:#f0f4f8; padding:20px; }}
    .container {{ max-width:1000px; margin:auto; background:#fff; padding:30px;
                  border-radius:10px; box-shadow:0 4px 10px rgba(0,0,0,0.1); }}
    h1,h2 {{ color:#1e3a8a; }}
    ul {{ margin:0; padding:0; list-style:none; }}
    li {{ background:#e2e8f0; padding:8px; margin:5px 0; border-radius:6px; }}
    table {{ width:100%; border-collapse:collapse; margin-top:20px; }}
    th, td {{ border:1px solid #cbd5e1; padding:6px; text-align:center; }}
    th {{ background:#1e3a8a; color:#fff; }}
    input, button {{ padding:8px; margin-top:10px; }}
    canvas {{ margin-top:20px; background:#fff; border-radius:6px; padding:10px; }}
    .controls {{ margin-top: 10px; }}
    .controls > * {{ margin-right: 10px; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>📊 Dashboard Bota</h1>
    <p><b>Ostatni pomiar:</b> {timestamp}</p>

    <h2>🔍 Sprawdź pogodę</h2>
    <input id="city" placeholder="Wpisz miasto"/><button onclick="search()">Sprawdź</button>
    <p id="weather-result"></p>

    <h2>🌦️ Pogoda</h2><ul>{weather_html}</ul>
    <h2>💱 Kursy walut</h2><ul>{rates_html}</ul>
    <h2>💲 Kryptowaluty</h2><ul>{crypto_html}</ul>
    <h2>📈 Indeksy</h2><ul>{indices_html}</ul>
    <h2>📰 Wiadomości</h2><ul>{news_html}</ul>

    <h2>📉 Wykres temperatur</h2>
    <canvas id="chart-temp" height="150"></canvas>
    <div class="controls" id="controls-temp">
      <button onclick="zoomIn(chartTemp)">Zoom In</button>
      <button onclick="zoomOut(chartTemp)">Zoom Out</button>
      <input type="range" id="slider-temp" min="0" max="100" value="0" oninput="slideChart(chartTemp, this.value)" />
    </div>

    <h2>💵 Wykres kursów walut</h2>
    <canvas id="chart-rates" height="150"></canvas>
    <div class="controls" id="controls-rates">
      <button onclick="zoomIn(chartRates)">Zoom In</button>
      <button onclick="zoomOut(chartRates)">Zoom Out</button>
      <input type="range" id="slider-rates" min="0" max="100" value="0" oninput="slideChart(chartRates, this.value)" />
    </div>

    <h2>💹 Wykres kryptowalut</h2>
    <canvas id="chart-crypto" height="150"></canvas>
    <div class="controls" id="controls-crypto">
      <button onclick="zoomIn(chartCrypto)">Zoom In</button>
      <button onclick="zoomOut(chartCrypto)">Zoom Out</button>
      <input type="range" id="slider-crypto" min="0" max="100" value="0" oninput="slideChart(chartCrypto, this.value)" />
    </div>

    <h2>📊 Wykres indeksów</h2>
    <canvas id="chart-indices" height="150"></canvas>
    <div class="controls" id="controls-indices">
      <button onclick="zoomIn(chartIndices)">Zoom In</button>
      <button onclick="zoomOut(chartIndices)">Zoom Out</button>
      <input type="range" id="slider-indices" min="0" max="100" value="0" oninput="slideChart(chartIndices, this.value)" />
    </div>

    <h2>🕒 Historia</h2>
    <table>
      <tr><th>Czas</th><th>Pogoda</th><th>Kursy</th><th>Crypto</th><th>Indeksy</th></tr>
      {table_rows}
    </table>
  </div>

  <script>
    function search() {{
      const city = document.getElementById('city').value;
      fetch(`https://wttr.in/${{city}}?format=%l:+%t`)
        .then(r => r.text())
        .then(d => document.getElementById('weather-result').textContent = d)
        .catch(() => document.getElementById('weather-result').textContent = 'Błąd');
    }}

    const labels = {labels_js};
    const zoomOptions = {{
      plugins: {{
        zoom: {{
          pan: {{ enabled: true, mode: 'x' }},
          zoom: {{
            wheel: {{ enabled: true }},
            pinch: {{ enabled: true }},
            mode: 'x'
          }}
        }}
      }}
    }};

    const chartTemp = new Chart(document.getElementById('chart-temp'), {{
      type: 'line',
      data: {{ labels, datasets: {weather_js} }},
      options: zoomOptions
    }});
    const chartRates = new Chart(document.getElementById('chart-rates'), {{
      type: 'line',
      data: {{ labels, datasets: {currency_js} }},
      options: zoomOptions
    }});
    const chartCrypto = new Chart(document.getElementById('chart-crypto'), {{
      type: 'line',
      data: {{ labels, datasets: {crypto_js} }},
      options: zoomOptions
    }});
    const chartIndices = new Chart(document.getElementById('chart-indices'), {{
      type: 'line',
      data: {{ labels, datasets: {indices_js} }},
      options: zoomOptions
    }});

    function zoomIn(chart) {{
      const zoomPlugin = chart.$zoom;
      if (!zoomPlugin) return;
      const range = chart.scales.x.max - chart.scales.x.min;
      const center = (chart.scales.x.max + chart.scales.x.min) / 2;
      const newRange = range / 1.2;
      const min = center - newRange / 2;
      const max = center + newRange / 2;
      chart.options.scales.x.min = min;
      chart.options.scales.x.max = max;
      chart.update();
    }}

    function zoomOut(chart) {{
      const range = chart.scales.x.max - chart.scales.x.min;
      const center = (chart.scales.x.max + chart.scales.x.min) / 2;
      const newRange = range * 1.2;
      const min = center - newRange / 2;
      const max = center + newRange / 2;
      chart.options.scales.x.min = min;
      chart.options.scales.x.max = max;
      chart.update();
    }}

    function slideChart(chart, value) {{
      const totalRange = chart.scales.x.max - chart.scales.x.min;
      const visibleRange = chart.options.scales.x.max - chart.options.scales.x.min;
      const maxPan = totalRange - visibleRange;
      const panAmount = (value / 100) * maxPan;
      const min = chart.options.scales.x.min + panAmount;
      const max = chart.options.scales.x.max + panAmount;
      chart.options.scales.x.min = min;
      chart.options.scales.x.max = max;
      chart.update();
    }}
  </script>
</body>
</html>
"""

OUTPUT_HTML.write_text(html, encoding="utf-8")
print("✅ Gotowe! Wygenerowano index.html")
