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
from ml_predictor import MLPredictor

# Configuration from GitHub Secrets
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "@lkiwanSP500")
FRED_API_KEY = os.environ.get("FRED_API_KEY", "")

# Thresholds
MIN_CONFIDENCE = 50

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

    economic_data = get_economic_data()
    df = data['df']
    prediction = ml_predictor.predict(df, economic_data)

    direction = prediction['direction']
    confidence = prediction['confidence']

    print(f"Signal: {direction} with {confidence:.1f}% confidence")

    if confidence >= MIN_CONFIDENCE:
        current_price = data['close']

        levels = ml_predictor.get_signal_levels(current_price, direction, confidence)
        entry = levels['entry']
        take_profit = levels['take_profit']
        stop_loss = levels['stop_loss']

        direction_emoji = EMOJI['bullish'] if direction == "LONG" else EMOJI['bearish']

        signal = tracker.add_signal(
            direction=direction,
            entry_price=entry,
            take_profit=take_profit,
            stop_loss=stop_loss,
            confidence=confidence,
            ticker="SPY"
        )

        rsi = data['rsi']
        macd_hist = data['macd_hist']
        explanation = mentor.explain_signal(direction, {
            'rsi': rsi,
            'macd_hist': macd_hist,
            'prev_macd_hist': data['prev_macd_hist']
        })

        tp_pct = ((take_profit - entry) / entry) * 100 if direction == "LONG" else ((entry - take_profit) / entry) * 100
        sl_pct = abs((stop_loss - entry) / entry) * 100
        rr = abs(tp_pct / sl_pct) if sl_pct > 0 else 0

        lot_size = tracker.get_lot_size(confidence)
        position_value = 1000 * lot_size

        msg = f"""
{EMOJI['signal']} <b>Signal Alert</b>

{direction_emoji} <b>{direction}</b> SPY

<b>Entry:</b> <code>${entry:,.2f}</code>
<b>Take Profit:</b> <code>${take_profit:,.2f}</code> ({tp_pct:+.2f}%)
<b>Stop Loss:</b> <code>${stop_loss:,.2f}</code> (-{sl_pct:.2f}%)
<b>Risk/Reward:</b> 1:{rr:.1f}
<b>Confidence:</b> {confidence:.0f}%

<b>Position Size:</b>
• Lot: {lot_size} ({lot_size*100:.0f}% of account)
• Value: ${position_value:,.0f}

<b>Analysis:</b>
{explanation}

• RSI: {rsi:.1f}
• MACD: {'Bullish' if macd_hist > 0 else 'Bearish'}
• VIX: {economic_data.get('vix', 20):.1f}

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
# ML-DRIVEN ANALYSIS POSTS
# ============================================

def post_ml_factor_analysis():
    """Post factor analysis - what's driving the prediction."""
    print("Posting factor analysis...")

    data = get_current_data()
    if not data:
        return False

    economic_data = get_economic_data()
    df = data['df']

    prediction = ml_predictor.predict(df, economic_data)
    factors = ml_predictor.get_factor_analysis(df, economic_data)
    tier = ml_predictor.get_confidence_tier(prediction['confidence'])

    if not factors:
        return False

    direction = prediction['direction']
    confidence = prediction['confidence']
    direction_emoji = EMOJI['bullish'] if direction == 'LONG' else EMOJI['bearish']

    rsi_emoji = '🟢' if factors['rsi']['signal'] == 'BULLISH' else ('🔴' if factors['rsi']['signal'] == 'BEARISH' else '⚪')
    mom_emoji = '🟢' if factors['momentum']['signal'] == 'BULLISH' else ('🔴' if factors['momentum']['signal'] == 'BEARISH' else '🟡')
    trend_emoji = '🟢' if factors['trend']['signal'] == 'BULLISH' else ('🔴' if factors['trend']['signal'] == 'BEARISH' else '🟡')
    macd_emoji = '🟢' if factors['macd']['signal'] == 'BULLISH' else '🔴'
    vix_emoji = '🟢' if factors['vix']['signal'] == 'GREED' else ('🔴' if factors['vix']['signal'] == 'FEAR' else '⚪')

    msg = f"""
{EMOJI['brain']} <b>Market Factor Analysis</b>

{mentor.get_greeting()}

{tier['emoji']} <b>Current Bias: {direction}</b> | Confidence: {confidence:.0f}%

━━━━━━━━━━━━━━━━━━━━━━

<b>What I'm Seeing:</b>

{rsi_emoji} <b>RSI:</b> {factors['rsi']['value']:.1f} - {factors['rsi']['note']}
{mom_emoji} <b>Momentum:</b> 5D: {factors['momentum']['value_5d']:+.2f}% | 20D: {factors['momentum']['value_20d']:+.2f}%
{trend_emoji} <b>Trend:</b> {'Above' if factors['trend']['above_sma20'] else 'Below'} SMA20, {'Above' if factors['trend']['above_sma50'] else 'Below'} SMA50
{macd_emoji} <b>MACD:</b> {factors['macd']['signal']} (Histogram: {factors['macd']['histogram']:.2f})
{vix_emoji} <b>VIX:</b> {factors['vix']['value']:.1f} - {factors['vix']['note']}

<b>Volatility:</b> {factors['volatility']['value_5d']:.2f}% (5D) | {'Expanding' if factors['volatility']['expanding'] else 'Contracting'}
<b>Bollinger:</b> {factors['bollinger']['signal']} (Position: {factors['bollinger']['position']:.0%})

━━━━━━━━━━━━━━━━━━━━━━

<b>Factor Count:</b> {factors['summary']['bullish_factors']} Bullish | {factors['summary']['bearish_factors']} Bearish
<b>Overall Bias:</b> {factors['summary']['overall']}

{mentor.get_closing_thought('bullish' if direction == 'LONG' else 'bearish')}

#SP500 #TradingSignals #TechnicalAnalysis
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


def post_high_confidence_alert():
    """Post ONLY if confidence >= 75% - elite signals."""
    print("Checking for high confidence signal...")

    data = get_current_data()
    if not data:
        return False

    economic_data = get_economic_data()
    df = data['df']

    prediction = ml_predictor.predict(df, economic_data)
    confidence = prediction['confidence']
    direction = prediction['direction']

    if confidence < 75:
        print(f"Confidence {confidence:.1f}% below elite threshold (75%)")
        return False

    tier = ml_predictor.get_confidence_tier(confidence)
    factors = ml_predictor.get_factor_analysis(df, economic_data)
    levels = ml_predictor.get_signal_levels(data['close'], direction, confidence)

    direction_emoji = EMOJI['bullish'] if direction == 'LONG' else EMOJI['bearish']

    signal = tracker.add_signal(
        direction=direction,
        entry_price=levels['entry'],
        take_profit=levels['take_profit'],
        stop_loss=levels['stop_loss'],
        confidence=confidence,
        ticker="SPY"
    )

    lot_size = tracker.get_lot_size(confidence)
    position_value = 1000 * lot_size

    tp_pct = abs((levels['take_profit'] - levels['entry']) / levels['entry']) * 100
    sl_pct = abs((levels['stop_loss'] - levels['entry']) / levels['entry']) * 100

    msg = f"""
{tier['emoji']} <b>HIGH CONVICTION SETUP</b> {tier['emoji']}

