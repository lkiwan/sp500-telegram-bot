# -*- coding: utf-8 -*-
"""
Content Database
================
Wisdom quotes, trading theory, historical events for educational posts
"""

import random
from datetime import datetime

# ============================================================================
# TRADING WISDOM QUOTES
# ============================================================================

TRADING_WISDOM = [
    {
        "quote": "The trend is your friend until the end when it bends.",
        "author": "Ed Seykota",
        "lesson": "Always trade with the trend, but watch for signs of reversal. Don't fight the market - let it guide you."
    },
    {
        "quote": "Cut your losses short, let your winners run.",
        "author": "Jesse Livermore",
        "lesson": "The key to long-term success is protecting capital. Small losses are okay - big losses kill accounts."
    },
    {
        "quote": "The market can stay irrational longer than you can stay solvent.",
        "author": "John Maynard Keynes",
        "lesson": "Never bet everything on being 'right'. The market doesn't care about your analysis."
    },
    {
        "quote": "Risk comes from not knowing what you're doing.",
        "author": "Warren Buffett",
        "lesson": "Education reduces risk. The more you understand, the better decisions you make."
    },
    {
        "quote": "The goal of a successful trader is to make the best trades. Money is secondary.",
        "author": "Alexander Elder",
        "lesson": "Focus on the process, not the profits. Good trades lead to good results over time."
    },
    {
        "quote": "In trading, the impossible happens about twice a year.",
        "author": "Henri M Simoes",
        "lesson": "Always expect the unexpected. Black swan events happen - be prepared."
    },
    {
        "quote": "The market is never wrong, opinions often are.",
        "author": "Jesse Livermore",
        "lesson": "Price is truth. Don't argue with the market - adapt to it."
    },
    {
        "quote": "Plan your trade and trade your plan.",
        "author": "Trading Proverb",
        "lesson": "Discipline beats emotion. Have a plan before you enter, and stick to it."
    },
    {
        "quote": "Don't focus on making money; focus on protecting what you have.",
        "author": "Paul Tudor Jones",
        "lesson": "Defense wins championships. Capital preservation is job #1."
    },
    {
        "quote": "It's not whether you're right or wrong, but how much you make when you're right.",
        "author": "George Soros",
        "lesson": "Position sizing matters more than win rate. Make your winners count."
    },
    {
        "quote": "The stock market is filled with individuals who know the price of everything, but the value of nothing.",
        "author": "Philip Fisher",
        "lesson": "Look beyond the numbers. Understand what drives value."
    },
    {
        "quote": "The most important thing in making money is not letting your losses get out of hand.",
        "author": "Marty Schwartz",
        "lesson": "Stop losses aren't optional - they're survival tools."
    },
    {
        "quote": "Amateurs think about how much money they can make. Professionals think about how much they could lose.",
        "author": "Jack Schwager",
        "lesson": "Risk management separates winners from losers."
    },
    {
        "quote": "The hard part is discipline, patience, and judgment.",
        "author": "Seth Klarman",
        "lesson": "Trading is simple but not easy. Master your emotions first."
    },
    {
        "quote": "Win or lose, everybody gets what they want from the market.",
        "author": "Ed Seykota",
        "lesson": "Take responsibility for your results. You control your actions."
    },
    {
        "quote": "Trading is not about being right, it's about making money.",
        "author": "Trading Proverb",
        "lesson": "Let go of your ego. It's okay to be wrong - just be wrong small."
    },
    {
        "quote": "The elements of good trading are: cutting losses, cutting losses, and cutting losses.",
        "author": "Ed Seykota",
        "lesson": "The message is clear - protect your downside at all costs."
    },
    {
        "quote": "Markets are constantly in a state of uncertainty. Money is made by discounting the obvious.",
        "author": "George Soros",
        "lesson": "Don't follow the crowd blindly. Think independently."
    },
    {
        "quote": "The desire to maximize the number of winning trades works against the trader.",
        "author": "William Eckhardt",
        "lesson": "High win rate means nothing if your losers are bigger than winners."
    },
    {
        "quote": "Learn to take losses. The most important thing is to not lose big.",
        "author": "Marty Schwartz",
        "lesson": "Accepting small losses is the path to long-term gains."
    },
]

# ============================================================================
# TRADING THEORY TOPICS
# ============================================================================

