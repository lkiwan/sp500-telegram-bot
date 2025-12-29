# -*- coding: utf-8 -*-
"""
Risk Manager
============
Advanced risk management for professional trading
"""

from datetime import datetime, time
from typing import Dict, Optional, Tuple
import pytz


class RiskManager:
    """Manages all risk-related decisions for trading."""

    def __init__(self):
        self.et_tz = pytz.timezone('US/Eastern')
        self.daily_pnl = 0.0
        self.daily_trades = 0
        self.last_reset_date = None

        # Configuration
        self.MAX_DAILY_LOSS_PCT = -2.0  # Stop trading after -2% daily loss
        self.MAX_DAILY_TRADES = 10  # Max trades per day

    def reset_daily_stats(self):
        """Reset daily statistics at market open."""
        today = datetime.now(self.et_tz).date()
        if self.last_reset_date != today:
            self.daily_pnl = 0.0
            self.daily_trades = 0
            self.last_reset_date = today

    def update_daily_pnl(self, pnl_pct: float):
        """Update daily P&L after a trade closes."""
        self.reset_daily_stats()
        self.daily_pnl += pnl_pct
        self.daily_trades += 1

    def can_trade_daily_limit(self) -> Tuple[bool, str]:
        """Check if we can trade based on daily limits."""
        self.reset_daily_stats()

        if self.daily_pnl <= self.MAX_DAILY_LOSS_PCT:
            return False, f"Daily loss limit hit ({self.daily_pnl:.2f}%)"

        if self.daily_trades >= self.MAX_DAILY_TRADES:
            return False, f"Max daily trades reached ({self.daily_trades})"

        return True, "OK"

    def is_good_trading_time(self) -> Tuple[bool, str]:
        """
        Check if current time is good for trading.

        Bad times:
        - 9:30-9:45 AM ET: Too volatile (market open)
        - 12:00-1:00 PM ET: Low volume (lunch)
        - 3:45-4:00 PM ET: Erratic (market close)

        Good times:
        - 9:45-11:45 AM ET: Morning momentum
        - 1:00-3:45 PM ET: Afternoon session
        """
        now_et = datetime.now(self.et_tz)
        current_time = now_et.time()

        # Market hours check
        market_open = time(9, 30)
        market_close = time(16, 0)

        if current_time < market_open or current_time >= market_close:
            return False, "Market closed"

        # Bad times
        bad_periods = [
            (time(9, 30), time(9, 45), "Market open volatility"),
            (time(12, 0), time(13, 0), "Lunch hour - low volume"),
            (time(15, 45), time(16, 0), "Market close - erratic"),
        ]

        for start, end, reason in bad_periods:
            if start <= current_time < end:
                return False, reason

        return True, "Good trading time"

    def get_dynamic_levels(self, entry_price: float, direction: str,
                           vix: float, atr_pct: float = None) -> Dict:
        """
        Calculate dynamic TP/SL based on VIX and ATR.

        VIX-based adjustments:
        - High volatility (VIX > 25): Wider stops
        - Normal (VIX 15-25): Standard stops
        - Low volatility (VIX < 15): Tighter stops
        """
        # Base percentages
        if vix > 30:
            # Extreme volatility - very wide stops
            tp_pct = 2.0
            sl_pct = 1.0
            partial_tp_pct = 1.0  # First target for partial profit
        elif vix > 25:
            # High volatility
            tp_pct = 1.5
            sl_pct = 0.8
            partial_tp_pct = 0.75
        elif vix > 20:
            # Above normal volatility
            tp_pct = 1.2
            sl_pct = 0.6
            partial_tp_pct = 0.6
        elif vix > 15:
            # Normal volatility
            tp_pct = 1.0
            sl_pct = 0.5
            partial_tp_pct = 0.5
        else:
            # Low volatility - tighter stops
            tp_pct = 0.7
            sl_pct = 0.35
            partial_tp_pct = 0.35

        # If ATR is provided, use it to fine-tune
        if atr_pct and atr_pct > 0:
            # ATR-based adjustment (ATR as % of price)
            atr_multiplier = min(max(atr_pct / 1.0, 0.5), 2.0)  # Clamp between 0.5x and 2x
            tp_pct *= atr_multiplier
            sl_pct *= atr_multiplier
            partial_tp_pct *= atr_multiplier

        # Calculate actual prices
        if direction.upper() == "LONG":
            take_profit = entry_price * (1 + tp_pct / 100)
            stop_loss = entry_price * (1 - sl_pct / 100)
            partial_target = entry_price * (1 + partial_tp_pct / 100)
        else:  # SHORT
            take_profit = entry_price * (1 - tp_pct / 100)
            stop_loss = entry_price * (1 + sl_pct / 100)
            partial_target = entry_price * (1 - partial_tp_pct / 100)

        return {
            'entry': entry_price,
            'take_profit': take_profit,
            'stop_loss': stop_loss,
            'partial_target': partial_target,
            'tp_pct': tp_pct,
            'sl_pct': sl_pct,
            'partial_tp_pct': partial_tp_pct,
            'vix_regime': self._get_vix_regime(vix)
        }

    def _get_vix_regime(self, vix: float) -> str:
        """Get volatility regime description."""
        if vix > 30:
            return "EXTREME"
        elif vix > 25:
            return "HIGH"
        elif vix > 20:
            return "ELEVATED"
        elif vix > 15:
            return "NORMAL"
        else:
            return "LOW"

    def calculate_trailing_stop(self, entry_price: float, current_price: float,
                                current_sl: float, direction: str,
                                atr_pct: float = 0.5) -> Optional[float]:
        """
        Calculate trailing stop loss.

        Rules:
        - When price moves +0.5% in favor → Move SL to entry (break-even)
        - When price moves +0.8% → Move SL to +0.3%
        - When price moves +1.2% → Move SL to +0.7%
        - Always trail by ATR or fixed %
        """
        if direction.upper() == "LONG":
            profit_pct = ((current_price - entry_price) / entry_price) * 100

            if profit_pct >= 1.2:
                # Lock in 0.7% profit
                new_sl = entry_price * 1.007
            elif profit_pct >= 0.8:
                # Lock in 0.3% profit
                new_sl = entry_price * 1.003
            elif profit_pct >= 0.5:
                # Move to break-even
                new_sl = entry_price
            else:
                return None  # No trailing yet

            # Only move SL up, never down
            if new_sl > current_sl:
                return new_sl

        else:  # SHORT
            profit_pct = ((entry_price - current_price) / entry_price) * 100

            if profit_pct >= 1.2:
                new_sl = entry_price * 0.993
            elif profit_pct >= 0.8:
                new_sl = entry_price * 0.997
            elif profit_pct >= 0.5:
                new_sl = entry_price
            else:
                return None

            # Only move SL down for shorts, never up
            if new_sl < current_sl:
                return new_sl

        return None

    def check_volume_confirmation(self, current_volume: float,
                                  avg_volume: float,
                                  min_ratio: float = 0.8) -> Tuple[bool, str]:
        """
        Check if current volume confirms the move.

        Args:
            current_volume: Current period volume
            avg_volume: Average volume (20-day)
            min_ratio: Minimum ratio required (default 0.8 = 80% of average)
        """
        if avg_volume <= 0:
            return True, "No volume data"

        ratio = current_volume / avg_volume

        if ratio >= 1.5:
            return True, f"Strong volume ({ratio:.1f}x average)"
        elif ratio >= 1.0:
            return True, f"Good volume ({ratio:.1f}x average)"
        elif ratio >= min_ratio:
            return True, f"Acceptable volume ({ratio:.1f}x average)"
        else:
            return False, f"Low volume ({ratio:.1f}x average) - avoid trading"

    def check_trend_alignment(self, daily_trend: str, signal_direction: str) -> Tuple[bool, float, str]:
        """
        Check if signal aligns with higher timeframe trend.

        Returns:
            Tuple of (is_aligned, confidence_multiplier, reason)
        """
        if daily_trend.upper() == signal_direction.upper():
            return True, 1.0, f"Aligned with daily trend ({daily_trend})"
        elif daily_trend.upper() == "NEUTRAL":
            return True, 0.9, "Neutral daily trend - proceed with caution"
        else:
            return False, 0.7, f"Against daily trend ({daily_trend}) - weak signal"

    def should_take_partial_profit(self, entry_price: float, current_price: float,
                                   partial_target: float, direction: str,
                                   already_partial: bool = False) -> bool:
        """Check if we should take partial profit."""
        if already_partial:
            return False

        if direction.upper() == "LONG":
            return current_price >= partial_target
        else:  # SHORT
            return current_price <= partial_target


# Global instance
risk_manager = RiskManager()
