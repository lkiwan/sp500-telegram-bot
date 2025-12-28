# -*- coding: utf-8 -*-
"""
Commentary Engine
=================
Trading Mentor voice for human-like market analysis
"""

import random
from datetime import datetime
from typing import Dict, Optional
from styles import EMOJI, get_hashtags


class TradingMentor:
    """
    Generate Trading Mentor style commentary.

    Voice characteristics:
    - Educational and supportive
    - Conversational and approachable
    - Uses "we" and "us" for community feel
    - Explains concepts clearly
    - Balances optimism with caution
    - Uses trading terminology naturally
    """

    # Greeting templates by time of day
    GREETINGS = {
        'morning': [
            "Good morning, traders! ☀️",
            "Rise and shine, trading family! 🌅",
            "Hey there, early birds! ☕",
            "Morning, everyone! Let's see what the market has for us today! 💪",
            "Good morning, team! Ready to analyze some charts? 📊",
        ],
        'midday': [
            "Hey traders! 👋",
            "What's up, trading family! 📊",
            "Alright, let's check in on the markets! 🎯",
            "Hey everyone! Time for a quick market check! 👀",
        ],
        'afternoon': [
            "Good afternoon, traders! 📈",
            "Hey team, afternoon check-in time! ⏰",
            "Alright folks, let's see where we stand! 💡",
            "Afternoon, everyone! Let's break down what's happening! 🔍",
        ],
        'close': [
            "Alright traders, that's a wrap! 🔔",
            "And that's the closing bell, team! 🛎️",
            "Market's closed, time for our recap! 📋",
            "That's a wrap for today, trading family! 📊",
        ]
    }

    # RSI explanations
    RSI_TEMPLATES = {
        'oversold': [
            "RSI is sitting at {value:.1f} - we're in oversold territory. Historically, we often see buyers stepping in around these levels. Watch for reversal candles! 🔍",
            "With RSI at {value:.1f}, we're pretty stretched to the downside. This doesn't mean 'buy immediately,' but it DOES mean we should watch for signs of a bottom forming. 👀",
            "RSI hitting {value:.1f} - that's oversold, folks. Remember, oversold can get MORE oversold, but this is where smart money often starts looking for entries. 📉",
        ],
        'neutral_low': [
            "RSI at {value:.1f} - we've bounced out of oversold but still have room to run higher. Momentum is building! ⚡",
            "With RSI at {value:.1f}, we're in that recovery zone. Not oversold anymore, but not overbought either. Stay patient! 🎯",
        ],
        'neutral': [
            "RSI sitting at {value:.1f} - right in the middle. The market is taking a breather here. Could go either way! ⚖️",
            "At {value:.1f} RSI, we're in no-man's land. Wait for a clearer signal before making big moves. 🧘",
            "RSI is neutral at {value:.1f}. The market hasn't made up its mind yet. Let's see which way it breaks! 🤔",
        ],
        'neutral_high': [
            "RSI at {value:.1f} shows nice bullish momentum. Still room to run, but keep those stops tight! 📈",
            "With RSI at {value:.1f}, bulls are in control. Ride the trend, but be ready for pullbacks! 🐂",
        ],
        'overbought': [
            "RSI at {value:.1f} - we're in overbought territory now. This doesn't mean 'sell everything,' but maybe lock in some profits! 🎯",
            "Okay, {value:.1f} on the RSI. That's getting stretched. I'd be cautious about chasing here. Wait for a pullback! ⚠️",
            "RSI hitting {value:.1f}. We're overbought, team. Doesn't mean we crash tomorrow, but the risk/reward for new longs isn't ideal. 🤔",
        ]
    }

    # MACD explanations
    MACD_TEMPLATES = {
        'bullish_cross': [
            "MACD just gave us a bullish crossover! 📈 The signal line crossed above - this often precedes upward momentum!",
            "Ooh, bullish MACD cross happening here! This is one of my favorite signals when we see it with good volume! ✨",
            "Nice! MACD bullish crossover in play. When the histogram turns green like this, it's worth paying attention to! 🟢",
        ],
        'bearish_cross': [
            "Heads up - MACD bearish crossover in play. 📉 Signal line crossed below. Time to be more defensive.",
            "MACD giving us a warning with that bearish cross. Doesn't mean panic, but definitely means caution! ⚠️",
            "Bearish MACD crossover here. The histogram turning red tells us momentum is shifting. Stay alert! 🔴",
        ],
        'strong_bullish': [
            "MACD histogram is expanding nicely - bullish momentum is building. Let the trend work for you! 🚀",
            "Look at that MACD histogram grow! Bulls are in control and pushing hard. Ride the wave! 🏄",
        ],
        'strong_bearish': [
            "MACD histogram deepening on the red side - bears are in control right now. Defense mode! 🛡️",
            "The MACD is telling us bears have the upper hand. No need to fight the trend here. ⬇️",
        ],
        'weakening': [
            "MACD histogram starting to shrink - momentum fading. The move might be running out of steam. 🔋",
            "Notice how the MACD histogram is getting smaller? That's often a sign the current move is losing juice. 📊",
        ]
    }

    # Bollinger Band explanations
    BB_TEMPLATES = {
        'upper_band': [
            "Price touching the upper Bollinger Band - we're riding high! Often means overbought in the short term. 📈",
            "Upper BB touch here. The market's running hot! Watch for a potential pullback to the middle band. 🔥",
        ],
        'lower_band': [
            "Price kissing the lower Bollinger Band - that's often a spot where buyers show up! 📉",
            "Lower BB touch. We're getting stretched to the downside. These levels often attract buyers. 👀",
        ],
        'squeeze': [
            "Bollinger Bands are squeezing! Low volatility like this usually precedes a big move. Get ready! ⚡",
            "Notice how tight those Bollinger Bands are? A squeeze like this often leads to an explosive breakout. 💥",
        ],
        'middle': [
            "Price around the middle Bollinger Band - neutral zone here. Waiting for direction! ⚖️",
        ]
    }

    # Trend descriptions
    TREND_TEMPLATES = {
        'strong_bullish': [
            "We're in a solid uptrend here, folks! Price above both the 20 and 50 SMA. Bulls are firmly in charge! 🐂",
            "Strong bullish structure! When price respects those moving averages like this, we ride the trend! 📈",
        ],
        'bullish': [
            "Bullish bias here - price holding above key moving averages. The trend is your friend! 💚",
            "Looking constructive! Price above the 20 SMA. As long as that holds, bulls have the edge. 📊",
        ],
        'neutral': [
            "Market's chopping around here - no clear trend. Sometimes the best trade is no trade! 🧘",
            "Consolidation mode! We're between the MAs. Wait for a clear breakout before committing. ⏳",
        ],
        'bearish': [
            "Bearish structure forming - price below key moving averages. Bears have control for now. 🐻",
            "Downtrend in play. When price stays below the 20 SMA, we need to respect that! 📉",
        ],
        'strong_bearish': [
            "Strong downtrend here, team. Price well below both MAs. Capital preservation is key! 🛡️",
            "Bears are dominating! No need to be a hero here. Wait for signs of a bottom. ⬇️",
        ]
    }

    # Closing thoughts
    CLOSING_THOUGHTS = {
        'bullish': [
            "The technicals look constructive here. Stay disciplined and let the trend work for you! 💪",
            "Bulls have the edge right now. Ride the wave, but always know your exits! 🏄",
            "Keep those trailing stops in place and let the winners run! You've got this! 🎯",
        ],
        'bearish': [
            "Bears have control for now. Focus on capital preservation - better setups will come! 🛡️",
            "Challenging conditions, but that's part of trading. Stay patient and wait for your pitch! ⚾",
            "Not every day is a trading day. Sometimes cash is a position! 💵",
        ],
        'neutral': [
            "Mixed signals today. Sometimes the best trade is no trade. Wait for clarity! 🧘",
            "Market's undecided. Use this time to review your watchlist and plan your next moves! 📝",
            "Choppy waters here. Stay nimble and don't force trades! 🌊",
        ]
    }

    # Signal explanations
    SIGNAL_TEMPLATES = {
        'long': [
            "We've got a LONG setup here! Multiple indicators aligning for a potential move higher. 📈",
            "Bulls are setting up! The technicals are giving us a buy signal. Let's break it down... 🟢",
            "Looking at a potential long entry here. Here's why I like this setup... 💡",
        ],
        'short': [
            "SELL signal flashing! The indicators are suggesting downside pressure ahead. 📉",
            "Bears might be taking over! Here's a short setup forming. Let's analyze... 🔴",
            "Potential short opportunity here. The technicals are turning bearish... ⬇️",
        ]
    }

    def __init__(self):
        self.current_hour = datetime.now().hour

    def get_greeting(self, time_of_day: Optional[str] = None) -> str:
        """Generate appropriate greeting based on time."""
        if time_of_day is None:
            hour = datetime.now().hour
            if hour < 10:
                time_of_day = 'morning'
            elif hour < 14:
                time_of_day = 'midday'
            elif hour < 16:
                time_of_day = 'afternoon'
            else:
                time_of_day = 'close'

        return random.choice(self.GREETINGS.get(time_of_day, self.GREETINGS['midday']))

    def explain_rsi(self, rsi_value: float) -> str:
        """Generate RSI explanation."""
        if rsi_value < 30:
            zone = 'oversold'
        elif rsi_value < 45:
            zone = 'neutral_low'
        elif rsi_value < 55:
            zone = 'neutral'
        elif rsi_value < 70:
            zone = 'neutral_high'
        else:
            zone = 'overbought'

        template = random.choice(self.RSI_TEMPLATES[zone])
        return template.format(value=rsi_value)

    def explain_macd(self, macd: float, signal: float,
                     histogram: float, prev_histogram: float = None) -> str:
        """Generate MACD explanation based on conditions."""
        # Check for crossovers
        if prev_histogram is not None:
            if prev_histogram < 0 and histogram >= 0:
                return random.choice(self.MACD_TEMPLATES['bullish_cross'])
            elif prev_histogram > 0 and histogram <= 0:
                return random.choice(self.MACD_TEMPLATES['bearish_cross'])

        # Check momentum strength
        if histogram > 0:
            if abs(histogram) > abs(prev_histogram or 0):
                return random.choice(self.MACD_TEMPLATES['strong_bullish'])
            else:
                return random.choice(self.MACD_TEMPLATES['weakening'])
        else:
            if abs(histogram) > abs(prev_histogram or 0):
                return random.choice(self.MACD_TEMPLATES['strong_bearish'])
            else:
                return random.choice(self.MACD_TEMPLATES['weakening'])

    def explain_bollinger(self, price: float, upper: float,
                          lower: float, middle: float) -> str:
        """Generate Bollinger Bands explanation."""
        bb_range = upper - lower
        bb_position = (price - lower) / bb_range if bb_range > 0 else 0.5

        # Check for squeeze
        band_width = bb_range / middle if middle > 0 else 0
        if band_width < 0.04:  # Tight bands
            return random.choice(self.BB_TEMPLATES['squeeze'])

        if bb_position > 0.9:
            return random.choice(self.BB_TEMPLATES['upper_band'])
        elif bb_position < 0.1:
            return random.choice(self.BB_TEMPLATES['lower_band'])
        else:
            return random.choice(self.BB_TEMPLATES['middle'])

    def explain_trend(self, price: float, sma_20: float, sma_50: float) -> str:
        """Generate trend explanation based on moving averages."""
        above_20 = price > sma_20
        above_50 = price > sma_50
        sma_20_above_50 = sma_20 > sma_50

        if above_20 and above_50 and sma_20_above_50:
            return random.choice(self.TREND_TEMPLATES['strong_bullish'])
        elif above_20 and above_50:
            return random.choice(self.TREND_TEMPLATES['bullish'])
        elif not above_20 and not above_50 and not sma_20_above_50:
            return random.choice(self.TREND_TEMPLATES['strong_bearish'])
        elif not above_20 and not above_50:
            return random.choice(self.TREND_TEMPLATES['bearish'])
        else:
            return random.choice(self.TREND_TEMPLATES['neutral'])

    def get_closing_thought(self, sentiment: str = 'neutral') -> str:
        """Generate closing thought based on overall sentiment."""
        return random.choice(self.CLOSING_THOUGHTS.get(sentiment,
                            self.CLOSING_THOUGHTS['neutral']))

    def explain_signal(self, direction: str, indicators: Dict) -> str:
        """Generate explanation for a trading signal."""
        parts = []

        # Opening
        if direction.upper() == 'LONG':
            parts.append(random.choice(self.SIGNAL_TEMPLATES['long']))
        else:
            parts.append(random.choice(self.SIGNAL_TEMPLATES['short']))

        parts.append("")

        # RSI explanation
        if 'rsi' in indicators:
            parts.append(self.explain_rsi(indicators['rsi']))

        # MACD explanation
        if 'macd_hist' in indicators:
            parts.append(self.explain_macd(
                indicators.get('macd', 0),
                indicators.get('macd_signal', 0),
                indicators['macd_hist'],
                indicators.get('prev_macd_hist')
            ))

        return '\n'.join(parts)

    def generate_market_summary(self, data: Dict) -> str:
        """Generate complete market summary with Trading Mentor voice."""
        parts = []

        # Greeting
        parts.append(self.get_greeting())
        parts.append("")

        # Price action
        change_pct = data.get('change_pct', 0)
        price = data.get('close', 0)

        if change_pct > 1:
            parts.append(f"{EMOJI['bullish']} <b>Strong day for the S&P!</b> We're up {change_pct:.2f}% at ${price:,.2f}. Bulls are definitely in charge today!")
        elif change_pct > 0:
            parts.append(f"{EMOJI['bullish']} <b>Modest gains today</b> - up {change_pct:.2f}% to ${price:,.2f}. Nothing explosive, but green is green!")
        elif change_pct > -1:
            parts.append(f"{EMOJI['bearish']} <b>Slight pullback today</b>, down {abs(change_pct):.2f}% to ${price:,.2f}. Nothing to panic about - pullbacks are healthy!")
        else:
            parts.append(f"{EMOJI['bearish']} <b>Tough day out there</b> - down {abs(change_pct):.2f}% to ${price:,.2f}. Stay calm and stick to your plan!")

        parts.append("")
        parts.append(f"{EMOJI['chart']} <b>Technical Breakdown:</b>")
        parts.append("")

        # Technical explanations
        if 'rsi' in data:
            parts.append(self.explain_rsi(data['rsi']))
            parts.append("")

        if 'macd_hist' in data:
            parts.append(self.explain_macd(
                data.get('macd', 0),
                data.get('macd_signal', 0),
                data['macd_hist'],
                data.get('prev_macd_hist')
            ))
            parts.append("")

        if all(k in data for k in ['close', 'sma_20', 'sma_50']):
            parts.append(self.explain_trend(
                data['close'], data['sma_20'], data['sma_50']
            ))
            parts.append("")

        # Closing thought
        sentiment = self._determine_sentiment(data)
        parts.append(self.get_closing_thought(sentiment))

        return '\n'.join(parts)

    def _determine_sentiment(self, data: Dict) -> str:
        """Determine overall sentiment from indicators."""
        bullish_signals = 0
        bearish_signals = 0

        # RSI
        rsi = data.get('rsi', 50)
        if rsi < 30:
            bullish_signals += 1  # Oversold = potential bounce
        elif rsi > 70:
            bearish_signals += 1  # Overbought = potential pullback

        # MACD
        macd_hist = data.get('macd_hist', 0)
        if macd_hist > 0:
            bullish_signals += 1
        else:
            bearish_signals += 1

        # Trend
        if data.get('close', 0) > data.get('sma_20', 0):
            bullish_signals += 1
        else:
            bearish_signals += 1

        # Price change
        if data.get('change_pct', 0) > 0:
            bullish_signals += 1
        else:
            bearish_signals += 1

        if bullish_signals >= 3:
            return 'bullish'
        elif bearish_signals >= 3:
            return 'bearish'
        else:
            return 'neutral'


