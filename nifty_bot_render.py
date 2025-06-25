from flask import Flask
from datetime import datetime
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup
from ta.momentum import RSIIndicator
from ta.trend import MACD

# --- CONFIG ---
BOT_TOKEN = "7974119756:AAESnz98xnm3XhPqoUkVQ6FQVQjOlsWAfw4"
CHAT_ID = "622334857"
SYMBOL = "^NSEI"  # Nifty 50

app = Flask(__name__)

@app.route("/")
def home():
    return "Nifty Render Bot is running."

@app.route("/ping")
def ping():
    return "Pong"

@app.route("/run")
def run_analysis():
    try:
        message = get_technical_summary()
        result = send_telegram_message(message)
        print("Telegram response:", result)
        if result.get("ok"):
            return "Message sent to Telegram!"
        else:
            return f"Telegram failed: {result.get('description', 'Unknown error')}"
    except Exception as e:
        print("Error in run_analysis:", e)
        return f"Internal Error: {str(e)}"

def get_technical_summary():
    try:
        df = yf.download(SYMBOL, period="2d", interval="5m", progress=False)
        if df is None or df.empty:
            return "No data received from yfinance (market closed or blocked)."
        df.dropna(inplace=True)
    except Exception as e:
        return f"Error downloading data: {str(e)}"

    try:
        close = df["Close"]
        last_price = close.iloc[-1]
        rsi = RSIIndicator(close).rsi().iloc[-1]
        macd = MACD(close)
        ema5 = close.ewm(span=5).mean().iloc[-1]
        ema20 = close.ewm(span=20).mean().iloc[-1]
        ema200 = close.ewm(span=200).mean().iloc[-1]
        df["VWAP"] = (df["Volume"] * (df["High"] + df["Low"] + df["Close"]) / 3).cumsum() / df["Volume"].cumsum()
        vwap = df["VWAP"].iloc[-1]
        avg_vol = df["Volume"].rolling(20).mean().iloc[-2]
        spike = "Yes" if df["Volume"].iloc[-2] > avg_vol * 1.5 else "No"
        supertrend, st_dir = calculate_supertrend(df)
        trend = "Bullish" if ema5 > ema20 > ema200 else "Bearish"
        vix = get_vix()
        fii = get_fii_dii_data()

        msg = f"""Nifty AI Trade Plan – {datetime.now().strftime('%A, %d %B %Y • %H:%M')}
Price: ₹{last_price:.2f}
Trend: {trend}

Indicators:
- RSI: {rsi:.2f}
- MACD: {macd.macd().iloc[-1]:.2f} / {macd.macd_signal().iloc[-1]:.2f}
- EMA: 5({ema5:.2f}), 20({ema20:.2f}), 200({ema200:.2f})
- VWAP: {vwap:.2f}
- Volume Spike: {spike}
- SuperTrend: {supertrend.iloc[-1]:.2f} ({'BUY' if st_dir.iloc[-1]==1 else 'SELL'})

VIX: {vix if vix else 'Unavailable'}
{fii}
"""
        return msg

    except Exception as e:
        return f"Error generating summary: {str(e)}"

def calculate_supertrend(df, period=10, multiplier=3):
    hl2 = (df["High"] + df["Low"]) / 2
    tr = pd.concat([
        df["High"] - df["Low"],
        abs(df["High"] - df["Close"].shift()),
        abs(df["Low"] - df["Close"].shift())
    ], axis=1).max(axis=1)
    atr = tr.rolling(period).mean()
    upperband = hl2 + multiplier * atr
    lowerband = hl2 - multiplier * atr
    supertrend = pd.Series(index=df.index, dtype='float64')
    direction = pd.Series(index=df.index, dtype='int')
    for i in range(period, len(df)):
        if df["Close"].iloc[i] > upperband.iloc[i - 1]:
            direction.iloc[i] = 1
        elif df["Close"].iloc[i] < lowerband.iloc[i - 1]:
            direction.iloc[i] = -1
        else:
            direction.iloc[i] = direction.iloc[i - 1] if i > period else 1
        supertrend.iloc[i] = lowerband.iloc[i] if direction.iloc[i] == 1 else upperband.iloc[i]
    return supertrend, direction

def get_vix():
    try:
        url = "https://www.nseindia.com/market-data/indices-vix"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        text = soup.get_text()
        idx = text.find("India VIX")
        if idx != -1:
            return float(text[idx:idx+50].split()[2])
        return None
    except:
        return None

def get_fii_dii_data():
    try:
        url = "https://www.moneycontrol.com/stocks/marketstats/fii_dii_activity/index.php"
        res = requests.get(url, timeout=10)
        soup = BeautifulSoup(res.text, 'html.parser')
        table = soup.find_all("table")[0]
        fii_net = table.find_all("tr")[1].find_all("td")[3].text.strip()
        return f"FII Net: {fii_net}"
    except:
        return "FII/DII data unavailable"

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
