# -*- coding: utf-8 -*-
"""
Chart Styles Configuration
==========================
TradingView Pro Dark Theme for professional trading charts
"""

# TradingView Pro Dark Theme Colors
COLORS = {
    # Background
    'background': '#131722',        # TradingView dark background
    'panel_bg': '#1e222d',          # Panel background
    'foreground': '#d1d4dc',        # Text/axis color
    'grid': '#2a2e39',              # Subtle grid lines

    # Candles
    'candle_up': '#26a69a',         # Teal green (up candles)
    'candle_down': '#ef5350',       # Coral red (down candles)
    'candle_wick_up': '#26a69a',
    'candle_wick_down': '#ef5350',

    # Volume
    'volume_up': '#26a69a80',       # Semi-transparent green
    'volume_down': '#ef535080',     # Semi-transparent red

    # Moving Averages
    'sma_20': '#f7931a',            # Orange (20-day MA)
    'sma_50': '#2962ff',            # Blue (50-day MA)
    'sma_200': '#ab47bc',           # Purple (200-day MA)
    'ema_12': '#ffeb3b',            # Yellow
    'ema_26': '#ff9800',            # Orange

    # Bollinger Bands
    'bollinger': '#9c27b0',         # Purple (distinct from SMAs)
    'bollinger_fill': '#9c27b020',  # Transparent fill

    # RSI
    'rsi_line': '#00e676',          # Neon green
    'rsi_overbought': '#ff5252',    # Red line at 70
    'rsi_oversold': '#69f0ae',      # Green line at 30
    'rsi_middle': '#ffffff30',      # Faint line at 50

    # MACD
    'macd_line': '#26c6da',         # Cyan
    'macd_signal': '#ff7043',       # Orange
    'macd_histogram_pos': '#26a69a',
    'macd_histogram_neg': '#ef5350',

    # VIX Zones
    'vix_extreme_fear': '#f44336',  # Red (VIX > 30)
    'vix_fear': '#ff9800',          # Orange (VIX 25-30)
    'vix_neutral': '#ffeb3b',       # Yellow (VIX 20-25)
    'vix_greed': '#8bc34a',         # Light green (VIX 15-20)
    'vix_extreme_greed': '#4caf50', # Green (VIX < 15)

    # Signals
    'buy_signal': '#00e676',        # Bright green
    'sell_signal': '#ff1744',       # Bright red
    'neutral_signal': '#ffc107',    # Amber

    # Performance
    'profit': '#00e676',            # Green
    'loss': '#ff1744',              # Red
    'breakeven': '#9e9e9e',         # Gray

    # Support/Resistance
    'support': '#4caf50',           # Green
    'resistance': '#f44336',        # Red
    'pivot': '#9c27b0',             # Purple

    # Trend indicators
    'bullish': '#26a69a',
    'bearish': '#ef5350',
    'neutral': '#78909c',

    # Text
    'text_primary': '#ffffff',
    'text_secondary': '#b2b5be',
    'text_muted': '#787b86',
}

# Chart dimensions
CHART_CONFIG = {
    'width': 12,
    'height': 8,
    'dpi': 150,
    'font_family': 'sans-serif',
    'title_size': 14,
    'label_size': 10,
    'tick_size': 9,
}

# Panel ratios for multi-panel charts
PANEL_RATIOS = {
    'price_only': (1,),
    'price_volume': (3, 1),
    'price_volume_rsi': (3, 1, 1),
    'price_volume_rsi_macd': (3, 1, 1, 1),
    'full': (4, 1, 1.2, 1.2),
}

# Emoji mappings for posts
EMOJI = {
    # Direction
    'bullish': '🟢',
    'bearish': '🔴',
    'neutral': '⚪',
    'up': '📈',
    'down': '📉',
    'sideways': '➡️',

    # Time
    'morning': '☀️',
    'midday': '🌤️',
    'afternoon': '🌅',
    'night': '🌙',
    'bell': '🔔',

    # Signals
    'signal': '⚡',
    'alert': '🚨',
    'target': '🎯',
    'stop': '🛑',
    'entry': '📍',

    # Analysis
    'chart': '📊',
    'technical': '📈',
    'fundamental': '🏦',
    'news': '📰',
    'calendar': '📅',
    'economic': '💹',

    # Sentiment
    'fear': '😰',
    'greed': '🤑',
    'neutral_face': '😐',
    'thinking': '🤔',

    # Performance
    'win': '✅',
    'loss': '❌',
    'fire': '🔥',
    'rocket': '🚀',
    'money': '💰',
    'trophy': '🏆',

    # Actions
    'watch': '👀',
    'strong': '💪',
    'wave': '👋',
    'point': '👉',

    # Misc
    'warning': '⚠️',
    'info': 'ℹ️',
    'star': '⭐',
    'gem': '💎',
    'brain': '🧠',
    'lightning': '⚡',
}

# Hashtag sets
HASHTAGS = {
    'always': ['#SP500', '#Trading', '#StockMarket'],
    'signal': ['#TradingSignals', '#TechnicalAnalysis', '#DayTrading'],
    'morning': ['#MorningBriefing', '#PreMarket', '#MarketAnalysis'],
    'open': ['#MarketOpen', '#WallStreet'],
    'close': ['#MarketClose', '#TradingRecap', '#DailyRecap'],
    'weekly': ['#WeeklyReport', '#Performance', '#TradingResults'],
    'economic': ['#Economy', '#FederalReserve', '#MacroEconomics'],
    'sentiment': ['#MarketSentiment', '#FearAndGreed'],
    'technical': ['#TechnicalAnalysis', '#ChartAnalysis', '#PriceAction'],
}

def get_hashtags(post_type: str) -> str:
    """Get formatted hashtag string for a post type."""
    tags = HASHTAGS['always'].copy()
    if post_type in HASHTAGS:
        tags.extend(HASHTAGS[post_type])
    return ' '.join(tags)
