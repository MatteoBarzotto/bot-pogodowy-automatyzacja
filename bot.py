import json
import requests
from datetime import datetime, timezone
from pathlib import Path


# --- Ustawienia ---
CITIES = {
    "Warsaw": "Warsaw",
    "Kraków": "Krakow",
    "Gdańsk": "Gdansk"
}
CURRENCY_PAIRS = ["USD", "EUR"]
INDICES = ["^WIG20", "^GSPC", "^GDAXI"]

# URL do pobierania starej historii z gałęzi gh-pages
GITHUB_RAW_URL = (
    "https://raw.githubusercontent.com/MatteoBarzotto/bot-pogodowy-automatyzacja/"
    "gh-pages/history.json"
)

HISTORY_FILE = Path("history.json")
OUTPUT_HTML  = Path("index.html")

# --- Funkcje pobierające dane ---

def fetch_weather(city_code):
    url = f"https://wttr.in/{city_code}?format=3"
    return requests.get(url).text.strip()

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



import time

def fetch_indices():
    url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={','.join(INDICES)}"
    max_attempts = 3
    backoff = 5  # sekund

    for attempt in range(1, max_attempts+1):
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
                print(f"⚠️ 429 limit prób {attempt}, odczekuję {backoff}s i próbuję ponownie...")
                time.sleep(backoff)
                backoff *= 2
                continue
            else:
                print("⚠️ Osiągnięto limit 429 po maksymalnej liczbie prób, zwracam pusty zestaw")
                return {}

        else:
            print(f"⚠️ Ostrzeżenie: HTTP {resp.status_code} przy pobieraniu indeksów")
            return {}

    return {}




# --- Załaduj historię (ostatnie 7 dni) ---

try:
    resp = requests.get(GITHUB_RAW_URL)
    resp.raise_for_status()
    history = resp.json()
except Exception:
    history = []

# --- Zbierz aktualne dane ---

today_str = datetime.utcnow().strftime("%Y-%m-%d")
today = {
    "date": today_str,
    "weather": {city: fetch_weather(code)
                for city,code in CITIES.items()},
    "rates": fetch_rates(),
    "indices": fetch_indices()
}

# Usuń dzisiejszy wpis, by nie duplikować
history = [h for h in history if h["date"] != today_str]
history.insert(0, today)
history = history[:7]

# Zapisz zaktualizowaną historię do pliku (w głównym folderze)
with HISTORY_FILE.open("w", encoding="utf-8") as f:
    json.dump(history, f, ensure_ascii=False, indent=2)

# --- Generuj HTML ---

rows_history = ""
for entry in history:
    # dla każdego dnia wypisujemy datę, kursy i indeksy
    rates = " | ".join(f"{k}: {v:.2f}" for k,v in entry["rates"].items())
    inds  = " | ".join(f"{k}: {v:.2f}" for k,v in entry["indices"].items())
    weas  = "<br>".join(entry["weather"].values())
    rows_history += (
        f"<tr>"
        f"<td>{entry['date']}</td>"
        f"<td>{weas}</td>"
        f"<td>{rates}</td>"
        f"<td>{inds}</td>"
        f"</tr>\n"
    )

from datetime import datetime, timezone

# … po zebraniu danych, przed zapisem do OUTPUT_HTML:

html_template = f"""<!DOCTYPE html>
<html lang="pl">
<head>
  <meta charset="utf-8">
  <title>Dashboard bota</title>
  <style>
    body {{
      margin: 0;
      padding: 0;
      background: linear-gradient(to bottom, #a1c4fd, #c2e9fb);
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      color: #333;
    }}
    .container {{
      max-width: 800px;
      margin: 40px auto;
      background: rgba(255,255,255,0.85);
      padding: 20px 30px;
      border-radius: 10px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }}
    header {{
      text-align: center;
      margin-bottom: 30px;
    }}
    h1 {{
      margin: 0;
      color: #2c3e50;
      font-size: 2em;
    }}
    h2 {{
      color: #34495e;
      margin-top: 30px;
      border-bottom: 2px solid #eee;
      padding-bottom: 5px;
    }}
    ul {{
      list-style: none;
      padding-left: 0;
    }}
    li {{
      margin: 5px 0;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 20px;
    }}
    th, td {{
      border: 1px solid #ddd;
      padding: 8px;
      text-align: left;
      vertical-align: top;
    }}
    th {{
      background-color: #2c3e50;
      color: #fff;
    }}
    tr:nth-child(even) {{
      background-color: #f9f9f9;
    }}
    footer {{
      text-align: center;
      margin-top: 30px;
      font-size: 0.85em;
      color: #555;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>Dashboard bota</h1>
      <p>Aktualne dane ({today_str})</p>
    </header>

    <h2>Pogoda</h2>
    <ul>
      {"".join(f"<li><strong>{city}:</strong> {w}</li>"
               for city,w in today["weather"].items())}
    </ul>

    <h2>Kursy walut (PLN → ...)</h2>
    <ul>
      {"".join(f"<li><strong>{cur}:</strong> {rate:.2f}</li>"
               for cur, rate in today["rates"].items())}
    </ul>

    <h2>Indeksy giełdowe</h2>
    <ul>
      {"".join(f"<li><strong>{idx}:</strong> {val:.2f}</li>"
               for idx, val in today["indices"].items())}
    </ul>

    <h2>Historia (max 7 dni)</h2>
    <table>
      <tr>
        <th>Data</th><th>Pogoda</th><th>Kursy</th><th>Indeksy</th>
      </tr>
      {rows_history}
    </table>

    <footer>
      Strona wygenerowana automatycznie: {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}
    </footer>
  </div>
</body>
</html>
"""

# … dalej zapis OUTPUT_HTML jak dotychczas


with OUTPUT_HTML.open("w", encoding="utf-8") as f:
    f.write(html_template)
