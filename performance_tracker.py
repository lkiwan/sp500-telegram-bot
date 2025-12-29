# -*- coding: utf-8 -*-
"""
Performance Tracker
===================
Tracks daily signals and builds cumulative analysis:
- Daily: Today's result + recent days
- Weekly: This week + previous weeks
- Monthly: This month + all data
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import pytz

TZ_ET = pytz.timezone('US/Eastern')
TZ_MOROCCO = pytz.FixedOffset(60)  # UTC+1


class PerformanceTracker:
    """Track signal performance over time."""

    def __init__(self, filepath: str = "data/performance.json"):
        self.filepath = filepath
        self.data = self._load_data()

    def _load_data(self) -> Dict:
        """Load performance data from file."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, 'r') as f:
                    return json.load(f)
            except:
                pass

        return {
            'daily_results': [],  # List of daily signal results
            'weeks': [],          # Weekly summaries
            'months': [],         # Monthly summaries
            'current_streak': 0,
            'best_streak': 0,
            'worst_streak': 0,
            'total_signals': 0,
            'total_wins': 0
        }

    def _save_data(self):
        """Save performance data to file."""
        os.makedirs(os.path.dirname(self.filepath), exist_ok=True)
        with open(self.filepath, 'w') as f:
            json.dump(self.data, f, indent=2, default=str)

    def record_daily_signal(self, date: str, direction: str, confidence: float,
                           entry_price: float, close_price: float = None):
        """
        Record a daily signal.
        Call this when signal is made (direction, confidence, entry_price).
        Call again with close_price when day ends to calculate result.
        """
        # Find existing record for this date
        existing = None
        for i, record in enumerate(self.data['daily_results']):
            if record['date'] == date:
                existing = i
                break

        if existing is not None:
            # Update existing record with close price
            record = self.data['daily_results'][existing]
            if close_price is not None and record.get('close_price') is None:
                record['close_price'] = close_price
                record['actual_change'] = ((close_price - record['entry_price']) / record['entry_price']) * 100

                # Determine if signal was correct
                if record['direction'] == 'UP':
                    record['is_correct'] = close_price > record['entry_price']
                else:  # DOWN
                    record['is_correct'] = close_price < record['entry_price']

                record['result'] = 'WIN' if record['is_correct'] else 'LOSS'

                # Update streaks
                self._update_streaks(record['is_correct'])
                self.data['total_signals'] += 1
                if record['is_correct']:
                    self.data['total_wins'] += 1

                self._save_data()
        else:
            # Create new record
            record = {
                'date': date,
                'direction': direction,
                'confidence': confidence,
                'entry_price': entry_price,
                'close_price': close_price,
                'actual_change': None,
                'is_correct': None,
                'result': 'PENDING'
            }
            self.data['daily_results'].append(record)
            self._save_data()

        return record

    def _update_streaks(self, is_win: bool):
        """Update win/loss streaks."""
        if is_win:
            if self.data['current_streak'] >= 0:
                self.data['current_streak'] += 1
            else:
                self.data['current_streak'] = 1
            self.data['best_streak'] = max(self.data['best_streak'], self.data['current_streak'])
        else:
            if self.data['current_streak'] <= 0:
                self.data['current_streak'] -= 1
            else:
                self.data['current_streak'] = -1
            self.data['worst_streak'] = min(self.data['worst_streak'], self.data['current_streak'])

    def get_recent_days(self, n: int = 7) -> List[Dict]:
        """Get last N days of results."""
        completed = [r for r in self.data['daily_results'] if r['result'] != 'PENDING']
        return completed[-n:] if completed else []

    def get_today_result(self) -> Optional[Dict]:
        """Get today's result if available."""
        today = datetime.now(TZ_ET).strftime('%Y-%m-%d')
        for record in reversed(self.data['daily_results']):
            if record['date'] == today:
                return record
        return None

    def get_week_stats(self, weeks_ago: int = 0) -> Dict:
        """Get stats for a specific week (0 = current week)."""
        now = datetime.now(TZ_ET)
        # Start of the target week (Monday)
        start_of_week = now - timedelta(days=now.weekday() + (weeks_ago * 7))
        start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_week = start_of_week + timedelta(days=7)

        start_str = start_of_week.strftime('%Y-%m-%d')
        end_str = end_of_week.strftime('%Y-%m-%d')

        week_results = []
        for record in self.data['daily_results']:
            if start_str <= record['date'] < end_str and record['result'] != 'PENDING':
                week_results.append(record)

        if not week_results:
            return {
                'week_start': start_str,
                'week_end': end_str,
                'signals': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0,
                'results': []
            }

        wins = sum(1 for r in week_results if r['is_correct'])
        losses = len(week_results) - wins

        return {
            'week_start': start_str,
            'week_end': end_str,
            'signals': len(week_results),
            'wins': wins,
            'losses': losses,
            'win_rate': (wins / len(week_results) * 100) if week_results else 0,
            'results': week_results
        }

    def get_month_stats(self, months_ago: int = 0) -> Dict:
        """Get stats for a specific month (0 = current month)."""
        now = datetime.now(TZ_ET)

        # Calculate target month
        target_month = now.month - months_ago
        target_year = now.year
        while target_month <= 0:
            target_month += 12
            target_year -= 1

        # Start and end of month
        start_of_month = datetime(target_year, target_month, 1, tzinfo=TZ_ET)
        if target_month == 12:
            end_of_month = datetime(target_year + 1, 1, 1, tzinfo=TZ_ET)
        else:
            end_of_month = datetime(target_year, target_month + 1, 1, tzinfo=TZ_ET)

        start_str = start_of_month.strftime('%Y-%m-%d')
        end_str = end_of_month.strftime('%Y-%m-%d')

        month_results = []
        for record in self.data['daily_results']:
            if start_str <= record['date'] < end_str and record['result'] != 'PENDING':
                month_results.append(record)

        if not month_results:
            return {
                'month': start_of_month.strftime('%B %Y'),
                'signals': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0,
                'results': []
            }

        wins = sum(1 for r in month_results if r['is_correct'])
        losses = len(month_results) - wins

        return {
            'month': start_of_month.strftime('%B %Y'),
            'signals': len(month_results),
            'wins': wins,
            'losses': losses,
            'win_rate': (wins / len(month_results) * 100) if month_results else 0,
            'results': month_results
        }

    def get_all_time_stats(self) -> Dict:
        """Get all-time statistics."""
        completed = [r for r in self.data['daily_results'] if r['result'] != 'PENDING']

        if not completed:
            return {
                'total_signals': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0,
                'current_streak': 0,
                'best_streak': 0,
                'worst_streak': 0
            }

        wins = sum(1 for r in completed if r['is_correct'])
        losses = len(completed) - wins

        return {
            'total_signals': len(completed),
            'wins': wins,
            'losses': losses,
            'win_rate': (wins / len(completed) * 100) if completed else 0,
            'current_streak': self.data['current_streak'],
            'best_streak': self.data['best_streak'],
            'worst_streak': self.data['worst_streak']
        }

    def _get_day_name(self, date_str: str) -> str:
        """Get day name from date string."""
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%a')  # Mon, Tue, Wed...

    def _get_week_number(self, date_str: str) -> int:
        """Get week number of the year."""
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.isocalendar()[1]

    def generate_daily_analysis(self) -> str:
        """Generate daily analysis with cumulative history."""
        recent_days = self.get_recent_days(7)
        all_time = self.get_all_time_stats()

        if not recent_days:
            return "No signals recorded yet. Start tracking tomorrow!"

        # Build days history (last 5 days)
        days_lines = []
        for record in reversed(recent_days[-5:]):
            day_name = self._get_day_name(record['date'])
            dir_emoji = "🟢" if record['direction'] == 'UP' else "🔴"
            result_emoji = "✅" if record['is_correct'] else "❌"
            change = record.get('actual_change', 0) or 0
            days_lines.append(f"• {day_name}: {dir_emoji} {record['direction']} {change:+.2f}% {result_emoji}")

        days_text = "\n".join(days_lines) if days_lines else "No days yet"

        # Current week stats
        current_week = self.get_week_stats(0)

        # Streak info
        streak = self.data['current_streak']
        if streak >= 3:
            streak_text = f"🔥 {streak} WIN STREAK!"
        elif streak >= 1:
            streak_text = f"✅ {streak} win(s)"
        elif streak <= -3:
            streak_text = f"📉 {abs(streak)} loss streak"
        elif streak <= -1:
            streak_text = f"❌ {abs(streak)} loss(es)"
        else:
            streak_text = "➡️ Starting fresh"

        analysis = f"""
<b>📊 RECENT DAYS</b>

{days_text}

━━━━━━━━━━━━━━━━━━━━

<b>📅 THIS WEEK</b>

✅ Wins: {current_week['wins']} | ❌ Losses: {current_week['losses']}
📊 Win Rate: {current_week['win_rate']:.0f}%
{streak_text}

━━━━━━━━━━━━━━━━━━━━

<b>📈 ALL TIME: {all_time['total_signals']} signals | {all_time['win_rate']:.0f}% win rate</b>
"""
        return analysis

    def generate_weekly_analysis(self) -> str:
        """Generate weekly analysis with days breakdown and previous weeks."""
        current_week = self.get_week_stats(0)
        all_time = self.get_all_time_stats()

        # Build days of this week
        days_lines = []
        for record in current_week.get('results', []):
            day_name = self._get_day_name(record['date'])
            dir_emoji = "🟢" if record['direction'] == 'UP' else "🔴"
            result_emoji = "✅" if record['is_correct'] else "❌"
            change = record.get('actual_change', 0) or 0
            days_lines.append(f"  • {day_name}: {dir_emoji} {change:+.2f}% {result_emoji}")

        days_text = "\n".join(days_lines) if days_lines else "  No signals yet"

        # Week result emoji
        if current_week['win_rate'] >= 70:
            week_emoji = "🏆"
        elif current_week['win_rate'] >= 50:
            week_emoji = "✅"
        elif current_week['signals'] > 0:
            week_emoji = "❌"
        else:
            week_emoji = "📊"

        # Build previous weeks history (up to 4 weeks)
        weeks_lines = []
        for i in range(1, 5):
            week = self.get_week_stats(i)
            if week['signals'] > 0:
                w_emoji = "✅" if week['win_rate'] >= 50 else "❌"
                weeks_lines.append(f"• Week -{i}: {week['wins']}W/{week['losses']}L ({week['win_rate']:.0f}%) {w_emoji}")

        weeks_text = "\n".join(weeks_lines) if weeks_lines else "No previous weeks"

        analysis = f"""
<b>📅 THIS WEEK</b> {week_emoji}

{days_text}

<b>Result:</b> {current_week['wins']}W / {current_week['losses']}L ({current_week['win_rate']:.0f}%)

━━━━━━━━━━━━━━━━━━━━

<b>📆 PREVIOUS WEEKS</b>

{weeks_text}

━━━━━━━━━━━━━━━━━━━━

<b>📈 ALL TIME: {all_time['total_signals']} signals | {all_time['win_rate']:.0f}%</b>
"""
        return analysis

    def generate_monthly_analysis(self) -> str:
        """Generate monthly analysis with weeks and previous months."""
        current_month = self.get_month_stats(0)
        all_time = self.get_all_time_stats()

        # Month emoji
        if current_month['win_rate'] >= 70:
            month_emoji = "🏆"
        elif current_month['win_rate'] >= 50:
            month_emoji = "✅"
        elif current_month['signals'] > 0:
            month_emoji = "❌"
        else:
            month_emoji = "📊"

        # Build weeks of this month
        weeks_lines = []
        for i in range(4, -1, -1):
            week = self.get_week_stats(i)
            if week['signals'] > 0:
                w_emoji = "✅" if week['win_rate'] >= 50 else "❌"
                weeks_lines.append(f"  • Week {5-i}: {week['wins']}W/{week['losses']}L ({week['win_rate']:.0f}%) {w_emoji}")

        weeks_text = "\n".join(weeks_lines[-4:]) if weeks_lines else "  No weeks yet"

        # Build previous months history (up to 3 months)
        months_lines = []
        for i in range(1, 4):
            month = self.get_month_stats(i)
            if month['signals'] > 0:
                m_emoji = "✅" if month['win_rate'] >= 50 else "❌"
                month_name = month['month'].split()[0][:3]  # Jan, Feb, etc
                months_lines.append(f"• {month_name}: {month['wins']}W/{month['losses']}L ({month['win_rate']:.0f}%) {m_emoji}")

        months_text = "\n".join(months_lines) if months_lines else "No previous months"

        analysis = f"""
<b>📆 {current_month['month'].upper()}</b> {month_emoji}

<b>Weeks:</b>
{weeks_text}

<b>Month Total:</b> {current_month['wins']}W / {current_month['losses']}L ({current_month['win_rate']:.0f}%)

━━━━━━━━━━━━━━━━━━━━

<b>📅 PREVIOUS MONTHS</b>

{months_text}

━━━━━━━━━━━━━━━━━━━━

<b>📈 ALL TIME STATS</b>

• Total Signals: {all_time['total_signals']}
• Win Rate: {all_time['win_rate']:.0f}%
• Best Streak: {all_time['best_streak']} 🏆
• Worst Streak: {abs(all_time['worst_streak'])} 📉
"""
        return analysis


# Global instance
performance_tracker = PerformanceTracker()
