# -*- coding: utf-8 -*-
"""
S&P 500 Fundamental Analysis Bot
=================================
Posts economic indicators, news, upcoming events to Telegram
"""

import os
import requests
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Configuration
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "@lkiwanSP500")
FRED_API_KEY = os.environ.get("FRED_API_KEY", "41b6f35db23fb89a5592c0dca803b4f7")


def send_telegram(text):
    """Send message to Telegram"""
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
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False


def get_fred_data(series_id):
    """Fetch latest value from FRED API"""
    try:
        url = "https://api.stlouisfed.org/fred/series/observations"
        params = {
            'series_id': series_id,
            'api_key': FRED_API_KEY,
            'file_type': 'json',
            'sort_order': 'desc',
            'limit': 10
        }
        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            if 'observations' in data and len(data['observations']) > 0:
                obs = data['observations']
                # Get latest non-empty value
                for o in obs:
                    if o['value'] != '.':
                        current = float(o['value'])
                        current_date = o['date']
                        # Get previous value for change
                        for p in obs[1:]:
                            if p['value'] != '.':
                                previous = float(p['value'])
                                change = current - previous
                                return {'value': current, 'change': change, 'date': current_date}
                        return {'value': current, 'change': 0, 'date': current_date}
        return None
    except Exception as e:
        print(f"FRED error for {series_id}: {e}")
        return None


def post_economic_indicators():
    """Post key economic indicators"""
    print("Fetching economic indicators...")

    indicators = {
        'DFF': ('FED RATE', '🏛️', '%'),
        'UNRATE': ('UNEMPLOYMENT', '💼', '%'),
        'CPIAUCSL': ('CPI (INFLATION)', '🛒', ''),
        'VIXCLS': ('VIX', '⚡', ''),
        'DGS10': ('10Y TREASURY', '🏦', '%'),
        'T10Y2Y': ('YIELD CURVE', '📊', ''),
    }

    results = []
    for series_id, (name, emoji, unit) in indicators.items():
        data = get_fred_data(series_id)
        if data:
            change_arrow = "↑" if data['change'] > 0 else "↓" if data['change'] < 0 else "→"
            change_color = "🟢" if data['change'] > 0 else "🔴" if data['change'] < 0 else "⚪"

            if series_id == 'VIXCLS':
                # VIX: lower is better for market
                change_color = "🔴" if data['change'] > 0 else "🟢" if data['change'] < 0 else "⚪"

            results.append({
                'name': name,
                'emoji': emoji,
                'value': data['value'],
                'change': data['change'],
                'unit': unit,
                'arrow': change_arrow,
                'color': change_color
            })

    if not results:
        print("No data fetched!")
        return False

    # Build message
    msg = """
📊📊📊 <b>KEY ECONOMIC INDICATORS</b> 📊📊📊

"""

    for r in results:
        if r['unit'] == '%':
            value_str = f"{r['value']:.2f}%"
            change_str = f"{r['arrow']} {r['change']:+.2f}"
        else:
            value_str = f"{r['value']:.2f}"
            change_str = f"{r['arrow']} {r['change']:+.2f}"

        msg += f"{r['emoji']} <b>{r['name']}</b>\n"
        msg += f"   <code>{value_str}</code>  {r['color']} {change_str}\n\n"

    # Market analysis based on indicators
    vix_data = next((r for r in results if r['name'] == 'VIX'), None)
    yield_data = next((r for r in results if r['name'] == 'YIELD CURVE'), None)

    msg += "<b>📈 Quick Analysis:</b>\n"

    if vix_data and vix_data['value'] > 20:
        msg += "• VIX elevated - market fear present\n"
    elif vix_data and vix_data['value'] < 15:
        msg += "• VIX low - market complacency\n"
    else:
        msg += "• VIX normal range\n"

    if yield_data and yield_data['value'] < 0:
        msg += "• ⚠️ Yield curve INVERTED - recession signal\n"
    else:
        msg += "• Yield curve normal\n"

    msg += f"""
📅 {datetime.utcnow().strftime("%B %d, %Y %H:%M UTC")}

#SP500 #Economics #FederalReserve
"""

    success = send_telegram(msg)
    print("Economic indicators posted!" if success else "Failed to post!")
    return success


