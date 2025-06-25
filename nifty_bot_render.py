from flask import Flask
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# --- CONFIG ---
BOT_TOKEN = "7974119756:AAESnz98xnm3XhPqoUkVQ6FQVQjOlsWAfw4"
CHAT_ID = "622334857"
NSE_URL = "https://www.nseindia.com/live_market/dynaContent/live_watch/stock_watch/liveIndexWatchData.json"

headers = {
    "User-Agent": "Mozilla/5.0"
}

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Nifty Render Bot is running."

@app.route("/ping")
def ping():
    return "Pong"

@app.route("/run")
def run_analysis():
    try:
        message = get_nifty_summary()
        result = send_telegram_message(message)
        print("Telegram response:", result)
        if result.get("ok"):
            return "✅ Message sent to Telegram!"
        else:
            return f"❌ Telegram failed: {result.get('description', 'Unknown error')}"
    except Exception as e:
        print("Error in /run:", e)
        return f"Internal Error: {str(e)}"

def get_nifty_summary():
    try:
        res = requests.get(NSE_URL, headers=headers, timeout=10)
        data = res.json()
        indices = data.get("data", [])

        nifty = next((item for item in indices if item["index"] == "NIFTY 50"), None)
        if not nifty:
            return "❌ Unable to fetch Nifty data from NSE."

        current = float(nifty["last"])
        open_price = float(nifty["open"])
        high = float(nifty["high"])
        low = float(nifty["low"])
        prev_close = float(nifty["previousClose"])

        trend = "Bullish" if current > prev_close else "Bearish"
        support = f"{current - 70:.0f} / {current - 120:.0f}"
        resistance = f"{current + 70:.0f} / {current + 120:.0f}"

        msg = f"""📊 *Nifty 50 Live Analysis* – {datetime.now().strftime('%A, %d %B %Y • %H:%M')}
*Price:* ₹{current:.2f}
*Trend:* {trend}
*Open:* ₹{open_price:.2f}
*High:* ₹{high:.2f}
*Low:* ₹{low:.2f}
*Prev Close:* ₹{prev_close:.2f}

📌 *Key Levels:*
Support: {support}
Resistance: {resistance}

🔁 Data Source: NSE India
"""
        return msg
    except Exception as e:
        return f"❌ Error fetching Nifty summary: {str(e)}"

def send_telegram_message(msg):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {
            "chat_id": CHAT_ID,
            "text": msg,
            "parse_mode": "Markdown"
        }
        response = requests.post(url, data=data)
        return response.json()
    except Exception as e:
        return {"ok": False, "description": str(e)}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
