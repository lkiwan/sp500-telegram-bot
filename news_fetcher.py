# -*- coding: utf-8 -*-
"""
News Fetcher
============
Fetch market news and earnings from free APIs
"""

import os
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional


# API Keys (free tiers)
ALPHA_VANTAGE_KEY = os.environ.get("ALPHA_VANTAGE_KEY", "")
FINNHUB_KEY = os.environ.get("FINNHUB_KEY", "")


class NewsFetcher:
    """Fetch market news from various free sources."""

    def __init__(self):
        self.alpha_vantage_key = ALPHA_VANTAGE_KEY
        self.finnhub_key = FINNHUB_KEY

    def get_market_news(self, limit: int = 5) -> List[Dict]:
        """Get general market news."""
        news = []

        # Try Finnhub first (free tier: 60 calls/min)
        if self.finnhub_key:
            try:
                url = "https://finnhub.io/api/v1/news"
                params = {
                    'category': 'general',
                    'token': self.finnhub_key
                }
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    for item in data[:limit]:
                        news.append({
                            'headline': item.get('headline', ''),
                            'summary': item.get('summary', '')[:200],
                            'source': item.get('source', 'Finnhub'),
                            'url': item.get('url', ''),
                            'datetime': datetime.fromtimestamp(item.get('datetime', 0))
                        })
                    if news:
                        return news
            except Exception as e:
                print(f"Finnhub error: {e}")

        # Try Alpha Vantage news sentiment (free: 25 requests/day)
        if self.alpha_vantage_key:
            try:
                url = "https://www.alphavantage.co/query"
                params = {
                    'function': 'NEWS_SENTIMENT',
                    'tickers': 'SPY',
                    'apikey': self.alpha_vantage_key,
                    'limit': limit
                }
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    feed = data.get('feed', [])
                    for item in feed[:limit]:
                        news.append({
                            'headline': item.get('title', ''),
                            'summary': item.get('summary', '')[:200],
                            'source': item.get('source', 'Alpha Vantage'),
                            'url': item.get('url', ''),
                            'sentiment': item.get('overall_sentiment_label', 'Neutral')
                        })
                    if news:
                        return news
            except Exception as e:
                print(f"Alpha Vantage error: {e}")

        # Fallback: Return placeholder
        return [{
            'headline': 'Market Update',
            'summary': 'Check major financial news sources for the latest updates.',
            'source': 'System',
            'url': ''
        }]

    def get_sp500_news(self, limit: int = 5) -> List[Dict]:
        """Get S&P 500 specific news."""
        if self.finnhub_key:
            try:
                url = "https://finnhub.io/api/v1/company-news"
                # Get news for SPY (S&P 500 ETF)
                params = {
                    'symbol': 'SPY',
                    'from': (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'),
                    'to': datetime.now().strftime('%Y-%m-%d'),
                    'token': self.finnhub_key
                }
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    news = []
                    for item in data[:limit]:
                        news.append({
                            'headline': item.get('headline', ''),
                            'summary': item.get('summary', '')[:200],
                            'source': item.get('source', 'Finnhub'),
                            'datetime': datetime.fromtimestamp(item.get('datetime', 0))
                        })
                    return news
            except Exception as e:
                print(f"Finnhub SP500 news error: {e}")

        return self.get_market_news(limit)

    def get_earnings_calendar(self) -> List[Dict]:
        """Get upcoming earnings for major S&P 500 companies."""
        # Major S&P 500 companies to track
        major_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'META', 'TSLA']
        earnings = []

        if self.finnhub_key:
            today = datetime.now()
            from_date = today.strftime('%Y-%m-%d')
            to_date = (today + timedelta(days=14)).strftime('%Y-%m-%d')

            try:
                url = "https://finnhub.io/api/v1/calendar/earnings"
                params = {
                    'from': from_date,
                    'to': to_date,
                    'token': self.finnhub_key
                }
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    for item in data.get('earningsCalendar', []):
                        if item.get('symbol') in major_tickers:
                            earnings.append({
                                'symbol': item.get('symbol'),
                                'date': item.get('date'),
                                'eps_estimate': item.get('epsEstimate'),
                                'revenue_estimate': item.get('revenueEstimate'),
                                'hour': item.get('hour', 'bmo')  # bmo=before market open, amc=after market close
                            })
            except Exception as e:
                print(f"Finnhub earnings error: {e}")

        return earnings[:10]  # Limit to 10 upcoming

    def get_market_sentiment(self) -> Dict:
        """Get overall market sentiment from news."""
        if self.alpha_vantage_key:
            try:
                url = "https://www.alphavantage.co/query"
                params = {
                    'function': 'NEWS_SENTIMENT',
                    'tickers': 'SPY',
                    'apikey': self.alpha_vantage_key,
                    'limit': 50
                }
                response = requests.get(url, params=params, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    feed = data.get('feed', [])

                    # Aggregate sentiment
                    sentiments = {
                        'Bullish': 0,
                        'Somewhat-Bullish': 0,
                        'Neutral': 0,
                        'Somewhat-Bearish': 0,
                        'Bearish': 0
                    }

                    for item in feed:
                        label = item.get('overall_sentiment_label', 'Neutral')
                        if label in sentiments:
                            sentiments[label] += 1

                    total = sum(sentiments.values())
                    if total > 0:
                        bullish_pct = ((sentiments['Bullish'] + sentiments['Somewhat-Bullish']) / total) * 100
                        bearish_pct = ((sentiments['Bearish'] + sentiments['Somewhat-Bearish']) / total) * 100

                        if bullish_pct > 60:
                            overall = 'BULLISH'
                        elif bearish_pct > 60:
                            overall = 'BEARISH'
                        else:
                            overall = 'NEUTRAL'

                        return {
                            'overall': overall,
                            'bullish_pct': bullish_pct,
                            'bearish_pct': bearish_pct,
                            'neutral_pct': (sentiments['Neutral'] / total) * 100,
                            'article_count': total
                        }
            except Exception as e:
                print(f"Sentiment analysis error: {e}")

        return {
            'overall': 'NEUTRAL',
            'bullish_pct': 33,
            'bearish_pct': 33,
            'neutral_pct': 34,
            'article_count': 0
        }


def format_news_post(news: List[Dict], title: str = "Market News") -> str:
    """Format news items for Telegram post."""
    if not news:
        return f"📰 <b>{title}</b>\n\nNo news available at this time."

    lines = [f"📰 <b>{title}</b>\n"]

    for i, item in enumerate(news[:5], 1):
        headline = item.get('headline', 'No headline')[:100]
        source = item.get('source', 'Unknown')
        sentiment = item.get('sentiment', '')

        # Sentiment emoji
        if sentiment:
            if 'Bullish' in sentiment:
                sent_emoji = '🟢'
            elif 'Bearish' in sentiment:
                sent_emoji = '🔴'
            else:
                sent_emoji = '⚪'
            lines.append(f"{i}. {sent_emoji} {headline}")
        else:
            lines.append(f"{i}. {headline}")

        lines.append(f"   <i>— {source}</i>\n")

    return '\n'.join(lines)


def format_earnings_post(earnings: List[Dict]) -> str:
    """Format earnings calendar for Telegram post."""
    if not earnings:
        return "📅 <b>Earnings Calendar</b>\n\nNo major earnings this week."

    lines = ["📅 <b>Upcoming Earnings (Major Companies)</b>\n"]

    for item in earnings[:7]:
        symbol = item.get('symbol', '')
        date = item.get('date', '')
        hour = item.get('hour', '')

        timing = '🌅 Pre-Market' if hour == 'bmo' else '🌙 After Hours'
        lines.append(f"• <b>{symbol}</b> - {date} ({timing})")

    lines.append("\n<i>Track these for potential market moves!</i>")

    return '\n'.join(lines)


if __name__ == "__main__":
    fetcher = NewsFetcher()

    print("=== Market News ===")
    news = fetcher.get_market_news()
    print(format_news_post(news))

    print("\n=== Earnings Calendar ===")
    earnings = fetcher.get_earnings_calendar()
    print(format_earnings_post(earnings))

    print("\n=== Market Sentiment ===")
    sentiment = fetcher.get_market_sentiment()
    print(sentiment)