def post_market_sentiment():
    """Post market sentiment analysis"""
    print("Fetching market sentiment...")

    # Fetch VIX and related data
    vix = get_fred_data('VIXCLS')
    treasury = get_fred_data('DGS10')
    spread = get_fred_data('T10Y2Y')

    if not vix:
        print("Could not fetch VIX data")
        return False

    # Determine sentiment
    if vix['value'] < 15:
        sentiment = "GREEDY"
        sentiment_emoji = "🟢🟢🟢"
        sentiment_desc = "Market is extremely calm - potential complacency"
    elif vix['value'] < 20:
        sentiment = "BULLISH"
        sentiment_emoji = "🟢🟢"
        sentiment_desc = "Market sentiment is positive"
    elif vix['value'] < 25:
        sentiment = "NEUTRAL"
        sentiment_emoji = "🟡🟡"
        sentiment_desc = "Market is cautious but stable"
    elif vix['value'] < 30:
        sentiment = "FEARFUL"
        sentiment_emoji = "🔴🔴"
        sentiment_desc = "Elevated fear in the market"
    else:
        sentiment = "PANIC"
        sentiment_emoji = "🔴🔴🔴"
        sentiment_desc = "Extreme fear - possible capitulation"

    # Fear & Greed scale (simplified)
    fear_greed = max(0, min(100, 100 - (vix['value'] - 10) * 3))

    msg = f"""
🎭🎭🎭 <b>MARKET SENTIMENT</b> 🎭🎭🎭

{sentiment_emoji} <b>Sentiment:</b> {sentiment}
📊 <b>Fear & Greed Index:</b> {fear_greed:.0f}/100

<b>Key Metrics:</b>
⚡ VIX: <code>{vix['value']:.2f}</code>
"""

    if treasury:
        msg += f"🏦 10Y Treasury: <code>{treasury['value']:.2f}%</code>\n"

    if spread:
        curve_status = "INVERTED ⚠️" if spread['value'] < 0 else "NORMAL ✅"
        msg += f"📊 Yield Curve: <code>{spread['value']:.2f}</code> ({curve_status})\n"

    msg += f"""
<b>Analysis:</b>
{sentiment_desc}

📅 {datetime.utcnow().strftime("%B %d, %Y %H:%M UTC")}

#SP500 #Sentiment #VIX #FearAndGreed
"""

    success = send_telegram(msg)
    print("Sentiment posted!" if success else "Failed to post!")
    return success


def post_upcoming_events():
    """Post upcoming economic events"""
    print("Posting upcoming events...")

    # Economic calendar - major events (static for now, can be enhanced with API)
    today = datetime.utcnow()
    weekday = today.weekday()

    # Key recurring events
    events = []

    # Monday
    if weekday == 0:
        events.append("🏭 ISM Manufacturing (if 1st Monday)")
    # Tuesday
    elif weekday == 1:
        events.append("🛒 Consumer Confidence")
    # Wednesday
    elif weekday == 2:
        events.append("🏠 ADP Employment Report")
        events.append("📊 Fed Minutes (if scheduled)")
    # Thursday
    elif weekday == 3:
        events.append("📋 Initial Jobless Claims")
        events.append("🏭 ISM Services (if 1st Thursday)")
    # Friday
    elif weekday == 4:
        events.append("👔 Jobs Report (if 1st Friday)")
        events.append("🏭 Manufacturing Data")

    # Monthly events based on date
    day = today.day

    if 10 <= day <= 15:
        events.append("📊 CPI Inflation Report")
    if 15 <= day <= 20:
        events.append("🏭 Industrial Production")
        events.append("🏠 Housing Starts")
    if 25 <= day <= 31:
        events.append("📈 GDP Report (if end of quarter)")
        events.append("💼 Consumer Spending")

    # FOMC meetings (rough schedule)
    if today.month in [1, 3, 5, 6, 7, 9, 11, 12] and 15 <= day <= 20:
        events.append("🏛️ FOMC Meeting / Fed Decision")

    msg = """
📅📅📅 <b>UPCOMING ECONOMIC EVENTS</b> 📅📅📅

<b>This Week's Key Events:</b>

"""

    if events:
        for event in events:
            msg += f"• {event}\n"
    else:
        msg += "• No major events scheduled today\n"

    msg += """
<b>Market Hours (ET):</b>
• Pre-market: 4:00 AM - 9:30 AM
• Regular: 9:30 AM - 4:00 PM
• After-hours: 4:00 PM - 8:00 PM

<b>Key Times to Watch:</b>
• 8:30 AM ET - Economic data releases
• 10:00 AM ET - ISM / Consumer data
• 2:00 PM ET - FOMC announcements
• 2:30 PM ET - Fed Chair press conference

"""

    msg += f"""
📅 {datetime.utcnow().strftime("%B %d, %Y")}

#SP500 #EconomicCalendar #Events
"""

    success = send_telegram(msg)
    print("Events posted!" if success else "Failed to post!")
    return success


