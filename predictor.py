# -*- coding: utf-8 -*-
"""
S&P 500 Cloud Predictor
=======================
Fetches data, generates features, makes predictions, posts to Telegram
Runs entirely on GitHub Actions
"""

import os
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Configuration
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "@lkiwanSP500")
MIN_CONFIDENCE = 0.60

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_DIR = os.path.join(BASE_DIR, 'models')


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
            "parse_mode": "HTML"
        }, timeout=30)
        return response.status_code == 200
    except Exception as e:
        print(f"Telegram error: {e}")
        return False


def fetch_sp500_data(days=60):
    """Fetch S&P 500 data using yfinance"""
    try:
        import yfinance as yf
        ticker = yf.Ticker("^GSPC")
        data = ticker.history(period=f"{days}d")

        if data.empty:
            print("No data from yfinance")
            return None

        # Reset index and rename
        data = data.reset_index()
        data.columns = [c.lower() for c in data.columns]
        data['date'] = pd.to_datetime(data['date']).dt.tz_localize(None)

        print(f"Fetched {len(data)} days of S&P 500 data")
        print(f"Latest: {data['date'].iloc[-1].strftime('%Y-%m-%d')} - ${data['close'].iloc[-1]:,.2f}")

        return data
    except Exception as e:
        print(f"Error fetching data: {e}")
        return None


def calculate_technical_indicators(df):
    """Calculate technical indicators for prediction"""
    df = df.copy()

    # Returns
    df['returns'] = df['close'].pct_change()
    df['returns_1d'] = df['returns'].shift(1)
    df['returns_2d'] = df['returns'].shift(2)
    df['returns_3d'] = df['returns'].shift(3)
    df['returns_5d'] = df['returns'].shift(5)

    # Moving averages
    df['sma_5'] = df['close'].rolling(5).mean()
    df['sma_10'] = df['close'].rolling(10).mean()
    df['sma_20'] = df['close'].rolling(20).mean()
    df['sma_50'] = df['close'].rolling(50).mean() if len(df) >= 50 else df['close'].rolling(20).mean()

    # EMA
    df['ema_12'] = df['close'].ewm(span=12).mean()
    df['ema_26'] = df['close'].ewm(span=26).mean()

    # MACD
    df['macd'] = df['ema_12'] - df['ema_26']
    df['macd_signal'] = df['macd'].ewm(span=9).mean()
    df['macd_hist'] = df['macd'] - df['macd_signal']

    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['rsi_14'] = 100 - (100 / (1 + rs))

    # Bollinger Bands
    df['bb_middle'] = df['close'].rolling(20).mean()
    bb_std = df['close'].rolling(20).std()
    df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
    df['bb_lower'] = df['bb_middle'] - (bb_std * 2)
    df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['bb_middle']
    df['bb_position'] = (df['close'] - df['bb_lower']) / (df['bb_upper'] - df['bb_lower'])

    # Volatility
    df['volatility_5'] = df['returns'].rolling(5).std()
    df['volatility_10'] = df['returns'].rolling(10).std()
    df['volatility_20'] = df['returns'].rolling(20).std()

    # Volume indicators
    df['volume_sma'] = df['volume'].rolling(20).mean()
    df['volume_ratio'] = df['volume'] / df['volume_sma']

    # Price momentum
    df['momentum_5'] = df['close'] / df['close'].shift(5) - 1
    df['momentum_10'] = df['close'] / df['close'].shift(10) - 1
    df['momentum_20'] = df['close'] / df['close'].shift(20) - 1

    # Price position relative to MAs
    df['price_sma5_ratio'] = df['close'] / df['sma_5']
    df['price_sma10_ratio'] = df['close'] / df['sma_10']
    df['price_sma20_ratio'] = df['close'] / df['sma_20']

    # Trend indicators
    df['sma5_sma20_ratio'] = df['sma_5'] / df['sma_20']
    df['sma10_sma20_ratio'] = df['sma_10'] / df['sma_20']

    # Day of week (0=Monday, 4=Friday)
    df['day_of_week'] = pd.to_datetime(df['date']).dt.dayofweek

    # High/Low features
    df['high_low_ratio'] = df['high'] / df['low']
    df['close_open_ratio'] = df['close'] / df['open']

    # Rolling returns
    df['rolling_return_5'] = df['close'].pct_change(5)
    df['rolling_return_10'] = df['close'].pct_change(10)

    return df


