# -*- coding: utf-8 -*-
"""
S&P 500 Telegram Bot - GitHub Actions
"""

import os
import requests
from datetime import datetime

# Configuration from GitHub Secrets
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "@lkiwanSP500")

def send_telegram(text):
    """Send message to Telegram"""
    if not TELEGRAM_BOT_TOKEN:
        print("No token!")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        response = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML"
        }, timeout=30)
        print(f"Status: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def post_market_open():
    msg = """
🔔🔔🔔 <b>MARKET OPEN</b> 🔔🔔🔔

🇺🇸 <b>US Stock Market is NOW OPEN!</b>

⏰ Trading Hours: 9:30 AM - 4:00 PM ET
📊 Index: S&P 500

Good luck traders! 💪

#MarketOpen #SP500 #Trading
"""
    return send_telegram(msg)

def post_market_close():
    today = datetime.utcnow()
    next_day = "Monday" if today.weekday() == 4 else "Tomorrow"

    msg = f"""
🔔🔔🔔 <b>MARKET CLOSED</b> 🔔🔔🔔

🇺🇸 <b>US Stock Market is NOW CLOSED!</b>

📊 Today's session has ended.
⏰ Next open: {next_day} 9:30 AM ET

See you next trading day! 👋

#MarketClose #SP500 #Trading
"""
    return send_telegram(msg)

def post_report():
    msg = """
📊 <b>S&P 500 Daily Report</b>

Bot is running on GitHub Actions!
Performance tracking coming soon.

#SP500 #Report
"""
    return send_telegram(msg)

if __name__ == "__main__":
    import sys

    cmd = sys.argv[1] if len(sys.argv) > 1 else "test"

    if cmd == "open":
        post_market_open()
        print("Market open posted!")
    elif cmd == "close":
        post_market_close()
        print("Market close posted!")
    elif cmd == "report":
        post_report()
        print("Report posted!")
    elif cmd == "test":
        send_telegram("✅ GitHub Actions Bot is working!")
        print("Test sent!")
    else:
        print(f"Unknown command: {cmd}")
