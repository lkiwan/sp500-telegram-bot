# -*- coding: utf-8 -*-
"""
Signal Tracker
==============
Track trading signals and portfolio performance
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum


class SignalStatus(Enum):
    OPEN = "open"
    TP_HIT = "tp_hit"
    SL_HIT = "sl_hit"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


@dataclass
class Signal:
    """Individual trading signal."""
    id: str
    timestamp: str
    direction: str  # "LONG" or "SHORT"
    ticker: str
    entry_price: float
    take_profit: float
    stop_loss: float
    confidence: float
    status: str = "open"
    exit_price: Optional[float] = None
    exit_timestamp: Optional[str] = None
    pnl_pct: Optional[float] = None
    notes: str = ""


class SignalTracker:
    """Track trading signals and portfolio performance."""

    def __init__(self, data_file: str = "data/signals.json",
                 initial_capital: float = 1000.0):
        self.data_file = data_file
        self.initial_capital = initial_capital
        self.data = self._load_data()

    def get_lot_size(self, confidence: float) -> float:
        """
        Get dynamic lot size based on confidence level.

        Returns lot size from 0.1 to 1.0 based on confidence:
        - < 55%: 0.1 (10%)
        - 55-60%: 0.2 (20%)
        - 60-65%: 0.3 (30%)
        - 65-70%: 0.4 (40%)
        - 70-75%: 0.5 (50%)
        - 75-80%: 0.6 (60%)
        - 80-85%: 0.7 (70%)
        - 85-90%: 0.8 (80%)
        - 90-95%: 0.9 (90%)
        - 95%+: 1.0 (100%)
        """
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

    def _load_data(self) -> Dict:
        """Load signal history from file."""
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        return self._create_empty_data()

    def _create_empty_data(self) -> Dict:
        """Create empty data structure."""
        return {
            'signals': [],
            'portfolio': {
                'initial_capital': self.initial_capital,
                'current_value': self.initial_capital,
                'cash': self.initial_capital,
                'positions': [],
                'history': [{
                    'timestamp': datetime.now().isoformat(),
                    'value': self.initial_capital,
                    'event': 'initial'
                }]
            },
            'stats': {
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'total_pnl_pct': 0.0,
                'best_trade': None,
                'worst_trade': None,
                'current_streak': 0,
                'best_streak': 0,
                'worst_streak': 0,
                'avg_win_pct': 0.0,
                'avg_loss_pct': 0.0
            }
        }

    def save_data(self):
        """Save signal history to file."""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f, indent=2)

    def generate_signal_id(self) -> str:
        """Generate unique signal ID."""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        count = len(self.data['signals']) + 1
        return f"SIG{timestamp}{count:04d}"

    def add_signal(self, direction: str, entry_price: float,
                   take_profit: float, stop_loss: float,
                   confidence: float, ticker: str = "SPY") -> Signal:
        """
        Add a new signal and update portfolio.

        Args:
            direction: "LONG" or "SHORT"
            entry_price: Entry price
            take_profit: Take profit price
            stop_loss: Stop loss price
            confidence: Confidence percentage (0-100)
            ticker: Ticker symbol

        Returns:
            Created Signal object
        """
        signal = Signal(
            id=self.generate_signal_id(),
            timestamp=datetime.now().isoformat(),
            direction=direction.upper(),
            ticker=ticker,
            entry_price=entry_price,
            take_profit=take_profit,
            stop_loss=stop_loss,
            confidence=confidence,
            status=SignalStatus.OPEN.value
        )

        self.data['signals'].append(asdict(signal))

        # Calculate position size based on confidence (dynamic lot sizing)
        lot_size = self.get_lot_size(confidence)
        portfolio_value = self.data['portfolio']['current_value']
        position_value = portfolio_value * lot_size

        self.data['portfolio']['positions'].append({
            'signal_id': signal.id,
            'entry_value': position_value,
            'shares': position_value / entry_price,
            'direction': direction.upper(),
            'lot_size': lot_size
        })

        self.save_data()
        return signal

    def get_open_signals(self) -> List[Dict]:
        """Get all open signals."""
        return [s for s in self.data['signals']
                if s['status'] == SignalStatus.OPEN.value]

    def check_signal_proximity(self, signal_id: str, current_price: float) -> Optional[Dict]:
        """
        Check if price is near TP or SL (within 50% of the way).

        Returns dict with 'near_tp', 'near_sl', 'tp_progress', 'sl_progress' if near target.
        """
        for signal in self.data['signals']:
            if signal['id'] == signal_id and signal['status'] == SignalStatus.OPEN.value:
                entry = signal['entry_price']
                tp = signal['take_profit']
                sl = signal['stop_loss']
                direction = signal['direction']

                # Calculate progress towards TP and SL
                if direction == "LONG":
                    tp_distance = tp - entry
                    sl_distance = entry - sl
                    current_tp_progress = (current_price - entry) / tp_distance if tp_distance != 0 else 0
                    current_sl_progress = (entry - current_price) / sl_distance if sl_distance != 0 else 0
                else:  # SHORT
                    tp_distance = entry - tp
                    sl_distance = sl - entry
                    current_tp_progress = (entry - current_price) / tp_distance if tp_distance != 0 else 0
                    current_sl_progress = (current_price - entry) / sl_distance if sl_distance != 0 else 0

                result = {
                    'signal': signal,
                    'current_price': current_price,
                    'tp_progress': current_tp_progress * 100,  # percentage
                    'sl_progress': current_sl_progress * 100,
                    'near_tp': current_tp_progress >= 0.7,  # 70% of the way to TP
                    'near_sl': current_sl_progress >= 0.7,  # 70% of the way to SL
                    'hit_tp': current_tp_progress >= 1.0,
                    'hit_sl': current_sl_progress >= 1.0
                }

                return result

        return None

    def check_all_signals(self, current_price: float) -> List[Dict]:
        """
        Check all open signals against current price.

        Returns list of alerts for signals that hit TP, SL, or are near targets.
        """
        alerts = []
        open_signals = self.get_open_signals()

        for signal in open_signals:
            result = self.check_signal_proximity(signal['id'], current_price)
            if result:
                if result['hit_tp']:
                    closed = self._close_signal(signal['id'], signal['take_profit'], SignalStatus.TP_HIT)
                    alerts.append({
                        'type': 'TP_HIT',
                        'signal': closed,
                        'price': current_price
                    })
                elif result['hit_sl']:
                    closed = self._close_signal(signal['id'], signal['stop_loss'], SignalStatus.SL_HIT)
                    alerts.append({
                        'type': 'SL_HIT',
                        'signal': closed,
                        'price': current_price
                    })
                elif result['near_tp'] and not signal.get('near_tp_alerted'):
                    signal['near_tp_alerted'] = True
                    self.save_data()
                    alerts.append({
                        'type': 'NEAR_TP',
                        'signal': signal,
                        'price': current_price,
                        'progress': result['tp_progress']
                    })
                elif result['near_sl'] and not signal.get('near_sl_alerted'):
                    signal['near_sl_alerted'] = True
                    self.save_data()
                    alerts.append({
                        'type': 'NEAR_SL',
                        'signal': signal,
                        'price': current_price,
                        'progress': result['sl_progress']
                    })

        return alerts

    def update_signal(self, signal_id: str, current_price: float) -> Optional[Dict]:
        """
        Check if signal hit TP or SL, update accordingly.

        Args:
            signal_id: Signal ID to check
            current_price: Current market price

        Returns:
            Updated signal dict if closed, None otherwise
        """
        for signal in self.data['signals']:
            if signal['id'] == signal_id and signal['status'] == SignalStatus.OPEN.value:
                entry = signal['entry_price']
                tp = signal['take_profit']
                sl = signal['stop_loss']
                direction = signal['direction']

                hit_tp = False
                hit_sl = False

                if direction == "LONG":
                    hit_tp = current_price >= tp
                    hit_sl = current_price <= sl
                else:  # SHORT
                    hit_tp = current_price <= tp
                    hit_sl = current_price >= sl

                if hit_tp:
                    return self._close_signal(signal_id, tp, SignalStatus.TP_HIT)
                elif hit_sl:
                    return self._close_signal(signal_id, sl, SignalStatus.SL_HIT)

        return None

    def _close_signal(self, signal_id: str, exit_price: float,
                      status: SignalStatus) -> Dict:
        """Close a signal and update statistics."""
        for signal in self.data['signals']:
            if signal['id'] == signal_id:
                signal['status'] = status.value
                signal['exit_price'] = exit_price
                signal['exit_timestamp'] = datetime.now().isoformat()

                # Calculate P&L
                entry = signal['entry_price']
                if signal['direction'] == "LONG":
                    pnl_pct = ((exit_price - entry) / entry) * 100
                else:
                    pnl_pct = ((entry - exit_price) / entry) * 100

                signal['pnl_pct'] = pnl_pct

                # Update stats
                self._update_stats(signal)

                # Update portfolio
                self._update_portfolio(signal_id, pnl_pct)

                self.save_data()
                return signal

        return None

    def close_signal_manually(self, signal_id: str, exit_price: float,
                              reason: str = "manual") -> Optional[Dict]:
        """Manually close a signal."""
        for signal in self.data['signals']:
            if signal['id'] == signal_id and signal['status'] == SignalStatus.OPEN.value:
                signal['notes'] = f"Closed manually: {reason}"
                return self._close_signal(signal_id, exit_price, SignalStatus.EXPIRED)
        return None

    def move_stops_to_breakeven(self, direction: str) -> List[Dict]:
        """
        Move stop losses to break-even (entry price) for all open signals
        in the specified direction.

        Args:
            direction: "LONG" or "SHORT" - the direction of trades to protect

        Returns:
            List of signals that were updated
        """
        updated_signals = []

        for signal in self.data['signals']:
            if signal['status'] == SignalStatus.OPEN.value and signal['direction'] == direction.upper():
                entry_price = signal['entry_price']
                old_sl = signal['stop_loss']

                # Only move SL if it would be an improvement (closer to profit)
                if direction.upper() == "LONG":
                    # For LONG, move SL up to entry if current SL is below entry
                    if old_sl < entry_price:
                        signal['stop_loss'] = entry_price
                        signal['notes'] = f"SL moved to break-even from ${old_sl:.2f}"
                        updated_signals.append(signal)
                else:  # SHORT
                    # For SHORT, move SL down to entry if current SL is above entry
                    if old_sl > entry_price:
                        signal['stop_loss'] = entry_price
                        signal['notes'] = f"SL moved to break-even from ${old_sl:.2f}"
                        updated_signals.append(signal)

        if updated_signals:
            self.save_data()

        return updated_signals

    def get_open_signals_by_direction(self, direction: str) -> List[Dict]:
        """Get all open signals for a specific direction."""
        return [s for s in self.data['signals']
                if s['status'] == SignalStatus.OPEN.value
                and s['direction'] == direction.upper()]

    def _update_stats(self, signal: Dict):
        """Update performance statistics."""
        stats = self.data['stats']
        stats['total_trades'] += 1

        pnl = signal['pnl_pct']
        is_win = pnl > 0

        if is_win:
            stats['wins'] += 1
            stats['current_streak'] = max(1, stats['current_streak'] + 1)
            stats['best_streak'] = max(stats['best_streak'], stats['current_streak'])

            # Update average win
            total_win_pct = stats['avg_win_pct'] * (stats['wins'] - 1) + pnl
            stats['avg_win_pct'] = total_win_pct / stats['wins']
        else:
            stats['losses'] += 1
            stats['current_streak'] = min(-1, stats['current_streak'] - 1)
            stats['worst_streak'] = min(stats['worst_streak'], stats['current_streak'])

            # Update average loss
            if stats['losses'] > 0:
                total_loss_pct = stats['avg_loss_pct'] * (stats['losses'] - 1) + pnl
                stats['avg_loss_pct'] = total_loss_pct / stats['losses']

        stats['total_pnl_pct'] += pnl

        # Track best/worst trades
        if stats['best_trade'] is None or pnl > stats['best_trade']['pnl_pct']:
            stats['best_trade'] = {
                'id': signal['id'],
                'pnl_pct': pnl,
                'date': signal['exit_timestamp'],
                'direction': signal['direction']
            }

        if stats['worst_trade'] is None or pnl < stats['worst_trade']['pnl_pct']:
            stats['worst_trade'] = {
                'id': signal['id'],
                'pnl_pct': pnl,
                'date': signal['exit_timestamp'],
                'direction': signal['direction']
            }

    def _update_portfolio(self, signal_id: str, pnl_pct: float):
        """Update portfolio value after trade."""
        portfolio = self.data['portfolio']

        for pos in portfolio['positions']:
            if pos['signal_id'] == signal_id:
                exit_value = pos['entry_value'] * (1 + pnl_pct / 100)

                portfolio['cash'] += exit_value
                portfolio['current_value'] = portfolio['cash']

                portfolio['history'].append({
                    'timestamp': datetime.now().isoformat(),
                    'value': portfolio['current_value'],
                    'trade_id': signal_id,
                    'pnl_pct': pnl_pct
                })

                portfolio['positions'].remove(pos)
                break

    def get_performance_summary(self) -> Dict:
        """Generate performance summary for reporting."""
        stats = self.data['stats']
        portfolio = self.data['portfolio']

        total_trades = stats['total_trades']
        win_rate = (stats['wins'] / total_trades * 100) if total_trades > 0 else 0
        total_return = ((portfolio['current_value'] - portfolio['initial_capital'])
                       / portfolio['initial_capital'] * 100)

        return {
            'total_trades': total_trades,
            'wins': stats['wins'],
            'losses': stats['losses'],
            'win_rate': win_rate,
            'total_pnl_pct': stats['total_pnl_pct'],
            'avg_pnl_pct': stats['total_pnl_pct'] / total_trades if total_trades > 0 else 0,
            'avg_win_pct': stats['avg_win_pct'],
            'avg_loss_pct': stats['avg_loss_pct'],
            'best_trade': stats['best_trade'],
            'worst_trade': stats['worst_trade'],
            'current_streak': stats['current_streak'],
            'best_streak': stats['best_streak'],
            'worst_streak': stats['worst_streak'],
            'portfolio_value': portfolio['current_value'],
            'initial_capital': portfolio['initial_capital'],
            'total_return_pct': total_return
        }

    def get_daily_performance(self) -> Dict:
        """Get today's performance."""
        today = datetime.now().date()

        today_signals = [
            s for s in self.data['signals']
            if s['exit_timestamp'] and
               datetime.fromisoformat(s['exit_timestamp']).date() == today
        ]

        wins = sum(1 for s in today_signals if s['pnl_pct'] > 0)
        total_pnl = sum(s['pnl_pct'] for s in today_signals)

        return {
            'date': today.isoformat(),
            'trades': len(today_signals),
            'wins': wins,
            'losses': len(today_signals) - wins,
            'win_rate': (wins / len(today_signals) * 100) if today_signals else 0,
            'total_pnl_pct': total_pnl,
            'signals': today_signals
        }

    def get_weekly_report(self) -> Dict:
        """Generate weekly performance report."""
        one_week_ago = datetime.now() - timedelta(days=7)

        weekly_signals = [
            s for s in self.data['signals']
            if s['exit_timestamp'] and
               datetime.fromisoformat(s['exit_timestamp']) > one_week_ago
        ]

        weekly_wins = sum(1 for s in weekly_signals if s['pnl_pct'] > 0)
        weekly_pnl = sum(s['pnl_pct'] for s in weekly_signals)

        # Find best/worst of the week
        best_trade = None
        worst_trade = None
        for s in weekly_signals:
            if best_trade is None or s['pnl_pct'] > best_trade['pnl_pct']:
                best_trade = s
            if worst_trade is None or s['pnl_pct'] < worst_trade['pnl_pct']:
                worst_trade = s

        return {
            'period': 'weekly',
            'start_date': one_week_ago.strftime('%Y-%m-%d'),
            'end_date': datetime.now().strftime('%Y-%m-%d'),
            'trades': len(weekly_signals),
            'wins': weekly_wins,
            'losses': len(weekly_signals) - weekly_wins,
            'win_rate': (weekly_wins / len(weekly_signals) * 100) if weekly_signals else 0,
            'total_pnl_pct': weekly_pnl,
            'best_trade': best_trade,
            'worst_trade': worst_trade,
            'signals': weekly_signals
        }

    def get_monthly_returns(self) -> Dict[str, float]:
        """Get monthly returns for charting."""
        monthly = {}

        for signal in self.data['signals']:
            if signal['exit_timestamp'] and signal['pnl_pct'] is not None:
                month = datetime.fromisoformat(signal['exit_timestamp']).strftime('%Y-%m')
                if month not in monthly:
                    monthly[month] = 0.0
                monthly[month] += signal['pnl_pct']

        return monthly

    def get_portfolio_history(self) -> List[tuple]:
        """Get portfolio value history for charting."""
        history = []
        for entry in self.data['portfolio']['history']:
            timestamp = datetime.fromisoformat(entry['timestamp'])
            value = entry['value']
            history.append((timestamp, value))
        return history

    def get_cumulative_returns(self) -> List[tuple]:
        """Get cumulative returns over time."""
        initial = self.data['portfolio']['initial_capital']
        returns = []

        for entry in self.data['portfolio']['history']:
            timestamp = datetime.fromisoformat(entry['timestamp'])
            value = entry['value']
            cumulative_return = ((value - initial) / initial) * 100
            returns.append((timestamp, cumulative_return))

        return returns

    def reset_portfolio(self, new_capital: float = None):
        """Reset portfolio to initial state."""
        if new_capital:
            self.initial_capital = new_capital

        self.data = self._create_empty_data()
        self.save_data()


def create_tracker(data_file: str = "data/signals.json",
                   initial_capital: float = 1000.0) -> SignalTracker:
    """Create and return a SignalTracker instance."""
    return SignalTracker(data_file, initial_capital)
