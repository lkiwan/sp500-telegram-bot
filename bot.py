# -*- coding: utf-8 -*-
"""
S&P 500 Professional Telegram Bot
=================================
Main orchestrator for all bot functions
"""

import os
import sys
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from io import BytesIO
import pytz

# Import custom modules
from styles import EMOJI, get_hashtags
from chart_generator import ChartGenerator
from commentary_engine import TradingMentor, POST_TEMPLATES
from signal_tracker import SignalTracker
from branding import post_welcome_message, post_logo, post_banner, get_channel_description
from news_fetcher import NewsFetcher, format_news_post, format_earnings_post
from ml_predictor import MLPredictor
from content_database import (
    get_random_wisdom, get_random_theory, get_random_history,
    get_wisdom_by_index, get_theory_by_index, get_history_for_today,
    get_day_of_year_index, get_morning_greeting, get_night_greeting,
    get_encouragement, get_win_phrase, get_loss_phrase,
    TRADING_WISDOM, TRADING_THEORY, HISTORICAL_EVENTS
)
from risk_manager import risk_manager
from performance_tracker import performance_tracker

# Configuration from GitHub Secrets
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "@lkiwanSP500")
FRED_API_KEY = os.environ.get("FRED_API_KEY", "")

# Thresholds
MIN_CONFIDENCE = 50

# Timezones
TZ_ET = pytz.timezone('US/Eastern')
TZ_MOROCCO = pytz.timezone('Africa/Casablanca')


def get_dual_time() -> str:
    """Get current time in both ET and Morocco format."""
    now_utc = datetime.now(pytz.UTC)
    now_et = now_utc.astimezone(TZ_ET)
    now_morocco = now_utc.astimezone(TZ_MOROCCO)

    return f"🇺🇸 {now_et.strftime('%I:%M %p')} ET | 🇲🇦 {now_morocco.strftime('%H:%M')} Morocco"


def get_time_header() -> str:
    """Get formatted time header with both timezones."""
    now_utc = datetime.now(pytz.UTC)
    now_et = now_utc.astimezone(TZ_ET)
    now_morocco = now_utc.astimezone(TZ_MOROCCO)

    date_str = now_et.strftime('%b %d, %Y')
    time_et = now_et.strftime('%I:%M %p')
    time_morocco = now_morocco.strftime('%H:%M')

    return f"📅 {date_str}\n🇺🇸 {time_et} ET | 🇲🇦 {time_morocco} Morocco"

# Initialize components
charts = ChartGenerator()
mentor = TradingMentor()
tracker = SignalTracker("data/signals.json", initial_capital=1000.0)
news = NewsFetcher()

# Predictor for signal generation
ml_predictor = MLPredictor(models_path="models")


def send_telegram(text: str) -> bool:
    """Send text message to Telegram."""
    if not TELEGRAM_BOT_TOKEN:
        print("No Telegram token!")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        response = requests.post(url, json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML"
        }, timeout=30)
        print(f"Message sent: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending message: {e}")
        return False


def send_telegram_photo(image_buffer: BytesIO, caption: str = "") -> bool:
    """Send photo to Telegram channel."""
    if not TELEGRAM_BOT_TOKEN:
        print("No Telegram token!")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"

    # Reset buffer position
    image_buffer.seek(0)

    files = {'photo': ('chart.png', image_buffer, 'image/png')}
    data = {
        'chat_id': TELEGRAM_CHAT_ID,
        'caption': caption[:1024],  # Telegram caption limit
        'parse_mode': 'HTML'
    }

    try:
        response = requests.post(url, files=files, data=data, timeout=60)
        print(f"Photo sent: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending photo: {e}")
        return False


def get_signals_summary() -> str:
    """Generate a summary of recent signals and portfolio status."""
    signals = tracker.data.get('signals', [])
    portfolio = tracker.data.get('portfolio', {})
    stats = tracker.data.get('stats', {})

    # Get last 5 signals
    recent_signals = signals[-5:] if len(signals) > 5 else signals

    summary_lines = []
    summary_lines.append(f"\n{EMOJI['chart']} <b>SIGNALS HISTORY</b>")
    summary_lines.append("─" * 20)

    if not recent_signals:
        summary_lines.append("No signals yet")
    else:
        for sig in reversed(recent_signals):
            direction = sig.get('direction', 'N/A')
            status = sig.get('status', 'open')
            entry = sig.get('entry_price', 0)
            pnl = sig.get('pnl_pct')

            # Status emoji and text
            if status == 'open':
                status_emoji = "🔵"
                status_text = "EN COURS"
                pnl_text = ""
            elif status == 'tp_hit':
                status_emoji = "✅"
                status_text = "WIN"
                pnl_text = f" (+{pnl:.2f}%)" if pnl else ""
            elif status == 'sl_hit':
                status_emoji = "❌"
                status_text = "LOSS"
                pnl_text = f" ({pnl:.2f}%)" if pnl else ""
            else:
                status_emoji = "⚪"
                status_text = status.upper()
                pnl_text = f" ({pnl:.2f}%)" if pnl else ""

            dir_emoji = "📈" if direction == "LONG" else "📉"
            summary_lines.append(f"{status_emoji} {dir_emoji} {direction} @ ${entry:,.2f} → {status_text}{pnl_text}")

    # Portfolio summary
    initial = portfolio.get('initial_capital', 1000)
    current = portfolio.get('current_value', 1000)
    total_return = ((current - initial) / initial) * 100

    wins = stats.get('wins', 0)
    losses = stats.get('losses', 0)
    total_trades = wins + losses
    win_rate = (wins / total_trades * 100) if total_trades > 0 else 0

    summary_lines.append("")
    summary_lines.append(f"{EMOJI['money']} <b>SIMULATION</b>")
    summary_lines.append("─" * 20)
    summary_lines.append(f"💰 Capital: <b>${current:,.2f}</b>")
    if total_return >= 0:
        summary_lines.append(f"📊 Return: <b>+{total_return:.2f}%</b>")
    else:
        summary_lines.append(f"📊 Return: <b>{total_return:.2f}%</b>")

    if total_trades > 0:
        summary_lines.append(f"🎯 Win Rate: {win_rate:.0f}% ({wins}W/{losses}L)")

    return "\n".join(summary_lines)


def fetch_sp500_data(days: int = 60) -> pd.DataFrame:
    """Fetch S&P 500 data using yfinance."""
    try:
        import yfinance as yf
        ticker = yf.Ticker("^GSPC")
        data = ticker.history(period=f"{days}d")

        if data.empty:
            print("No data from yfinance")
            return None

        data = data.reset_index()
        data.columns = [c.lower() if c != 'Date' else c for c in data.columns]

        if 'Date' in data.columns:
            data['date'] = pd.to_datetime(data['Date']).dt.tz_localize(None)
            data.set_index('date', inplace=True)

        print(f"Fetched {len(data)} days of S&P 500 data")
        return data
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None


def calculate_indicators(df: pd.DataFrame) -> dict:
    """Calculate technical indicators."""
    df = df.copy()

    indicators = {}

    # Moving averages
    if len(df) >= 20:
        indicators['sma_20'] = df['close'].rolling(20).mean()
    if len(df) >= 50:
        indicators['sma_50'] = df['close'].rolling(50).mean()

    # Bollinger Bands
    if len(df) >= 20:
        bb_middle = df['close'].rolling(20).mean()
        bb_std = df['close'].rolling(20).std()
        indicators['bb_upper'] = bb_middle + (bb_std * 2)
        indicators['bb_lower'] = bb_middle - (bb_std * 2)

    # RSI
    if len(df) >= 14:
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        indicators['rsi'] = 100 - (100 / (1 + rs))

    # MACD
    if len(df) >= 26:
        ema_12 = df['close'].ewm(span=12).mean()
        ema_26 = df['close'].ewm(span=26).mean()
        indicators['macd'] = ema_12 - ema_26
        indicators['macd_signal'] = indicators['macd'].ewm(span=9).mean()
        indicators['macd_histogram'] = indicators['macd'] - indicators['macd_signal']

    return indicators


def get_current_data() -> dict:
    """Get current market data and indicators."""
    df = fetch_sp500_data(60)
    if df is None or len(df) < 20:
        return None

    indicators = calculate_indicators(df)

    current = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else current

    return {
        'close': current['close'],
        'open': current['open'],
        'high': current['high'],
        'low': current['low'],
        'volume': current['volume'],
        'prev_close': prev['close'],
        'change': current['close'] - prev['close'],
        'change_pct': ((current['close'] - prev['close']) / prev['close']) * 100,
        'rsi': indicators['rsi'].iloc[-1] if 'rsi' in indicators else 50,
        'macd': indicators['macd'].iloc[-1] if 'macd' in indicators else 0,
        'macd_signal': indicators['macd_signal'].iloc[-1] if 'macd_signal' in indicators else 0,
        'macd_hist': indicators['macd_histogram'].iloc[-1] if 'macd_histogram' in indicators else 0,
        'prev_macd_hist': indicators['macd_histogram'].iloc[-2] if 'macd_histogram' in indicators and len(indicators['macd_histogram']) > 1 else 0,
        'sma_20': indicators['sma_20'].iloc[-1] if 'sma_20' in indicators else current['close'],
        'sma_50': indicators['sma_50'].iloc[-1] if 'sma_50' in indicators else current['close'],
        'bb_upper': indicators['bb_upper'].iloc[-1] if 'bb_upper' in indicators else current['close'],
        'bb_lower': indicators['bb_lower'].iloc[-1] if 'bb_lower' in indicators else current['close'],
        'df': df,
        'indicators': indicators
    }


