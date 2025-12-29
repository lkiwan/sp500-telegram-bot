# -*- coding: utf-8 -*-
"""
Backtester
==========
Backtest the S&P 500 trading strategy on historical data
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import json
import os

# Try to import visualization libraries
try:
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


class Trade:
    """Represents a single trade in the backtest."""

    def __init__(self, entry_date: datetime, direction: str, entry_price: float,
                 take_profit: float, stop_loss: float, confidence: float,
                 partial_target: float = None, vix_regime: str = "NORMAL"):
        self.entry_date = entry_date
        self.direction = direction
        self.entry_price = entry_price
        self.take_profit = take_profit
        self.stop_loss = stop_loss
        self.original_sl = stop_loss
        self.confidence = confidence
        self.partial_target = partial_target
        self.vix_regime = vix_regime

        self.exit_date = None
        self.exit_price = None
        self.exit_reason = None
        self.pnl_pct = None
        self.partial_taken = False
        self.trailing_active = False

    def to_dict(self) -> Dict:
        return {
            'entry_date': self.entry_date.isoformat() if self.entry_date else None,
            'exit_date': self.exit_date.isoformat() if self.exit_date else None,
            'direction': self.direction,
            'entry_price': self.entry_price,
            'exit_price': self.exit_price,
            'take_profit': self.take_profit,
            'stop_loss': self.stop_loss,
            'confidence': self.confidence,
            'exit_reason': self.exit_reason,
            'pnl_pct': self.pnl_pct,
            'vix_regime': self.vix_regime,
            'partial_taken': self.partial_taken
        }


class Backtester:
    """Backtest trading strategy on historical data."""

    def __init__(self, initial_capital: float = 1000.0):
        self.initial_capital = initial_capital
        self.capital = initial_capital
        self.trades: List[Trade] = []
        self.open_trades: List[Trade] = []
        self.equity_curve: List[Tuple[datetime, float]] = []
        self.daily_pnl: Dict[str, float] = {}

        # Configuration - Trust the model (71% win rate)
        self.MAX_OPEN_TRADES = 5
        self.MIN_CONFIDENCE = 70  # Lowered to match model's win rate
        self.MAX_DAILY_LOSS_PCT = -2.0
        self.MAX_DAILY_TRADES = 10
        self.USE_STRICT_FILTERS = False  # Disabled - trust the model

        # VIX-based TP/SL settings
        self.VIX_LEVELS = {
            'EXTREME': {'tp': 2.0, 'sl': 1.0, 'partial': 1.0, 'vix_min': 30},
            'HIGH': {'tp': 1.5, 'sl': 0.8, 'partial': 0.75, 'vix_min': 25},
            'ELEVATED': {'tp': 1.2, 'sl': 0.6, 'partial': 0.6, 'vix_min': 20},
            'NORMAL': {'tp': 1.0, 'sl': 0.5, 'partial': 0.5, 'vix_min': 15},
            'LOW': {'tp': 0.7, 'sl': 0.35, 'partial': 0.35, 'vix_min': 0}
        }

        # Trailing stop levels
        self.TRAILING_LEVELS = [
            (1.2, 0.7),   # At +1.2% profit, lock in 0.7%
            (0.8, 0.3),   # At +0.8% profit, lock in 0.3%
            (0.5, 0.0),   # At +0.5% profit, move to break-even
        ]

    def get_vix_regime(self, vix: float) -> str:
        """Get volatility regime based on VIX."""
        if vix > 30:
            return 'EXTREME'
        elif vix > 25:
            return 'HIGH'
        elif vix > 20:
            return 'ELEVATED'
        elif vix > 15:
            return 'NORMAL'
        else:
            return 'LOW'

    def get_dynamic_levels(self, entry_price: float, direction: str, vix: float) -> Dict:
        """Calculate dynamic TP/SL based on VIX."""
        regime = self.get_vix_regime(vix)
        levels = self.VIX_LEVELS[regime]

        tp_pct = levels['tp']
        sl_pct = levels['sl']
        partial_pct = levels['partial']

        if direction == "LONG":
            take_profit = entry_price * (1 + tp_pct / 100)
            stop_loss = entry_price * (1 - sl_pct / 100)
            partial_target = entry_price * (1 + partial_pct / 100)
        else:
            take_profit = entry_price * (1 - tp_pct / 100)
            stop_loss = entry_price * (1 + sl_pct / 100)
            partial_target = entry_price * (1 - partial_pct / 100)

        return {
            'take_profit': take_profit,
            'stop_loss': stop_loss,
            'partial_target': partial_target,
            'tp_pct': tp_pct,
            'sl_pct': sl_pct,
            'regime': regime
        }

    def calculate_trailing_stop(self, trade: Trade, current_price: float) -> Optional[float]:
        """Calculate trailing stop based on profit."""
        entry = trade.entry_price
        current_sl = trade.stop_loss

        if trade.direction == "LONG":
            profit_pct = ((current_price - entry) / entry) * 100

            for trigger_pct, lock_pct in self.TRAILING_LEVELS:
                if profit_pct >= trigger_pct:
                    new_sl = entry * (1 + lock_pct / 100)
                    if new_sl > current_sl:
                        return new_sl
                    break
        else:  # SHORT
            profit_pct = ((entry - current_price) / entry) * 100

            for trigger_pct, lock_pct in self.TRAILING_LEVELS:
                if profit_pct >= trigger_pct:
                    new_sl = entry * (1 - lock_pct / 100)
                    if new_sl < current_sl:
                        return new_sl
                    break

        return None

    def is_good_trading_time(self, timestamp: datetime) -> bool:
        """Check if it's a good trading time (avoid bad hours)."""
        hour = timestamp.hour
        minute = timestamp.minute
        time_decimal = hour + minute / 60

        # Bad times (in ET, assuming data is in ET)
        bad_periods = [
            (9.5, 9.75),    # 9:30-9:45 AM - market open
            (12.0, 13.0),   # 12:00-1:00 PM - lunch
            (15.75, 16.0),  # 3:45-4:00 PM - market close
        ]

        for start, end in bad_periods:
            if start <= time_decimal < end:
                return False

        return True

    def check_volume(self, current_volume: float, avg_volume: float) -> bool:
        """Check if volume confirms the move (80% of average)."""
        if avg_volume <= 0:
            return True
        return current_volume >= avg_volume * 0.8

    def check_trend_alignment(self, price: float, sma50: float, direction: str) -> Tuple[bool, float]:
        """Check if signal aligns with daily trend."""
        if price > sma50:
            daily_trend = "LONG"
        elif price < sma50:
            daily_trend = "SHORT"
        else:
            daily_trend = "NEUTRAL"

        if daily_trend == direction:
            return True, 1.0
        elif daily_trend == "NEUTRAL":
            return True, 0.9
        else:
            return False, 0.7

    def get_lot_size(self, confidence: float) -> float:
        """Get position size based on confidence."""
        if confidence < 55:
            return 0.1
        elif confidence < 60:
            return 0.2
        elif confidence < 65:
            return 0.3
        elif confidence < 70:
            return 0.4
        elif confidence < 75:
            return 0.5
        elif confidence < 80:
            return 0.6
        elif confidence < 85:
            return 0.7
        elif confidence < 90:
            return 0.8
        elif confidence < 95:
            return 0.9
        else:
            return 1.0

    def can_open_trade(self, date: datetime) -> Tuple[bool, str]:
        """Check if we can open a new trade."""
        # Max open trades
        if len(self.open_trades) >= self.MAX_OPEN_TRADES:
            return False, f"Max {self.MAX_OPEN_TRADES} open trades"

        # Daily loss limit
        date_str = date.strftime('%Y-%m-%d')
        daily_pnl = self.daily_pnl.get(date_str, 0.0)
        if daily_pnl <= self.MAX_DAILY_LOSS_PCT:
            return False, f"Daily loss limit hit ({daily_pnl:.2f}%)"

        # Count today's trades
        today_trades = sum(1 for t in self.trades
                         if t.entry_date.strftime('%Y-%m-%d') == date_str)
        if today_trades >= self.MAX_DAILY_TRADES:
            return False, f"Max {self.MAX_DAILY_TRADES} daily trades"

        return True, "OK"

    def open_trade(self, date: datetime, direction: str, price: float,
                   confidence: float, vix: float) -> Optional[Trade]:
        """Open a new trade."""
        can_trade, reason = self.can_open_trade(date)
        if not can_trade:
            return None

        levels = self.get_dynamic_levels(price, direction, vix)

        trade = Trade(
            entry_date=date,
            direction=direction,
            entry_price=price,
            take_profit=levels['take_profit'],
            stop_loss=levels['stop_loss'],
            confidence=confidence,
            partial_target=levels['partial_target'],
            vix_regime=levels['regime']
        )

        self.open_trades.append(trade)
        return trade

    def close_trade(self, trade: Trade, date: datetime, price: float, reason: str):
        """Close a trade and update capital."""
        trade.exit_date = date
        trade.exit_price = price
        trade.exit_reason = reason

        # Calculate P&L
        if trade.direction == "LONG":
            trade.pnl_pct = ((price - trade.entry_price) / trade.entry_price) * 100
        else:
            trade.pnl_pct = ((trade.entry_price - price) / trade.entry_price) * 100

        # Adjust for partial profit if taken
        if trade.partial_taken:
            trade.pnl_pct = trade.pnl_pct * 0.5  # Only 50% of position remaining

        # Update capital
        lot_size = self.get_lot_size(trade.confidence)
        position_value = self.capital * lot_size
        pnl_dollar = position_value * (trade.pnl_pct / 100)
        self.capital += pnl_dollar

        # Update daily P&L
        date_str = date.strftime('%Y-%m-%d')
        if date_str not in self.daily_pnl:
            self.daily_pnl[date_str] = 0.0
        self.daily_pnl[date_str] += trade.pnl_pct

        # Move from open to closed
        if trade in self.open_trades:
            self.open_trades.remove(trade)
        self.trades.append(trade)

    def update_trades(self, date: datetime, high: float, low: float, close: float):
        """Update all open trades with current price action."""
        trades_to_close = []

        for trade in self.open_trades:
            # Check trailing stop
            new_sl = self.calculate_trailing_stop(trade, close)
            if new_sl:
                trade.stop_loss = new_sl
                trade.trailing_active = True

            # Check partial profit
            if not trade.partial_taken and trade.partial_target:
                if trade.direction == "LONG" and high >= trade.partial_target:
                    trade.partial_taken = True
                    trade.stop_loss = trade.entry_price  # Move to break-even
                elif trade.direction == "SHORT" and low <= trade.partial_target:
                    trade.partial_taken = True
                    trade.stop_loss = trade.entry_price

            # Check TP/SL hits
            if trade.direction == "LONG":
                if high >= trade.take_profit:
                    trades_to_close.append((trade, trade.take_profit, "TP_HIT"))
                elif low <= trade.stop_loss:
                    trades_to_close.append((trade, trade.stop_loss, "SL_HIT"))
            else:  # SHORT
                if low <= trade.take_profit:
                    trades_to_close.append((trade, trade.take_profit, "TP_HIT"))
                elif high >= trade.stop_loss:
                    trades_to_close.append((trade, trade.stop_loss, "SL_HIT"))

        # Close trades
        for trade, exit_price, reason in trades_to_close:
            self.close_trade(trade, date, exit_price, reason)

        # Record equity
        self.equity_curve.append((date, self.capital))

    def run_backtest(self, data: pd.DataFrame, predictions: pd.DataFrame) -> Dict:
        """
        Run the backtest.

        Args:
            data: DataFrame with columns: date, open, high, low, close, volume, vix, sma50
            predictions: DataFrame with columns: date, direction, confidence

        Returns:
            Dictionary with backtest results
        """
        print("Starting backtest...")
        print(f"Initial capital: ${self.initial_capital:,.2f}")
        print(f"Data period: {data.index[0]} to {data.index[-1]}")
        print(f"Total bars: {len(data)}")
        print("-" * 50)

        self.capital = self.initial_capital
        self.trades = []
        self.open_trades = []
        self.equity_curve = [(data.index[0], self.initial_capital)]
        self.daily_pnl = {}

        # Merge data with predictions
        for idx, row in data.iterrows():
            date = idx if isinstance(idx, datetime) else pd.to_datetime(idx)

            # Get prediction for this date
            if date in predictions.index:
                pred = predictions.loc[date]
                direction = pred.get('direction', None)
                confidence = pred.get('confidence', 0)
            else:
                direction = None
                confidence = 0

            # Update existing trades
            self.update_trades(
                date=date,
                high=row['high'],
                low=row['low'],
                close=row['close']
            )

            # Check for new signal
            if direction and confidence >= self.MIN_CONFIDENCE:
                vix = row.get('vix', 20)

                # Only apply strict filters if enabled
                if self.USE_STRICT_FILTERS:
                    volume = row.get('volume', 0)
                    avg_volume = row.get('avg_volume', volume)
                    sma50 = row.get('sma50', row['close'])

                    # Volume check
                    if not self.check_volume(volume, avg_volume):
                        continue

                    # Trend alignment
                    aligned, multiplier = self.check_trend_alignment(row['close'], sma50, direction)
                    adjusted_confidence = confidence * multiplier

                    if adjusted_confidence < self.MIN_CONFIDENCE:
                        continue

                # Open trade - trust the model
                trade = self.open_trade(
                    date=date,
                    direction=direction,
                    price=row['close'],
                    confidence=confidence,
                    vix=vix
                )

                if trade:
                    print(f"{date.strftime('%Y-%m-%d')}: {direction} @ ${row['close']:,.2f} "
                          f"(Conf: {confidence:.0f}%, VIX: {vix:.1f} - {trade.vix_regime})")

        # Close any remaining open trades at last price
        last_row = data.iloc[-1]
        last_date = data.index[-1]
        for trade in self.open_trades[:]:
            self.close_trade(trade, last_date, last_row['close'], "END_OF_TEST")

        # Calculate results
        results = self.calculate_results()

        print("-" * 50)
        print("Backtest complete!")

        return results

    def calculate_results(self) -> Dict:
        """Calculate backtest performance metrics."""
        if not self.trades:
            return {'error': 'No trades executed'}

        # Basic stats
        total_trades = len(self.trades)
        wins = [t for t in self.trades if t.pnl_pct > 0]
        losses = [t for t in self.trades if t.pnl_pct <= 0]

        win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0

        # P&L stats
        total_pnl_pct = sum(t.pnl_pct for t in self.trades)
        avg_pnl = total_pnl_pct / total_trades if total_trades > 0 else 0
        avg_win = np.mean([t.pnl_pct for t in wins]) if wins else 0
        avg_loss = np.mean([t.pnl_pct for t in losses]) if losses else 0

        # Best/worst trades
        best_trade = max(self.trades, key=lambda t: t.pnl_pct)
        worst_trade = min(self.trades, key=lambda t: t.pnl_pct)

        # Profit factor
        gross_profit = sum(t.pnl_pct for t in wins)
        gross_loss = abs(sum(t.pnl_pct for t in losses))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')

        # Equity curve analysis
        equity_values = [e[1] for e in self.equity_curve]

        # Maximum drawdown
        peak = equity_values[0]
        max_drawdown = 0
        for value in equity_values:
            if value > peak:
                peak = value
            drawdown = (peak - value) / peak * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # Total return
        total_return = ((self.capital - self.initial_capital) / self.initial_capital) * 100

        # Sharpe ratio (simplified, assuming 252 trading days)
        if len(self.trades) > 1:
            returns = [t.pnl_pct for t in self.trades]
            sharpe = (np.mean(returns) / np.std(returns)) * np.sqrt(252) if np.std(returns) > 0 else 0
        else:
            sharpe = 0

        # Win/loss streaks
        current_streak = 0
        best_streak = 0
        worst_streak = 0

        for trade in self.trades:
            if trade.pnl_pct > 0:
                if current_streak >= 0:
                    current_streak += 1
                else:
                    current_streak = 1
                best_streak = max(best_streak, current_streak)
            else:
                if current_streak <= 0:
                    current_streak -= 1
                else:
                    current_streak = -1
                worst_streak = min(worst_streak, current_streak)

        # By VIX regime
        regime_stats = {}
        for regime in ['EXTREME', 'HIGH', 'ELEVATED', 'NORMAL', 'LOW']:
            regime_trades = [t for t in self.trades if t.vix_regime == regime]
            if regime_trades:
                regime_wins = len([t for t in regime_trades if t.pnl_pct > 0])
                regime_stats[regime] = {
                    'trades': len(regime_trades),
                    'win_rate': regime_wins / len(regime_trades) * 100,
                    'total_pnl': sum(t.pnl_pct for t in regime_trades)
                }

        # Exit reason analysis
        exit_stats = {}
        for reason in ['TP_HIT', 'SL_HIT', 'END_OF_TEST']:
            reason_trades = [t for t in self.trades if t.exit_reason == reason]
            if reason_trades:
                exit_stats[reason] = {
                    'count': len(reason_trades),
                    'avg_pnl': np.mean([t.pnl_pct for t in reason_trades])
                }

        return {
            'summary': {
                'initial_capital': self.initial_capital,
                'final_capital': self.capital,
                'total_return_pct': total_return,
                'total_trades': total_trades,
                'wins': len(wins),
                'losses': len(losses),
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'sharpe_ratio': sharpe,
                'max_drawdown_pct': max_drawdown
            },
            'pnl': {
                'total_pnl_pct': total_pnl_pct,
                'avg_pnl_pct': avg_pnl,
                'avg_win_pct': avg_win,
                'avg_loss_pct': avg_loss,
                'best_trade_pct': best_trade.pnl_pct,
                'worst_trade_pct': worst_trade.pnl_pct,
                'gross_profit_pct': gross_profit,
                'gross_loss_pct': gross_loss
            },
            'streaks': {
                'best_win_streak': best_streak,
                'worst_loss_streak': abs(worst_streak)
            },
            'by_regime': regime_stats,
            'by_exit': exit_stats,
            'equity_curve': self.equity_curve,
            'trades': [t.to_dict() for t in self.trades]
        }

    def print_results(self, results: Dict):
        """Print formatted backtest results."""
        if 'error' in results:
            print(f"Error: {results['error']}")
            return

        s = results['summary']
        p = results['pnl']

        print("\n" + "=" * 60)
        print("                    BACKTEST RESULTS")
        print("=" * 60)

        print(f"\n{'PORTFOLIO PERFORMANCE':^60}")
        print("-" * 60)
        print(f"Initial Capital:      ${s['initial_capital']:>15,.2f}")
        print(f"Final Capital:        ${s['final_capital']:>15,.2f}")
        print(f"Total Return:         {s['total_return_pct']:>15.2f}%")
        print(f"Max Drawdown:         {s['max_drawdown_pct']:>15.2f}%")
        print(f"Sharpe Ratio:         {s['sharpe_ratio']:>15.2f}")

        print(f"\n{'TRADE STATISTICS':^60}")
        print("-" * 60)
        print(f"Total Trades:         {s['total_trades']:>15}")
        print(f"Winning Trades:       {s['wins']:>15}")
        print(f"Losing Trades:        {s['losses']:>15}")
        print(f"Win Rate:             {s['win_rate']:>14.1f}%")
        print(f"Profit Factor:        {s['profit_factor']:>15.2f}")

        print(f"\n{'P&L ANALYSIS':^60}")
        print("-" * 60)
        print(f"Total P&L:            {p['total_pnl_pct']:>14.2f}%")
        print(f"Average Trade:        {p['avg_pnl_pct']:>14.2f}%")
        print(f"Average Win:          {p['avg_win_pct']:>14.2f}%")
        print(f"Average Loss:         {p['avg_loss_pct']:>14.2f}%")
        print(f"Best Trade:           {p['best_trade_pct']:>14.2f}%")
        print(f"Worst Trade:          {p['worst_trade_pct']:>14.2f}%")

        print(f"\n{'STREAKS':^60}")
        print("-" * 60)
        print(f"Best Win Streak:      {results['streaks']['best_win_streak']:>15}")
        print(f"Worst Loss Streak:    {results['streaks']['worst_loss_streak']:>15}")

        if results['by_regime']:
            print(f"\n{'PERFORMANCE BY VIX REGIME':^60}")
            print("-" * 60)
            for regime, stats in results['by_regime'].items():
                print(f"{regime:12} | Trades: {stats['trades']:3} | "
                      f"Win Rate: {stats['win_rate']:5.1f}% | "
                      f"P&L: {stats['total_pnl']:+6.2f}%")

        if results['by_exit']:
            print(f"\n{'EXIT REASON ANALYSIS':^60}")
            print("-" * 60)
            for reason, stats in results['by_exit'].items():
                print(f"{reason:12} | Count: {stats['count']:3} | "
                      f"Avg P&L: {stats['avg_pnl']:+6.2f}%")

        print("\n" + "=" * 60)

    def plot_results(self, results: Dict, save_path: str = None):
        """Generate performance charts."""
        if not HAS_MATPLOTLIB:
            print("Matplotlib not available for charts")
            return

        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('Backtest Results', fontsize=14, fontweight='bold')

        # 1. Equity Curve
        ax1 = axes[0, 0]
        dates = [e[0] for e in results['equity_curve']]
        values = [e[1] for e in results['equity_curve']]
        ax1.plot(dates, values, 'b-', linewidth=1.5)
        ax1.axhline(y=self.initial_capital, color='gray', linestyle='--', alpha=0.7)
        ax1.fill_between(dates, self.initial_capital, values,
                         where=[v >= self.initial_capital for v in values],
                         color='green', alpha=0.3)
        ax1.fill_between(dates, self.initial_capital, values,
                         where=[v < self.initial_capital for v in values],
                         color='red', alpha=0.3)
        ax1.set_title('Equity Curve')
        ax1.set_ylabel('Capital ($)')
        ax1.grid(True, alpha=0.3)

        # 2. Trade P&L Distribution
        ax2 = axes[0, 1]
        pnls = [t['pnl_pct'] for t in results['trades']]
        colors = ['green' if p > 0 else 'red' for p in pnls]
        ax2.bar(range(len(pnls)), pnls, color=colors, alpha=0.7)
        ax2.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
        ax2.set_title('Trade P&L Distribution')
        ax2.set_xlabel('Trade #')
        ax2.set_ylabel('P&L (%)')
        ax2.grid(True, alpha=0.3)

        # 3. Win Rate Pie Chart
        ax3 = axes[1, 0]
        wins = results['summary']['wins']
        losses = results['summary']['losses']
        ax3.pie([wins, losses], labels=['Wins', 'Losses'],
                colors=['#26a69a', '#ef5350'], autopct='%1.1f%%',
                startangle=90)
        ax3.set_title(f"Win Rate: {results['summary']['win_rate']:.1f}%")

        # 4. Performance by VIX Regime
        ax4 = axes[1, 1]
        if results['by_regime']:
            regimes = list(results['by_regime'].keys())
            win_rates = [results['by_regime'][r]['win_rate'] for r in regimes]
            colors = ['#ff6b6b' if r in ['EXTREME', 'HIGH'] else
                     '#ffd93d' if r == 'ELEVATED' else '#6bcb77'
                     for r in regimes]
            bars = ax4.bar(regimes, win_rates, color=colors, alpha=0.8)
            ax4.axhline(y=50, color='gray', linestyle='--', alpha=0.7)
            ax4.set_title('Win Rate by VIX Regime')
            ax4.set_ylabel('Win Rate (%)')
            ax4.set_ylim(0, 100)

            # Add trade counts on bars
            for bar, regime in zip(bars, regimes):
                count = results['by_regime'][regime]['trades']
                ax4.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                        f'n={count}', ha='center', va='bottom', fontsize=9)

        plt.tight_layout()

        if save_path:
            plt.savefig(save_path, dpi=150, bbox_inches='tight')
            print(f"Chart saved to {save_path}")
        else:
            plt.show()

        plt.close()

    def save_results(self, results: Dict, filepath: str):
        """Save results to JSON file."""
        # Convert datetime objects for JSON serialization
        output = results.copy()
        output['equity_curve'] = [(d.isoformat(), v) for d, v in results['equity_curve']]

        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2, default=str)

        print(f"Results saved to {filepath}")


