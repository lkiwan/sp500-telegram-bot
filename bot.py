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

# Import custom modules
from styles import EMOJI, get_hashtags
from chart_generator import ChartGenerator
from commentary_engine import TradingMentor, POST_TEMPLATES
from signal_tracker import SignalTracker
from branding import post_welcome_message, post_logo, post_banner, get_channel_description
from news_fetcher import NewsFetcher, format_news_post, format_earnings_post

# Configuration from GitHub Secrets
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "@lkiwanSP500")
FRED_API_KEY = os.environ.get("FRED_API_KEY", "")

# Thresholds
MIN_CONFIDENCE = 60

# Initialize components
charts = ChartGenerator()
mentor = TradingMentor()
tracker = SignalTracker("data/signals.json", initial_capital=1000.0)
news = NewsFetcher()


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
    """Post morning briefing with analysis."""
    print("Posting morning briefing...")

    data = get_current_data()
    if not data:
        print("Could not get market data")
        return False

    # Get yesterday's data for overnight analysis
    prev_close = data['prev_close']
    current = data['close']

    greeting = mentor.get_greeting('morning')

    msg = f"""
{greeting}

{EMOJI['morning']} <b>Morning Briefing - {datetime.now().strftime('%B %d, %Y')}</b>

<b>Yesterday's Close:</b> ${prev_close:,.2f}

<b>Key Levels to Watch:</b>
• Resistance: ${current * 1.01:,.2f}
• Support: ${current * 0.99:,.2f}
• Pivot: ${current:,.2f}

<b>Technical Status:</b>
• RSI: {data['rsi']:.1f}
• MACD: {'Bullish' if data['macd_hist'] > 0 else 'Bearish'}
• Trend: {'Above' if current > data['sma_20'] else 'Below'} 20 SMA

{mentor.get_closing_thought('neutral')}

{get_hashtags('morning')}
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
    """Post technical analysis with chart."""
    print("Posting technical analysis...")

    data = get_current_data()
    if not data:
        return False

    df = data['df']

    # Generate chart
    chart_df = df.copy()
    chart_df.columns = [c.capitalize() for c in chart_df.columns]

    try:
        chart_buffer = charts.generate_technical_chart(
            chart_df,
            title=f"S&P 500 Technical Analysis - {datetime.now().strftime('%b %d')}",
            show_volume=True,
            show_rsi=True,
            show_macd=True,
            show_bollinger=True,
            show_sma=True
        )

        # Generate mentor commentary
        summary = mentor.generate_market_summary(data)

        caption = f"""
{EMOJI['chart']} <b>Technical Analysis</b>

{summary}

{get_hashtags('technical')}
"""
        return send_telegram_photo(chart_buffer, caption[:1024])

    except Exception as e:
        print(f"Chart error: {e}")
        return False


def post_economic_dashboard():
    """Post economic indicators with dashboard."""
    print("Posting economic dashboard...")

    econ_data = get_economic_data()

    try:
        chart_buffer = charts.generate_economic_dashboard(econ_data)

        # Determine sentiment
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

        caption = f"""
{EMOJI['economic']} <b>Economic Dashboard</b>

<b>Market Sentiment:</b> {sentiment}
<b>VIX:</b> {econ_data['vix']:.2f}
<b>Fear & Greed:</b> {econ_data['fear_greed']}/100

<b>Key Indicators:</b>
• Fed Rate: {econ_data['fed_rate']:.2f}%
• 10Y Treasury: {econ_data['treasury_10y']:.2f}%
• Unemployment: {econ_data['unemployment']:.1f}%

