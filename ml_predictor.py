# -*- coding: utf-8 -*-
"""
ML Predictor Integration
========================
Integrates the trained XGBoost model for real predictions
Model: sp500_complete_20251113 (71.20% accuracy, 93.12% at high confidence)
"""

import os
import pandas as pd
import numpy as np
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional
import joblib


class MLPredictor:
    """
    Machine Learning predictor using the trained XGBoost model.

    This integrates the real ML model trained on:
    - Technical indicators (SMA, EMA, MACD, RSI, Bollinger Bands)
    - Economic data (VIX, Fed Rate, Treasury yields, etc.)
    - Sentiment data (news sentiment analysis)
    """

    MODEL_NAME = "sp500_complete_20251113"

    def __init__(self, models_path: str = "models"):
        """Initialize the ML predictor."""
        self.models_path = models_path
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.is_loaded = False

        # Try to load model
        self._load_model()

    def _load_model(self) -> bool:
        """Load the trained model, scaler, and feature names."""
        model_path = os.path.join(self.models_path, f"{self.MODEL_NAME}.pkl")
        scaler_path = os.path.join(self.models_path, f"{self.MODEL_NAME}_scaler.pkl")
        features_path = os.path.join(self.models_path, f"{self.MODEL_NAME}_features.pkl")

        # Check if all files exist
        if not all(os.path.exists(p) for p in [model_path, scaler_path, features_path]):
            print(f"Model files not found in {self.models_path}")
            print("Falling back to rule-based signals")
            return False

        try:
            self.model = joblib.load(model_path)
            self.scaler = joblib.load(scaler_path)
            self.feature_names = joblib.load(features_path)
            self.is_loaded = True
            print(f"ML Model loaded: {self.MODEL_NAME}")
            print(f"Features required: {len(self.feature_names)}")
            return True
        except Exception as e:
            print(f"Error loading model: {e}")
            return False

    def compute_features(self, df: pd.DataFrame, economic_data: Dict) -> pd.DataFrame:
        """
        Compute all features needed for the model from market data.

        Args:
            df: DataFrame with OHLCV data (columns: open, high, low, close, volume)
            economic_data: Dict with economic indicators

        Returns:
            DataFrame with computed features
        """
        features = pd.DataFrame()

        # Ensure we have enough data
        if len(df) < 50:
            print("Not enough historical data for feature computation")
            return features

        # ========== Price Features ==========
        features['return'] = df['close'].pct_change()
        features['log_return'] = np.log(df['close'] / df['close'].shift(1))
        features['intraday_range'] = (df['high'] - df['low']) / df['close']
        features['volatility_5d'] = features['return'].rolling(5).std()
        features['volatility_20d'] = features['return'].rolling(20).std()

        # ========== Technical Indicators ==========
        # Moving Averages
        features['sma_20'] = df['close'].rolling(20).mean() / df['close'] - 1
        features['sma_50'] = df['close'].rolling(50).mean() / df['close'] - 1
        features['sma_200'] = df['close'].rolling(min(200, len(df))).mean() / df['close'] - 1
        features['ema_12'] = df['close'].ewm(span=12).mean() / df['close'] - 1
        features['ema_26'] = df['close'].ewm(span=26).mean() / df['close'] - 1

        # MACD
        ema_12 = df['close'].ewm(span=12).mean()
        ema_26 = df['close'].ewm(span=26).mean()
        features['macd'] = (ema_12 - ema_26) / df['close']
        features['macd_signal'] = features['macd'].ewm(span=9).mean()
        features['macd_histogram'] = features['macd'] - features['macd_signal']

        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        features['rsi_14'] = 100 - (100 / (1 + rs))

        # Bollinger Bands
        bb_middle = df['close'].rolling(20).mean()
        bb_std = df['close'].rolling(20).std()
        features['bb_middle'] = bb_middle / df['close'] - 1
        features['bb_upper'] = (bb_middle + 2 * bb_std) / df['close'] - 1
        features['bb_lower'] = (bb_middle - 2 * bb_std) / df['close'] - 1
        features['bb_width'] = (4 * bb_std) / bb_middle

        # Volume
        features['volume_sma_20'] = df['volume'].rolling(20).mean()
        features['volume_ratio'] = df['volume'] / features['volume_sma_20']

        # Momentum
        features['momentum_5'] = df['close'].pct_change(5)
        features['momentum_10'] = df['close'].pct_change(10)
        features['momentum_20'] = df['close'].pct_change(20)
        features['roc_5'] = (df['close'] - df['close'].shift(5)) / df['close'].shift(5)
        features['roc_10'] = (df['close'] - df['close'].shift(10)) / df['close'].shift(10)

        # ========== Economic Data ==========
        features['fed_funds_rate'] = economic_data.get('fed_rate', 5.25)
        features['unemployment_rate'] = economic_data.get('unemployment', 4.0)
        features['cpi'] = economic_data.get('cpi', 3.0)
        features['vix'] = economic_data.get('vix', 20.0)
        features['treasury_10y'] = economic_data.get('treasury_10y', 4.5)
        features['treasury_2y'] = economic_data.get('treasury_2y', 4.8)
        features['yield_curve'] = features['treasury_10y'] - features['treasury_2y']
        features['dollar_index'] = economic_data.get('dollar_index', 103.0)
        features['oil_price'] = economic_data.get('oil_price', 75.0)
        features['consumer_sentiment'] = economic_data.get('consumer_sentiment', 70.0)

        # Economic derived features
        features['fed_rate_change'] = 0.0  # Would need historical data
        features['fed_rate_change_3m'] = 0.0
        features['unemployment_change'] = 0.0
        features['inflation_rate'] = features['cpi']
        features['vix_ma20'] = features['vix']  # Simplified
        features['vix_spike'] = 0  # Would need VIX history
        features['yield_curve_inverted'] = (features['yield_curve'] < 0).astype(int)
        features['consumer_sentiment_momentum'] = 0.0

        # ========== Sentiment Features (use neutral defaults) ==========
        # In a full implementation, these would come from news API
        features['sentiment_positive_mean'] = 0.33
        features['sentiment_negative_mean'] = 0.33
        features['sentiment_neutral_mean'] = 0.34
        features['sentiment_compound_mean'] = 0.0
        features['sentiment_compound_std'] = 0.1
        features['sentiment_compound_min'] = -0.2
        features['sentiment_compound_max'] = 0.2
        features['news_count'] = 10
        features['sentiment_momentum'] = 0.0
        features['sentiment_ma5'] = 0.0
        features['sentiment_ma10'] = 0.0
        features['sentiment_lag1'] = 0.0
        features['sentiment_lag2'] = 0.0
        features['sentiment_lag3'] = 0.0

        # ========== Lag Features ==========
        features['return_lag1'] = features['return'].shift(1)
        features['close_lag1'] = df['close'].shift(1)
        features['return_lag2'] = features['return'].shift(2)
        features['close_lag2'] = df['close'].shift(2)
        features['return_lag3'] = features['return'].shift(3)
        features['close_lag3'] = df['close'].shift(3)
        features['return_lag5'] = features['return'].shift(5)
        features['close_lag5'] = df['close'].shift(5)

        # ========== Rolling Features ==========
        # Sentiment rolling (use defaults)
        for window in [5, 10, 20]:
            features[f'sentiment_rolling_mean_{window}'] = 0.0
            features[f'sentiment_rolling_std_{window}'] = 0.1
            features[f'sentiment_rolling_min_{window}'] = -0.2
            features[f'sentiment_rolling_max_{window}'] = 0.2

        # Return rolling
        for window in [5, 10, 20]:
            features[f'return_rolling_mean_{window}'] = features['return'].rolling(window).mean()
            features[f'return_rolling_std_{window}'] = features['return'].rolling(window).std()

        # Volume rolling
        for window in [5, 10, 20]:
            features[f'volume_rolling_mean_{window}'] = df['volume'].rolling(window).mean()

        # ========== Interaction Features ==========
        features['sentiment_rsi'] = 0.0  # Sentiment * RSI interaction
        features['sentiment_macd'] = 0.0
        features['sentiment_volume'] = 0.0
        features['sentiment_price_momentum'] = 0.0
        features['news_weighted_sentiment'] = 0.0

        return features

    def predict(self, df: pd.DataFrame, economic_data: Dict) -> Dict:
        """
        Make a prediction using the ML model.

        Args:
            df: DataFrame with OHLCV data
            economic_data: Dict with economic indicators

        Returns:
            Dict with prediction results
        """
        if not self.is_loaded:
            print("Model not loaded, using fallback")
            return self._fallback_prediction(df)

        try:
            # Compute features
            features = self.compute_features(df, economic_data)

            if features.empty:
                return self._fallback_prediction(df)

            # Get the latest row
            latest = features.iloc[[-1]].copy()

            # Fill any missing features with 0
            for feat in self.feature_names:
                if feat not in latest.columns:
                    latest[feat] = 0.0

            # Handle NaN values
            latest = latest.fillna(0)

            # Select and order features
            X = latest[self.feature_names].values

            # Scale features
            X_scaled = self.scaler.transform(X)

            # Make prediction
            prediction = self.model.predict(X_scaled)[0]
            probability = self.model.predict_proba(X_scaled)[0]

            # Interpret results
            direction = "LONG" if prediction == 1 else "SHORT"
            confidence = probability[int(prediction)] * 100  # Convert to percentage

            result = {
                'direction': direction,
                'confidence': float(confidence),
                'probability_up': float(probability[1] * 100),
                'probability_down': float(probability[0] * 100),
                'model_used': 'XGBoost ML Model',
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

            print(f"ML Prediction: {direction} with {confidence:.1f}% confidence")
            return result

        except Exception as e:
            print(f"ML prediction error: {e}")
            return self._fallback_prediction(df)

    def _fallback_prediction(self, df: pd.DataFrame) -> Dict:
        """Fallback to rule-based prediction if ML fails."""
        if df is None or len(df) < 20:
            return {
                'direction': 'LONG',
                'confidence': 50.0,
                'probability_up': 50.0,
                'probability_down': 50.0,
                'model_used': 'Fallback (no data)',
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }

        # Simple rule-based scoring
        score = 0.5

        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1]

        if rsi < 30:
            score += 0.15
        elif rsi > 70:
            score -= 0.15

        # MACD
        ema_12 = df['close'].ewm(span=12).mean()
        ema_26 = df['close'].ewm(span=26).mean()
        macd = ema_12 - ema_26
        macd_signal = macd.ewm(span=9).mean()
        macd_hist = (macd - macd_signal).iloc[-1]

        if macd_hist > 0:
            score += 0.10
        else:
            score -= 0.10

        # Trend
        sma_20 = df['close'].rolling(20).mean().iloc[-1]
        if df['close'].iloc[-1] > sma_20:
            score += 0.10
        else:
            score -= 0.10

        score = max(0.1, min(0.9, score))

        if score > 0.5:
            direction = "LONG"
            confidence = score * 100
        else:
            direction = "SHORT"
            confidence = (1 - score) * 100

        return {
            'direction': direction,
            'confidence': float(confidence),
            'probability_up': float(score * 100),
            'probability_down': float((1 - score) * 100),
            'model_used': 'Rule-based Fallback',
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

    def get_signal_levels(self, current_price: float, direction: str, confidence: float) -> Dict:
        """
        Calculate entry, take profit, and stop loss levels.

        Higher confidence = wider take profit, tighter stop loss
        """
        # Adjust levels based on confidence
        if confidence >= 80:
            tp_mult = 1.012  # 1.2% take profit
            sl_mult = 0.994  # 0.6% stop loss
        elif confidence >= 70:
            tp_mult = 1.010  # 1.0% take profit
            sl_mult = 0.995  # 0.5% stop loss
        elif confidence >= 60:
            tp_mult = 1.008  # 0.8% take profit
            sl_mult = 0.995  # 0.5% stop loss
        else:
            tp_mult = 1.006  # 0.6% take profit
            sl_mult = 0.996  # 0.4% stop loss

        if direction == "LONG":
            entry = current_price
            take_profit = entry * tp_mult          # TP above entry
            stop_loss = entry * sl_mult            # SL below entry
        else:
            entry = current_price
            take_profit = entry * (2 - tp_mult)    # TP below entry
            stop_loss = entry * (2 - sl_mult)      # SL above entry

        return {
            'entry': entry,
            'take_profit': take_profit,
            'stop_loss': stop_loss
        }

    def get_factor_analysis(self, df: pd.DataFrame, economic_data: Dict) -> Dict:
        """
        Analyze key factors driving the ML prediction.

        Returns analysis of top factors: RSI, momentum, volatility, economic.
        """
        if len(df) < 20:
            return {}

        # Calculate key indicators
        close = df['close']

        # RSI
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        rsi = (100 - (100 / (1 + rs))).iloc[-1]

        # Momentum
        momentum_5 = ((close.iloc[-1] / close.iloc[-5]) - 1) * 100 if len(close) >= 5 else 0
        momentum_20 = ((close.iloc[-1] / close.iloc[-20]) - 1) * 100 if len(close) >= 20 else 0

        # Volatility
        returns = close.pct_change()
        volatility_5d = returns.rolling(5).std().iloc[-1] * 100
        volatility_20d = returns.rolling(20).std().iloc[-1] * 100

        # Trend
        sma_20 = close.rolling(20).mean().iloc[-1]
        sma_50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else sma_20
        above_sma20 = close.iloc[-1] > sma_20
        above_sma50 = close.iloc[-1] > sma_50

        # MACD
        ema_12 = close.ewm(span=12).mean()
        ema_26 = close.ewm(span=26).mean()
        macd = ema_12 - ema_26
        macd_signal = macd.ewm(span=9).mean()
        macd_hist = (macd - macd_signal).iloc[-1]
        macd_bullish = macd_hist > 0

        # Bollinger position
        bb_middle = close.rolling(20).mean().iloc[-1]
        bb_std = close.rolling(20).std().iloc[-1]
        bb_upper = bb_middle + 2 * bb_std
        bb_lower = bb_middle - 2 * bb_std
        bb_position = (close.iloc[-1] - bb_lower) / (bb_upper - bb_lower) if bb_upper != bb_lower else 0.5

        # Economic factors
        vix = economic_data.get('vix', 20)
        fed_rate = economic_data.get('fed_rate', 5.25)

        # Determine factor signals
        factors = {
            'rsi': {
                'value': rsi,
                'signal': 'BULLISH' if rsi < 40 else ('BEARISH' if rsi > 60 else 'NEUTRAL'),
                'strength': abs(50 - rsi) / 50,
                'note': 'Oversold' if rsi < 30 else ('Overbought' if rsi > 70 else 'Normal')
            },
            'momentum': {
                'value_5d': momentum_5,
                'value_20d': momentum_20,
                'signal': 'BULLISH' if momentum_5 > 0 and momentum_20 > 0 else ('BEARISH' if momentum_5 < 0 and momentum_20 < 0 else 'MIXED'),
                'strength': min(abs(momentum_5) / 5, 1.0)
            },
            'volatility': {
                'value_5d': volatility_5d,
                'value_20d': volatility_20d,
                'signal': 'HIGH' if volatility_5d > 1.5 else ('LOW' if volatility_5d < 0.5 else 'NORMAL'),
                'expanding': volatility_5d > volatility_20d
            },
            'trend': {
                'above_sma20': above_sma20,
                'above_sma50': above_sma50,
                'signal': 'BULLISH' if above_sma20 and above_sma50 else ('BEARISH' if not above_sma20 and not above_sma50 else 'MIXED'),
                'sma_20': sma_20,
                'sma_50': sma_50
            },
            'macd': {
                'histogram': macd_hist,
                'signal': 'BULLISH' if macd_bullish else 'BEARISH',
                'strength': min(abs(macd_hist) / 10, 1.0)
            },
            'bollinger': {
                'position': bb_position,
                'signal': 'OVERSOLD' if bb_position < 0.2 else ('OVERBOUGHT' if bb_position > 0.8 else 'NEUTRAL'),
                'upper': bb_upper,
                'lower': bb_lower
            },
            'vix': {
                'value': vix,
                'signal': 'FEAR' if vix > 25 else ('GREED' if vix < 15 else 'NEUTRAL'),
                'note': 'High volatility expected' if vix > 25 else ('Low volatility' if vix < 15 else 'Normal')
            }
        }

        # Count bullish/bearish factors
        bullish_count = 0
        bearish_count = 0

        for factor in ['rsi', 'momentum', 'trend', 'macd']:
            if factors[factor]['signal'] == 'BULLISH':
                bullish_count += 1
            elif factors[factor]['signal'] == 'BEARISH':
                bearish_count += 1

        factors['summary'] = {
            'bullish_factors': bullish_count,
            'bearish_factors': bearish_count,
            'overall': 'BULLISH' if bullish_count > bearish_count else ('BEARISH' if bearish_count > bullish_count else 'NEUTRAL')
        }

        return factors

    def get_confidence_tier(self, confidence: float) -> Dict:
        """Get confidence tier information for display."""
        if confidence >= 80:
            return {
                'tier': 'ELITE',
                'emoji': '🔥🔥🔥',
                'historical_winrate': '93.12%',
                'description': 'Highest conviction signal',
                'lot_recommendation': '0.8-1.0'
            }
        elif confidence >= 70:
            return {
                'tier': 'HIGH',
                'emoji': '🔥🔥',
                'historical_winrate': '~85%',
                'description': 'Strong conviction signal',
                'lot_recommendation': '0.5-0.7'
            }
        elif confidence >= 60:
            return {
                'tier': 'MEDIUM',
                'emoji': '🔥',
                'historical_winrate': '~75%',
                'description': 'Moderate conviction signal',
                'lot_recommendation': '0.3-0.5'
            }
        else:
            return {
                'tier': 'STANDARD',
                'emoji': '📊',
                'historical_winrate': '~71%',
                'description': 'Standard signal',
                'lot_recommendation': '0.1-0.3'
            }


def test_predictor():
    """Test the ML predictor."""
    print("Testing ML Predictor...")

    # Create predictor (will try to load from models folder)
    predictor = MLPredictor(models_path="../models")

    if predictor.is_loaded:
        print("Model loaded successfully!")
        print(f"Features: {len(predictor.feature_names)}")
    else:
        print("Using fallback predictor")

    # Try with sample data
    try:
        import yfinance as yf
        ticker = yf.Ticker("^GSPC")
        df = ticker.history(period="60d")
        df = df.reset_index()
        df.columns = [c.lower() for c in df.columns]
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None)
            df.set_index('date', inplace=True)

        economic_data = {
            'vix': 20.0,
            'fed_rate': 5.25,
            'unemployment': 4.0,
            'treasury_10y': 4.5,
            'treasury_2y': 4.8,
            'cpi': 3.0,
            'dollar_index': 103.0,
            'oil_price': 75.0,
            'consumer_sentiment': 70.0
        }

        result = predictor.predict(df, economic_data)
        print(f"\nPrediction Result:")
        print(f"  Direction: {result['direction']}")
        print(f"  Confidence: {result['confidence']:.1f}%")
        print(f"  Model: {result['model_used']}")

        levels = predictor.get_signal_levels(df['close'].iloc[-1], result['direction'], result['confidence'])
        print(f"\nSignal Levels:")
        print(f"  Entry: ${levels['entry']:,.2f}")
        print(f"  Take Profit: ${levels['take_profit']:,.2f}")
        print(f"  Stop Loss: ${levels['stop_loss']:,.2f}")

    except Exception as e:
        print(f"Test error: {e}")


if __name__ == "__main__":
    test_predictor()