TRADING_THEORY = [
    {
        "topic": "Support & Resistance",
        "emoji": "📊",
        "what": "Price levels where buying (support) or selling (resistance) pressure is strong enough to stop the current trend.",
        "how": "Buy near support with stops below. Sell near resistance with stops above. Broken support becomes resistance and vice versa.",
        "tip": "The more times a level is tested, the stronger it becomes - until it breaks!"
    },
    {
        "topic": "RSI (Relative Strength Index)",
        "emoji": "📈",
        "what": "A momentum indicator measuring speed and change of price movements on a 0-100 scale. Above 70 = overbought, below 30 = oversold.",
        "how": "Look for divergences between price and RSI. Oversold in uptrend = buy opportunity. Overbought in downtrend = sell opportunity.",
        "tip": "RSI can stay overbought/oversold for extended periods in strong trends. Use with trend direction!"
    },
    {
        "topic": "MACD (Moving Average Convergence Divergence)",
        "emoji": "📉",
        "what": "A trend-following momentum indicator showing relationship between two moving averages. Consists of MACD line, signal line, and histogram.",
        "how": "Bullish when MACD crosses above signal line. Bearish when it crosses below. Histogram shows momentum strength.",
        "tip": "MACD works best in trending markets. In sideways markets, it gives false signals!"
    },
    {
        "topic": "Moving Averages (SMA & EMA)",
        "emoji": "〰️",
        "what": "SMA = Simple Moving Average (equal weight). EMA = Exponential Moving Average (more weight on recent prices).",
        "how": "Price above MA = bullish bias. Price below MA = bearish bias. Golden Cross (50 crosses above 200) = very bullish.",
        "tip": "Use shorter MAs (20, 50) for entries, longer MAs (100, 200) for overall trend direction."
    },
    {
        "topic": "Bollinger Bands",
        "emoji": "📏",
        "what": "A volatility indicator with 3 lines: middle (20 SMA), upper band (+2 std dev), lower band (-2 std dev).",
        "how": "Price at upper band = potentially overbought. Price at lower band = potentially oversold. Squeeze = big move coming.",
        "tip": "Bollinger Band 'walks' happen in strong trends - price can ride the band for extended periods."
    },
    {
        "topic": "Volume Analysis",
        "emoji": "📊",
        "what": "Volume shows the number of shares traded. High volume confirms moves, low volume suggests weakness.",
        "how": "Breakouts on high volume are more reliable. Reversals on high volume signal real change. Low volume rallies often fail.",
        "tip": "Volume precedes price. Watch for volume spikes before major moves!"
    },
    {
        "topic": "Candlestick Patterns",
        "emoji": "🕯️",
        "what": "Visual representation of price action showing open, high, low, close. Patterns signal potential reversals or continuations.",
        "how": "Hammer/Doji at support = potential reversal. Engulfing patterns signal momentum shifts. Use with other indicators.",
        "tip": "Candlestick patterns work best at key support/resistance levels, not in the middle of nowhere."
    },
    {
        "topic": "Risk/Reward Ratio",
        "emoji": "⚖️",
        "what": "Compares potential profit to potential loss. A 1:2 ratio means risking $1 to make $2.",
        "how": "Only take trades with at least 1:2 risk/reward. This way you can be wrong 50% and still profit.",
        "tip": "Calculate R:R before entering. If it's not favorable, skip the trade!"
    },
    {
        "topic": "Position Sizing",
        "emoji": "💰",
        "what": "How much of your capital to risk on each trade. The key to survival.",
        "how": "Risk 1-2% of account per trade max. If you have $1000, risk $10-20 per trade, not $200.",
        "tip": "Position size = (Account * Risk%) / (Entry - Stop Loss). Calculate it every time!"
    },
    {
        "topic": "Stop Loss Strategies",
        "emoji": "🛑",
        "what": "An order to exit a position at a predetermined price to limit losses.",
        "how": "Place stops below support (longs) or above resistance (shorts). Give room for normal volatility.",
        "tip": "Never move your stop loss further away - that's how small losses become account-killers."
    },
    {
        "topic": "Take Profit Strategies",
        "emoji": "🎯",
        "what": "Predetermined price levels where you lock in profits.",
        "how": "Set TP at resistance levels or based on risk/reward ratio. Consider scaling out (partial profits).",
        "tip": "Trailing stops let winners run while protecting profits. Best of both worlds!"
    },
    {
        "topic": "Market Sentiment",
        "emoji": "🧠",
        "what": "The overall attitude of investors toward the market. Fear or greed drives short-term moves.",
        "how": "Extreme fear = buying opportunity. Extreme greed = caution. Be greedy when others are fearful.",
        "tip": "Sentiment is contrarian - when everyone is bullish, the market often reverses."
    },
    {
        "topic": "VIX (Volatility Index)",
        "emoji": "📈",
        "what": "The 'Fear Gauge' - measures expected S&P 500 volatility. High VIX = fear, Low VIX = complacency.",
        "how": "VIX above 30 = high fear (potential bottom). VIX below 15 = complacency (watch for correction).",
        "tip": "VIX spikes are often short-lived. High VIX can be a buying signal for contrarians."
    },
    {
        "topic": "Trend Lines",
        "emoji": "📐",
        "what": "Lines connecting higher lows (uptrend) or lower highs (downtrend) to visualize trend direction.",
        "how": "Buy bounces off uptrend lines. Sell bounces off downtrend lines. Break of trend line = potential reversal.",
        "tip": "A trend line needs at least 3 touches to be valid. More touches = stronger line."
    },
    {
        "topic": "Fibonacci Retracements",
        "emoji": "🔢",
        "what": "Key levels (23.6%, 38.2%, 50%, 61.8%) where price often pulls back before continuing the trend.",
        "how": "In an uptrend, buy at 38.2% or 61.8% pullbacks. Use with other support/resistance for confirmation.",
        "tip": "The 61.8% level (golden ratio) is the most important Fibonacci level!"
    },
    {
        "topic": "Gap Trading",
        "emoji": "⬆️",
        "what": "Gaps occur when price opens significantly higher or lower than previous close.",
        "how": "Breakaway gaps continue in gap direction. Exhaustion gaps often reverse. Gap fills are common.",
        "tip": "80% of gaps eventually fill - but timing the fill is the hard part!"
    },
    {
        "topic": "Divergence Trading",
        "emoji": "↔️",
        "what": "When price makes a new high/low but the indicator doesn't - signals potential reversal.",
        "how": "Bearish divergence: price higher high, RSI lower high. Bullish divergence: price lower low, RSI higher low.",
        "tip": "Divergence signals weakness but not timing. Wait for price confirmation before acting."
    },
    {
        "topic": "Sector Rotation",
        "emoji": "🔄",
        "what": "Money flows between sectors based on economic cycle. Different sectors lead at different times.",
        "how": "Early cycle: Consumer discretionary, financials. Late cycle: Energy, materials. Recession: Utilities, healthcare.",
        "tip": "Watch sector ETFs (XLF, XLK, XLE) to see where smart money is flowing."
    },
]