{get_hashtags('economic')}
"""
        return send_telegram_photo(chart_buffer, caption)

    except Exception as e:
        print(f"Dashboard error: {e}")
        # Fallback to text
        return post_economic_text(econ_data)


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
    """Post market sentiment analysis."""
    print("Posting sentiment...")

    econ_data = get_economic_data()
    vix = econ_data['vix']

    if vix < 15:
        emoji = f"{EMOJI['bullish']}{EMOJI['bullish']}{EMOJI['bullish']}"
        sentiment = "EXTREME GREED"
        commentary = "Markets are euphoric! Great for bulls, but watch for pullbacks."
    elif vix < 20:
        emoji = f"{EMOJI['bullish']}{EMOJI['bullish']}"
        sentiment = "GREED"
        commentary = "Bullish vibes! Momentum is on our side."
    elif vix < 25:
        emoji = f"{EMOJI['neutral']}{EMOJI['neutral']}"
        sentiment = "NEUTRAL"
        commentary = "Market's undecided. Wait for clearer signals."
    elif vix < 30:
        emoji = f"{EMOJI['bearish']}{EMOJI['bearish']}"
        sentiment = "FEAR"
        commentary = "Caution in the air. Defensive mode might be smart."
    else:
        emoji = f"{EMOJI['bearish']}{EMOJI['bearish']}{EMOJI['bearish']}"
        sentiment = "EXTREME FEAR"
        commentary = "High fear often means opportunity. Watch for bounces!"

    msg = f"""
{mentor.get_greeting()}

{emoji} <b>Market Sentiment: {sentiment}</b>

<b>Fear & Greed Index:</b> {econ_data['fear_greed']}/100
<b>VIX (Fear Gauge):</b> {vix:.2f}

{commentary}

{mentor.get_closing_thought('neutral')}

{get_hashtags('sentiment')}
"""
    return send_telegram(msg)


def post_signal_check():
    """Check for trading signals and post if found."""
    print("Checking for signals...")

    data = get_current_data()
    if not data:
        print("No data available")
        return False

    # Calculate signal
    score = 0.5
    rsi = data['rsi']
    macd_hist = data['macd_hist']
    bb_position = (data['close'] - data['bb_lower']) / (data['bb_upper'] - data['bb_lower']) if data['bb_upper'] != data['bb_lower'] else 0.5

    # RSI signals
    if rsi < 30:
        score += 0.15
    elif rsi > 70:
        score -= 0.15
    elif rsi < 45:
        score += 0.05
    elif rsi > 55:
        score -= 0.05

    # MACD
    if macd_hist > 0:
        score += 0.10
    else:
        score -= 0.10

    # Bollinger
    if bb_position < 0.2:
        score += 0.10
    elif bb_position > 0.8:
        score -= 0.10

    # Trend
    if data['close'] > data['sma_20']:
        score += 0.10
    else:
        score -= 0.10

    score = max(0.1, min(0.9, score))

    # Determine direction and confidence
    if score > 0.5:
        direction = "LONG"
        confidence = score * 100
    else:
        direction = "SHORT"
        confidence = (1 - score) * 100

    print(f"Signal: {direction} with {confidence:.1f}% confidence")

    # Only post if confident
    if confidence >= MIN_CONFIDENCE:
        current_price = data['close']

        if direction == "LONG":
            entry = current_price
            take_profit = entry * 1.008
            stop_loss = entry * 0.995
            direction_emoji = EMOJI['bullish']
        else:
            entry = current_price
            take_profit = entry * 0.992
            stop_loss = entry * 1.005
            direction_emoji = EMOJI['bearish']

        # Track signal
        signal = tracker.add_signal(
            direction=direction,
            entry_price=entry,
            take_profit=take_profit,
            stop_loss=stop_loss,
            confidence=confidence,
            ticker="SPY"
        )

        # Generate explanation
        explanation = mentor.explain_signal(direction, {
            'rsi': rsi,
            'macd_hist': macd_hist,
            'prev_macd_hist': data['prev_macd_hist']
        })

        tp_pct = ((take_profit - entry) / entry) * 100 if direction == "LONG" else ((entry - take_profit) / entry) * 100
        sl_pct = abs((stop_loss - entry) / entry) * 100
        rr = abs(tp_pct / sl_pct) if sl_pct > 0 else 0

        msg = f"""
{EMOJI['signal']} <b>Signal Alert</b>

{direction_emoji} <b>{direction}</b> SPY

<b>Entry:</b> <code>${entry:,.2f}</code>
<b>Take Profit:</b> <code>${take_profit:,.2f}</code> ({tp_pct:+.2f}%)
<b>Stop Loss:</b> <code>${stop_loss:,.2f}</code> (-{sl_pct:.2f}%)
<b>Risk/Reward:</b> 1:{rr:.1f}
<b>Confidence:</b> {confidence:.0f}%