def prepare_features(df):
    """Prepare feature matrix for prediction"""
    # List of features we'll use (matching trained model)
    feature_cols = [
        'returns_1d', 'returns_2d', 'returns_3d', 'returns_5d',
        'rsi_14', 'macd', 'macd_signal', 'macd_hist',
        'bb_width', 'bb_position',
        'volatility_5', 'volatility_10', 'volatility_20',
        'volume_ratio',
        'momentum_5', 'momentum_10', 'momentum_20',
        'price_sma5_ratio', 'price_sma10_ratio', 'price_sma20_ratio',
        'sma5_sma20_ratio', 'sma10_sma20_ratio',
        'day_of_week',
        'high_low_ratio', 'close_open_ratio',
        'rolling_return_5', 'rolling_return_10'
    ]

    # Get latest row
    latest = df.iloc[-1:].copy()

    # Fill missing columns with 0
    for col in feature_cols:
        if col not in latest.columns:
            latest[col] = 0

    # Select features
    X = latest[feature_cols].fillna(0)

    return X, feature_cols


def make_prediction(features_df):
    """Make prediction using simple model logic"""
    # Get key indicators
    rsi = features_df['rsi_14'].values[0]
    macd_hist = features_df['macd_hist'].values[0]
    bb_position = features_df['bb_position'].values[0]
    momentum_5 = features_df['momentum_5'].values[0]
    momentum_10 = features_df['momentum_10'].values[0]
    sma_ratio = features_df['sma5_sma20_ratio'].values[0]
    volatility = features_df['volatility_10'].values[0]

    # Scoring system
    score = 0.5  # Start neutral

    # RSI signals
    if rsi < 30:
        score += 0.15  # Oversold - bullish
    elif rsi > 70:
        score -= 0.15  # Overbought - bearish
    elif rsi < 45:
        score += 0.05
    elif rsi > 55:
        score -= 0.05

    # MACD signals
    if macd_hist > 0:
        score += 0.10
    else:
        score -= 0.10

    # Bollinger position
    if bb_position < 0.2:
        score += 0.10  # Near lower band - bullish
    elif bb_position > 0.8:
        score -= 0.10  # Near upper band - bearish

    # Momentum
    if momentum_5 > 0.01:
        score += 0.10
    elif momentum_5 < -0.01:
        score -= 0.10

    if momentum_10 > 0.02:
        score += 0.05
    elif momentum_10 < -0.02:
        score -= 0.05

    # Trend (SMA ratio)
    if sma_ratio > 1.01:
        score += 0.10  # Uptrend
    elif sma_ratio < 0.99:
        score -= 0.10  # Downtrend

    # Clamp score between 0.1 and 0.9
    score = max(0.1, min(0.9, score))

    # Determine direction
    if score > 0.5:
        direction = "UP"
        confidence = score
        prob_up = score
        prob_down = 1 - score
    else:
        direction = "DOWN"
        confidence = 1 - score
        prob_up = score
        prob_down = 1 - score

    return {
        'direction': direction,
        'confidence': confidence,
        'prob_up': prob_up,
        'prob_down': prob_down,
        'rsi': rsi,
        'macd_hist': macd_hist,
        'momentum': momentum_5
    }