def post_technical_summary():
    """Post technical analysis summary"""
    print("Fetching S&P 500 data for technical analysis...")

    try:
        import yfinance as yf
        sp500 = yf.Ticker("^GSPC")
        data = sp500.history(period="60d")

        if data.empty:
            print("No data!")
            return False

        current = data['Close'].iloc[-1]
        prev = data['Close'].iloc[-2]
        change = current - prev
        change_pct = (change / prev) * 100

        # Calculate indicators
        sma_20 = data['Close'].rolling(20).mean().iloc[-1]
        sma_50 = data['Close'].rolling(50).mean().iloc[-1]

        # RSI
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1]

        # MACD
        ema12 = data['Close'].ewm(span=12).mean()
        ema26 = data['Close'].ewm(span=26).mean()
        macd = (ema12 - ema26).iloc[-1]
        signal = (ema12 - ema26).ewm(span=9).mean().iloc[-1]

        # Bollinger Bands
        bb_mid = sma_20
        bb_std = data['Close'].rolling(20).std().iloc[-1]
        bb_upper = bb_mid + (bb_std * 2)
        bb_lower = bb_mid - (bb_std * 2)

        # Trend
        trend = "BULLISH 📈" if current > sma_20 > sma_50 else "BEARISH 📉" if current < sma_20 < sma_50 else "NEUTRAL ➡️"

        # RSI signal
        if rsi > 70:
            rsi_signal = "OVERBOUGHT 🔴"
        elif rsi < 30:
            rsi_signal = "OVERSOLD 🟢"
        else:
            rsi_signal = "NEUTRAL 🟡"

        # MACD signal
        macd_signal = "BULLISH 🟢" if macd > signal else "BEARISH 🔴"

        change_emoji = "🟢" if change > 0 else "🔴"

        msg = f"""
📈📈📈 <b>S&P 500 TECHNICAL ANALYSIS</b> 📈📈📈

<b>Current Price:</b>
{change_emoji} <code>${current:,.2f}</code>
   Change: {change:+.2f} ({change_pct:+.2f}%)

<b>Moving Averages:</b>
• SMA 20: <code>${sma_20:,.2f}</code>
• SMA 50: <code>${sma_50:,.2f}</code>
• Trend: {trend}

<b>Momentum Indicators:</b>
• RSI (14): <code>{rsi:.1f}</code> - {rsi_signal}
• MACD: <code>{macd:.2f}</code> - {macd_signal}

<b>Bollinger Bands:</b>
• Upper: <code>${bb_upper:,.2f}</code>
• Middle: <code>${bb_mid:,.2f}</code>
• Lower: <code>${bb_lower:,.2f}</code>

<b>Support/Resistance:</b>
• Resistance: <code>${current * 1.02:,.2f}</code>
• Support: <code>${current * 0.98:,.2f}</code>

📅 {datetime.utcnow().strftime("%B %d, %Y %H:%M UTC")}

#SP500 #TechnicalAnalysis #RSI #MACD
"""

        success = send_telegram(msg)
        print("Technical analysis posted!" if success else "Failed to post!")
        return success

    except Exception as e:
        print(f"Error: {e}")
        return False


def post_daily_summary():
    """Post comprehensive daily summary"""
    print("Creating daily summary...")

    try:
        import yfinance as yf
        sp500 = yf.Ticker("^GSPC")
        data = sp500.history(period="5d")

        if data.empty:
            return False

        current = data['Close'].iloc[-1]
        prev = data['Close'].iloc[-2]
        week_ago = data['Close'].iloc[0]

        daily_change = ((current - prev) / prev) * 100
        weekly_change = ((current - week_ago) / week_ago) * 100

        # Get VIX
        vix = get_fred_data('VIXCLS')
        vix_value = vix['value'] if vix else "N/A"

        daily_emoji = "🟢" if daily_change > 0 else "🔴"
        weekly_emoji = "🟢" if weekly_change > 0 else "🔴"

        msg = f"""
📊📊📊 <b>S&P 500 DAILY SUMMARY</b> 📊📊📊

<b>Market Overview:</b>
💰 Price: <code>${current:,.2f}</code>
{daily_emoji} Daily: <code>{daily_change:+.2f}%</code>
{weekly_emoji} Weekly: <code>{weekly_change:+.2f}%</code>
⚡ VIX: <code>{vix_value}</code>

<b>Key Levels:</b>
• High: <code>${data['High'].iloc[-1]:,.2f}</code>
• Low: <code>${data['Low'].iloc[-1]:,.2f}</code>
• Open: <code>${data['Open'].iloc[-1]:,.2f}</code>

<b>Volume:</b>
📊 {data['Volume'].iloc[-1]:,.0f}

📅 {datetime.utcnow().strftime("%B %d, %Y")}

#SP500 #DailySummary #StockMarket
"""

        success = send_telegram(msg)
        print("Daily summary posted!" if success else "Failed to post!")
        return success

    except Exception as e:
        print(f"Error: {e}")
        return False


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()

        if cmd == "economic":
            post_economic_indicators()
        elif cmd == "sentiment":
            post_market_sentiment()
        elif cmd == "events":
            post_upcoming_events()
        elif cmd == "technical":
            post_technical_summary()
        elif cmd == "summary":
            post_daily_summary()
        elif cmd == "all":
            post_economic_indicators()
            post_market_sentiment()
            post_technical_summary()
        elif cmd == "test":
            send_telegram("✅ Fundamental Analysis Bot is working!")
            print("Test sent!")
        else:
            print(f"Unknown: {cmd}")
            print("Commands: economic, sentiment, events, technical, summary, all, test")
    else:
        print("Fundamental Analysis Bot")
        print("Commands: economic, sentiment, events, technical, summary, all, test")