<b>Why this setup:</b>
{explanation}

⚠️ <i>Educational content only. Not financial advice.</i>

{get_hashtags('signal')}
"""
        return send_telegram(msg)
    else:
        print(f"Confidence {confidence:.1f}% below threshold {MIN_CONFIDENCE}%")
        return False


def post_market_close():
    """Post market close with recap."""
    print("Posting market close...")

    data = get_current_data()
    daily_perf = tracker.get_daily_performance()

    if not data:
        msg = f"""
{EMOJI['bell']} <b>MARKET CLOSED</b>

US Market is now closed!
See you tomorrow! 👋

{get_hashtags('close')}
"""
        return send_telegram(msg)

    # Get sentiment
    if data['change_pct'] > 0:
        sentiment = 'bullish'
    elif data['change_pct'] < 0:
        sentiment = 'bearish'
    else:
        sentiment = 'neutral'

    # Format signal performance
    if daily_perf['trades'] > 0:
        signal_text = f"Trades: {daily_perf['trades']} | Win Rate: {daily_perf['win_rate']:.0f}% | P&L: {daily_perf['total_pnl_pct']:+.2f}%"
    else:
        signal_text = "No signals today"

    msg = f"""
{mentor.get_greeting('close')}

{EMOJI['bell']} <b>Market Close Recap - {datetime.now().strftime('%B %d, %Y')}</b>

<b>Final Score:</b>
• Close: <code>${data['close']:,.2f}</code>
• Change: {data['change']:+.2f} ({data['change_pct']:+.2f}%)
• High: <code>${data['high']:,.2f}</code>
• Low: <code>${data['low']:,.2f}</code>

<b>Technical Status:</b>
• RSI: {data['rsi']:.1f}
• MACD: {'Bullish' if data['macd_hist'] > 0 else 'Bearish'}

<b>Today's Signals:</b>
{signal_text}

{mentor.get_closing_thought(sentiment)}

Rest up, traders! See you tomorrow! 🌙

{get_hashtags('close')}
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


def post_news():
    """Post market news update."""
    print("Posting market news...")

    news_items = news.get_market_news(limit=5)
    sentiment = news.get_market_sentiment()

    # Add sentiment to the post
    if sentiment['article_count'] > 0:
        sent_emoji = '🟢' if sentiment['overall'] == 'BULLISH' else ('🔴' if sentiment['overall'] == 'BEARISH' else '⚪')
        sentiment_text = f"\n<b>News Sentiment:</b> {sent_emoji} {sentiment['overall']}\n({sentiment['bullish_pct']:.0f}% bullish, {sentiment['bearish_pct']:.0f}% bearish)\n"
    else:
        sentiment_text = ""

    msg = format_news_post(news_items, "Market News Update")
    msg += sentiment_text
    msg += f"\n{get_hashtags('signal')}"

    return send_telegram(msg)


def post_earnings():
    """Post upcoming earnings calendar."""
    print("Posting earnings calendar...")

    earnings = news.get_earnings_calendar()
    msg = format_earnings_post(earnings)
    msg += f"\n\n{get_hashtags('signal')}"

    return send_telegram(msg)


# ============================================
# COMMAND ROUTING
# ============================================

COMMANDS = {
    'test': post_test,
    'morning': post_morning_briefing,
    'morning_briefing': post_morning_briefing,
    'open': post_market_open,
    'market_open': post_market_open,
    'technical': post_technical_analysis,
    'technical_analysis': post_technical_analysis,
    'economic': post_economic_dashboard,
    'economic_update': post_economic_dashboard,
    'sentiment': post_sentiment,
    'sentiment_check': post_sentiment,
    'signal': post_signal_check,
    'signal_check': post_signal_check,
    'predict': post_signal_check,
    'close': post_market_close,
    'market_close': post_market_close,
    'weekly': post_weekly_report,
    'weekly_report': post_weekly_report,
    # Branding
    'welcome': post_welcome_message,
    'logo': post_logo,
    'banner': post_banner,
    # News
    'news': post_news,
    'earnings': post_earnings,
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
