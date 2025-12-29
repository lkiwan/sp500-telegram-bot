# -*- coding: utf-8 -*-
"""
Channel Branding
================
Logo and welcome message for @lkiwanSP500
"""

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from io import BytesIO
from datetime import datetime
import os
import requests

# Telegram config
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "@lkiwanSP500")

# Colors (matching our dark theme)
COLORS = {
    'background': '#131722',
    'primary': '#26a69a',      # Teal
    'secondary': '#ef5350',    # Coral
    'accent': '#f7931a',       # Orange
    'text': '#ffffff',
    'text_muted': '#787b86',
}


def create_logo(size: int = 500) -> BytesIO:
    """
    Create professional channel logo.

    Design: Dark background with stylized chart line and "SP500" text
    """
    fig, ax = plt.subplots(figsize=(5, 5), facecolor=COLORS['background'])
    ax.set_facecolor(COLORS['background'])
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis('off')

    # Background circle
    circle_bg = mpatches.Circle((50, 50), 45,
                                 facecolor=COLORS['background'],
                                 edgecolor=COLORS['primary'],
                                 linewidth=4)
    ax.add_patch(circle_bg)

    # Inner glow circle
    circle_glow = mpatches.Circle((50, 50), 42,
                                   facecolor='none',
                                   edgecolor=COLORS['primary'],
                                   linewidth=1, alpha=0.3)
    ax.add_patch(circle_glow)

    # Stylized upward chart line
    x_line = [15, 25, 35, 45, 50, 60, 70, 80, 85]
    y_line = [40, 35, 45, 38, 50, 55, 48, 60, 70]

    # Chart line with gradient effect
    ax.plot(x_line, y_line, color=COLORS['primary'], linewidth=4,
            solid_capstyle='round', solid_joinstyle='round')

    # Upward arrow at the end
    ax.annotate('', xy=(88, 75), xytext=(82, 65),
                arrowprops=dict(arrowstyle='->', color=COLORS['primary'], lw=3))

    # Small candles for decoration
    candle_positions = [(20, 38), (35, 42), (55, 52), (75, 55)]
    for x, y in candle_positions:
        # Wick
        ax.plot([x, x], [y-3, y+5], color=COLORS['primary'], linewidth=1, alpha=0.5)
        # Body
        rect = mpatches.Rectangle((x-1.5, y-1), 3, 4,
                                   facecolor=COLORS['primary'], alpha=0.7)
        ax.add_patch(rect)

    # "S&P" text
    ax.text(50, 28, 'S&P', fontsize=28, fontweight='bold',
            ha='center', va='center', color=COLORS['text'],
            fontfamily='sans-serif')

    # "500" text with accent
    ax.text(50, 15, '500', fontsize=22, fontweight='bold',
            ha='center', va='center', color=COLORS['accent'],
            fontfamily='sans-serif')

    # Save to buffer
    buffer = BytesIO()
    fig.savefig(buffer, format='png', dpi=100,
               facecolor=COLORS['background'],
               edgecolor='none', bbox_inches='tight',
               pad_inches=0)
    buffer.seek(0)
    plt.close(fig)

    return buffer


def create_banner() -> BytesIO:
    """Create a banner image for channel header or posts."""
    fig, ax = plt.subplots(figsize=(12, 4), facecolor=COLORS['background'])
    ax.set_facecolor(COLORS['background'])
    ax.set_xlim(0, 120)
    ax.set_ylim(0, 40)
    ax.axis('off')

    # Background gradient effect (simulated with rectangles)
    for i in range(120):
        alpha = 0.02 if i % 10 < 5 else 0.01
        ax.axvline(x=i, color=COLORS['primary'], alpha=alpha, linewidth=2)

    # Chart line across banner
    x = np.linspace(0, 120, 50)
    y = 20 + 8 * np.sin(x/10) + np.random.randn(50) * 0.5
    y = np.cumsum(np.random.randn(50) * 0.3) + 20
    y = np.clip(y, 10, 30)

    ax.fill_between(x, 5, y, color=COLORS['primary'], alpha=0.1)
    ax.plot(x, y, color=COLORS['primary'], linewidth=2, alpha=0.8)

    # Main text
    ax.text(60, 28, '@lkiwanSP500', fontsize=32, fontweight='bold',
            ha='center', va='center', color=COLORS['text'],
            fontfamily='sans-serif')

    ax.text(60, 18, 'S&P 500 Trading Signals & Analysis', fontsize=14,
            ha='center', va='center', color=COLORS['text_muted'],
            fontfamily='sans-serif')

    # Decorative elements
    ax.text(10, 20, '📈', fontsize=24, ha='center', va='center')
    ax.text(110, 20, '💹', fontsize=24, ha='center', va='center')

    buffer = BytesIO()
    fig.savefig(buffer, format='png', dpi=150,
               facecolor=COLORS['background'],
               edgecolor='none', bbox_inches='tight')
    buffer.seek(0)
    plt.close(fig)

    return buffer


