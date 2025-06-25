from flask import Flask
import requests
from datetime import datetime

# --- CONFIG ---
BOT_TOKEN = "7974119756:AAESnz98xnm3XhPqoUkVQ6FQVQjOlsWAfw4"
CHAT_ID = "622334857"

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
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/"
        })

        # Hit NSE homepage once to get cookies
        session.get("https://www.nseindia.com", timeout=10)

        # Get option chain snapshot with live spot price
        response = session.get(
            "https://www.nseindia.com/api/option-chain-indices?symbol=NIFTY",
            timeout=10
        )
        data = response.json()
        spot_price = float(data["records"]["underlyingValue"])

        # Approximate previous close from change in CE (not exact, but works)
        try:
            prev_close = spot_price - float(data["filtered"]["data"][0]["CE"]["change"])
        except:
            prev_close = spot_price  # fallback

        trend = "Bullish" if spot_price > prev_close else "Bearish"
        support = f"{spot_price - 70:.0f} / {spot_price - 120:.0f}"
        resistance = f"{spot_price + 70:.0f} / {spot_price + 120:.0f}"

        msg = f"""📊 *Nifty 50 Live Analysis* – {datetime.now().strftime('%A, %d %B %Y • %H:%M')}
*Spot Price:* ₹{spot_price:.2f}
*Trend:* {trend}
*Prev Close (approx):* ₹{prev_close:.2f}

📌 *Key Levels:*
- Support: {support}
- Resistance: {resistance}

🔁 Data Source: NSE Option Chain API
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