{mentor.get_greeting()}

I'm seeing something really good here, traders!

{direction_emoji} <b>{direction}</b> SPY

<b>Confidence:</b> {confidence:.0f}%

━━━━━━━━━━━━━━━━━━━━━━

<b>Entry:</b> <code>${levels['entry']:,.2f}</code>
<b>Take Profit:</b> <code>${levels['take_profit']:,.2f}</code> (+{tp_pct:.2f}%)
<b>Stop Loss:</b> <code>${levels['stop_loss']:,.2f}</code> (-{sl_pct:.2f}%)

<b>Position:</b>
• Lot: {lot_size} ({lot_size*100:.0f}%)
• Value: ${position_value:,.0f}

━━━━━━━━━━━━━━━━━━━━━━

<b>Why I Like This Setup:</b>
• RSI: {factors['rsi']['value']:.1f} ({factors['rsi']['signal']})
• Momentum: {factors['momentum']['signal']}
• Trend: {factors['trend']['signal']}
• MACD: {factors['macd']['signal']}

{EMOJI['fire']} <b>Multiple factors are aligning perfectly!</b>

This is exactly the kind of setup I look for. Strong technicals, good momentum, and the trend is on our side.

⚠️ <i>Educational content only. Not financial advice.</i>

#SP500 #TradingSignals #HighConfidence
"""
    return send_telegram(msg)


def post_ml_momentum():
    """Post momentum update with trend analysis."""
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
        mom_status = "STRONG UPTREND"
        mom_emoji = "🚀"
    elif mom_5d > 0 and mom_20d > 0:
        mom_status = "UPTREND"
        mom_emoji = "📈"
    elif mom_5d < -1 and mom_20d < -2:
        mom_status = "STRONG DOWNTREND"
        mom_emoji = "📉"
    elif mom_5d < 0 and mom_20d < 0:
        mom_status = "DOWNTREND"
        mom_emoji = "⬇️"
    else:
        mom_status = "CONSOLIDATING"
        mom_emoji = "↔️"

    vol = factors['volatility']['value_5d']
    if vol > 1.5:
        vol_status = "HIGH - Be careful with position sizing"
    elif vol > 1.0:
        vol_status = "ELEVATED - Normal market conditions"
    else:
        vol_status = "LOW - Good for trend following"

    msg = f"""
{mom_emoji} <b>Momentum Update</b>