def get_channel_description() -> str:
    """Get the channel description/bio text."""
    return """📊 S&P 500 Trading Signals & Analysis

🎯 What We Offer:
• Daily trading signals with entry/TP/SL
• Technical analysis with professional charts
• Economic indicators & market sentiment
• Performance tracking (starting $1,000)

⏰ Daily Schedule (Mon-Fri):
• 8:00 AM - Morning Briefing
• 9:30 AM - Market Open Analysis
• 12:00 PM - Technical Breakdown
• 4:00 PM - Market Close Recap

📈 Our Approach:
Data-driven signals using RSI, MACD, Bollinger Bands, and more. We explain WHY, not just WHAT.

🤖 Powered by AI & Technical Analysis"""


def get_welcome_message() -> str:
    """Get the pinned welcome message."""
    return """
🎉 <b>Welcome to @lkiwanSP500!</b> 🎉

Your home for <b>professional S&P 500 analysis</b> and trading signals.

━━━━━━━━━━━━━━━━━━━━━━

📊 <b>WHAT YOU'LL GET:</b>

🔹 <b>Trading Signals</b>
   Entry, Take Profit, Stop Loss levels
   Only when confidence > 60%

🔹 <b>Technical Analysis</b>
   Professional charts with RSI, MACD, Bollinger
   Human-like explanations

🔹 <b>Economic Dashboard</b>
   VIX, Fed Rate, Treasury Yields
   Fear & Greed Index

🔹 <b>Performance Tracking</b>
   $1,000 starting portfolio
   Win rate & P&L statistics

━━━━━━━━━━━━━━━━━━━━━━

⏰ <b>DAILY SCHEDULE (Mon-Fri ET):</b>

☀️ 8:00 AM  → Morning Briefing
🔔 9:30 AM  → Market Open + Chart
📊 10:30 AM → Sentiment Analysis
📈 12:00 PM → Technical Analysis
💹 1:30 PM  → Economic Update
🔔 4:00 PM  → Market Close Recap
🏆 Friday   → Weekly Report

━━━━━━━━━━━━━━━━━━━━━━

🎓 <b>OUR PHILOSOPHY:</b>

"Hey traders! We don't just tell you WHAT to do - we explain WHY. Every signal comes with technical reasoning so you can learn and grow as a trader."

━━━━━━━━━━━━━━━━━━━━━━

🚀 <b>Let's grow together!</b>

Turn on notifications 🔔 to never miss a signal!

#SP500 #Trading #StockMarket #TradingSignals
"""


def send_telegram(text: str) -> bool:
    """Send message to Telegram."""
    if not TELEGRAM_BOT_TOKEN:
        print("No Telegram token!")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        response = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }, timeout=30)
        print(f"Message sent: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def send_photo(image_buffer: BytesIO, caption: str = "") -> bool:
    """Send photo to Telegram."""
    if not TELEGRAM_BOT_TOKEN:
        print("No Telegram token!")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    image_buffer.seek(0)

    files = {'photo': ('image.png', image_buffer, 'image/png')}
    data = {
        'chat_id': TELEGRAM_CHAT_ID,
        'caption': caption[:1024],
        'parse_mode': 'HTML'
    }

    try:
        response = requests.post(url, files=files, data=data, timeout=60)
        print(f"Photo sent: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def post_welcome_message():
    """Post the welcome message to the channel."""
    print("Posting welcome message...")
    return send_telegram(get_welcome_message())


def post_logo():
    """Post the logo to the channel."""
    print("Creating and posting logo...")
    logo = create_logo()
    return send_photo(logo, "🎨 Channel Logo - @lkiwanSP500")


def post_banner():
    """Post the banner to the channel."""
    print("Creating and posting banner...")
    banner = create_banner()
    return send_photo(banner, "")


def save_logo_locally(path: str = "logo.png"):
    """Save logo to local file."""
    logo = create_logo()
    with open(path, 'wb') as f:
        f.write(logo.getvalue())
    print(f"Logo saved to {path}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()

        if cmd == "welcome":
            post_welcome_message()
        elif cmd == "logo":
            post_logo()
        elif cmd == "banner":
            post_banner()
        elif cmd == "save_logo":
            save_logo_locally("logo.png")
        elif cmd == "description":
            print(get_channel_description())
        elif cmd == "all":
            post_banner()
            post_welcome_message()
        else:
            print(f"Unknown command: {cmd}")
            print("Available: welcome, logo, banner, save_logo, description, all")
    else:
        print("Channel Branding Tools")
        print("=" * 40)
        print("\nChannel Description:")
        print(get_channel_description())
