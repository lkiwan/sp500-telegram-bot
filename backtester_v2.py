# -*- coding: utf-8 -*-
"""
Backtester V2 - Matches Trading Simulation Tracker Logic
=========================================================
Uses the same strategy as trading_simulation_tracker.py:
- 50% position size
- Direction-based trading (UP = BUY, DOWN = CASH)
- Hold for 1 day, check next day's close
- No TP/SL levels
"""

import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
from typing import Dict, List, Tuple
import json
import os

try:
    import matplotlib.pyplot as plt
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


class BacktesterV2:
    """
    Backtest matching the trading_simulation_tracker.py logic exactly.

    Strategy:
    - When prediction is UP: Buy (invest 50% of portfolio)
    - When prediction is DOWN: Hold cash (no position)
    - Track actual market movement to determine win/loss
    """

    def __init__(self, initial_capital: float = 10000.0, position_size: float = 0.5):
        self.initial_capital = initial_capital
        self.position_size = position_size  # 50% of portfolio per trade

        self.cash = initial_capital
        self.shares = 0.0
        self.trades = []
        self.portfolio_history = []

    def run_backtest(self, data: pd.DataFrame, predictions: pd.DataFrame) -> Dict:
        """
        Run backtest with direction-based strategy.

        Args:
            data: DataFrame with OHLCV data
            predictions: DataFrame with direction and confidence
        """
        print("=" * 60)
        print("BACKTEST V2 - Direction-Based Strategy")
        print("=" * 60)
        print(f"Initial Capital: ${self.initial_capital:,.2f}")
        print(f"Position Size: {self.position_size * 100:.0f}%")
        print(f"Data: {len(data)} bars")
        print("-" * 60)

        self.cash = self.initial_capital
        self.shares = 0.0
        self.trades = []
        self.portfolio_history = []

        # Need at least 2 days to calculate next day return
        for i in range(len(data) - 1):
            current_date = data.index[i]
            next_date = data.index[i + 1]

            current_price = data.iloc[i]['close']
            next_price = data.iloc[i + 1]['close']

            # Get prediction for this date
            if current_date in predictions.index:
                pred = predictions.loc[current_date]
                direction = pred.get('direction', None)
                confidence = pred.get('confidence', 0)
            else:
                direction = None
                confidence = 0

            if direction is None:
                continue

            # Calculate market return
            market_return = ((next_price - current_price) / current_price) * 100
            actual_direction = 'UP' if market_return > 0 else 'DOWN'

            # Portfolio value before trade
            portfolio_before = self.cash + (self.shares * current_price)

            # Execute strategy
            if direction == 'LONG' or direction == 'UP':
                # Buy signal - invest position_size of cash
                if self.shares == 0:  # Not already in position
                    invest_amount = self.cash * self.position_size
                    shares_to_buy = invest_amount / current_price if current_price > 0 else 0
                    self.cash -= invest_amount
                    self.shares = shares_to_buy
                    action = 'BUY'
                else:
                    action = 'HOLD_LONG'

                # Calculate P&L
                position_pnl = self.shares * (next_price - current_price)
                is_correct = (actual_direction == 'UP')
                result = 'WIN' if is_correct else 'LOSS'

            else:  # DOWN or SHORT
                # Sell/Hold cash signal
                if self.shares > 0:
                    sell_value = self.shares * current_price
                    self.cash += sell_value
                    self.shares = 0
                    action = 'SELL'
                else:
                    action = 'HOLD_CASH'

                position_pnl = 0
                is_correct = (actual_direction == 'DOWN')
                result = 'CORRECT_SAVE' if is_correct else 'MISSED_GAIN'

            # Calculate portfolio after
            position_value = self.shares * next_price
            portfolio_after = self.cash + position_value
            daily_return = ((portfolio_after - portfolio_before) / portfolio_before) * 100

            # Record trade
            trade = {
                'date': current_date,
                'next_date': next_date,
                'prediction': direction,
                'confidence': confidence,
                'action': action,
                'current_price': current_price,
                'next_price': next_price,
                'market_return': market_return,
                'actual_direction': actual_direction,
                'is_correct': is_correct,
                'result': result,
                'pnl': position_pnl,
                'portfolio_before': portfolio_before,
                'portfolio_after': portfolio_after,
                'daily_return': daily_return
            }
            self.trades.append(trade)

            # Record portfolio state
            self.portfolio_history.append({
                'date': next_date,
                'portfolio_value': portfolio_after,
                'cash': self.cash,
                'position_value': position_value,
                'shares': self.shares
            })

        # Calculate results
        results = self.calculate_results()
        self.print_results(results)

        return results

    def calculate_results(self) -> Dict:
        """Calculate performance metrics."""
        if not self.trades:
            return {'error': 'No trades'}

        # Final portfolio value
        final_value = self.portfolio_history[-1]['portfolio_value'] if self.portfolio_history else self.initial_capital
        total_return = ((final_value - self.initial_capital) / self.initial_capital) * 100

        # Win rate calculation (matching their logic)
        wins = sum(1 for t in self.trades if t['result'] in ['WIN', 'CORRECT_SAVE'])
        total = len(self.trades)
        win_rate = (wins / total * 100) if total > 0 else 0

        # Separate stats
        buy_trades = [t for t in self.trades if t['action'] in ['BUY', 'HOLD_LONG']]
        buy_wins = sum(1 for t in buy_trades if t['result'] == 'WIN')
        buy_win_rate = (buy_wins / len(buy_trades) * 100) if buy_trades else 0

        # Calculate max drawdown
        peak = self.initial_capital
        max_drawdown = 0
        for ph in self.portfolio_history:
            if ph['portfolio_value'] > peak:
                peak = ph['portfolio_value']
            drawdown = (peak - ph['portfolio_value']) / peak * 100
            max_drawdown = max(max_drawdown, drawdown)

        # Results breakdown
        results_count = {}
        for t in self.trades:
            r = t['result']
            results_count[r] = results_count.get(r, 0) + 1

        # Buy & Hold comparison
        if self.portfolio_history:
            first_price = self.trades[0]['current_price']
            last_price = self.trades[-1]['next_price']
            buy_hold_return = ((last_price - first_price) / first_price) * 100
        else:
            buy_hold_return = 0

        outperformance = total_return - buy_hold_return

        return {
            'initial_capital': self.initial_capital,
            'final_capital': final_value,
            'total_return_pct': total_return,
            'total_return_dollars': final_value - self.initial_capital,
            'win_rate': win_rate,
            'total_trades': total,
            'wins': wins,
            'losses': total - wins,
            'buy_trades': len(buy_trades),
            'buy_win_rate': buy_win_rate,
            'max_drawdown': max_drawdown,
            'results_breakdown': results_count,
            'buy_hold_return': buy_hold_return,
            'outperformance': outperformance,
            'trades': self.trades,
            'portfolio_history': self.portfolio_history
        }

    def print_results(self, results: Dict):
        """Print formatted results."""
        print("\n" + "=" * 60)
        print("                 BACKTEST RESULTS")
        print("=" * 60)

        print(f"\n{'PORTFOLIO PERFORMANCE':^60}")
        print("-" * 60)
        print(f"Starting Capital:     ${results['initial_capital']:>12,.2f}")
        print(f"Final Capital:        ${results['final_capital']:>12,.2f}")
        print(f"Total Return:         {results['total_return_pct']:>12.2f}%")
        print(f"Total Return ($):     ${results['total_return_dollars']:>12,.2f}")
        print(f"Max Drawdown:         {results['max_drawdown']:>12.2f}%")

        print(f"\n{'COMPARISON VS BUY & HOLD':^60}")
        print("-" * 60)
        print(f"Model Strategy:       {results['total_return_pct']:>12.2f}%")
        print(f"Buy & Hold:           {results['buy_hold_return']:>12.2f}%")
        print(f"Outperformance:       {results['outperformance']:>+12.2f}pp")

        print(f"\n{'WIN RATE':^60}")
        print("-" * 60)
        print(f"Overall Win Rate:     {results['win_rate']:>12.1f}%")
        print(f"Buy Signal Win Rate:  {results['buy_win_rate']:>12.1f}%")
        print(f"Total Trades:         {results['total_trades']:>12}")
        print(f"Wins:                 {results['wins']:>12}")
        print(f"Losses:               {results['losses']:>12}")

        print(f"\n{'RESULTS BREAKDOWN':^60}")
        print("-" * 60)
        for result, count in results['results_breakdown'].items():
            print(f"{result:20} {count:>12}")

        print("\n" + "=" * 60)

    def save_results(self, results: Dict, filepath: str):
        """Save results to JSON."""
        output = {
            'summary': {
                'initial_capital': results['initial_capital'],
                'final_capital': results['final_capital'],
                'total_return_pct': results['total_return_pct'],
                'win_rate': results['win_rate'],
                'buy_hold_return': results['buy_hold_return'],
                'outperformance': results['outperformance']
            },
            'results_breakdown': results['results_breakdown']
        }

        with open(filepath, 'w') as f:
            json.dump(output, f, indent=2, default=str)

        print(f"Results saved to {filepath}")