# ============================================================================
# HISTORICAL MARKET EVENTS
# ============================================================================

HISTORICAL_EVENTS = [
    {
        "date": "October 19",
        "year": 1987,
        "title": "Black Monday",
        "description": "The Dow Jones crashed 22.6% in a single day - the largest one-day percentage drop in history.",
        "lesson": "Even the worst days end. Those who panic sold missed the recovery. Always have a plan for extreme events."
    },
    {
        "date": "October 29",
        "year": 1929,
        "title": "Black Tuesday",
        "description": "The stock market crash that triggered the Great Depression. The Dow fell 12% in one day.",
        "lesson": "Leverage kills. Many investors were wiped out because they bought on margin. Never risk more than you can afford to lose."
    },
    {
        "date": "March 10",
        "year": 2000,
        "title": "Dot-Com Peak",
        "description": "The Nasdaq hit 5,048 at the peak of the dot-com bubble, then crashed 78% over the next 2 years.",
        "lesson": "Valuations matter eventually. 'This time is different' is the most dangerous phrase in investing."
    },
    {
        "date": "September 15",
        "year": 2008,
        "title": "Lehman Brothers Collapse",
        "description": "Lehman Brothers filed for bankruptcy, triggering the worst financial crisis since the Great Depression.",
        "lesson": "Counterparty risk is real. The market can panic faster than you think. Cash is king in a crisis."
    },
    {
        "date": "March 9",
        "year": 2009,
        "title": "2009 Market Bottom",
        "description": "The S&P 500 hit 666, its lowest point in the financial crisis. What followed was the longest bull market in history.",
        "lesson": "Maximum pessimism = maximum opportunity. The best time to buy is when everyone else is selling."
    },
    {
        "date": "May 6",
        "year": 2010,
        "title": "Flash Crash",
        "description": "The Dow dropped nearly 1,000 points (9%) in minutes, then recovered most losses the same day.",
        "lesson": "Algorithms can amplify volatility. Don't panic on intraday moves. Have stop losses but give them room."
    },
    {
        "date": "August 24",
        "year": 2015,
        "title": "China Crash Spillover",
        "description": "The Dow dropped 1,000 points at the open due to China concerns, but recovered significantly.",
        "lesson": "Global markets are interconnected. What happens overseas affects US markets. Stay informed."
    },
    {
        "date": "June 24",
        "year": 2016,
        "title": "Brexit Vote",
        "description": "UK voted to leave EU, causing the Dow to drop 600 points. Markets recovered within days.",
        "lesson": "Political events cause short-term volatility but rarely change long-term trends. Don't overreact to news."
    },
    {
        "date": "February 5",
        "year": 2018,
        "title": "Volmageddon",
        "description": "The VIX spiked 116% in one day, destroying volatility-selling products and causing a 4% market drop.",
        "lesson": "Complex financial products have hidden risks. Understand what you're trading before you trade it."
    },
    {
        "date": "December 24",
        "year": 2018,
        "title": "Christmas Eve Crash",
        "description": "S&P 500 fell to its lowest Christmas Eve level ever, down 20% from highs. It rallied 30% in 2019.",
        "lesson": "Selling in panic is usually wrong. The market recovered all losses and more within months."
    },
    {
        "date": "March 16",
        "year": 2020,
        "title": "COVID Crash",
        "description": "The Dow dropped 2,997 points (12.9%) - the worst point drop ever - as COVID pandemic fears peaked.",
        "lesson": "Black swans happen. The market fell 34% in 23 days - the fastest bear market ever. But it recovered to new highs."
    },
    {
        "date": "March 23",
        "year": 2020,
        "title": "COVID Bottom",
        "description": "The S&P 500 hit 2,237 - the pandemic low. The Fed announced unlimited QE. Markets never looked back.",
        "lesson": "Never fight the Fed. Central bank intervention can change everything. The bottom felt like the end of the world."
    },
    {
        "date": "January 28",
        "year": 2021,
        "title": "GameStop Squeeze",
        "description": "GME rose from $20 to $483 in days as retail traders squeezed short sellers. Brokers halted trading.",
        "lesson": "Short squeezes are powerful but unpredictable. Don't chase parabolic moves. What goes up fast comes down faster."
    },
]

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_random_wisdom():
    """Get a random trading wisdom quote."""
    return random.choice(TRADING_WISDOM)