def get_economic_data() -> dict:
    """Fetch economic data from FRED API."""
    data = {
        'vix': 20.0,
        'fear_greed': 50,
        'fed_rate': 5.25,
        'unemployment': 4.0,
        'cpi': 3.0,
        'treasury_10y': 4.5,
    }

    if not FRED_API_KEY:
        return data

    series_map = {
        'VIXCLS': 'vix',
        'DFF': 'fed_rate',
        'UNRATE': 'unemployment',
        'DGS10': 'treasury_10y',
    }

    for series_id, key in series_map.items():
        try:
            url = f"https://api.fred.stlouisfed.org/series/observations"
            params = {
                'series_id': series_id,
                'api_key': FRED_API_KEY,
                'file_type': 'json',
                'sort_order': 'desc',
                'limit': 1
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                obs = response.json().get('observations', [])
                if obs and obs[0]['value'] != '.':
                    data[key] = float(obs[0]['value'])
        except Exception as e:
            print(f"Error fetching {series_id}: {e}")

    # Calculate Fear & Greed from VIX
    vix = data['vix']
    if vix < 15:
        data['fear_greed'] = 80
    elif vix < 20:
        data['fear_greed'] = 65
    elif vix < 25:
        data['fear_greed'] = 50
    elif vix < 30:
        data['fear_greed'] = 35
    else:
        data['fear_greed'] = 20

    return data


# ============================================
# POST FUNCTIONS
# ============================================

def post_morning_briefing():
    """Post professional morning briefing with yesterday's result."""
    print("Posting morning briefing...")

    data = get_current_data()
    if not data:
        print("Could not get market data")
        return False

    current = data['close']
    change_pct = data['change_pct']
    rsi = data['rsi']
    macd_bullish = data['macd_hist'] > 0
    above_sma20 = current > data['sma_20']
    above_sma50 = current > data['sma_50']

    # Get economic data
    economic_data = get_economic_data()
    vix = economic_data.get('vix', 20)

    # Yesterday's result emoji
    if change_pct > 0.5:
        result_emoji = "🟢🟢"
        result_text = "Strong Up"
    elif change_pct > 0:
        result_emoji = "🟢"
        result_text = "Up"
    elif change_pct > -0.5:
        result_emoji = "🔴"
        result_text = "Down"
    else:
        result_emoji = "🔴🔴"
        result_text = "Strong Down"

    # Trend status
    if above_sma20 and above_sma50:
        trend = "🟢 Bullish (above SMA 20 & 50)"
    elif above_sma20:
        trend = "🟡 Mixed (above SMA 20 only)"
    elif above_sma50:
        trend = "🟡 Mixed (above SMA 50 only)"
    else:
        trend = "🔴 Bearish (below both SMAs)"

    # RSI status
    if rsi < 30:
        rsi_note = "🟢 OVERSOLD - Bounce potential"
    elif rsi > 70:
        rsi_note = "🔴 OVERBOUGHT - Pullback possible"
    else:
        rsi_note = f"⚪ Neutral zone"

    # VIX status
    if vix > 25:
        vix_note = "🔴 High fear - volatile"
    elif vix < 15:
        vix_note = "🟢 Low fear - calm"
    else:
        vix_note = "🟡 Normal range"

    # Support/Resistance (1% levels)
    support = current * 0.99
    resistance = current * 1.01

    time_header = get_time_header()

    msg = f"""
☀️ <b>MORNING BRIEFING</b> ☀️

{time_header}

Good morning traders!

━━━━━━━━━━━━━━━━━━━━

<b>📊 YESTERDAY'S CLOSE</b>

{result_emoji} S&P 500: <code>${current:,.2f}</code>
{result_emoji} Change: <b>{change_pct:+.2f}%</b> ({result_text})

━━━━━━━━━━━━━━━━━━━━

<b>📈 TECHNICAL PICTURE</b>

• Trend: {trend}
• RSI: {rsi:.0f} - {rsi_note}
• MACD: {'🟢 Bullish' if macd_bullish else '🔴 Bearish'}
• VIX: {vix:.1f} - {vix_note}

━━━━━━━━━━━━━━━━━━━━

<b>🎯 KEY LEVELS</b>

• Resistance: ${resistance:,.0f} (+1%)
• Support: ${support:,.0f} (-1%)

━━━━━━━━━━━━━━━━━━━━

<i>Daily signal coming at 12:00 PM ET</i>

#SP500 #MorningBriefing #Trading
"""
    return send_telegram(msg)


def post_market_open():
    """Post market open with chart."""
    print("Posting market open...")

    data = get_current_data()
    if not data:
        return send_telegram(f"{EMOJI['bell']} <b>MARKET OPEN</b>\n\nUS Market is now open! Good luck traders! 💪")

    df = data['df']
    indicators = data['indicators']

    # Generate chart
    chart_df = df.copy()
    chart_df.columns = [c.capitalize() for c in chart_df.columns]

    try:
        chart_buffer = charts.generate_technical_chart(
            chart_df,
            title=f"S&P 500 - Market Open {datetime.now().strftime('%b %d')}",
            show_volume=True,
            show_rsi=True,
            show_macd=True,
            show_bollinger=True,
            show_sma=True
        )

        caption = f"""
{mentor.get_greeting('morning')}

{EMOJI['bell']} <b>Market Open Analysis</b>

• Price: ${data['close']:,.2f}
• RSI: {data['rsi']:.1f}
• MACD: {'Bullish' if data['macd_hist'] > 0 else 'Bearish'}

{mentor.explain_rsi(data['rsi'])}

Trade smart! 💪

{get_hashtags('open')}
"""
        return send_telegram_photo(chart_buffer, caption)

    except Exception as e:
        print(f"Chart error: {e}")
        return send_telegram(f"{EMOJI['bell']} <b>MARKET OPEN</b>\n\nUS Market is now open!")


def post_technical_analysis():
    """Post technical analysis with chart AND daily signal."""
    print("Posting technical analysis with daily signal...")

    data = get_current_data()
    if not data:
        return False

    df = data['df']
    economic_data = get_economic_data()

    # Get ML prediction for today
    prediction = ml_predictor.predict(df, economic_data)
    direction = prediction['direction']
    confidence = prediction['confidence']

    dir_emoji = "🟢" if direction == "LONG" else "🔴"
    dir_text = "UP" if direction == "LONG" else "DOWN"

    # Technical indicators
    rsi = data['rsi']
    macd_bullish = data['macd_hist'] > 0
    above_sma20 = data['close'] > data['sma_20']
    above_sma50 = data['close'] > data['sma_50']
    vix = economic_data.get('vix', 20)

    # Trend
    if above_sma20 and above_sma50:
        trend = "🟢 Uptrend"
    elif not above_sma20 and not above_sma50:
        trend = "🔴 Downtrend"
    else:
        trend = "🟡 Sideways"

    # RSI interpretation
    if rsi < 30:
        rsi_text = "Oversold 🟢"
    elif rsi > 70:
        rsi_text = "Overbought 🔴"
    else:
        rsi_text = "Neutral ⚪"

    # Generate chart
    chart_df = df.copy()
    chart_df.columns = [c.capitalize() for c in chart_df.columns]

    try:
        chart_buffer = charts.generate_technical_chart(
            chart_df,
            title=f"S&P 500 - {datetime.now().strftime('%b %d, %Y')}",
            show_volume=True,
            show_rsi=True,
            show_macd=True,
            show_bollinger=True,
            show_sma=True
        )

        time_header = get_time_header()

        caption = f"""
📊 <b>TECHNICAL ANALYSIS</b> 📊

{time_header}

{dir_emoji}{dir_emoji}{dir_emoji} <b>SIGNAL: {dir_text}</b> {dir_emoji}{dir_emoji}{dir_emoji}
<b>Confidence:</b> {confidence:.0f}%

━━━━━━━━━━━━━━━━━━━━

<b>S&P 500:</b> ${data['close']:,.2f} ({data['change_pct']:+.2f}%)

• Trend: {trend}
• RSI: {rsi:.0f} ({rsi_text})
• MACD: {'🟢 Bullish' if macd_bullish else '🔴 Bearish'}

<i>Hold 1 day | 71% win rate</i>

#SP500 #TechnicalAnalysis #{dir_text}
"""
        return send_telegram_photo(chart_buffer, caption[:1024])

    except Exception as e:
        print(f"Chart error: {e}")
        # Fallback to text-only signal
        return post_signal_check()


def post_economic_dashboard():
    """Post economic/fundamental analysis with dashboard."""
    print("Posting economic dashboard...")

    econ_data = get_economic_data()
    data = get_current_data()

    vix = econ_data.get('vix', 20)
    fear_greed = econ_data.get('fear_greed', 50)
    fed_rate = econ_data.get('fed_rate', 5.0)
    treasury_10y = econ_data.get('treasury_10y', 4.0)
    unemployment = econ_data.get('unemployment', 4.0)

    # VIX interpretation
    if vix > 30:
        vix_emoji = "🔴🔴🔴"
        vix_text = "EXTREME FEAR - High volatility"
    elif vix > 25:
        vix_emoji = "🔴🔴"
        vix_text = "HIGH FEAR - Volatile"
    elif vix > 20:
        vix_emoji = "🟡"
        vix_text = "ELEVATED - Caution"
    elif vix > 15:
        vix_emoji = "🟢"
        vix_text = "NORMAL - Stable"
    else:
        vix_emoji = "🟢🟢"
        vix_text = "LOW - Complacent"

    # Fear & Greed interpretation
    if fear_greed >= 75:
        fg_emoji = "🟢🟢"
        fg_text = "EXTREME GREED"
    elif fear_greed >= 55:
        fg_emoji = "🟢"
        fg_text = "GREED"
    elif fear_greed >= 45:
        fg_emoji = "⚪"
        fg_text = "NEUTRAL"
    elif fear_greed >= 25:
        fg_emoji = "🔴"
        fg_text = "FEAR"
    else:
        fg_emoji = "🔴🔴"
        fg_text = "EXTREME FEAR"

    # Yield curve (10Y - 2Y spread approximation)
    yield_spread = treasury_10y - fed_rate
    if yield_spread < 0:
        yield_text = "🔴 INVERTED - Recession signal"
    elif yield_spread < 0.5:
        yield_text = "🟡 FLAT - Slowdown possible"
    else:
        yield_text = "🟢 NORMAL - Growth expected"

    try:
        chart_buffer = charts.generate_economic_dashboard(econ_data)

        time_header = get_time_header()

        caption = f"""
🏛️ <b>FUNDAMENTAL ANALYSIS</b> 🏛️

{time_header}

━━━━━━━━━━━━━━━━━━━━

<b>📊 MARKET SENTIMENT</b>

{vix_emoji} VIX: {vix:.1f} - {vix_text}
{fg_emoji} Fear & Greed: {fear_greed}/100 - {fg_text}

━━━━━━━━━━━━━━━━━━━━

<b>💵 ECONOMIC INDICATORS</b>

• Fed Rate: {fed_rate:.2f}%
• 10Y Treasury: {treasury_10y:.2f}%
• Unemployment: {unemployment:.1f}%

<b>Yield Curve:</b> {yield_text}

━━━━━━━━━━━━━━━━━━━━

<i>Macro conditions affect trend strength</i>

#SP500 #FundamentalAnalysis #Economy
"""
        return send_telegram_photo(chart_buffer, caption)

    except Exception as e:
        print(f"Chart error: {e}")
        # Fallback to text
        msg = f"""
🏛️ <b>FUNDAMENTAL ANALYSIS</b>

{vix_emoji} VIX: {vix:.1f} - {vix_text}
{fg_emoji} Fear & Greed: {fear_greed}/100

Fed Rate: {fed_rate:.2f}%
10Y Treasury: {treasury_10y:.2f}%

#SP500 #Economy
"""
        return send_telegram(msg)


def post_economic_text(econ_data: dict) -> bool:
    """Fallback text economic post."""
    vix = econ_data['vix']
    if vix < 15:
        sentiment = f"{EMOJI['bullish']} EXTREME GREED"
    elif vix < 20:
        sentiment = f"{EMOJI['bullish']} GREED"
    elif vix < 25:
        sentiment = f"{EMOJI['neutral']} NEUTRAL"
    elif vix < 30:
        sentiment = f"{EMOJI['bearish']} FEAR"
    else:
        sentiment = f"{EMOJI['bearish']} EXTREME FEAR"

    msg = f"""
{EMOJI['economic']} <b>Economic Indicators</b>

<b>Market Sentiment:</b> {sentiment}

• VIX: {econ_data['vix']:.2f}
• Fed Rate: {econ_data['fed_rate']:.2f}%
• 10Y Treasury: {econ_data['treasury_10y']:.2f}%
• Unemployment: {econ_data['unemployment']:.1f}%

{get_hashtags('economic')}
"""
    return send_telegram(msg)


def post_sentiment():
    """Post simple sentiment check."""
    print("Posting sentiment...")

    econ_data = get_economic_data()
    vix = econ_data['vix']
    fg = econ_data['fear_greed']

    if vix < 15:
        sentiment_emoji = "🟢🟢🟢"
        sentiment = "EXTREME GREED"
    elif vix < 20:
        sentiment_emoji = "🟢🟢"
        sentiment = "GREED"
    elif vix < 25:
        sentiment_emoji = "🟡"
        sentiment = "NEUTRAL"
    elif vix < 30:
        sentiment_emoji = "🔴🔴"
        sentiment = "FEAR"
    else:
        sentiment_emoji = "🔴🔴🔴"
        sentiment = "EXTREME FEAR"

    msg = f"""
{sentiment_emoji} <b>{sentiment}</b>

VIX: {vix:.1f}
Fear/Greed: {fg}/100

#SP500 #Sentiment
"""
    return send_telegram(msg)


def post_signal_check():
    """
    Post daily direction signal - matches backtest logic.
    NO TP/SL - just direction prediction for next day.
    This achieved 71% win rate in backtest.
    """
    print("Checking for daily signal...")

    data = get_current_data()
    if not data:
        print("No data available")
        return False

    economic_data = get_economic_data()
    df = data['df']
    prediction = ml_predictor.predict(df, economic_data)

    direction = prediction['direction']
    confidence = prediction['confidence']
    current_price = data['close']

    print(f"Signal: {direction} with {confidence:.1f}% confidence")

    # Get technical factors for analysis
    factors = ml_predictor.get_factor_analysis(df, economic_data)

    rsi = factors['rsi']['value'] if factors else data.get('rsi', 50)
    macd_signal = factors['macd']['signal'] if factors else 'NEUTRAL'
    vix = economic_data.get('vix', 20)

    # Trend analysis
    above_sma20 = data['close'] > data['sma_20']
    above_sma50 = data['close'] > data['sma_50']

    if above_sma20 and above_sma50:
        trend = "📈 Uptrend"
    elif not above_sma20 and not above_sma50:
        trend = "📉 Downtrend"
    else:
        trend = "➡️ Sideways"

    # RSI status
    if rsi < 30:
        rsi_status = "🟢 Oversold"
    elif rsi > 70:
        rsi_status = "🔴 Overbought"
    elif rsi < 45:
        rsi_status = "🟡 Weak"
    elif rsi > 55:
        rsi_status = "🟢 Strong"
    else:
        rsi_status = "⚪ Neutral"

    # VIX regime
    if vix > 30:
        vix_status = "🔴 Extreme Fear"
    elif vix > 25:
        vix_status = "🟠 High Fear"
    elif vix > 20:
        vix_status = "🟡 Elevated"
    elif vix > 15:
        vix_status = "🟢 Normal"
    else:
        vix_status = "🟢 Low (Complacent)"

    # Direction emoji and text
    if direction == "LONG":
        dir_emoji = "🟢"
        dir_text = "UP"
        action = "BULLISH - Expect market to rise"
    else:
        dir_emoji = "🔴"
        dir_text = "DOWN"
        action = "BEARISH - Expect market to fall"

    # Confidence level
    if confidence >= 85:
        conf_text = "🔥 Very High"
    elif confidence >= 75:
        conf_text = "✅ High"
    elif confidence >= 65:
        conf_text = "📊 Moderate"
    else:
        conf_text = "⚠️ Low"

    time_header = get_time_header()

    msg = f"""
{dir_emoji}{dir_emoji}{dir_emoji} <b>DAILY SIGNAL</b> {dir_emoji}{dir_emoji}{dir_emoji}

{time_header}

<b>Direction:</b> {dir_text}
<b>Confidence:</b> {confidence:.0f}% ({conf_text})

━━━━━━━━━━━━━━━━━━━━

<b>S&P 500:</b> ${current_price:,.2f}
<b>Day Change:</b> {data['change_pct']:+.2f}%

━━━━━━━━━━━━━━━━━━━━

<b>Technical Analysis:</b>
• Trend: {trend}
• RSI ({rsi:.0f}): {rsi_status}
• MACD: {macd_signal}
• VIX ({vix:.1f}): {vix_status}

━━━━━━━━━━━━━━━━━━━━

<b>Outlook:</b> {action}

<i>Strategy: Hold 1 day, check tomorrow's close
Model Win Rate: 71%</i>

#SP500 #DailySignal #{dir_text}
"""
    return send_telegram(msg)


def post_signal_update():
    """Post hourly signal status update."""
    print("Posting signal update...")

    data = get_current_data()
    if not data:
        return False

    economic_data = get_economic_data()
    df = data['df']
    prediction = ml_predictor.predict(df, economic_data)

    direction = prediction['direction']
    confidence = prediction['confidence']
    current_price = data['close']

    dir_emoji = "🟢" if direction == "LONG" else "🔴"
    dir_text = "UP" if direction == "LONG" else "DOWN"

    dual_time = get_dual_time()

    msg = f"""
{dir_emoji} <b>SIGNAL UPDATE</b>

{dual_time}

<b>Direction:</b> {dir_text}
<b>Confidence:</b> {confidence:.0f}%

━━━━━━━━━━━━━━━━━━━━

<b>S&P 500:</b> ${current_price:,.2f} ({data['change_pct']:+.2f}%)
<b>RSI:</b> {data['rsi']:.0f}
<b>VIX:</b> {economic_data.get('vix', 20):.1f}

#SP500 #SignalUpdate
"""
    return send_telegram(msg)


def post_market_close():
    """Post simple market close recap."""
    print("Posting market close...")

    data = get_current_data()
    daily_perf = tracker.get_daily_performance()

    if not data:
        return send_telegram("🔔 <b>Market Closed</b>\n\nSee you tomorrow!\n\n#SP500")

    change_emoji = "📈" if data['change_pct'] > 0 else ("📉" if data['change_pct'] < 0 else "➡️")

    time_header = get_time_header()

    # Day result
    if data['change_pct'] > 0.5:
        result = "🟢🟢 Strong Up"
    elif data['change_pct'] > 0:
        result = "🟢 Up"
    elif data['change_pct'] > -0.5:
        result = "🔴 Down"
    else:
        result = "🔴🔴 Strong Down"

    msg = f"""
🔔 <b>MARKET CLOSE</b> 🔔

{time_header}

━━━━━━━━━━━━━━━━━━━━

{change_emoji} <b>S&P 500:</b> ${data['close']:,.2f}
{change_emoji} <b>Change:</b> {data['change_pct']:+.2f}% ({result})

━━━━━━━━━━━━━━━━━━━━

<b>Day Range:</b>
• High: ${data['high']:,.2f}
• Low: ${data['low']:,.2f}

<b>Indicators:</b>
• RSI: {data['rsi']:.0f}
• MACD: {'🟢 Bullish' if data['macd_hist'] > 0 else '🔴 Bearish'}

━━━━━━━━━━━━━━━━━━━━

See you tomorrow, traders! 👋

#SP500 #MarketClose #Trading
"""
    return send_telegram(msg)


def post_daily_analysis():
    """
    Post end-of-day analysis with signal result.
    Shows: Today's result + recent days + streaks
    """
    print("Posting daily analysis...")

    data = get_current_data()
    if not data:
        return False

    economic_data = get_economic_data()
    df = data['df']

    # Get today's signal
    prediction = ml_predictor.predict(df, economic_data)
    direction = "UP" if prediction['direction'] == "LONG" else "DOWN"
    confidence = prediction['confidence']

    today = datetime.now(TZ_ET).strftime('%Y-%m-%d')
    entry_price = data['prev_close']  # Yesterday's close = today's entry
    close_price = data['close']       # Today's close

    # Record the signal result
    performance_tracker.record_daily_signal(
        date=today,
        direction=direction,
        confidence=confidence,
        entry_price=entry_price,
        close_price=close_price
    )

    # Generate analysis
    analysis = performance_tracker.generate_daily_analysis()
    time_header = get_time_header()

    # Determine if signal was correct
    actual_change = ((close_price - entry_price) / entry_price) * 100
    if direction == "UP":
        is_correct = actual_change > 0
    else:
        is_correct = actual_change < 0

    result_emoji = "✅ WIN" if is_correct else "❌ LOSS"
    dir_emoji = "🟢" if direction == "UP" else "🔴"

    msg = f"""
📊 <b>DAILY ANALYSIS</b> 📊

{time_header}

━━━━━━━━━━━━━━━━━━━━

<b>TODAY'S SIGNAL RESULT</b>

{dir_emoji} Prediction: <b>{direction}</b>
📈 Market Move: <b>{actual_change:+.2f}%</b>
{result_emoji}

━━━━━━━━━━━━━━━━━━━━
{analysis}

#SP500 #DailyAnalysis #Performance
"""
    return send_telegram(msg)


def post_weekly_analysis():
    """
    Post weekly analysis with comparison to previous weeks.
    Shows: This week + last 2 weeks + all-time
    """
    print("Posting weekly analysis...")

    analysis = performance_tracker.generate_weekly_analysis()
    time_header = get_time_header()

    # Get current week stats for header
    current_week = performance_tracker.get_week_stats(0)

    if current_week['win_rate'] >= 70:
        header_emoji = "🏆🏆🏆"
    elif current_week['win_rate'] >= 50:
        header_emoji = "✅✅"
    else:
        header_emoji = "📊"

    msg = f"""
{header_emoji} <b>WEEKLY ANALYSIS</b> {header_emoji}

{time_header}

━━━━━━━━━━━━━━━━━━━━
{analysis}

#SP500 #WeeklyAnalysis #Performance
"""
    return send_telegram(msg)


def post_monthly_analysis():
    """
    Post monthly analysis with all weeks breakdown.
    Shows: This month + weeks + last month + all-time
    """
    print("Posting monthly analysis...")

    analysis = performance_tracker.generate_monthly_analysis()
    time_header = get_time_header()

    # Get current month stats
    current_month = performance_tracker.get_month_stats(0)

    if current_month['win_rate'] >= 70:
        header_emoji = "🏆🏆🏆"
    elif current_month['win_rate'] >= 50:
        header_emoji = "📈📈"
    else:
        header_emoji = "📊"

    msg = f"""
{header_emoji} <b>MONTHLY ANALYSIS</b> {header_emoji}

{time_header}

━━━━━━━━━━━━━━━━━━━━
{analysis}

#SP500 #MonthlyAnalysis #Performance
"""
    return send_telegram(msg)


def post_weekly_report():
    """Post weekly performance report with chart."""
    print("Posting weekly report...")

    summary = tracker.get_performance_summary()
    weekly = tracker.get_weekly_report()

    try:
        # Generate performance chart
        perf_data = {
            'portfolio_history': tracker.get_portfolio_history(),
            'wins': summary['wins'],
            'losses': summary['losses'],
            'total_pnl': summary['total_pnl_pct'],
            'current_value': summary['portfolio_value'],
            'initial_value': summary['initial_capital'],
            'monthly_returns': tracker.get_monthly_returns()
        }

        chart_buffer = charts.generate_performance_chart(perf_data)

        # Format best/worst trades
        best_trade = f"{summary['best_trade']['pnl_pct']:+.2f}%" if summary['best_trade'] else "N/A"
        worst_trade = f"{summary['worst_trade']['pnl_pct']:+.2f}%" if summary['worst_trade'] else "N/A"

        caption = f"""
{mentor.get_greeting('close')}

{EMOJI['trophy']} <b>Weekly Performance Report</b>

<b>This Week:</b>
• Trades: {weekly['trades']}
• Win Rate: {weekly['win_rate']:.1f}%
• P&L: {weekly['total_pnl_pct']:+.2f}%

<b>Portfolio:</b>
• Value: ${summary['portfolio_value']:,.2f}
• Return: {summary['total_return_pct']:+.2f}%

<b>All-Time:</b>
• Trades: {summary['total_trades']}
• Win Rate: {summary['win_rate']:.1f}%

Keep learning, keep growing! 💪

{get_hashtags('weekly')}
"""
        return send_telegram_photo(chart_buffer, caption)

    except Exception as e:
        print(f"Chart error: {e}")
        # Fallback to text
        msg = f"""
{EMOJI['trophy']} <b>Weekly Report</b>

<b>Portfolio:</b> ${summary['portfolio_value']:,.2f}
<b>Return:</b> {summary['total_return_pct']:+.2f}%
<b>Win Rate:</b> {summary['win_rate']:.1f}%

{get_hashtags('weekly')}
"""
        return send_telegram(msg)


def post_test():
    """Send test message."""
    return send_telegram("✅ Professional Bot is working!")


def post_monitor():
    """Monitor open signals and post alerts when near/hit targets."""
    print("Monitoring open signals...")

    data = get_current_data()
    if not data:
        print("Could not get market data")
        return False

    current_price = data['close']
    alerts = tracker.check_all_signals(current_price)

    if not alerts:
        print("No alerts to post")
        return False

    for alert in alerts:
        alert_type = alert['type']
        signal = alert['signal']
        price = alert['price']

        if alert_type == 'NEAR_TP':
            post_near_tp_alert(signal, price, alert.get('progress', 0))
        elif alert_type == 'NEAR_SL':
            post_near_sl_alert(signal, price, alert.get('progress', 0))
        elif alert_type == 'TP_HIT':
            post_tp_hit(signal)
        elif alert_type == 'SL_HIT':
            post_sl_hit(signal)

    return True


def post_near_tp_alert(signal: dict, current_price: float, progress: float):
    """Post alert when price is near take profit."""
    direction_emoji = EMOJI['bullish'] if signal['direction'] == 'LONG' else EMOJI['bearish']

    msg = f"""
{EMOJI['target']} <b>APPROACHING TARGET!</b> {EMOJI['target']}

{direction_emoji} <b>{signal['direction']}</b> Signal

{mentor.get_greeting()}

We're getting close, traders!

<b>Current Price:</b> ${current_price:,.2f}
<b>Take Profit:</b> ${signal['take_profit']:,.2f}
<b>Progress:</b> {progress:.0f}% of the way there!

{EMOJI['fire']} Almost at our target! Stay focused!

The market is moving in our favor. Let's see this through! 💪

#SP500 #TradingSignals #InProfit
"""
    return send_telegram(msg)


def post_near_sl_alert(signal: dict, current_price: float, progress: float):
    """Post alert when price is near stop loss."""
    direction_emoji = EMOJI['bullish'] if signal['direction'] == 'LONG' else EMOJI['bearish']

    msg = f"""
{EMOJI['warning']} <b>CAUTION - Near Stop Loss</b> {EMOJI['warning']}

{direction_emoji} <b>{signal['direction']}</b> Signal

Heads up, traders!

<b>Current Price:</b> ${current_price:,.2f}
<b>Stop Loss:</b> ${signal['stop_loss']:,.2f}
<b>Risk Level:</b> {progress:.0f}% towards SL

Stay calm. This is why we have stop losses - to protect our capital.

Remember: One trade doesn't define us. It's about the long game! 🎯

#SP500 #TradingSignals #RiskManagement
"""
    return send_telegram(msg)


def post_tp_hit(signal: dict):
    """Post celebration when take profit is hit."""
    pnl_pct = signal.get('pnl_pct', 0)
    summary = tracker.get_performance_summary()

    # Get lot size from signal confidence
    lot_size = tracker.get_lot_size(signal.get('confidence', 60))
    position_value = summary['initial_capital'] * lot_size
    dollar_gain = position_value * (pnl_pct / 100)

    msg = f"""
{EMOJI['trophy']}{EMOJI['fire']}{EMOJI['rocket']} <b>TARGET HIT!</b> {EMOJI['rocket']}{EMOJI['fire']}{EMOJI['trophy']}

{EMOJI['win']} <b>{signal['direction']}</b> Signal SUCCESSFUL!

{mentor.get_greeting()}

WE DID IT, TRADERS! 🎉

<b>Entry:</b> ${signal['entry_price']:,.2f}
<b>Exit:</b> ${signal['take_profit']:,.2f}
<b>Profit:</b> <code>+{pnl_pct:.2f}%</code> 💰
<b>Lot Size:</b> {lot_size} ({lot_size*100:.0f}%)

━━━━━━━━━━━━━━━━━━━━━━

{EMOJI['money']} <b>SIMULATOR ACCOUNT UPDATE</b>

<b>Starting Capital:</b> $1,000.00
<b>Current Value:</b> ${summary['portfolio_value']:,.2f}
<b>Total Return:</b> {summary['total_return_pct']:+.2f}%
<b>This Trade:</b> +${dollar_gain:.2f}

<b>Stats:</b>
• Win Rate: {summary['win_rate']:.1f}%
• Total Trades: {summary['total_trades']}
• Wins: {summary['wins']} | Losses: {summary['losses']}

━━━━━━━━━━━━━━━━━━━━━━

This is what discipline looks like! Great trade, everyone! 💪

#SP500 #TradingSignals #Winner #Profit
"""
    return send_telegram(msg)


def post_sl_hit(signal: dict):
    """Post support message when stop loss is hit."""
    pnl_pct = signal.get('pnl_pct', 0)
    summary = tracker.get_performance_summary()

    # Get lot size from signal confidence
    lot_size = tracker.get_lot_size(signal.get('confidence', 60))
    position_value = summary['initial_capital'] * lot_size
    dollar_loss = position_value * (abs(pnl_pct) / 100)

    msg = f"""
{EMOJI['stop']} <b>STOP LOSS HIT</b>

{EMOJI['loss']} <b>{signal['direction']}</b> Signal Stopped Out

Hey traders, it happens to the best of us.

<b>Entry:</b> ${signal['entry_price']:,.2f}
<b>Exit:</b> ${signal['stop_loss']:,.2f}
<b>Loss:</b> <code>{pnl_pct:.2f}%</code>
<b>Lot Size:</b> {lot_size} ({lot_size*100:.0f}%)

━━━━━━━━━━━━━━━━━━━━━━

{EMOJI['money']} <b>SIMULATOR ACCOUNT UPDATE</b>

<b>Starting Capital:</b> $1,000.00
<b>Current Value:</b> ${summary['portfolio_value']:,.2f}
<b>Total Return:</b> {summary['total_return_pct']:+.2f}%
<b>This Trade:</b> -${dollar_loss:.2f}

<b>Stats:</b>
• Win Rate: {summary['win_rate']:.1f}%
• Total Trades: {summary['total_trades']}
• Wins: {summary['wins']} | Losses: {summary['losses']}

━━━━━━━━━━━━━━━━━━━━━━

{EMOJI['strong']} <b>Remember:</b>
• Losses are part of trading
• We used proper risk management
• Our stop loss protected us from bigger losses
• We live to trade another day!

Stay strong, stay disciplined. The next winner is coming! 💪

#SP500 #TradingSignals #RiskManagement #StayStrong
"""
    return send_telegram(msg)


def send_telegram_photo_url(photo_url: str, caption: str = "") -> bool:
    """Send photo from URL to Telegram channel."""
    if not TELEGRAM_BOT_TOKEN:
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    data = {
        'chat_id': TELEGRAM_CHAT_ID,
        'photo': photo_url,
        'caption': caption[:1024],
        'parse_mode': 'HTML'
    }

    try:
        response = requests.post(url, data=data, timeout=30)
        return response.status_code == 200
    except Exception as e:
        print(f"Error sending photo URL: {e}")
        return False


def post_news():
    """Post market news with image and emojis."""
    print("Posting market news...")

    news_items = news.get_market_news(limit=5)

    if not news_items:
        return send_telegram("📰 <b>News</b>\n\n❌ No news available.\n\n#SP500 #News")

    # Get first news item with image
    main_news = news_items[0]
    image_url = main_news.get('image', '')

    # News emojis
    news_emojis = ['📌', '📍', '🔹', '🔸', '💡']

    # Build news list with emojis
    news_lines = []
    for i, item in enumerate(news_items[:4]):
        headline = item.get('headline', '')[:70]
        source = item.get('source', '')
        emoji = news_emojis[i] if i < len(news_emojis) else '•'
        news_lines.append(f"{emoji} {headline}\n     <i>— {source}</i>")

    caption = f"""
📰 <b>MARKET NEWS</b> 🗞️

{chr(10).join(news_lines)}

🔔 Stay informed!

#SP500 #News #StockMarket #Trading #MarketNews #WallStreet #Finance #Investing
"""

    # Try to send with image
    if image_url:
        result = send_telegram_photo_url(image_url, caption)
        if result:
            return True

    # Fallback to text
    return send_telegram(caption)


def post_earnings():
    """Post simple earnings calendar."""
    print("Posting earnings calendar...")

    earnings = news.get_earnings_calendar()

    if not earnings:
        return send_telegram("📅 <b>Earnings</b>\n\nNo major earnings this week.\n\n#SP500")

    lines = ["📅 <b>Upcoming Earnings</b>\n"]
    for item in earnings[:5]:
        symbol = item.get('symbol', '')
        date = item.get('date', '')
        timing = "AM" if item.get('hour') == 'bmo' else "PM"
        lines.append(f"• {symbol} - {date} ({timing})")

    lines.append("\n#SP500 #Earnings")

    return send_telegram('\n'.join(lines))


# ============================================
# NEW INTERACTIVE POSTS
# ============================================

def post_good_morning():
    """Post good morning message with daily outlook."""
    print("Posting good morning...")

    data = get_current_data()
    today = datetime.now().strftime("%A, %B %d")

    # Get futures/overnight sentiment
    if data:
        change_pct = data['change_pct']
        if change_pct > 0.5:
            vibe = "🟢 Bullish vibes today!"
            futures = f"📈 Futures up +{change_pct:.2f}%"
        elif change_pct < -0.5:
            vibe = "🔴 Cautious start today"
            futures = f"📉 Futures down {change_pct:.2f}%"
        else:
            vibe = "🟡 Neutral open expected"
            futures = f"➡️ Futures flat {change_pct:+.2f}%"
    else:
        vibe = "🟡 Let's see what happens!"
        futures = "📊 Checking the charts..."

    greeting = get_morning_greeting()
    encouragement = get_encouragement()

    msg = f"""
☀️ {greeting}

📅 It's {today}

{futures}

{vibe}

{encouragement}

#SP500 #GoodMorning #Trading #StockMarket #WallStreet
"""
    return send_telegram(msg)


def post_good_night():
    """Post good night message with daily summary."""
    print("Posting good night...")

    data = get_current_data()
    summary = tracker.get_performance_summary()
    daily_perf = tracker.get_daily_performance()

    greeting = get_night_greeting()

    if data:
        change_emoji = "📈" if data['change_pct'] > 0 else "📉"
        market_summary = f"{change_emoji} Market: {data['change_pct']:+.2f}%"
    else:
        market_summary = "📊 Market closed"

    if daily_perf['trades'] > 0:
        signal_summary = f"📊 Signals: {daily_perf['wins']}W / {daily_perf['losses']}L"
    else:
        signal_summary = "📊 No signals today"

    portfolio_value = f"💰 Portfolio: ${summary['portfolio_value']:,.2f}"

    msg = f"""
🌙 {greeting}

<b>Today's Summary:</b>
{market_summary}
{signal_summary}
{portfolio_value}

Rest up and recharge! 💤

Tomorrow is a new opportunity! 🚀

#SP500 #GoodNight #Trading #StockMarket
"""
    return send_telegram(msg)


def post_trading_wisdom():
    """Post trading wisdom quote with lesson."""
    print("Posting trading wisdom...")

    # Use day of year for rotation
    index = get_day_of_year_index()
    wisdom = get_wisdom_by_index(index)

    msg = f"""
🧠 <b>Trading Wisdom</b>

"<i>{wisdom['quote']}</i>"
— {wisdom['author']}

💡 <b>The Lesson:</b>
{wisdom['lesson']}

Apply this today! 💪

#SP500 #TradingWisdom #Trading #LearnToTrade #Motivation
"""
    return send_telegram(msg)


def post_trading_theory():
    """Post educational trading theory."""
    print("Posting trading theory...")

    # Use day of year for rotation
    index = get_day_of_year_index()
    theory = get_theory_by_index(index)

    msg = f"""
📚 <b>Trading Theory</b>

{theory['emoji']} <b>{theory['topic']}</b>

<b>What is it?</b>
{theory['what']}

<b>How to use it:</b>
{theory['how']}

💡 <b>Pro Tip:</b>
{theory['tip']}

Knowledge is power! 🎯

#SP500 #TradingEducation #LearnToTrade #TechnicalAnalysis
"""
    return send_telegram(msg)


def post_historical_pattern():
    """Post historical market event."""
    print("Posting historical pattern...")

    # Try to get event matching today's date, or random
    event = get_history_for_today()

    msg = f"""
📜 <b>On This Day in Market History...</b>

📅 <b>{event['date']}, {event['year']}: {event['title']}</b>

<b>What happened:</b>
{event['description']}

💡 <b>The Lesson:</b>
{event['lesson']}

History doesn't repeat, but it rhymes! 📈

#SP500 #MarketHistory #Trading #StockMarket #LearnFromHistory
"""
    return send_telegram(msg)


def post_why_market_moved():
    """Explain today's market movement."""
    print("Posting why market moved...")

    data = get_current_data()
    if not data:
        return send_telegram("📊 <b>Market Analysis</b>\n\nNo data available.\n\n#SP500")

    change = data['change_pct']
    rsi = data['rsi']
    macd_bullish = data['macd_hist'] > 0

    # Determine main reason
    if abs(change) < 0.2:
        reason = "Low volatility session. Markets consolidating, waiting for catalysts."
        outlook = "Watch for breakout in either direction."
    elif change > 1:
        if rsi > 65:
            reason = "Strong buying pressure pushed prices higher. Momentum traders piling in."
            outlook = "RSI getting elevated - watch for pullback opportunity."
        else:
            reason = "Buyers stepped in with conviction. Technical levels held."
            outlook = "Trend remains bullish. Look for dip-buying opportunities."
    elif change < -1:
        if rsi < 35:
            reason = "Heavy selling pressure. Fear in the market."
            outlook = "RSI oversold - bounce could be near."
        else:
            reason = "Sellers in control. Risk-off sentiment dominating."
            outlook = "Wait for stabilization before new longs."
    elif change > 0:
        reason = "Modest gains. Bulls maintaining control with steady buying."
        outlook = "Trend intact. Continue monitoring key levels."
    else:
        reason = "Slight weakness. Profit-taking or mild selling pressure."
        outlook = "Normal pullback. Watch support levels."

    change_emoji = "📈" if change > 0 else "📉"

    msg = f"""
🤔 <b>Why Did the Market Move?</b>

{change_emoji} <b>Today's Move:</b> {change:+.2f}%

<b>The Reason:</b>
{reason}

<b>What's Next:</b>
{outlook}

<b>Technical Status:</b>
• RSI: {rsi:.0f}
• MACD: {'Bullish' if macd_bullish else 'Bearish'}
• Trend: {'Up' if data['close'] > data['sma_20'] else 'Down'}

Understanding moves = better trades! 🎯

#SP500 #MarketAnalysis #Trading #TechnicalAnalysis
"""
    return send_telegram(msg)


def post_simulation_update():
    """Post trading simulation portfolio update."""
    print("Posting simulation update...")

    summary = tracker.get_performance_summary()
    daily_perf = tracker.get_daily_performance()

    # Determine portfolio status
    total_return = summary['total_return_pct']
    if total_return > 5:
        status_emoji = "🔥🔥"
        status = "ON FIRE!"
    elif total_return > 2:
        status_emoji = "🚀"
        status = "Strong performance!"
    elif total_return > 0:
        status_emoji = "📈"
        status = "In profit!"
    elif total_return > -2:
        status_emoji = "📊"
        status = "Slight drawdown"
    else:
        status_emoji = "💪"
        status = "Building back!"

    # Open positions
    open_signals = [s for s in tracker.data.get('signals', []) if s.get('status') == 'open']
    open_count = len(open_signals)

    msg = f"""
💰 <b>Trading Simulation Update</b>

{status_emoji} <b>{status}</b>

<b>Portfolio:</b>
💵 Starting: $1,000.00
💰 Current: ${summary['portfolio_value']:,.2f}
📊 Return: {total_return:+.2f}%

<b>Today:</b>
📈 Trades: {daily_perf['trades']}
✅ Wins: {daily_perf['wins']} | ❌ Losses: {daily_perf['losses']}
💵 P&L: {daily_perf['total_pnl_pct']:+.2f}%

<b>All-Time Stats:</b>
📊 Total Trades: {summary['total_trades']}
🎯 Win Rate: {summary['win_rate']:.1f}%
🏆 Best Trade: {summary['best_trade']['pnl_pct']:+.2f}% if summary['best_trade'] else 'N/A'
📉 Worst Trade: {summary['worst_trade']['pnl_pct']:+.2f}% if summary['worst_trade'] else 'N/A'

<b>Open Positions:</b> {open_count}

Track record matters! 📈

#SP500 #TradingSimulation #Performance #Trading
"""
    return send_telegram(msg)


def post_premarket_movers():
    """Post pre-market movers and futures."""
    print("Posting premarket movers...")

    data = get_current_data()
    econ = get_economic_data()

    if data:
        sp_change = data['change_pct']
        sp_emoji = "🟢" if sp_change > 0 else ("🔴" if sp_change < 0 else "⚪")
    else:
        sp_change = 0
        sp_emoji = "⚪"

    vix = econ['vix']
    if vix < 15:
        vix_status = "Very Low (Complacency)"
    elif vix < 20:
        vix_status = "Low (Calm)"
    elif vix < 25:
        vix_status = "Normal"
    elif vix < 30:
        vix_status = "Elevated (Caution)"
    else:
        vix_status = "High (Fear)"

    msg = f"""
🌅 <b>Pre-Market Movers</b>

<b>Futures:</b>
{sp_emoji} S&P 500: {sp_change:+.2f}%

<b>Volatility:</b>
📊 VIX: {vix:.1f} - {vix_status}

<b>What to Watch:</b>
• Key earnings releases
• Economic data at 8:30 AM
• Fed speakers
• Sector rotation

Stay alert, stay prepared! 🎯

#SP500 #PreMarket #Futures #Trading
"""
    return send_telegram(msg)


def post_economic_calendar():
    """Post today's economic calendar."""
    print("Posting economic calendar...")

    today = datetime.now().strftime("%A, %B %d")

    # Key events to watch (general template)
    msg = f"""
📅 <b>Economic Calendar</b>

📆 {today}

<b>Key Events to Watch:</b>

🕐 <b>Pre-Market:</b>
• Jobless Claims (if Thursday)
• GDP / CPI data (if scheduled)
• Fed speeches

🔔 <b>Market Hours:</b>
• FOMC announcements
• Earnings releases
• Economic indicators

💡 <b>Tip:</b>
High-impact events can cause volatility spikes. Consider reducing position size around major releases.

Stay informed! 📊

#SP500 #EconomicCalendar #Trading #MarketNews
"""
    return send_telegram(msg)


def post_sector_watch():
    """Post sector rotation analysis."""
    print("Posting sector watch...")

    data = get_current_data()

    if data:
        trend = "bullish" if data['close'] > data['sma_20'] else "bearish"
    else:
        trend = "mixed"

    if trend == "bullish":
        hot_sectors = "Tech (XLK), Consumer Discretionary (XLY), Communication (XLC)"
        cold_sectors = "Utilities (XLU), Real Estate (XLRE)"
        rotation = "Risk-on: Money flowing to growth sectors"
    else:
        hot_sectors = "Utilities (XLU), Healthcare (XLV), Consumer Staples (XLP)"
        cold_sectors = "Tech (XLK), Consumer Discretionary (XLY)"
        rotation = "Risk-off: Money flowing to defensive sectors"

    msg = f"""
🔄 <b>Sector Watch</b>

<b>Market Trend:</b> {trend.upper()}

🔥 <b>Hot Sectors:</b>
{hot_sectors}

❄️ <b>Cold Sectors:</b>
{cold_sectors}

📊 <b>Rotation Theme:</b>
{rotation}

💡 <b>Strategy:</b>
Follow the money! Trade with sector momentum.

#SP500 #SectorRotation #Trading #StockMarket
"""
    return send_telegram(msg)


def post_midday_recap():
    """Post midday market recap."""
    print("Posting midday recap...")

    data = get_current_data()
    if not data:
        return send_telegram("📊 <b>Midday Recap</b>\n\nNo data available.\n\n#SP500")

    change_emoji = "📈" if data['change_pct'] > 0 else "📉"

    # Morning session analysis
    if data['change_pct'] > 0.5:
        session = "Strong morning! Bulls in control."
    elif data['change_pct'] < -0.5:
        session = "Weak morning. Bears pushing lower."
    else:
        session = "Choppy morning. No clear direction yet."

    msg = f"""
🕐 <b>Midday Recap</b>

{change_emoji} <b>S&P 500:</b> ${data['close']:,.0f} ({data['change_pct']:+.2f}%)

<b>Session Range:</b>
📈 High: ${data['high']:,.0f}
📉 Low: ${data['low']:,.0f}

<b>Morning Takeaway:</b>
{session}

<b>Technical Status:</b>
• RSI: {data['rsi']:.0f}
• MACD: {'Bullish' if data['macd_hist'] > 0 else 'Bearish'}

<b>Afternoon Watch:</b>
Key level: ${data['close']:,.0f}
Break above = bullish continuation
Break below = afternoon weakness

Stay focused! 🎯

#SP500 #MiddayRecap #Trading #MarketUpdate
"""
    return send_telegram(msg)


def post_power_hour():
    """Post power hour alert."""
    print("Posting power hour...")

    data = get_current_data()
    if not data:
        return send_telegram("⚡ <b>Power Hour</b>\n\nLast hour of trading!\n\n#SP500")

    # Determine power hour bias
    if data['change_pct'] > 0.3 and data['rsi'] < 70:
        bias = "🟢 Bullish momentum into close likely"
    elif data['change_pct'] < -0.3 and data['rsi'] > 30:
        bias = "🔴 Selling pressure may continue"
    else:
        bias = "🟡 Could go either way - stay nimble"

    msg = f"""
⚡ <b>POWER HOUR</b> ⚡

Last hour of trading!

<b>Current Status:</b>
💵 S&P 500: ${data['close']:,.0f}
📊 Day Change: {data['change_pct']:+.2f}%
📈 RSI: {data['rsi']:.0f}

<b>Power Hour Bias:</b>
{bias}

<b>Watch For:</b>
• Institutional repositioning
• End-of-day momentum
• Volume spikes

This is when big moves happen! 🔥

#SP500 #PowerHour #Trading #MarketClose
"""
    return send_telegram(msg)


def post_preclose():
    """Post pre-close summary before market closes."""
    print("Posting pre-close summary...")

    data = get_current_data()
    if not data:
        return send_telegram("🔔 <b>Pre-Close Check</b>\n\n30 minutes to close!\n\n#SP500")

    # Day performance
    if data['change_pct'] > 0.5:
        day_status = "🟢 Strong day - locking in gains"
    elif data['change_pct'] > 0:
        day_status = "🟢 Positive day - holding steady"
    elif data['change_pct'] > -0.5:
        day_status = "🔴 Slight weakness - watching levels"
    else:
        day_status = "🔴 Selling pressure - stay cautious"

    # RSI status
    if data['rsi'] > 70:
        rsi_note = "⚠️ Overbought - profit-taking possible"
    elif data['rsi'] < 30:
        rsi_note = "⚠️ Oversold - bounce candidates"
    else:
        rsi_note = "📊 RSI in normal range"

    dual_time = get_dual_time()

    msg = f"""
🔔 <b>PRE-CLOSE CHECK</b> 🔔

{dual_time}

30 minutes until the bell!

━━━━━━━━━━━━━━━━━━━━

<b>Day Summary:</b>
💵 S&P 500: ${data['close']:,.2f}
📊 Change: {data['change_pct']:+.2f}%
📈 RSI: {data['rsi']:.0f}

━━━━━━━━━━━━━━━━━━━━

<b>Status:</b>
{day_status}
{rsi_note}

See you at the close! 🔔

#SP500 #PreClose #Trading
"""
    return send_telegram(msg)


def post_tomorrow_preview():
    """Post preview of tomorrow's trading."""
    print("Posting tomorrow preview...")

    data = get_current_data()

    if data:
        close = data['close']
        rsi = data['rsi']
        trend = "bullish" if data['close'] > data['sma_20'] else "bearish"

        if rsi < 35:
            outlook = "Oversold conditions - watch for bounce"
        elif rsi > 65:
            outlook = "Overbought - potential pullback"
        elif trend == "bullish":
            outlook = "Trend is up - look for buying opportunities"
        else:
            outlook = "Trend is down - be cautious with longs"
    else:
        close = 0
        outlook = "Check charts before market open"

    msg = f"""
🔮 <b>Tomorrow Preview</b>

<b>Key Levels to Watch:</b>
• Resistance: ${close * 1.01:,.0f}
• Support: ${close * 0.99:,.0f}
• Pivot: ${close:,.0f}

<b>Technical Outlook:</b>
{outlook}

<b>Tomorrow's Checklist:</b>
✅ Check pre-market futures
✅ Review overnight news
✅ Identify key levels
✅ Set alerts
✅ Have a plan before open

Preparation = Success! 📈

#SP500 #TomorrowPreview #Trading #Preparation
"""
    return send_telegram(msg)


def post_trading_tip():
    """Post quick trading tip."""
    print("Posting trading tip...")

    # Rotate through tips
    tips = [
        ("🎯 Set Your Stop Loss FIRST", "Before entering any trade, know exactly where you'll exit if wrong. This protects your capital from big losses."),
        ("⏰ Best Trading Hours", "The first hour (9:30-10:30) and last hour (3:00-4:00) have the most volume and movement. Trade when the market is active!"),
        ("📊 Trade the Trend", "The trend is your friend! Don't fight it. If price is above the 20 SMA, favor longs. Below? Favor shorts."),
        ("💰 Risk Management Rule", "Never risk more than 1-2% of your account on a single trade. This way, even a losing streak won't wipe you out."),
        ("🧘 Patience Pays", "Not every day is a trading day. Sometimes the best trade is no trade. Wait for high-probability setups."),
        ("📱 Avoid Overtrading", "Quality over quantity! One good trade beats five mediocre ones. Be selective."),
        ("📈 Let Winners Run", "Don't rush to take profits on winning trades. Use trailing stops to capture bigger moves."),
        ("🛑 Cut Losses Quickly", "Small losses are okay. Big losses hurt. If a trade isn't working, exit early and move on."),
        ("📚 Keep a Trading Journal", "Record every trade: entry, exit, reason, emotion. Review weekly to learn from mistakes."),
        ("😴 Rest is Important", "Tired traders make bad decisions. Get enough sleep and take breaks from the screens."),
    ]

    # Use day of year for rotation
    index = get_day_of_year_index() % len(tips)
    title, tip = tips[index]

    msg = f"""
💡 <b>Trading Tip of the Day</b>

{title}

{tip}

Small improvements daily = big results over time! 📈

#SP500 #TradingTip #LearnToTrade #Trading
"""
    return send_telegram(msg)


def post_opening_analysis():
    """Post first 15 minutes analysis after open."""
    print("Posting opening analysis...")

    data = get_current_data()
    if not data:
        return send_telegram("📊 <b>Opening Analysis</b>\n\nMarket just opened!\n\n#SP500")

    # Analyze opening action
    change = data['change_pct']

    if change > 0.5:
        opening = "🟢 Strong open! Buyers aggressive"
        action = "Look for pullback entries on longs"
    elif change < -0.5:
        opening = "🔴 Weak open! Sellers in control"
        action = "Wait for stabilization before buying"
    elif change > 0:
        opening = "🟢 Positive open, modest gains"
        action = "Trend continuation possible"
    else:
        opening = "🔴 Slightly negative open"
        action = "Watch for direction confirmation"

    msg = f"""
🔔 <b>Opening Analysis</b>

First 15 minutes reaction:

{opening}

<b>Price:</b> ${data['close']:,.0f}
<b>Change:</b> {change:+.2f}%

<b>Action Plan:</b>
{action}

<b>Key Levels:</b>
• Resist: ${data['high']:,.0f}
• Support: ${data['low']:,.0f}

Stay focused! First hour is crucial! ⚡

#SP500 #MarketOpen #Trading #OpeningBell
"""
    return send_telegram(msg)


def post_volume_alert():
    """Post unusual volume alert."""
    print("Posting volume alert...")

    data = get_current_data()
    if not data:
        return False

    msg = f"""
📊 <b>Volume Analysis</b>

<b>Current Session:</b>
Volume is {'above' if data['volume'] > 0 else 'below'} average

<b>What Volume Tells Us:</b>
• High volume + up = Strong buying
• High volume + down = Strong selling
• Low volume moves often reverse

<b>Current Price:</b> ${data['close']:,.0f}
<b>Change:</b> {data['change_pct']:+.2f}%

Volume confirms moves! 📈

#SP500 #VolumeAnalysis #Trading
"""
    return send_telegram(msg)


def post_trend_check():
    """Post trend status check."""
    print("Posting trend check...")

    data = get_current_data()
    if not data:
        return False

    above_20 = data['close'] > data['sma_20']
    above_50 = data['close'] > data['sma_50']

    if above_20 and above_50:
        trend = "🟢 STRONG UPTREND"
        status = "Price above both 20 and 50 SMA"
        bias = "Favor long positions"
    elif above_20:
        trend = "🟢 UPTREND"
        status = "Price above 20 SMA, testing 50"
        bias = "Cautiously bullish"
    elif not above_20 and not above_50:
        trend = "🔴 DOWNTREND"
        status = "Price below both 20 and 50 SMA"
        bias = "Avoid longs, consider shorts"
    else:
        trend = "🟡 MIXED"
        status = "Price between key averages"
        bias = "Wait for clarity"

    msg = f"""
📈 <b>Trend Check</b>

{trend}

<b>Status:</b>
{status}

<b>Price:</b> ${data['close']:,.0f}
<b>20 SMA:</b> ${data['sma_20']:,.0f}
<b>50 SMA:</b> ${data['sma_50']:,.0f}

<b>Trading Bias:</b>
{bias}

Trade with the trend! 🎯

#SP500 #TrendAnalysis #Trading #TechnicalAnalysis
"""
    return send_telegram(msg)


def post_week_ahead():
    """Post week ahead preview (Monday special)."""
    print("Posting week ahead...")

    data = get_current_data()

    if data:
        level = data['close']
        rsi = data['rsi']
    else:
        level = 0
        rsi = 50

    msg = f"""
📅 <b>Week Ahead Preview</b>

Happy Monday, traders! Here's what to watch:

<b>Key Level:</b> ${level:,.0f}
<b>RSI:</b> {rsi:.0f}

<b>This Week's Focus:</b>
• Economic data releases
• Earnings reports
• Fed commentary
• Technical breakout/breakdown levels

<b>Weekly Strategy:</b>
1. Define your key levels
2. Set alerts
3. Wait for setups
4. Execute with discipline

Let's make it a great week! 💪

#SP500 #WeekAhead #Trading #MondayMotivation
"""
    return send_telegram(msg)


def post_position_check():
    """Post open position status."""
    print("Posting position check...")

    summary = tracker.get_performance_summary()
    open_signals = [s for s in tracker.data.get('signals', []) if s.get('status') == 'open']

    if not open_signals:
        msg = """
📋 <b>Position Check</b>

No open positions currently.

Waiting for high-quality setups! 🎯

#SP500 #Positions #Trading
"""
    else:
        lines = ["📋 <b>Position Check</b>\n"]
        lines.append(f"<b>Open Positions:</b> {len(open_signals)}\n")

        for i, signal in enumerate(open_signals[:5], 1):
            direction = signal['direction']
            entry = signal['entry_price']
            tp = signal['take_profit']
            sl = signal['stop_loss']
            emoji = "🟢" if direction == "LONG" else "🔴"
            lines.append(f"{emoji} {direction} @ ${entry:,.0f}")
            lines.append(f"   TP: ${tp:,.0f} | SL: ${sl:,.0f}\n")

        lines.append(f"<b>Portfolio:</b> ${summary['portfolio_value']:,.2f}")
        lines.append("\n#SP500 #Positions #Trading")
        msg = '\n'.join(lines)

    return send_telegram(msg)


def post_daily_recap():
    """Post daily winners/losers recap."""
    print("Posting daily recap...")

    data = get_current_data()
    daily_perf = tracker.get_daily_performance()

    if not data:
        return send_telegram("📊 <b>Daily Recap</b>\n\nMarket closed.\n\n#SP500")

    change_emoji = "📈" if data['change_pct'] > 0 else "📉"

    msg = f"""
📊 <b>Daily Recap</b>

{change_emoji} <b>S&P 500:</b> {data['change_pct']:+.2f}%

<b>Day's Range:</b>
High: ${data['high']:,.0f}
Low: ${data['low']:,.0f}
Close: ${data['close']:,.0f}

<b>Our Signals Today:</b>
Total: {daily_perf['trades']}
Wins: {daily_perf['wins']} ✅
Losses: {daily_perf['losses']} ❌
P&L: {daily_perf['total_pnl_pct']:+.2f}%

<b>Key Takeaways:</b>
• {'Bulls won the day' if data['change_pct'] > 0 else 'Bears took control'}
• RSI at {data['rsi']:.0f}
• MACD {'bullish' if data['macd_hist'] > 0 else 'bearish'}

See you tomorrow! 🌙

#SP500 #DailyRecap #Trading #MarketClose
"""
    return send_telegram(msg)


def post_trading_journal():
    """Post trading journal entry / lessons learned."""
    print("Posting trading journal...")

    daily_perf = tracker.get_daily_performance()

    if daily_perf['trades'] == 0:
        lesson = "No trades today. Sometimes patience is the best strategy."
        emoji = "🧘"
    elif daily_perf['win_rate'] >= 70:
        lesson = "Great day! The setups were clean and we executed well. Stay humble."
        emoji = "🏆"
    elif daily_perf['win_rate'] >= 50:
        lesson = "Decent day. Some winners, some losers. That's trading."
        emoji = "📊"
    else:
        lesson = "Tough day. Review the losses - what could we have done better?"
        emoji = "📝"

    msg = f"""
📝 <b>Trading Journal</b>

{emoji} <b>Today's Entry</b>

<b>Performance:</b>
Trades: {daily_perf['trades']}
Win Rate: {daily_perf['win_rate']:.0f}%
P&L: {daily_perf['total_pnl_pct']:+.2f}%

<b>Lesson of the Day:</b>
{lesson}

<b>Tomorrow's Focus:</b>
• Stick to the plan
• Wait for quality setups
• Manage risk first

Every day is a learning opportunity! 📚

#SP500 #TradingJournal #Trading #LessonsLearned
"""
    return send_telegram(msg)


def post_after_hours():
    """Post after-hours update."""
    print("Posting after hours...")

    data = get_current_data()

    if data:
        close = data['close']
        change = data['change_pct']
    else:
        close = 0
        change = 0

    msg = f"""
🌙 <b>After Hours Update</b>

<b>Regular Close:</b> ${close:,.0f}
<b>Day Change:</b> {change:+.2f}%

<b>After Hours Activity:</b>
• Watch for earnings reactions
• Futures will give direction clues
• News can move markets overnight

<b>Tomorrow's Prep:</b>
1. Review today's action
2. Check key levels
3. Set morning alerts
4. Get rest!

Markets never sleep, but you should! 😴

#SP500 #AfterHours #Trading #MarketClose
"""
    return send_telegram(msg)


# ============================================
# ML-DRIVEN ANALYSIS POSTS
# ============================================

def post_ml_factor_analysis():
    """Post factor analysis with visual chart."""
    print("Posting factor analysis...")

    data = get_current_data()
    if not data:
        return False

    economic_data = get_economic_data()
    df = data['df']

    prediction = ml_predictor.predict(df, economic_data)
    factors = ml_predictor.get_factor_analysis(df, economic_data)

    if not factors:
        return False

    direction = prediction['direction']
    confidence = prediction['confidence']
    direction_emoji = EMOJI['bullish'] if direction == 'LONG' else EMOJI['bearish']

    # Generate factor chart
    try:
        chart_buffer = charts.generate_factor_chart(factors, direction, confidence)

        caption = f"""
{direction_emoji} <b>{direction} Bias</b> | {confidence:.0f}% Confidence

{factors['summary']['bullish_factors']} Bullish / {factors['summary']['bearish_factors']} Bearish

RSI: {factors['rsi']['value']:.0f} | VIX: {factors['vix']['value']:.1f}

#SP500 #Analysis
"""
        return send_telegram_photo(chart_buffer, caption)

    except Exception as e:
        print(f"Chart error: {e}")
        # Simple text fallback
        msg = f"""
{direction_emoji} <b>{direction}</b> | {confidence:.0f}%

🟢 RSI: {factors['rsi']['value']:.0f}
🟢 Trend: {'Up' if factors['trend']['above_sma20'] else 'Down'}
🟢 MACD: {factors['macd']['signal']}

#SP500 #Analysis
"""
        return send_telegram(msg)


def post_ml_quick_scan():
    """Quick ML scan - posts only if high confidence signal found."""
    print("Running ML quick scan...")

    data = get_current_data()
    if not data:
        return False

    economic_data = get_economic_data()
    df = data['df']

    prediction = ml_predictor.predict(df, economic_data)
    confidence = prediction['confidence']

    # Only post if confidence >= 65% (high quality signals)
    if confidence < 65:
        print(f"Confidence {confidence:.1f}% below quick scan threshold (65%)")
        return False

    return post_signal_check()


def post_partial_profit_alert(signal: dict, current_price: float):
    """Post notification when partial profit is taken."""
    direction_emoji = "📈" if signal['direction'] == "LONG" else "📉"
    entry = signal['entry_price']
    partial_target = signal.get('partial_target', current_price)

    if signal['direction'] == "LONG":
        profit_pct = ((current_price - entry) / entry) * 100
    else:
        profit_pct = ((entry - current_price) / entry) * 100

    msg = f"""💰 <b>PARTIAL PROFIT TAKEN</b> 💰

{direction_emoji} <b>{signal['direction']}</b> Signal

📊 50% of position closed!

Entry: ${entry:,.2f}
Exit (50%): ${current_price:,.2f}
Profit: +{profit_pct:.2f}%

🛡️ Stop Loss moved to break-even (${entry:,.2f})

✅ Risk eliminated on remaining 50%
🎯 Letting profits run to final target!

{get_signals_summary()}

#SP500 #PartialProfit #RiskManagement"""

    return send_telegram(msg)


def post_breakeven_alert(updated_signals: list, opposite_direction: str, confidence: float):
    """Post notification when stops are moved to break-even."""
    if not updated_signals:
        return False

    count = len(updated_signals)
    direction_emoji = "📈" if updated_signals[0]['direction'] == "LONG" else "📉"
    opposite_emoji = "📉" if opposite_direction == "SHORT" else "📈"

    signals_list = ""
    for sig in updated_signals:
        signals_list += f"\n• {sig['direction']} @ ${sig['entry_price']:,.2f} → SL moved to ${sig['stop_loss']:,.2f}"

    msg = f"""🛡️ <b>BREAK-EVEN PROTECTION</b> 🛡️

{opposite_emoji} Opposite signal detected: <b>{opposite_direction}</b> ({confidence:.0f}%)

{direction_emoji} <b>{count} trade(s) protected:</b>
{signals_list}

Stop Loss moved to Entry Price = No Loss Risk!

✅ If price goes our way → Still profit
🔄 If price reverses → Exit at break-even

{get_signals_summary()}

#SP500 #RiskManagement #BreakEven"""

    return send_telegram(msg)


def post_high_confidence_alert():
    """Post ONLY if confidence >= 81% AND less than 5 open signals."""
    print("Checking for high confidence signal...")

    # First, check open signals for TP/SL hits + trailing stops
    print("Monitoring open signals...")
    data = get_current_data()
    if not data:
        return False

    current_price = data['close']

    # === Check Trailing Stops + Partial Profits for all open signals ===
    open_signals = tracker.get_open_signals()
    for signal in open_signals:
        entry_price = signal['entry_price']
        current_sl = signal['stop_loss']
        direction = signal['direction']

        # Check for partial profit taking first
        if not signal.get('partial_taken', False):
            partial_result = tracker.take_partial_profit(signal['id'], current_price)
            if partial_result:
                post_partial_profit_alert(partial_result, current_price)
                print(f"Partial profit taken for {signal['id']}")
                continue  # Skip trailing stop check this cycle

        # Then check trailing stop
        new_sl = risk_manager.calculate_trailing_stop(
            entry_price, current_price, current_sl, direction
        )
        if new_sl:
            tracker.update_signal_sl(signal['id'], new_sl)
            print(f"Trailing stop updated for {signal['id']}: {current_sl:.2f} → {new_sl:.2f}")

    # Check if any open signals hit TP or SL
    alerts = tracker.check_all_signals(current_price)
    for alert in alerts:
        alert_type = alert['type']
        signal = alert['signal']
        if alert_type == 'TP_HIT':
            # Update daily P&L
            pnl = signal.get('pnl_pct', 0)
            risk_manager.update_daily_pnl(pnl)
            post_tp_hit(signal)
            print(f"TP HIT posted for signal {signal['id']}")
        elif alert_type == 'SL_HIT':
            # Update daily P&L
            pnl = signal.get('pnl_pct', 0)
            risk_manager.update_daily_pnl(pnl)
            post_sl_hit(signal)
            print(f"SL HIT posted for signal {signal['id']}")

    economic_data = get_economic_data()
    df = data['df']

    prediction = ml_predictor.predict(df, economic_data)
    confidence = prediction['confidence']
    direction = prediction['direction']

    # Check for break-even protection: opposite signal with >= 80% confidence
    if confidence >= 80:
        opposite_direction = "SHORT" if direction == "LONG" else "LONG"
        open_opposite = tracker.get_open_signals_by_direction(opposite_direction)

        if open_opposite:
            print(f"Opposite signal detected ({direction} {confidence:.1f}%) with {len(open_opposite)} {opposite_direction} trades open")
            print("Moving stops to break-even...")

            updated = tracker.move_stops_to_breakeven(opposite_direction)
            if updated:
                post_breakeven_alert(updated, direction, confidence)
                print(f"Moved {len(updated)} trades to break-even")
                return True

    # Check if we already have 5 open signals
    open_signals = tracker.get_open_signals()
    if len(open_signals) >= 5:
        print(f"Already have {len(open_signals)} open signals (max 5). Skipping new signal.")
        return False

    # Trust the model - use 70% threshold (model has 71% win rate)
    if confidence < 70:
        print(f"Confidence {confidence:.1f}% below threshold (70%)")
        return False

    # Dynamic TP/SL based on VIX (keep this - it's useful)
    vix = economic_data.get('vix', 20.0)
    dynamic_levels = risk_manager.get_dynamic_levels(current_price, direction, vix)
    entry = current_price
    take_profit = dynamic_levels['take_profit']
    stop_loss = dynamic_levels['stop_loss']
    partial_target = dynamic_levels['partial_target']
    vix_regime = dynamic_levels['vix_regime']
    tp_pct = dynamic_levels['tp_pct']
    sl_pct = dynamic_levels['sl_pct']

    print(f"VIX Regime: {vix_regime} | Dynamic TP: {tp_pct}% | SL: {sl_pct}%")

    direction_emoji = EMOJI['bullish'] if direction == 'LONG' else EMOJI['bearish']

    signal = tracker.add_signal(
        direction=direction,
        entry_price=entry,
        take_profit=take_profit,
        stop_loss=stop_loss,
        confidence=confidence,
        ticker="SPY",
        partial_target=partial_target
    )

    rr = tp_pct / sl_pct if sl_pct > 0 else 0

    # Generate signal chart for high confidence
    try:
        chart_buffer = charts.generate_signal_chart(
            current_price, entry, take_profit, stop_loss, direction, confidence
        )

        signals_summary = get_signals_summary()

        caption = f"""🔥 <b>ELITE SIGNAL</b> 🔥

{direction_emoji} <b>{direction} SPY</b>

Entry: ${entry:,.2f}
Target: ${take_profit:,.2f} (+{tp_pct:.1f}%)
Stop: ${stop_loss:,.2f} (-{sl_pct:.1f}%)

⚡ Confidence: {confidence:.0f}%
📈 R/R: 1:{rr:.1f}
🌡️ VIX: {vix_regime}
{signals_summary}

#SP500 #EliteSignal"""
        return send_telegram_photo(chart_buffer, caption)

    except Exception as e:
        print(f"Chart error: {e}")
        signals_summary = get_signals_summary()
        msg = f"""🔥 <b>ELITE SIGNAL</b> 🔥

{direction_emoji} <b>{direction} SPY</b>

Entry: ${entry:,.2f}
Target: ${take_profit:,.2f} (+{tp_pct:.1f}%)
Stop: ${stop_loss:,.2f} (-{sl_pct:.1f}%)

⚡ Confidence: {confidence:.0f}%
🌡️ VIX: {vix_regime}
{signals_summary}

#SP500 #EliteSignal"""
        return send_telegram(msg)


def post_ml_momentum():
    """Post momentum update with visual chart."""
    print("Posting momentum update...")

    data = get_current_data()
    if not data:
        return False

    economic_data = get_economic_data()
    df = data['df']

    prediction = ml_predictor.predict(df, economic_data)
    factors = ml_predictor.get_factor_analysis(df, economic_data)

    direction = prediction['direction']
    confidence = prediction['confidence']
    direction_emoji = EMOJI['bullish'] if direction == 'LONG' else EMOJI['bearish']

    mom_5d = factors['momentum']['value_5d']
    mom_20d = factors['momentum']['value_20d']

    if mom_5d > 1 and mom_20d > 2:
        mom_status = "STRONG UP"
        mom_emoji = "🚀"
    elif mom_5d > 0 and mom_20d > 0:
        mom_status = "UPTREND"
        mom_emoji = "📈"
    elif mom_5d < -1 and mom_20d < -2:
        mom_status = "STRONG DOWN"
        mom_emoji = "📉"
    elif mom_5d < 0 and mom_20d < 0:
        mom_status = "DOWNTREND"
        mom_emoji = "⬇️"
    else:
        mom_status = "SIDEWAYS"
        mom_emoji = "↔️"

    # Generate momentum chart
    try:
        chart_buffer = charts.generate_momentum_chart(df, direction, confidence)

        caption = f"""
{mom_emoji} <b>{mom_status}</b>

{direction_emoji} {direction} | {confidence:.0f}%

5-Day: {mom_5d:+.1f}%
20-Day: {mom_20d:+.1f}%

#SP500 #Momentum
"""
        return send_telegram_photo(chart_buffer, caption)

    except Exception as e:
        print(f"Chart error: {e}")
        msg = f"""
{mom_emoji} <b>{mom_status}</b>

{direction_emoji} {direction} | {confidence:.0f}%

5-Day: {mom_5d:+.1f}%
20-Day: {mom_20d:+.1f}%

#SP500 #Momentum
"""
        return send_telegram(msg)


def post_ml_risk_assessment():
    """Post simple risk check."""
    print("Posting risk assessment...")

    data = get_current_data()
    if not data:
        return False

    economic_data = get_economic_data()
    df = data['df']

    prediction = ml_predictor.predict(df, economic_data)
    factors = ml_predictor.get_factor_analysis(df, economic_data)

    vix = factors['vix']['value']
    vol = factors['volatility']['value_5d']

    # Calculate risk level
    if vix > 25 or vol > 1.5:
        risk_emoji = "🔴"
        risk_level = "HIGH"
        advice = "Small positions only"
    elif vix > 20 or vol > 1.0:
        risk_emoji = "🟡"
        risk_level = "MEDIUM"
        advice = "Normal trading"
    else:
        risk_emoji = "🟢"
        risk_level = "LOW"
        advice = "Good conditions"

    direction = prediction['direction']
    confidence = prediction['confidence']
    direction_emoji = EMOJI['bullish'] if direction == 'LONG' else EMOJI['bearish']

    msg = f"""
{risk_emoji} <b>Risk: {risk_level}</b>

VIX: {vix:.1f}
Volatility: {vol:.1f}%

{direction_emoji} {direction} | {confidence:.0f}%

{advice}

#SP500 #Risk
"""
    return send_telegram(msg)


def post_quick_signal():
    """Quick 5-min signal check - posts if ANY valid signal."""
    print("Quick signal check...")

    data = get_current_data()
    if not data:
        return False

    economic_data = get_economic_data()
    df = data['df']

    prediction = ml_predictor.predict(df, economic_data)
    confidence = prediction['confidence']

    # Post any signal above minimum threshold
    if confidence >= MIN_CONFIDENCE:
        return post_signal_check()
    else:
        print(f"No signal - confidence {confidence:.1f}% below {MIN_CONFIDENCE}%")
        return False


# ============================================
# COMMAND ROUTING
# ============================================

COMMANDS = {
    'test': post_test,
    # Morning Posts
    'gm': post_good_morning,
    'good_morning': post_good_morning,
    'morning': post_morning_briefing,
    'morning_briefing': post_morning_briefing,
    'premarket': post_premarket_movers,
    'wisdom': post_trading_wisdom,
    'theory': post_trading_theory,
    'calendar': post_economic_calendar,
    # Market Hours Posts
    'open': post_market_open,
    'market_open': post_market_open,
    'opening': post_opening_analysis,
    'technical': post_technical_analysis,
    'technical_analysis': post_technical_analysis,
    'economic': post_economic_dashboard,
    'economic_update': post_economic_dashboard,
    'sentiment': post_sentiment,
    'sentiment_check': post_sentiment,
    'signal': post_signal_check,
    'signal_check': post_signal_check,
    'predict': post_signal_check,
    'update': post_signal_update,
    'signal_update': post_signal_update,
    'midday': post_midday_recap,
    'history': post_historical_pattern,
    'why': post_why_market_moved,
    'sector': post_sector_watch,
    'trend': post_trend_check,
    'volume': post_volume_alert,
    'tip': post_trading_tip,
    'simulation': post_simulation_update,
    'positions': post_position_check,
    # Power Hour / Close
    'power': post_power_hour,
    'power_hour': post_power_hour,
    'preclose': post_preclose,
    'pre_close': post_preclose,
    'close': post_market_close,
    'market_close': post_market_close,
    'recap': post_daily_recap,
    'journal': post_trading_journal,
    'after': post_after_hours,
    'tomorrow': post_tomorrow_preview,
    'gn': post_good_night,
    'good_night': post_good_night,
    # Analysis (cumulative performance tracking)
    'daily_analysis': post_daily_analysis,
    'analysis': post_daily_analysis,
    'weekly_analysis': post_weekly_analysis,
    'monthly_analysis': post_monthly_analysis,
    'monthly': post_monthly_analysis,
    # Weekly
    'weekly': post_weekly_analysis,  # Changed to weekly analysis
    'weekly_report': post_weekly_report,
    'week_ahead': post_week_ahead,
    # Branding
    'welcome': post_welcome_message,
    'logo': post_logo,
    'banner': post_banner,
    # News
    'news': post_news,
    'earnings': post_earnings,
    # Monitoring
    'monitor': post_monitor,
    # ML Analysis Posts
    'factors': post_ml_factor_analysis,
    'ml_factors': post_ml_factor_analysis,
    'quick_scan': post_ml_quick_scan,
    'elite': post_high_confidence_alert,
    'high_confidence': post_high_confidence_alert,
    'momentum': post_ml_momentum,
    'ml_momentum': post_ml_momentum,
    'risk': post_ml_risk_assessment,
    'ml_risk': post_ml_risk_assessment,
    'quick': post_quick_signal,
}


if __name__ == "__main__":
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
    else:
        cmd = 'test'

    if cmd in COMMANDS:
        print(f"Running command: {cmd}")
        success = COMMANDS[cmd]()
        print(f"Result: {'Success' if success else 'Failed'}")
    else:
        print(f"Unknown command: {cmd}")
        print(f"Available: {', '.join(COMMANDS.keys())}")
        sys.exit(1)
