# -*- coding: utf-8 -*-
"""
Chart Generator
===============
Professional TradingView-style dark theme charts for Telegram
"""

import matplotlib
matplotlib.use('Agg')  # Non-interactive backend for server

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
import mplfinance as mpf
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime
from styles import COLORS, CHART_CONFIG, PANEL_RATIOS


class ChartGenerator:
    """Generate professional trading charts with TradingView dark theme."""

    def __init__(self):
        self.style = self._create_tradingview_style()
        self.width = CHART_CONFIG['width']
        self.height = CHART_CONFIG['height']
        self.dpi = CHART_CONFIG['dpi']

    def _create_tradingview_style(self):
        """Create TradingView Pro Dark theme style for mplfinance."""
        market_colors = mpf.make_marketcolors(
            up=COLORS['candle_up'],
            down=COLORS['candle_down'],
            edge='inherit',
            wick={'up': COLORS['candle_wick_up'], 'down': COLORS['candle_wick_down']},
            volume={'up': COLORS['volume_up'], 'down': COLORS['volume_down']}
        )

        style = mpf.make_mpf_style(
            base_mpl_style='dark_background',
            marketcolors=market_colors,
            facecolor=COLORS['background'],
            figcolor=COLORS['background'],
            gridcolor=COLORS['grid'],
            gridstyle='--',
            gridaxis='both',
            y_on_right=True,
            rc={
                'axes.labelcolor': COLORS['foreground'],
                'axes.edgecolor': COLORS['grid'],
                'xtick.color': COLORS['foreground'],
                'ytick.color': COLORS['foreground'],
                'font.size': CHART_CONFIG['tick_size'],
                'font.family': CHART_CONFIG['font_family'],
                'axes.titlesize': CHART_CONFIG['title_size'],
                'axes.labelsize': CHART_CONFIG['label_size'],
            }
        )
        return style

    def generate_technical_chart(self, df: pd.DataFrame,
                                  title: str = "S&P 500",
                                  show_volume: bool = True,
                                  show_rsi: bool = True,
                                  show_macd: bool = True,
                                  show_bollinger: bool = True,
                                  show_sma: bool = True) -> BytesIO:
        """
        Generate professional candlestick chart with technical indicators.

        Args:
            df: OHLCV DataFrame with DatetimeIndex (columns: Open, High, Low, Close, Volume)
            title: Chart title
            show_volume: Include volume panel
            show_rsi: Include RSI panel
            show_macd: Include MACD panel
            show_bollinger: Show Bollinger Bands
            show_sma: Show moving averages

        Returns:
            BytesIO buffer containing PNG image
        """
        # Ensure proper column names
        df = df.copy()
        df.columns = [c.capitalize() for c in df.columns]

        # Set DatetimeIndex if not already
        if not isinstance(df.index, pd.DatetimeIndex):
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'])
                df.set_index('Date', inplace=True)
            else:
                df.index = pd.to_datetime(df.index)

        # Calculate indicators
        df = self._calculate_indicators(df)

        # Build additional plots
        add_plots = []
        panel_count = 1  # Start with price panel

        # Volume panel
        if show_volume:
            panel_count += 1

        # Moving averages on main chart
        if show_sma and 'SMA_20' in df.columns:
            add_plots.append(mpf.make_addplot(
                df['SMA_20'], color=COLORS['sma_20'],
                width=1.2, label='SMA 20'
            ))
        if show_sma and 'SMA_50' in df.columns:
            add_plots.append(mpf.make_addplot(
                df['SMA_50'], color=COLORS['sma_50'],
                width=1.2, label='SMA 50'
            ))

        # Bollinger Bands
        if show_bollinger and 'BB_Upper' in df.columns:
            add_plots.append(mpf.make_addplot(
                df['BB_Upper'], color=COLORS['bollinger'],
                width=0.8, linestyle='--'
            ))
            add_plots.append(mpf.make_addplot(
                df['BB_Lower'], color=COLORS['bollinger'],
                width=0.8, linestyle='--'
            ))

        # RSI panel
        rsi_panel = None
        if show_rsi and 'RSI' in df.columns:
            rsi_panel = panel_count
            panel_count += 1
            add_plots.append(mpf.make_addplot(
                df['RSI'], panel=rsi_panel, color=COLORS['rsi_line'],
                ylabel='RSI', ylim=(0, 100), width=1.2
            ))
            # Overbought/oversold lines
            add_plots.append(mpf.make_addplot(
                pd.Series([70] * len(df), index=df.index),
                panel=rsi_panel, color=COLORS['rsi_overbought'],
                linestyle='--', width=0.6
            ))
            add_plots.append(mpf.make_addplot(
                pd.Series([30] * len(df), index=df.index),
                panel=rsi_panel, color=COLORS['rsi_oversold'],
                linestyle='--', width=0.6
            ))

        # MACD panel
        if show_macd and 'MACD' in df.columns:
            macd_panel = panel_count
            panel_count += 1
            add_plots.append(mpf.make_addplot(
                df['MACD'], panel=macd_panel, color=COLORS['macd_line'],
                ylabel='MACD', width=1.2
            ))
            add_plots.append(mpf.make_addplot(
                df['MACD_Signal'], panel=macd_panel, color=COLORS['macd_signal'],
                width=1.0
            ))
            # Histogram with colors
            hist_colors = [COLORS['macd_histogram_pos'] if v >= 0
                          else COLORS['macd_histogram_neg']
                          for v in df['MACD_Hist'].fillna(0)]
            add_plots.append(mpf.make_addplot(
                df['MACD_Hist'], panel=macd_panel, type='bar',
                color=hist_colors, width=0.7
            ))

        # Determine panel ratios
        if show_rsi and show_macd:
            panel_ratios = PANEL_RATIOS['full']
        elif show_rsi or show_macd:
            panel_ratios = PANEL_RATIOS['price_volume_rsi']
        elif show_volume:
            panel_ratios = PANEL_RATIOS['price_volume']
        else:
            panel_ratios = PANEL_RATIOS['price_only']

        # Generate chart
        fig, axes = mpf.plot(
            df,
            type='candle',
            style=self.style,
            title=f'\n{title}',
            ylabel='Price ($)',
            volume=show_volume,
            volume_panel=1 if show_volume else None,
            addplot=add_plots if add_plots else None,
            figsize=(self.width, self.height),
            panel_ratios=panel_ratios,
            returnfig=True,
            tight_layout=True,
            datetime_format='%b %d',
            xrotation=0,
        )

        # Add watermark
        fig.text(0.99, 0.01, '@lkiwanSP500', fontsize=10,
                color=COLORS['text_muted'], alpha=0.7,
                ha='right', va='bottom',
                fontfamily='monospace')

        # Add current price annotation
        current_price = df['Close'].iloc[-1]
        current_change = ((df['Close'].iloc[-1] - df['Close'].iloc[-2]) /
                         df['Close'].iloc[-2] * 100) if len(df) > 1 else 0
        change_color = COLORS['bullish'] if current_change >= 0 else COLORS['bearish']

        fig.text(0.01, 0.97, f'${current_price:,.2f} ({current_change:+.2f}%)',
                fontsize=12, color=change_color,
                ha='left', va='top', fontweight='bold')

        # Save to buffer
        buffer = BytesIO()
        fig.savefig(buffer, format='png', dpi=self.dpi,
                   facecolor=COLORS['background'],
                   edgecolor='none', bbox_inches='tight',
                   pad_inches=0.1)
        buffer.seek(0)
        plt.close(fig)

        return buffer

    def generate_economic_dashboard(self, data: dict) -> BytesIO:
        """
        Generate economic indicators dashboard.

        Args:
            data: Dict with economic indicators
                - vix: Current VIX value
                - fear_greed: Fear & Greed score (0-100)
                - fed_rate: Federal Funds Rate
                - unemployment: Unemployment rate
                - cpi: CPI inflation rate
                - treasury_10y: 10-year Treasury yield
                - yield_spread: 10Y-2Y spread

        Returns:
            BytesIO buffer containing PNG image
        """
        fig = plt.figure(figsize=(14, 10), facecolor=COLORS['background'])

        # Title
        fig.suptitle('Economic Dashboard', fontsize=18,
                    color=COLORS['text_primary'], fontweight='bold', y=0.98)

        gs = GridSpec(3, 3, figure=fig, hspace=0.35, wspace=0.3,
                     left=0.05, right=0.95, top=0.92, bottom=0.08)

        # Panel 1: VIX Gauge (large)
        ax_vix = fig.add_subplot(gs[0:2, 0:2])
        self._draw_vix_gauge(ax_vix, data.get('vix', 20))

        # Panel 2: Fear & Greed
        ax_fg = fig.add_subplot(gs[0, 2])
        self._draw_fear_greed_meter(ax_fg, data.get('fear_greed', 50))

        # Panel 3: Fed Rate
        ax_fed = fig.add_subplot(gs[1, 2])
        self._draw_indicator_card(ax_fed, 'FED RATE',
                                  data.get('fed_rate', 5.25), '%', '🏛️')

        # Panel 4: Unemployment
        ax_unemp = fig.add_subplot(gs[2, 0])
        self._draw_indicator_card(ax_unemp, 'UNEMPLOYMENT',
                                  data.get('unemployment', 4.0), '%', '💼')

        # Panel 5: CPI Inflation
        ax_cpi = fig.add_subplot(gs[2, 1])
        self._draw_indicator_card(ax_cpi, 'CPI INFLATION',
                                  data.get('cpi', 3.0), '%', '🛒')

        # Panel 6: 10Y Treasury
        ax_treasury = fig.add_subplot(gs[2, 2])
        self._draw_indicator_card(ax_treasury, '10Y TREASURY',
                                  data.get('treasury_10y', 4.5), '%', '🏦')

        # Watermark
        fig.text(0.99, 0.01, '@lkiwanSP500', fontsize=10,
                color=COLORS['text_muted'], alpha=0.7,
                ha='right', va='bottom', fontfamily='monospace')

        # Timestamp
        fig.text(0.01, 0.01, datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
                fontsize=9, color=COLORS['text_muted'],
                ha='left', va='bottom')

        buffer = BytesIO()
        fig.savefig(buffer, format='png', dpi=self.dpi,
                   facecolor=COLORS['background'],
                   edgecolor='none', bbox_inches='tight')
        buffer.seek(0)
        plt.close(fig)

        return buffer

    def generate_performance_chart(self, data: dict) -> BytesIO:
        """
        Generate signal performance tracking chart.

        Args:
            data: Dict with performance data
                - portfolio_history: List of (date, value) tuples
                - wins: Number of winning trades
                - losses: Number of losing trades
                - total_pnl: Total P&L percentage
                - current_value: Current portfolio value
                - initial_value: Starting value

        Returns:
            BytesIO buffer containing PNG image
        """
        fig = plt.figure(figsize=(14, 8), facecolor=COLORS['background'])

        # Title
        fig.suptitle('Signal Performance Tracking', fontsize=18,
                    color=COLORS['text_primary'], fontweight='bold', y=0.98)

        gs = GridSpec(2, 3, figure=fig, hspace=0.3, wspace=0.3,
                     left=0.08, right=0.95, top=0.90, bottom=0.1)

        # Panel 1: Portfolio Value Chart (top, full width)
        ax_portfolio = fig.add_subplot(gs[0, :])
        self._draw_portfolio_chart(ax_portfolio, data.get('portfolio_history', []),
                                   data.get('initial_value', 1000))

        # Panel 2: Win/Loss Pie
        ax_pie = fig.add_subplot(gs[1, 0])
        self._draw_winloss_pie(ax_pie, data.get('wins', 0), data.get('losses', 0))

        # Panel 3: Monthly Returns
        ax_monthly = fig.add_subplot(gs[1, 1])
        self._draw_monthly_bars(ax_monthly, data.get('monthly_returns', {}))

        # Panel 4: Key Metrics
        ax_metrics = fig.add_subplot(gs[1, 2])
        self._draw_metrics_card(ax_metrics, data)

        # Watermark
        fig.text(0.99, 0.01, '@lkiwanSP500', fontsize=10,
                color=COLORS['text_muted'], alpha=0.7,
                ha='right', va='bottom', fontfamily='monospace')

        buffer = BytesIO()
        fig.savefig(buffer, format='png', dpi=self.dpi,
                   facecolor=COLORS['background'],
                   edgecolor='none', bbox_inches='tight')
        buffer.seek(0)
        plt.close(fig)

        return buffer

    def _calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators for the chart."""
        # Moving averages
        if len(df) >= 20:
            df['SMA_20'] = df['Close'].rolling(window=20).mean()
        if len(df) >= 50:
            df['SMA_50'] = df['Close'].rolling(window=50).mean()

        # Bollinger Bands
        if len(df) >= 20:
            df['BB_Middle'] = df['Close'].rolling(window=20).mean()
            bb_std = df['Close'].rolling(window=20).std()
            df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
            df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)

        # RSI
        if len(df) >= 14:
            delta = df['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['RSI'] = 100 - (100 / (1 + rs))

        # MACD
        if len(df) >= 26:
            ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
            ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
            df['MACD'] = ema_12 - ema_26
            df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
            df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']

        return df

    def _draw_vix_gauge(self, ax, vix_value: float):
        """Draw VIX gauge with colored zones."""
        ax.set_facecolor(COLORS['background'])
        ax.set_xlim(-1.5, 1.5)
        ax.set_ylim(-0.3, 1.2)
        ax.axis('off')

        # Draw gauge arc segments
        zones = [
            (0, 15, COLORS['vix_extreme_greed'], 'EXTREME\nGREED'),
            (15, 20, COLORS['vix_greed'], 'GREED'),
            (20, 25, COLORS['vix_neutral'], 'NEUTRAL'),
            (25, 30, COLORS['vix_fear'], 'FEAR'),
            (30, 50, COLORS['vix_extreme_fear'], 'EXTREME\nFEAR'),
        ]

        for vix_min, vix_max, color, label in zones:
            theta1 = 180 - (vix_min / 50 * 180)
            theta2 = 180 - (vix_max / 50 * 180)
            wedge = mpatches.Wedge((0, 0), 1.0, theta2, theta1,
                                   width=0.3, facecolor=color, alpha=0.8)
            ax.add_patch(wedge)

        # Draw needle
        needle_angle = np.radians(180 - (min(vix_value, 50) / 50 * 180))
        needle_x = 0.85 * np.cos(needle_angle)
        needle_y = 0.85 * np.sin(needle_angle)
        ax.plot([0, needle_x], [0, needle_y], color=COLORS['text_primary'],
               linewidth=3, solid_capstyle='round')
        ax.plot(0, 0, 'o', color=COLORS['text_primary'], markersize=10)

        # VIX value text
        ax.text(0, -0.15, f'{vix_value:.1f}', fontsize=36,
               ha='center', va='center', color=COLORS['text_primary'],
               fontweight='bold')
        ax.text(0, 0.45, 'VIX', fontsize=24,
               ha='center', va='center', color=COLORS['text_secondary'])

        # Zone labels
        ax.text(-1.2, 0.3, 'GREED', fontsize=10, color=COLORS['vix_greed'],
               ha='center', va='center', fontweight='bold')
        ax.text(1.2, 0.3, 'FEAR', fontsize=10, color=COLORS['vix_fear'],
               ha='center', va='center', fontweight='bold')

    def _draw_fear_greed_meter(self, ax, score: float):
        """Draw Fear & Greed meter."""
        ax.set_facecolor(COLORS['panel_bg'])
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 1)
        ax.axis('off')

        # Gradient bar
        gradient = np.linspace(0, 1, 100).reshape(1, -1)
        ax.imshow(gradient, aspect='auto', extent=[0, 100, 0.3, 0.7],
                 cmap='RdYlGn')

        # Marker
        ax.plot([score, score], [0.25, 0.75], color=COLORS['text_primary'],
               linewidth=3)
        ax.plot(score, 0.5, 'v', color=COLORS['text_primary'], markersize=15)

        # Labels
        ax.text(50, 0.95, 'FEAR & GREED', fontsize=12,
               ha='center', va='top', color=COLORS['text_primary'],
               fontweight='bold')
        ax.text(score, 0.1, f'{score:.0f}', fontsize=18,
               ha='center', va='bottom', color=COLORS['text_primary'],
               fontweight='bold')
        ax.text(5, 0.5, 'Fear', fontsize=9, ha='left', va='center',
               color=COLORS['bearish'])
        ax.text(95, 0.5, 'Greed', fontsize=9, ha='right', va='center',
               color=COLORS['bullish'])

    def _draw_indicator_card(self, ax, title: str, value: float,
                            unit: str, emoji: str):
        """Draw a single indicator card."""
        ax.set_facecolor(COLORS['panel_bg'])
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

        # Card border
        rect = mpatches.FancyBboxPatch((0.05, 0.05), 0.9, 0.9,
                                       boxstyle="round,pad=0.02",
                                       facecolor=COLORS['panel_bg'],
                                       edgecolor=COLORS['grid'],
                                       linewidth=1)
        ax.add_patch(rect)

        # Content
        ax.text(0.5, 0.85, f'{emoji} {title}', fontsize=10,
               ha='center', va='top', color=COLORS['text_secondary'])
        ax.text(0.5, 0.45, f'{value:.2f}{unit}', fontsize=22,
               ha='center', va='center', color=COLORS['text_primary'],
               fontweight='bold')

    def _draw_portfolio_chart(self, ax, history: list, initial_value: float):
        """Draw portfolio value over time."""
        ax.set_facecolor(COLORS['panel_bg'])

        if not history:
            ax.text(0.5, 0.5, 'No trading history yet',
                   ha='center', va='center', color=COLORS['text_muted'],
                   fontsize=14, transform=ax.transAxes)
            ax.set_xticks([])
            ax.set_yticks([])
            return

        dates = [h[0] for h in history]
        values = [h[1] for h in history]

        # Fill under line
        ax.fill_between(dates, values, initial_value,
                       where=[v >= initial_value for v in values],
                       color=COLORS['profit'], alpha=0.3)
        ax.fill_between(dates, values, initial_value,
                       where=[v < initial_value for v in values],
                       color=COLORS['loss'], alpha=0.3)

        # Line
        ax.plot(dates, values, color=COLORS['text_primary'], linewidth=2)

        # Initial value line
        ax.axhline(y=initial_value, color=COLORS['text_muted'],
                  linestyle='--', linewidth=1)

        ax.set_ylabel('Portfolio Value ($)', color=COLORS['text_secondary'])
        ax.tick_params(colors=COLORS['text_secondary'])
        ax.spines['bottom'].set_color(COLORS['grid'])
        ax.spines['left'].set_color(COLORS['grid'])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

    def _draw_winloss_pie(self, ax, wins: int, losses: int):
        """Draw win/loss pie chart."""
        ax.set_facecolor(COLORS['panel_bg'])

        if wins == 0 and losses == 0:
            ax.text(0.5, 0.5, 'No trades yet',
                   ha='center', va='center', color=COLORS['text_muted'],
                   fontsize=12, transform=ax.transAxes)
            ax.axis('off')
            return

        total = wins + losses
        win_rate = (wins / total * 100) if total > 0 else 0

        sizes = [wins, losses]
        colors = [COLORS['profit'], COLORS['loss']]
        explode = (0.05, 0)

        ax.pie(sizes, explode=explode, colors=colors, startangle=90,
              wedgeprops={'linewidth': 2, 'edgecolor': COLORS['background']})

        # Center text
        ax.text(0, 0, f'{win_rate:.0f}%', fontsize=20,
               ha='center', va='center', color=COLORS['text_primary'],
               fontweight='bold')
        ax.text(0, -0.15, 'Win Rate', fontsize=10,
               ha='center', va='top', color=COLORS['text_secondary'])

        ax.set_title(f'{wins}W / {losses}L', fontsize=11,
                    color=COLORS['text_secondary'], pad=5)

    def _draw_monthly_bars(self, ax, monthly_returns: dict):
        """Draw monthly returns bar chart."""
        ax.set_facecolor(COLORS['panel_bg'])

        if not monthly_returns:
            ax.text(0.5, 0.5, 'No monthly data',
                   ha='center', va='center', color=COLORS['text_muted'],
                   fontsize=12, transform=ax.transAxes)
            ax.axis('off')
            return

        months = list(monthly_returns.keys())[-6:]  # Last 6 months
        returns = [monthly_returns[m] for m in months]
        colors = [COLORS['profit'] if r >= 0 else COLORS['loss'] for r in returns]

        bars = ax.bar(months, returns, color=colors, edgecolor=COLORS['background'])

        ax.axhline(y=0, color=COLORS['grid'], linewidth=0.5)
        ax.set_ylabel('Return %', fontsize=9, color=COLORS['text_secondary'])
        ax.tick_params(colors=COLORS['text_secondary'], labelsize=8)
        ax.spines['bottom'].set_color(COLORS['grid'])
        ax.spines['left'].set_color(COLORS['grid'])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

        ax.set_title('Monthly Returns', fontsize=11,
                    color=COLORS['text_secondary'], pad=5)

    def _draw_metrics_card(self, ax, data: dict):
        """Draw key metrics card."""
        ax.set_facecolor(COLORS['panel_bg'])
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

        current = data.get('current_value', 1000)
        initial = data.get('initial_value', 1000)
        total_return = ((current - initial) / initial * 100) if initial > 0 else 0
        total_trades = data.get('wins', 0) + data.get('losses', 0)

        metrics = [
            ('Portfolio', f'${current:,.2f}'),
            ('Total Return', f'{total_return:+.2f}%'),
            ('Total Trades', f'{total_trades}'),
            ('Total P&L', f'{data.get("total_pnl", 0):+.2f}%'),
        ]

        y_positions = [0.85, 0.60, 0.35, 0.10]
        for (label, value), y in zip(metrics, y_positions):
            ax.text(0.1, y, label, fontsize=10,
                   ha='left', va='center', color=COLORS['text_secondary'])
            color = COLORS['text_primary']
            if '+' in value:
                color = COLORS['profit']
            elif '-' in value:
                color = COLORS['loss']
            ax.text(0.9, y, value, fontsize=11,
                   ha='right', va='center', color=color, fontweight='bold')


# Convenience function
def create_chart_generator() -> ChartGenerator:
    """Create and return a ChartGenerator instance."""
    return ChartGenerator()
