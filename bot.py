# Pełna wersja bot.py z wkomponowanym szablonem HTML premium
from pathlib import Path
import requests
import json
import xml.etree.ElementTree as ET
from datetime import datetime

CITIES = {"Warsaw": "Warsaw", "Kraków": "Krakow", "Gdańsk": "Gdansk"}
CURRENCY_PAIRS = ["USD", "EUR", "GBP", "CHF", "JPY", "AUD", "CAD", "CNY"]
CRYPTO_IDS = ["bitcoin", "ethereum", "ripple", "litecoin", "dogecoin"]
INDICES = ["^WIG20", "^GSPC", "^DJI", "^IXIC", "^FTSE"]
RSS_FEED_URL = "https://news.google.com/rss?hl=pl&gl=PL&ceid=PL:PL"

HISTORY_FILE = Path("history.json")
OUTPUT_HTML = Path("index.html")


def fetch_weather(city_code):
    try:
        resp = requests.get(f"https://wttr.in/{city_code}?m&format=%l:+%t", timeout=5)
        return resp.text.strip()
    except:
        return "brak danych"

def fetch_rates():
    rates = {}
    for cur in CURRENCY_PAIRS:
        try:
            r = requests.get(f"http://api.nbp.pl/api/exchangerates/rates/a/{cur}/?format=json")
            if r.status_code == 200:
                data = r.json()
                rates[cur] = data["rates"][0]["mid"]
        except:
            pass
    return rates

def fetch_crypto():
    try:
        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": ",".join(CRYPTO_IDS), "vs_currencies": "pln"}
        r = requests.get(url, params=params)
        data = r.json()
        return {cid.upper(): data.get(cid, {}).get("pln") for cid in CRYPTO_IDS}
    except:
        return {}

def fetch_indices():
    try:
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={','.join(INDICES)}"
        r = requests.get(url)
        results = r.json().get("quoteResponse", {}).get("result", [])
        return {x["symbol"]: x["regularMarketPrice"] for x in results if "regularMarketPrice" in x}
    except:
        return {}

def fetch_news():
    try:
        r = requests.get(RSS_FEED_URL)
        items = []
        if r.status_code == 200:
            root = ET.fromstring(r.text)
            for item in root.findall(".//item")[:5]:
                items.append({
                    "title": item.findtext("title", default="–"),
                    "link": item.findtext("link", default="#")
                })
        return items
    except:
        return []

# Historia
if HISTORY_FILE.exists():
    try:
        history = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except:
        history = []
else:
    history = []

now = datetime.now()
timestamp = now.strftime("%Y-%m-%d %H:%M:%S")

entry = {
    "timestamp": timestamp,
    "weather": {city: fetch_weather(code) for city, code in CITIES.items()},
    "rates": fetch_rates(),
    "crypto": fetch_crypto(),
    "indices": fetch_indices(),
    "news": fetch_news()
}

history.append(entry)
HISTORY_FILE.write_text(json.dumps(history, ensure_ascii=False, indent=2), encoding="utf-8")

weather_list = "".join(f"<li><strong>{city}:</strong> {w}</li>" for city, w in entry["weather"].items())
rates_list = "".join(f"<li><strong>{cur}:</strong> {val:.2f} PLN</li>" for cur, val in entry["rates"].items())
crypto_list = "".join(f"<li><strong>{sym}:</strong> {val:.2f} PLN</li>" for sym, val in entry["crypto"].items())
indices_list = "".join(f"<li><strong>{idx}:</strong> {val:.2f}</li>" for idx, val in entry["indices"].items())
news_list = "".join(f"<li><a href='{item['link']}' target='_blank'>{item['title']}</a></li>" for item in entry["news"])

rows_history = ""
for h in history[-7:]:
    w = "<br>".join(h.get("weather", {}).values())
    r = " | ".join(f"{k}: {v:.2f}" for k, v in h.get("rates", {}).items())
    c = " | ".join(f"{k}: {v:.2f}" for k, v in h.get("crypto", {}).items())
    i = " | ".join(f"{k}: {v:.2f}" for k, v in h.get("indices", {}).items())
    rows_history += f"<tr><td>{h['timestamp']}</td><td>{w}</td><td>{r}</td><td>{c}</td><td>{i}</td></tr>\n"

html_template = """<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="utf-8"/>
  <title>Dashboard Bota</title>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <link href="https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap" rel="stylesheet">
  <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
  <style>
    body {{ margin:0; font-family:'Roboto', sans-serif; background:#f0f4f8; padding:20px; color:#1e293b; }}
    .container {{ max-width:1100px; margin:auto; background:#fff; padding:30px; border-radius:12px; box-shadow:0 8px 20px rgba(0,0,0,0.1); }}
    h1 {{ text-align:center; font-size:2em; margin-bottom:20px; }}
    h2 {{ margin-top:40px; border-left:6px solid #2563eb; padding-left:12px; font-size:1.5em; }}
    ul {{ list-style:none; padding:0; }}
    ul li {{ background:#f1f5f9; padding:8px; margin-bottom:6px; border-radius:6px; }}
    table {{ width:100%; border-collapse:collapse; margin-top:20px; font-size:0.95em; }}
    th, td {{ border:1px solid #cbd5e1; padding:8px; text-align:center; }}
    th {{ background-color:#2563eb; color:white; }}
    canvas {{ background:#fff; border-radius:8px; padding:10px; margin-top:20px; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>📊 Dashboard Bota</h1>
    <p><em>Ostatni pomiar: {timestamp}</em></p>
    <h2>🌦️ Pogoda</h2><ul>{weather_list}</ul>
    <h2>💱 Kursy Walut</h2><ul>{rates_list}</ul>
    <h2>💲 Kryptowaluty</h2><ul>{crypto_list}</ul>
    <h2>📈 Indeksy</h2><ul>{indices_list}</ul>
    <h2>📰 Wiadomości</h2><ul>{news_list}</ul>
    <h2>🕓 Historia Pomiarów</h2>
    <table><tr><th>Czas</th><th>Pogoda</th><th>Kursy</th><th>Crypto</th><th>Indeksy</th></tr>{rows_history}</table>
  </div>
</body>
</html>
""".format(
    timestamp=timestamp,
    weather_list=weather_list,
    rates_list=rates_list,
    crypto_list=crypto_list,
    indices_list=indices_list,
    news_list=news_list,
    rows_history=rows_history
)

OUTPUT_HTML.write_text(html_template, encoding="utf-8")
OUTPUT_HTML.name