{mentor.get_greeting()}

<b>Current Trend:</b> {mom_status}

<b>My Bias:</b> {direction_emoji} {direction} ({confidence:.0f}%)

━━━━━━━━━━━━━━━━━━━━━━

<b>Momentum Breakdown:</b>
• 5-Day: {mom_5d:+.2f}%
• 20-Day: {mom_20d:+.2f}%

<b>Price vs Moving Averages:</b>
• vs SMA 20: {'Above' if factors['trend']['above_sma20'] else 'Below'} (${factors['trend']['sma_20']:,.2f})
• vs SMA 50: {'Above' if factors['trend']['above_sma50'] else 'Below'} (${factors['trend']['sma_50']:,.2f})

<b>Volatility:</b> {vol:.2f}%
{vol_status}

<b>MACD:</b> {factors['macd']['signal']}

━━━━━━━━━━━━━━━━━━━━━━

{'Momentum is aligned with my analysis!' if (mom_5d > 0 and direction == 'LONG') or (mom_5d < 0 and direction == 'SHORT') else 'Watching for momentum to confirm direction.'}

Stay patient, traders! 💪

#SP500 #Momentum #TrendAnalysis
"""
    return send_telegram(msg)


def post_ml_risk_assessment():
    """Post risk assessment."""
    print("Posting risk assessment...")

    data = get_current_data()
    if not data:
        return False

    economic_data = get_economic_data()
    df = data['df']

    prediction = ml_predictor.predict(df, economic_data)
    factors = ml_predictor.get_factor_analysis(df, economic_data)

    risk_score = 0

    vix = factors['vix']['value']
    if vix > 30:
        risk_score += 3
        vix_risk = "EXTREME"
    elif vix > 25:
        risk_score += 2
        vix_risk = "HIGH"
    elif vix > 20:
        risk_score += 1
        vix_risk = "MODERATE"
    else:
        vix_risk = "LOW"

    vol = factors['volatility']['value_5d']
    if vol > 2:
        risk_score += 2
        vol_risk = "HIGH"
    elif vol > 1:
        risk_score += 1
        vol_risk = "MODERATE"
    else:
        vol_risk = "LOW"

    bb_pos = factors['bollinger']['position']
    if bb_pos > 0.9 or bb_pos < 0.1:
        risk_score += 1
        bb_risk = "EXTREME ZONE"
    elif bb_pos > 0.8 or bb_pos < 0.2:
        bb_risk = "CAUTION ZONE"
    else:
        bb_risk = "NORMAL"

    if risk_score >= 5:
        overall_risk = "HIGH"
        risk_emoji = "🔴"
        lot_advice = "I'd recommend 0.1-0.2 lots max"
    elif risk_score >= 3:
        overall_risk = "MODERATE"
        risk_emoji = "🟡"
        lot_advice = "Standard lot sizing should be fine"
    else:
        overall_risk = "LOW"
        risk_emoji = "🟢"
        lot_advice = "Normal lot sizing is appropriate"

    confidence = prediction['confidence']
    direction = prediction['direction']

    msg = f"""
{risk_emoji} <b>Risk Check</b>

{mentor.get_greeting()}

<b>Overall Risk Level:</b> {overall_risk}
<b>Risk Score:</b> {risk_score}/6

━━━━━━━━━━━━━━━━━━━━━━

<b>What I'm Watching:</b>

{EMOJI['warning'] if vix_risk in ['HIGH', 'EXTREME'] else '✅'} <b>VIX:</b> {vix:.1f} ({vix_risk})
{EMOJI['warning'] if vol_risk == 'HIGH' else '✅'} <b>Volatility:</b> {vol:.2f}% ({vol_risk})
{EMOJI['warning'] if 'EXTREME' in bb_risk else '✅'} <b>Bollinger:</b> {bb_risk}

━━━━━━━━━━━━━━━━━━━━━━

<b>Current Bias:</b>
Direction: {direction}
Confidence: {confidence:.0f}%

<b>My Advice:</b>
{lot_advice}

━━━━━━━━━━━━━━━━━━━━━━

<b>Remember:</b>
• Always use stop losses
• Never risk more than 2% per trade
• Reduce size in high volatility
• Don't chase losses

Stay disciplined! 💪

#SP500 #RiskManagement #TradingTips
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
