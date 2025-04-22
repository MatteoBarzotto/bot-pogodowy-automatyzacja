import requests
from datetime import datetime

def get_weather():
    url = "https://wttr.in/Warsaw?format=3"
    response = requests.get(url)
    weather = response.text

    # zapis do pliku HTML
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(f"""
        <html>
            <head><title>Bot Pogodowy</title></head>
            <body>
                <h1>Aktualna pogoda</h1>
                <p>{weather}</p>
                <p>Ostatnia aktualizacja: {datetime.now()}</p>
            </body>
        </html>
        """)

if __name__ == "__main__":
    get_weather()