def post_signal(prediction, current_price):
    """Post trading signal to Telegram"""
    direction = prediction['direction']
    confidence = prediction['confidence']

    is_buy = direction == "UP"

    if is_buy:
        emoji, action, trend, arrow = "🟢", "BUY", "BULLISH", "📈"
        # Calculate levels for BUY
        entry = current_price
        tp = entry * 1.008  # 0.8% profit target
        sl = entry * 0.995  # 0.5% stop loss
    else:
        emoji, action, trend, arrow = "🔴", "SELL", "BEARISH", "📉"
        # Calculate levels for SELL
        entry = current_price
        tp = entry * 0.992  # 0.8% profit target
        sl = entry * 1.005  # 0.5% stop loss

    if confidence >= 0.80:
        strength = "🔥 STRONG SIGNAL"
    elif confidence >= 0.70:
        strength = "✅ HIGH CONFIDENCE"
    elif confidence >= 0.60:
        strength = "📊 MODERATE"
    else:
        strength = "⚠️ WEAK"

    rr = abs(entry - tp) / abs(entry - sl) if abs(entry - sl) > 0 else 0

    msg = f"""
{emoji}{emoji}{emoji} <b>S&P 500 SIGNAL</b> {emoji}{emoji}{emoji}

{arrow} <b>Action:</b> {action}
📊 <b>Trend:</b> {trend}
💪 <b>Strength:</b> {strength}
🎯 <b>Confidence:</b> {confidence*100:.1f}%

<b>📈 Probabilities:</b>
   UP: {prediction['prob_up']*100:.1f}%
   DOWN: {prediction['prob_down']*100:.1f}%

<b>💰 Trading Levels:</b>
   ▫️ Entry: <code>${entry:,.2f}</code>
   ▫️ Take Profit: <code>${tp:,.2f}</code>
   ▫️ Stop Loss: <code>${sl:,.2f}</code>
   ▫️ Risk/Reward: <code>{rr:.2f}</code>

<b>📊 Technical Indicators:</b>
   RSI: {prediction['rsi']:.1f}
   MACD: {prediction['macd_hist']:.4f}
   Momentum: {prediction['momentum']*100:.2f}%

📅 {datetime.utcnow().strftime("%B %d, %Y %H:%M UTC")}

#SP500 #Trading #{action}
"""
    return send_telegram(msg)


def run_prediction():
    """Main function: fetch data, predict, post if confident"""
    print("=" * 50)
    print("S&P 500 Cloud Predictor")
    print("=" * 50)

    # Step 1: Fetch data
    print("\n[1/4] Fetching S&P 500 data...")
    df = fetch_sp500_data(days=60)

    if df is None or len(df) < 20:
        print("Not enough data!")
        return False

    current_price = df['close'].iloc[-1]

    # Step 2: Calculate indicators
    print("\n[2/4] Calculating technical indicators...")
    df = calculate_technical_indicators(df)

    # Step 3: Prepare features and predict
    print("\n[3/4] Making prediction...")
    features, feature_cols = prepare_features(df)
    prediction = make_prediction(features)

    print(f"  Direction: {prediction['direction']}")
    print(f"  Confidence: {prediction['confidence']*100:.1f}%")
    print(f"  Prob UP: {prediction['prob_up']*100:.1f}%")
    print(f"  Prob DOWN: {prediction['prob_down']*100:.1f}%")

    # Step 4: Post if confident
    print("\n[4/4] Checking confidence threshold...")

    if prediction['confidence'] >= MIN_CONFIDENCE:
        print(f"  Confidence {prediction['confidence']*100:.1f}% >= {MIN_CONFIDENCE*100:.0f}% - POSTING!")
        success = post_signal(prediction, current_price)
        print("  Signal posted!" if success else "  Failed to post!")
        return success
    else:
        print(f"  Confidence {prediction['confidence']*100:.1f}% < {MIN_CONFIDENCE*100:.0f}% - NOT POSTING")
        return False


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()

        if cmd == "predict":
            run_prediction()
        elif cmd == "test":
            send_telegram("✅ Cloud Predictor is working!")
            print("Test sent!")
        else:
            print(f"Unknown: {cmd}")
    else:
        run_prediction()
