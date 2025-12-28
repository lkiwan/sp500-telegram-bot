# -*- coding: utf-8 -*-
"""
Chart Generator - Fixed Version
===============================
Professional TradingView-style dark theme charts for Telegram
"""

import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.gridspec import GridSpec
from matplotlib.lines import Line2D
import pandas as pd
import numpy as np
from io import BytesIO
from datetime import datetime
from styles import COLORS, CHART_CONFIG


class ChartGenerator:
    """Generate professional trading charts with TradingView dark theme."""

    def __init__(self):
        self.width = 14
        self.height = 10
        self.dpi = 150

        # Set matplotlib style
        plt.style.use('dark_background')
        plt.rcParams.update({
            'figure.facecolor': COLORS['background'],
            'axes.facecolor': COLORS['background'],
            'axes.edgecolor': COLORS['grid'],
            'axes.labelcolor': COLORS['foreground'],
            'text.color': COLORS['foreground'],
            'xtick.color': COLORS['foreground'],
            'ytick.color': COLORS['foreground'],
            'grid.color': COLORS['grid'],
            'grid.linestyle': '--',
            'grid.alpha': 0.3,
            'font.size': 10,
        })

    def generate_technical_chart(self, df: pd.DataFrame,
                                  title: str = "S&P 500",
                                  show_volume: bool = True,
                                  show_rsi: bool = True,
                                  show_macd: bool = True,
                                  show_bollinger: bool = True,
                                  show_sma: bool = True) -> BytesIO:
        """Generate professional candlestick chart with technical indicators."""

        # Prepare data
        df = df.copy()
        df.columns = [c.lower() for c in df.columns]

        if not isinstance(df.index, pd.DatetimeIndex):
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)

        # Calculate all indicators
        df = self._calculate_all_indicators(df)

        # Create figure with subplots
        n_panels = 1 + show_volume + show_rsi + show_macd

        if n_panels == 4:
            height_ratios = [4, 1, 1.2, 1.2]
        elif n_panels == 3:
            height_ratios = [4, 1, 1.2]
        elif n_panels == 2:
            height_ratios = [4, 1]
        else:
            height_ratios = [1]

        fig, axes = plt.subplots(n_panels, 1, figsize=(self.width, self.height),
                                  gridspec_kw={'height_ratios': height_ratios, 'hspace': 0.05},
                                  facecolor=COLORS['background'])

        if n_panels == 1:
            axes = [axes]

        # Panel index tracker
        panel_idx = 0

        # === MAIN PRICE PANEL ===
        ax_price = axes[panel_idx]
        self._draw_candlesticks(ax_price, df)

        if show_sma:
            self._draw_sma(ax_price, df)

        if show_bollinger:
            self._draw_bollinger(ax_price, df)

        # Price panel formatting
        ax_price.set_title(title, fontsize=14, fontweight='bold',
                          color=COLORS['foreground'], pad=10)
        ax_price.set_ylabel('Price ($)', fontsize=10, color=COLORS['foreground'])
        ax_price.yaxis.set_label_position('right')
        ax_price.yaxis.tick_right()
        ax_price.grid(True, alpha=0.3)
        ax_price.set_xticklabels([])

        # Add current price label
        current_price = df['close'].iloc[-1]
        prev_price = df['close'].iloc[-2] if len(df) > 1 else current_price
        change_pct = ((current_price - prev_price) / prev_price) * 100
        price_color = COLORS['candle_up'] if change_pct >= 0 else COLORS['candle_down']
        trend_arrow = '▲' if change_pct >= 0 else '▼'

        ax_price.text(0.01, 0.97, f'{trend_arrow} ${current_price:,.2f} ({change_pct:+.2f}%)',
                     transform=ax_price.transAxes, fontsize=12, fontweight='bold',
                     color=price_color, verticalalignment='top')

        # Draw current price horizontal line
        ax_price.axhline(y=current_price, color=price_color, linewidth=1,
                        linestyle='--', alpha=0.5)

        # Draw support/resistance levels
        self._draw_support_resistance(ax_price, df)

        # Add legend for price panel
        legend_elements = []
        if show_sma:
            legend_elements.append(Line2D([0], [0], color=COLORS['sma_20'], linewidth=2, label='SMA 20'))
            legend_elements.append(Line2D([0], [0], color=COLORS['sma_50'], linewidth=2, label='SMA 50'))
        if show_bollinger:
            legend_elements.append(Line2D([0], [0], color=COLORS['bollinger'], linewidth=1,
                                         linestyle='--', label='Bollinger'))

        if legend_elements:
            ax_price.legend(handles=legend_elements, loc='upper right',
                           fontsize=9, framealpha=0.8,
                           facecolor=COLORS['background'], edgecolor=COLORS['grid'])

        panel_idx += 1

        # === VOLUME PANEL ===
        if show_volume:
            ax_vol = axes[panel_idx]
            self._draw_volume(ax_vol, df)
            ax_vol.set_ylabel('Volume', fontsize=9, color=COLORS['text_muted'])
            ax_vol.yaxis.set_label_position('right')
            ax_vol.yaxis.tick_right()
            ax_vol.grid(True, alpha=0.2)
            ax_vol.set_xticklabels([])
            panel_idx += 1

        # === RSI PANEL ===
        if show_rsi:
            ax_rsi = axes[panel_idx]
            self._draw_rsi(ax_rsi, df)
            ax_rsi.set_ylabel('RSI', fontsize=9, color=COLORS['text_muted'])
            ax_rsi.yaxis.set_label_position('right')
            ax_rsi.yaxis.tick_right()
            ax_rsi.set_ylim(0, 100)
            ax_rsi.grid(True, alpha=0.2)
            ax_rsi.set_xticklabels([])
            panel_idx += 1

        # === MACD PANEL ===
        if show_macd:
            ax_macd = axes[panel_idx]
            self._draw_macd(ax_macd, df)
            ax_macd.set_ylabel('MACD', fontsize=9, color=COLORS['text_muted'])
            ax_macd.yaxis.set_label_position('right')
            ax_macd.yaxis.tick_right()
            ax_macd.grid(True, alpha=0.2)
            ax_macd.axhline(y=0, color=COLORS['grid'], linewidth=0.5)
            panel_idx += 1

        # Format x-axis on bottom panel
        bottom_ax = axes[-1]
        self._format_xaxis(bottom_ax, df)

        # Add watermark
        fig.text(0.99, 0.01, '@lkiwanSP500', fontsize=11,
                color=COLORS['text_muted'], alpha=0.8,
                ha='right', va='bottom', fontfamily='monospace',
                fontweight='bold')

        # Tight layout
        plt.tight_layout()

        # Save to buffer
        buffer = BytesIO()
        fig.savefig(buffer, format='png', dpi=self.dpi,
                   facecolor=COLORS['background'],
                   edgecolor='none', bbox_inches='tight',
                   pad_inches=0.1)
        buffer.seek(0)
        plt.close(fig)

        return buffer

    def _calculate_all_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all technical indicators."""

        # SMA
        if len(df) >= 20:
            df['sma_20'] = df['close'].rolling(window=20).mean()
        if len(df) >= 50:
            df['sma_50'] = df['close'].rolling(window=50).mean()

        # Bollinger Bands
        if len(df) >= 20:
            df['bb_middle'] = df['close'].rolling(window=20).mean()
            bb_std = df['close'].rolling(window=20).std()
            df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
            df['bb_lower'] = df['bb_middle'] - (bb_std * 2)

        # RSI
        if len(df) >= 14:
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            df['rsi'] = 100 - (100 / (1 + rs))

        # MACD
        if len(df) >= 26:
            ema_12 = df['close'].ewm(span=12, adjust=False).mean()
            ema_26 = df['close'].ewm(span=26, adjust=False).mean()
            df['macd'] = ema_12 - ema_26
            df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
            df['macd_hist'] = df['macd'] - df['macd_signal']

        return df

    def _draw_candlesticks(self, ax, df: pd.DataFrame):
        """Draw candlestick chart."""
        x = range(len(df))

        for i, (idx, row) in enumerate(df.iterrows()):
            open_price = row['open']
            close_price = row['close']
            high_price = row['high']
            low_price = row['low']

            if close_price >= open_price:
                color = COLORS['candle_up']
                body_bottom = open_price
                body_height = close_price - open_price
            else:
                color = COLORS['candle_down']
                body_bottom = close_price
                body_height = open_price - close_price

            # Draw wick
            ax.plot([i, i], [low_price, high_price], color=color, linewidth=1)

            # Draw body
            body_width = 0.6
            rect = plt.Rectangle((i - body_width/2, body_bottom), body_width,
                                 max(body_height, 0.001),
                                 facecolor=color, edgecolor=color)
            ax.add_patch(rect)

        ax.set_xlim(-1, len(df))
        ax.set_ylim(df['low'].min() * 0.995, df['high'].max() * 1.005)

    def _draw_sma(self, ax, df: pd.DataFrame):
        """Draw SMA lines."""
        x = range(len(df))

        if 'sma_20' in df.columns:
            ax.plot(x, df['sma_20'], color=COLORS['sma_20'], linewidth=1.5,
                   label='SMA 20', alpha=0.9)

        if 'sma_50' in df.columns:
            ax.plot(x, df['sma_50'], color=COLORS['sma_50'], linewidth=1.5,
                   label='SMA 50', alpha=0.9)

    def _draw_bollinger(self, ax, df: pd.DataFrame):
        """Draw Bollinger Bands."""
        x = range(len(df))

        if 'bb_upper' in df.columns and 'bb_lower' in df.columns:
            # Draw bands as dashed lines
            ax.plot(x, df['bb_upper'], color='#9c27b0', linewidth=1,
                   linestyle='--', alpha=0.7)
            ax.plot(x, df['bb_lower'], color='#9c27b0', linewidth=1,
                   linestyle='--', alpha=0.7)

            # Fill between bands
            ax.fill_between(x, df['bb_lower'], df['bb_upper'],
                           color='#9c27b0', alpha=0.08)

    def _draw_volume(self, ax, df: pd.DataFrame):
        """Draw volume bars."""
        x = range(len(df))

        colors = []
        for i in range(len(df)):
            if i == 0:
                colors.append(COLORS['candle_up'])
            else:
                if df['close'].iloc[i] >= df['close'].iloc[i-1]:
                    colors.append(COLORS['candle_up'])
                else:
                    colors.append(COLORS['candle_down'])

        ax.bar(x, df['volume'], color=colors, alpha=0.7, width=0.7)
        ax.set_xlim(-1, len(df))

    def _draw_support_resistance(self, ax, df: pd.DataFrame):
        """Draw support and resistance levels."""
        # Get recent highs and lows for support/resistance
        recent_high = df['high'].tail(20).max()
        recent_low = df['low'].tail(20).min()

        # Draw resistance level
        ax.axhline(y=recent_high, color=COLORS['resistance'], linewidth=1,
                  linestyle=':', alpha=0.6)
        ax.text(len(df) + 0.5, recent_high, f'R ${recent_high:,.0f}',
               fontsize=8, color=COLORS['resistance'], va='center')

        # Draw support level
        ax.axhline(y=recent_low, color=COLORS['support'], linewidth=1,
                  linestyle=':', alpha=0.6)
        ax.text(len(df) + 0.5, recent_low, f'S ${recent_low:,.0f}',
               fontsize=8, color=COLORS['support'], va='center')

    def _draw_rsi(self, ax, df: pd.DataFrame):
        """Draw RSI indicator - CLEAN VERSION."""
        x = range(len(df))

        if 'rsi' in df.columns:
            # RSI line only - single clean line
            ax.plot(x, df['rsi'], color=COLORS['rsi_line'], linewidth=1.5)

            # Overbought/oversold zones
            ax.axhline(y=70, color='#ff5252', linewidth=1, linestyle='--', alpha=0.7)
            ax.axhline(y=30, color='#69f0ae', linewidth=1, linestyle='--', alpha=0.7)
            ax.axhline(y=50, color=COLORS['grid'], linewidth=0.5, linestyle='-', alpha=0.3)

            # Fill zones
            ax.fill_between(x, 70, 100, color='#ff5252', alpha=0.1)
            ax.fill_between(x, 0, 30, color='#69f0ae', alpha=0.1)

            # Labels
            ax.text(len(df)-1, 70, '70', fontsize=8, color='#ff5252', va='bottom')
            ax.text(len(df)-1, 30, '30', fontsize=8, color='#69f0ae', va='top')

        ax.set_xlim(-1, len(df))

    def _draw_macd(self, ax, df: pd.DataFrame):
        """Draw MACD indicator - CLEAN VERSION."""
        x = range(len(df))

        if 'macd' in df.columns and 'macd_signal' in df.columns:
            # Histogram bars
            hist = df['macd_hist'].fillna(0)
            colors = [COLORS['candle_up'] if v >= 0 else COLORS['candle_down'] for v in hist]
            ax.bar(x, hist, color=colors, alpha=0.6, width=0.7)

            # MACD and Signal lines
            ax.plot(x, df['macd'], color=COLORS['macd_line'], linewidth=1.5, label='MACD')
            ax.plot(x, df['macd_signal'], color=COLORS['macd_signal'], linewidth=1.5, label='Signal')

            # Legend
            ax.legend(loc='upper left', fontsize=8, framealpha=0.8,
                     facecolor=COLORS['background'], edgecolor=COLORS['grid'])

        ax.set_xlim(-1, len(df))

    def _format_xaxis(self, ax, df: pd.DataFrame):
        """Format x-axis with date labels."""
        x = range(len(df))

        # Show every 10th date label
        step = max(1, len(df) // 8)
        tick_positions = list(range(0, len(df), step))
        tick_labels = [df.index[i].strftime('%b %d') for i in tick_positions if i < len(df)]

        ax.set_xticks(tick_positions[:len(tick_labels)])
        ax.set_xticklabels(tick_labels, fontsize=9)

    def generate_economic_dashboard(self, data: dict) -> BytesIO:
        """Generate economic indicators dashboard."""

        fig = plt.figure(figsize=(14, 10), facecolor=COLORS['background'])

        # Title
        fig.suptitle('Economic Dashboard', fontsize=20,
                    color=COLORS['text_primary'], fontweight='bold', y=0.96)

        gs = GridSpec(3, 3, figure=fig, hspace=0.4, wspace=0.3,
                     left=0.05, right=0.95, top=0.90, bottom=0.08)

        # Panel 1: VIX Gauge (large)
        ax_vix = fig.add_subplot(gs[0:2, 0:2])
        self._draw_vix_gauge(ax_vix, data.get('vix', 20))

        # Panel 2: Fear & Greed
        ax_fg = fig.add_subplot(gs[0, 2])
        self._draw_fear_greed_meter(ax_fg, data.get('fear_greed', 50))

        # Panel 3: Fed Rate
        ax_fed = fig.add_subplot(gs[1, 2])
        self._draw_indicator_card(ax_fed, 'FED RATE',
                                  data.get('fed_rate', 5.25), '%', '#f7931a')

        # Panel 4: Unemployment
        ax_unemp = fig.add_subplot(gs[2, 0])
        self._draw_indicator_card(ax_unemp, 'UNEMPLOYMENT',
                                  data.get('unemployment', 4.0), '%', '#2962ff')

        # Panel 5: CPI Inflation
        ax_cpi = fig.add_subplot(gs[2, 1])
        self._draw_indicator_card(ax_cpi, 'CPI INFLATION',
                                  data.get('cpi', 3.0), '%', '#ab47bc')

        # Panel 6: 10Y Treasury
        ax_treasury = fig.add_subplot(gs[2, 2])
        self._draw_indicator_card(ax_treasury, '10Y TREASURY',
                                  data.get('treasury_10y', 4.5), '%', '#00bcd4')

        # Watermark
        fig.text(0.99, 0.01, '@lkiwanSP500', fontsize=11,
                color=COLORS['text_muted'], alpha=0.8,
                ha='right', va='bottom', fontfamily='monospace',
                fontweight='bold')

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

    def _draw_vix_gauge(self, ax, vix_value: float):
        """Draw VIX gauge with colored zones."""
        ax.set_facecolor(COLORS['background'])
        ax.set_xlim(-1.5, 1.5)
        ax.set_ylim(-0.4, 1.3)
        ax.axis('off')

        # Draw gauge arc segments
        import matplotlib.patches as mpatches

        zones = [
            (0, 15, COLORS['vix_extreme_greed'], 'GREED'),
            (15, 20, COLORS['vix_greed'], ''),
            (20, 25, COLORS['vix_neutral'], 'NEUTRAL'),
            (25, 30, COLORS['vix_fear'], ''),
            (30, 50, COLORS['vix_extreme_fear'], 'FEAR'),
        ]

        for vix_min, vix_max, color, label in zones:
            theta1 = 180 - (vix_min / 50 * 180)
            theta2 = 180 - (vix_max / 50 * 180)
            wedge = mpatches.Wedge((0, 0), 1.0, theta2, theta1,
                                   width=0.35, facecolor=color, alpha=0.85,
                                   edgecolor=COLORS['background'], linewidth=2)
            ax.add_patch(wedge)

        # Draw needle
        needle_angle = np.radians(180 - (min(vix_value, 50) / 50 * 180))
        needle_x = 0.75 * np.cos(needle_angle)
        needle_y = 0.75 * np.sin(needle_angle)

        ax.annotate('', xy=(needle_x, needle_y), xytext=(0, 0),
                   arrowprops=dict(arrowstyle='->', color='white', lw=3))
        ax.plot(0, 0, 'o', color='white', markersize=12, zorder=5)
        ax.plot(0, 0, 'o', color=COLORS['background'], markersize=6, zorder=6)

        # VIX value text
        ax.text(0, -0.2, f'{vix_value:.1f}', fontsize=42,
               ha='center', va='center', color=COLORS['text_primary'],
               fontweight='bold')
        ax.text(0, 0.5, 'VIX', fontsize=28,
               ha='center', va='center', color=COLORS['text_secondary'],
               fontweight='bold')

        # Zone labels
        ax.text(-1.15, 0.4, 'GREED', fontsize=11, color=COLORS['vix_greed'],
               ha='center', va='center', fontweight='bold')
        ax.text(1.15, 0.4, 'FEAR', fontsize=11, color=COLORS['vix_fear'],
               ha='center', va='center', fontweight='bold')

    def _draw_fear_greed_meter(self, ax, score: float):
        """Draw Fear & Greed meter."""
        ax.set_facecolor(COLORS['panel_bg'])
        ax.set_xlim(0, 100)
        ax.set_ylim(0, 1)
        ax.axis('off')

        # Background bar
        for i in range(100):
            if i < 25:
                color = '#f44336'
            elif i < 45:
                color = '#ff9800'
            elif i < 55:
                color = '#ffeb3b'
            elif i < 75:
                color = '#8bc34a'
            else:
                color = '#4caf50'
            ax.bar(i, 0.4, bottom=0.3, width=1, color=color, alpha=0.8)

        # Marker triangle
        ax.plot([score], [0.75], marker='v', markersize=15, color='white')
        ax.plot([score, score], [0.25, 0.7], color='white', linewidth=2)

        # Labels
        ax.text(50, 0.95, 'FEAR & GREED INDEX', fontsize=11,
               ha='center', va='top', color=COLORS['text_primary'],
               fontweight='bold')
        ax.text(score, 0.12, f'{score:.0f}', fontsize=20,
               ha='center', va='bottom', color=COLORS['text_primary'],
               fontweight='bold')
        ax.text(5, 0.5, 'Fear', fontsize=9, ha='left', va='center',
               color='#f44336', fontweight='bold')
        ax.text(95, 0.5, 'Greed', fontsize=9, ha='right', va='center',
               color='#4caf50', fontweight='bold')

    def _draw_indicator_card(self, ax, title: str, value: float,
                            unit: str, accent_color: str):
        """Draw a single indicator card."""
        ax.set_facecolor(COLORS['panel_bg'])
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')

        # Card border
        rect = mpatches.FancyBboxPatch((0.05, 0.05), 0.9, 0.9,
                                       boxstyle="round,pad=0.03",
                                       facecolor=COLORS['panel_bg'],
                                       edgecolor=accent_color,
                                       linewidth=2)
        ax.add_patch(rect)

        # Accent bar on top
        ax.plot([0.1, 0.9], [0.9, 0.9], color=accent_color, linewidth=4, solid_capstyle='round')

        # Content
        ax.text(0.5, 0.75, title, fontsize=11,
               ha='center', va='center', color=COLORS['text_secondary'],
               fontweight='bold')
        ax.text(0.5, 0.4, f'{value:.2f}{unit}', fontsize=24,
               ha='center', va='center', color=COLORS['text_primary'],
               fontweight='bold')

    def generate_performance_chart(self, data: dict) -> BytesIO:
        """Generate signal performance tracking chart."""

        fig = plt.figure(figsize=(14, 8), facecolor=COLORS['background'])

        # Title
        fig.suptitle('Signal Performance Tracking', fontsize=18,
                    color=COLORS['text_primary'], fontweight='bold', y=0.96)

        gs = GridSpec(2, 3, figure=fig, hspace=0.35, wspace=0.3,
                     left=0.08, right=0.95, top=0.88, bottom=0.1)

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
        fig.text(0.99, 0.01, '@lkiwanSP500', fontsize=11,
                color=COLORS['text_muted'], alpha=0.8,
                ha='right', va='bottom', fontfamily='monospace',
                fontweight='bold')

        buffer = BytesIO()
        fig.savefig(buffer, format='png', dpi=self.dpi,
                   facecolor=COLORS['background'],
                   edgecolor='none', bbox_inches='tight')
        buffer.seek(0)
        plt.close(fig)

        return buffer

    def _draw_portfolio_chart(self, ax, history: list, initial_value: float):
        """Draw portfolio value over time."""
        ax.set_facecolor(COLORS['panel_bg'])

        if not history or len(history) < 2:
            ax.text(0.5, 0.5, 'No trading history yet',
                   ha='center', va='center', color=COLORS['text_muted'],
                   fontsize=14, transform=ax.transAxes)
            ax.set_xticks([])
            ax.set_yticks([])
            return

        dates = [h[0] for h in history]
        values = [h[1] for h in history]

        # Line chart
        ax.plot(dates, values, color=COLORS['text_primary'], linewidth=2)

        # Fill under line
        ax.fill_between(dates, values, initial_value,
                       where=[v >= initial_value for v in values],
                       color=COLORS['profit'], alpha=0.3)
        ax.fill_between(dates, values, initial_value,
                       where=[v < initial_value for v in values],
                       color=COLORS['loss'], alpha=0.3)

        # Initial value line
        ax.axhline(y=initial_value, color=COLORS['text_muted'],
                  linestyle='--', linewidth=1, label=f'Start: ${initial_value:,.0f}')

        ax.set_ylabel('Portfolio Value ($)', color=COLORS['text_secondary'])
        ax.legend(loc='upper left', fontsize=9, framealpha=0.8,
                 facecolor=COLORS['background'])
        ax.tick_params(colors=COLORS['text_secondary'])

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

        wedges, texts = ax.pie(sizes, explode=explode, colors=colors, startangle=90,
                               wedgeprops={'linewidth': 2, 'edgecolor': COLORS['background']})

        # Center text
        ax.text(0, 0, f'{win_rate:.0f}%', fontsize=22,
               ha='center', va='center', color=COLORS['text_primary'],
               fontweight='bold')
        ax.text(0, -0.2, 'Win Rate', fontsize=10,
               ha='center', va='top', color=COLORS['text_secondary'])

        ax.set_title(f'{wins}W / {losses}L', fontsize=12,
                    color=COLORS['text_secondary'], pad=10)

    def _draw_monthly_bars(self, ax, monthly_returns: dict):
        """Draw monthly returns bar chart."""
        ax.set_facecolor(COLORS['panel_bg'])

        if not monthly_returns:
            ax.text(0.5, 0.5, 'No monthly data',
                   ha='center', va='center', color=COLORS['text_muted'],
                   fontsize=12, transform=ax.transAxes)
            ax.axis('off')
            return

        months = list(monthly_returns.keys())[-6:]
        returns = [monthly_returns[m] for m in months]
        colors = [COLORS['profit'] if r >= 0 else COLORS['loss'] for r in returns]

        ax.bar(range(len(months)), returns, color=colors,
               edgecolor=COLORS['background'], width=0.6)

        ax.axhline(y=0, color=COLORS['grid'], linewidth=0.5)
        ax.set_xticks(range(len(months)))
        ax.set_xticklabels([m[-2:] for m in months], fontsize=9)
        ax.set_ylabel('Return %', fontsize=9, color=COLORS['text_secondary'])
        ax.tick_params(colors=COLORS['text_secondary'], labelsize=8)
        ax.set_title('Monthly Returns', fontsize=11,
                    color=COLORS['text_secondary'], pad=8)

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
            ('Portfolio', f'${current:,.2f}', COLORS['text_primary']),
            ('Total Return', f'{total_return:+.2f}%', COLORS['profit'] if total_return >= 0 else COLORS['loss']),
            ('Total Trades', f'{total_trades}', COLORS['text_primary']),
            ('Total P&L', f'{data.get("total_pnl", 0):+.2f}%', COLORS['profit'] if data.get("total_pnl", 0) >= 0 else COLORS['loss']),
        ]

        ax.set_title('Key Metrics', fontsize=11, color=COLORS['text_secondary'], pad=8)

        y_positions = [0.8, 0.55, 0.30, 0.05]
        for (label, value, color), y in zip(metrics, y_positions):
            ax.text(0.1, y, label, fontsize=10,
                   ha='left', va='center', color=COLORS['text_secondary'])
            ax.text(0.9, y, value, fontsize=11,
                   ha='right', va='center', color=color, fontweight='bold')


def create_chart_generator() -> ChartGenerator:
    """Create and return a ChartGenerator instance."""
    return ChartGenerator()