# Post templates
POST_TEMPLATES = {
    'morning_briefing': """
{greeting}

{EMOJI_MORNING} <b>Morning Briefing - {date}</b>

<b>Overnight Recap:</b>
{overnight_summary}

<b>Key Levels to Watch:</b>
• Resistance: {resistance}
• Support: {support}
• Pivot: {pivot}

<b>On the Calendar Today:</b>
{calendar_events}

{mentor_insight}

{hashtags}
""",

    'market_open': """
{greeting}

{EMOJI_BELL} <b>Market Open Analysis</b>

The bell just rang! Here's what I'm seeing:

{opening_analysis}

<b>Opening Stats:</b>
• Open: ${open_price:,.2f}
• Gap: {gap_pct:+.2f}%
• Yesterday Close: ${prev_close:,.2f}

{mentor_insight}

Trade smart, not hard! 💪

{hashtags}
""",

    'signal': """
{EMOJI_SIGNAL} <b>Signal Alert</b>

{direction_emoji} <b>{direction}</b> {ticker}

<b>Entry:</b> <code>${entry:,.2f}</code>
<b>Take Profit:</b> <code>${take_profit:,.2f}</code> ({tp_pct:+.2f}%)
<b>Stop Loss:</b> <code>${stop_loss:,.2f}</code> ({sl_pct:.2f}%)
<b>Risk/Reward:</b> {risk_reward}
<b>Confidence:</b> {confidence:.0f}%

<b>Why this setup:</b>
{setup_explanation}

⚠️ <i>This is educational content, not financial advice. Always do your own research!</i>

{hashtags}
""",

    'market_close': """
{greeting}

{EMOJI_BELL} <b>Market Close Recap - {date}</b>

<b>Final Score:</b>
• Close: <code>${close:,.2f}</code>
• Change: {change:+.2f} ({change_pct:+.2f}%)
• High: <code>${high:,.2f}</code>
• Low: <code>${low:,.2f}</code>

{technical_summary}

<b>Today's Signals:</b>
{signal_performance}

{mentor_closing}

Rest up, traders! See you tomorrow! 🌙

{hashtags}
""",

    'weekly_report': """
{greeting}

{EMOJI_TROPHY} <b>Weekly Performance Report</b>

<b>This Week's Stats:</b>
• Total Trades: {total_trades}
• Win Rate: {win_rate:.1f}%
• Wins/Losses: {wins}/{losses}
• Week P&L: {week_pnl:+.2f}%

<b>Portfolio Update:</b>
• Starting: ${initial:,.2f}
• Current: ${current:,.2f}
• Total Return: {total_return:+.2f}%

<b>Best Trade:</b> {best_trade}
<b>Worst Trade:</b> {worst_trade}

{mentor_insight}

Keep learning, keep growing! See you next week! 💪

{hashtags}
"""
}


def create_mentor() -> TradingMentor:
    """Create and return a TradingMentor instance."""
    return TradingMentor()