def get_random_theory():
    """Get a random trading theory topic."""
    return random.choice(TRADING_THEORY)

def get_random_history():
    """Get a random historical event."""
    return random.choice(HISTORICAL_EVENTS)

def get_wisdom_by_index(index):
    """Get wisdom by index (for daily rotation)."""
    return TRADING_WISDOM[index % len(TRADING_WISDOM)]

def get_theory_by_index(index):
    """Get theory by index (for daily rotation)."""
    return TRADING_THEORY[index % len(TRADING_THEORY)]

def get_history_for_today():
    """Get historical event matching today's date (if any)."""
    today = datetime.now().strftime("%B %d").replace(" 0", " ")
    for event in HISTORICAL_EVENTS:
        if event["date"].lower() in today.lower():
            return event
    return get_random_history()

def get_day_of_year_index():
    """Get index based on day of year for content rotation."""
    return datetime.now().timetuple().tm_yday


# ============================================================================
# GREETINGS AND PHRASES
# ============================================================================

MORNING_GREETINGS = [
    "Good morning, traders! Rise and shine!",
    "Hey traders! New day, new opportunities!",
    "Good morning, trading family! Let's get it!",
    "Rise and grind, traders! Markets await!",
    "Morning, everyone! Ready to trade?",
    "Hey there! Another day to learn and earn!",
    "Good morning! Let's make today count!",
    "Wake up, traders! The market is calling!",
]

NIGHT_GREETINGS = [
    "Good night, traders! Rest up!",
    "That's a wrap! Sweet dreams and green candles!",
    "Night, everyone! Tomorrow is a new opportunity!",
    "Rest well, traders! You earned it!",
    "Good night! See you at market open!",
    "Time to recharge! Great work today!",
]

ENCOURAGEMENT_PHRASES = [
    "Stay disciplined!",
    "Trust the process!",
    "Let's get this bread!",
    "Keep learning, keep growing!",
    "One trade at a time!",
    "Patience pays off!",
    "Stay focused!",
    "We've got this!",
]

WIN_PHRASES = [
    "That's how it's done!",
    "Nailed it! Great trade!",
    "This is what discipline looks like!",
    "Another one in the books!",
    "Clean execution!",
    "The plan worked perfectly!",
]

LOSS_PHRASES = [
    "It happens to the best of us.",
    "That's why we have stop losses.",
    "Every loss is a lesson.",
    "Stay strong - the next winner is coming!",
    "Risk managed, no big deal.",
    "Part of the game. We move on!",
]

def get_morning_greeting():
    return random.choice(MORNING_GREETINGS)

def get_night_greeting():
    return random.choice(NIGHT_GREETINGS)

def get_encouragement():
    return random.choice(ENCOURAGEMENT_PHRASES)

def get_win_phrase():
    return random.choice(WIN_PHRASES)

def get_loss_phrase():
    return random.choice(LOSS_PHRASES)