def prepare_data(days: int = 365):
    """Prepare historical data for backtesting."""
    print(f"Downloading {days} days of data...")

    spy = yf.Ticker("^GSPC")
    data = spy.history(period=f"{days}d")

    if data.empty:
        raise ValueError("No data")

    data.columns = [c.lower() for c in data.columns]

    print(f"Downloaded {len(data)} bars")
    print(f"Date range: {data.index[0].strftime('%Y-%m-%d')} to {data.index[-1].strftime('%Y-%m-%d')}")

    return data


def generate_predictions_with_ml(data: pd.DataFrame) -> pd.DataFrame:
    """Generate predictions using actual ML model."""
    try:
        from ml_predictor import MLPredictor
        ml = MLPredictor(models_path="models")
        print("Using ML model for predictions...")
    except:
        print("ML model not available")
        return pd.DataFrame()

    predictions = pd.DataFrame(index=data.index)

    for i, idx in enumerate(data.index):
        if i < 50:
            predictions.loc[idx, 'direction'] = None
            predictions.loc[idx, 'confidence'] = 0
            continue

        hist = data.iloc[:i+1].copy()
        economic = {'vix': 20, 'fear_greed': 50}

        try:
            pred = ml.predict(hist, economic)
            # Convert LONG to UP, SHORT to DOWN
            direction = 'UP' if pred['direction'] == 'LONG' else 'DOWN'
            predictions.loc[idx, 'direction'] = direction
            predictions.loc[idx, 'confidence'] = pred['confidence']
        except:
            predictions.loc[idx, 'direction'] = None
            predictions.loc[idx, 'confidence'] = 0

        if (i + 1) % 50 == 0:
            print(f"  Processed {i+1}/{len(data)} bars...")

    return predictions