def prepare_backtest_data(days: int = 365, use_ml_model: bool = True) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Prepare historical data for backtesting.

    Args:
        days: Number of days of historical data
        use_ml_model: If True, use actual ML model; if False, use simulated predictions

    Returns:
        Tuple of (market_data, predictions)
    """
    import yfinance as yf

    print(f"Downloading {days} days of historical data...")

    # Download S&P 500 data
    spy = yf.Ticker("^GSPC")
    data = spy.history(period=f"{days}d")

    if data.empty:
        raise ValueError("Could not download market data")

    # Download VIX data
    vix = yf.Ticker("^VIX")
    vix_data = vix.history(period=f"{days}d")

    # Prepare market data
    data.columns = [c.lower() for c in data.columns]

    # Fix timezone alignment for VIX data
    if not vix_data.empty:
        # Normalize both indices to date only (remove time and timezone)
        data_dates = data.index.normalize().tz_localize(None)
        vix_dates = vix_data.index.normalize().tz_localize(None)

        # Create VIX series with normalized dates
        vix_series = pd.Series(vix_data['Close'].values, index=vix_dates)

        # Map VIX values to S&P data by date
        data['vix'] = data_dates.map(lambda d: vix_series.get(d, 20.0))

        # Fill any remaining NaN with forward fill then default
        data['vix'] = data['vix'].ffill().fillna(20.0)

        print(f"VIX data merged: {(data['vix'] != 20.0).sum()}/{len(data)} days with real VIX")
    else:
        data['vix'] = 20.0
        print("WARNING: No VIX data available, using default 20.0")
    data['sma50'] = data['close'].rolling(50).mean()
    data['sma20'] = data['close'].rolling(20).mean()
    data['avg_volume'] = data['volume'].rolling(20).mean()

    # Calculate RSI
    delta = data['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    data['rsi'] = 100 - (100 / (1 + rs))

    # Calculate MACD
    ema12 = data['close'].ewm(span=12).mean()
    ema26 = data['close'].ewm(span=26).mean()
    data['macd'] = ema12 - ema26
    data['macd_signal'] = data['macd'].ewm(span=9).mean()

    # Generate predictions
    predictions = pd.DataFrame(index=data.index)

    if use_ml_model:
        # Try to use actual ML model
        try:
            from ml_predictor import MLPredictor
            ml_predictor = MLPredictor(models_path="models")
            print("Using actual ML model for predictions...")

            for i, idx in enumerate(data.index):
                if i < 50:  # Need enough data for indicators
                    predictions.loc[idx, 'direction'] = None
                    predictions.loc[idx, 'confidence'] = 0
                    continue

                # Get historical slice up to this point
                hist_data = data.iloc[:i+1].copy()

                # Create economic data dict
                vix_val = data.loc[idx, 'vix'] if not pd.isna(data.loc[idx, 'vix']) else 20.0
                economic_data = {'vix': vix_val, 'fear_greed': 50, 'fed_rate': 5.0, 'unemployment': 4.0}

                try:
                    prediction = ml_predictor.predict(hist_data, economic_data)
                    predictions.loc[idx, 'direction'] = prediction['direction']
                    predictions.loc[idx, 'confidence'] = prediction['confidence']
                except Exception as e:
                    predictions.loc[idx, 'direction'] = None
                    predictions.loc[idx, 'confidence'] = 0

                # Progress indicator
                if (i + 1) % 50 == 0:
                    print(f"  Processed {i+1}/{len(data)} bars...")

        except ImportError:
            print("ML model not available, using simulated predictions...")
            use_ml_model = False

    if not use_ml_model:
        # Fallback: Simple signal logic (simulating ML model)
        print("Using simulated predictions...")
        for idx in data.index:
            row = data.loc[idx]

            # Skip if not enough data
            if pd.isna(row['sma50']) or pd.isna(row['rsi']):
                predictions.loc[idx, 'direction'] = None
                predictions.loc[idx, 'confidence'] = 0
                continue

            bullish_score = 0
            bearish_score = 0

            # RSI
            if row['rsi'] < 30:
                bullish_score += 25
            elif row['rsi'] < 40:
                bullish_score += 15
            elif row['rsi'] > 70:
                bearish_score += 25
            elif row['rsi'] > 60:
                bearish_score += 15

            # MACD
            if row['macd'] > row['macd_signal']:
                bullish_score += 20
            else:
                bearish_score += 20

            # Trend
            if row['close'] > row['sma20'] > row['sma50']:
                bullish_score += 25
            elif row['close'] < row['sma20'] < row['sma50']:
                bearish_score += 25
            elif row['close'] > row['sma20']:
                bullish_score += 15
            elif row['close'] < row['sma20']:
                bearish_score += 15

            # VIX
            vix_val = row['vix'] if not pd.isna(row['vix']) else 20
            if vix_val > 25:
                if row['rsi'] < 35:
                    bullish_score += 20
            elif vix_val < 15:
                if row['close'] > row['sma20']:
                    bullish_score += 10
                else:
                    bearish_score += 10

            # Determine direction and confidence
            total_score = bullish_score + bearish_score
            if total_score > 0:
                if bullish_score > bearish_score:
                    predictions.loc[idx, 'direction'] = 'LONG'
                    predictions.loc[idx, 'confidence'] = min(50 + bullish_score, 95)
                else:
                    predictions.loc[idx, 'direction'] = 'SHORT'
                    predictions.loc[idx, 'confidence'] = min(50 + bearish_score, 95)
            else:
                predictions.loc[idx, 'direction'] = None
                predictions.loc[idx, 'confidence'] = 0

    # Drop rows with NaN (only critical columns)
    data = data.dropna(subset=['close', 'high', 'low', 'open'])
    predictions = predictions.loc[data.index]

    # Fill remaining NaN with defaults
    data['vix'] = data['vix'].fillna(20.0)
    data['sma50'] = data['sma50'].fillna(data['close'])
    data['sma20'] = data['sma20'].fillna(data['close'])
    data['avg_volume'] = data['avg_volume'].fillna(data['volume'])
    data['rsi'] = data['rsi'].fillna(50.0)
    data['macd'] = data['macd'].fillna(0.0)
    data['macd_signal'] = data['macd_signal'].fillna(0.0)

    print(f"Prepared {len(data)} bars of data")
    if len(data) > 0:
        print(f"Date range: {data.index[0].strftime('%Y-%m-%d')} to {data.index[-1].strftime('%Y-%m-%d')}")

    return data, predictions


def run_full_backtest(days: int = 365, save_results: bool = True):
    """Run a complete backtest with reporting."""
    print("=" * 60)
    print("       S&P 500 TRADING STRATEGY BACKTEST")
    print("=" * 60)

    # Prepare data
    data, predictions = prepare_backtest_data(days)

    if len(data) == 0:
        print("ERROR: No data available for backtesting")
        return {'error': 'No data available'}

    # Run backtest
    backtester = Backtester(initial_capital=1000.0)
    results = backtester.run_backtest(data, predictions)

    # Print results
    backtester.print_results(results)

    # Save results
    if save_results:
        os.makedirs('data', exist_ok=True)
        backtester.save_results(results, 'data/backtest_results.json')

        if HAS_MATPLOTLIB:
            backtester.plot_results(results, 'data/backtest_chart.png')

    return results


if __name__ == "__main__":
    import sys

    days = 365
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except ValueError:
            pass

    results = run_full_backtest(days=days)