def load_historical_predictions(filepath: str = None) -> pd.DataFrame:
    """Load historical predictions from predictions_with_accuracy.csv."""
    if filepath is None:
        # Try parent folder first
        parent_path = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                                   'predictions_with_accuracy.csv')
        if os.path.exists(parent_path):
            filepath = parent_path
        else:
            filepath = 'predictions_with_accuracy.csv'

    if not os.path.exists(filepath):
        print(f"Historical predictions file not found: {filepath}")
        return pd.DataFrame()

    df = pd.read_csv(filepath)
    df['data_date'] = pd.to_datetime(df['data_date'])
    df = df.set_index('data_date')

    # Map to standard format
    predictions = pd.DataFrame(index=df.index)
    predictions['direction'] = df['predicted_direction']
    predictions['confidence'] = df['confidence']

    print(f"Loaded {len(predictions)} historical predictions")
    print(f"Date range: {predictions.index.min().strftime('%Y-%m-%d')} to {predictions.index.max().strftime('%Y-%m-%d')}")

    return predictions


def run_backtest_v2(days: int = 365, use_historical: bool = True):
    """Run the backtest matching simulation tracker logic."""
    print("\n" + "=" * 60)
    print("S&P 500 BACKTEST V2")
    print("Matching trading_simulation_tracker.py logic")
    print("=" * 60 + "\n")

    if use_historical:
        # Use historical predictions from file
        predictions = load_historical_predictions()
        if predictions.empty:
            print("Falling back to ML model predictions...")
            use_historical = False
        else:
            # Get data for the same period as predictions
            start_date = predictions.index.min()
            end_date = predictions.index.max()
            days_needed = (end_date - start_date).days + 30
            data = prepare_data(days_needed)
            # Normalize data index to date-only for comparison
            data.index = data.index.normalize().tz_localize(None)
            # Filter data to match predictions period
            data = data[data.index >= start_date]

    if not use_historical:
        # Get data and generate predictions with ML
        data = prepare_data(days)
        predictions = generate_predictions_with_ml(data)

    # Run backtest
    backtester = BacktesterV2(initial_capital=10000.0, position_size=0.5)
    results = backtester.run_backtest(data, predictions)

    # Save results
    os.makedirs('data', exist_ok=True)
    backtester.save_results(results, 'data/backtest_v2_results.json')

    return results


if __name__ == "__main__":
    import sys

    days = 365
    if len(sys.argv) > 1:
        try:
            days = int(sys.argv[1])
        except:
            pass

    run_backtest_v2(days)
