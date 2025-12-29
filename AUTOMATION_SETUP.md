# S&P 500 Telegram Bot - Automation Setup

## Overview

This bot automatically posts trading signals, analysis, and educational content to the Telegram channel **@lkiwanSP500** every 5 minutes during market hours.

---

## Architecture

```
┌─────────────────┐         ┌─────────────────┐         ┌──────────────┐
│  cron-job.org   │ ──────▶ │  GitHub Actions │ ──────▶ │   Telegram   │
│  Every 5 min    │   API   │  Smart Workflow │  Post   │  @lkiwanSP500│
└─────────────────┘         └─────────────────┘         └──────────────┘
```

---

## 1. cron-job.org Setup

### Account
- Website: https://cron-job.org
- Schedule: Every 5 minutes

### Cron Job Configuration

| Field | Value |
|-------|-------|
| **Title** | SP500 Bot |
| **URL** | `https://api.github.com/repos/lkiwan/sp500-telegram-bot/actions/workflows/market_signals.yml/dispatches` |
| **Method** | POST |
| **Schedule** | Every 5 minutes (`*/5 * * * *`) |
| **Days** | Monday - Friday |
| **Hours** | 12:00 - 23:00 UTC (7 AM - 6 PM ET) |
| **Timezone** | Africa/Casablanca (UTC+0) |

### Headers

| Header | Value |
|--------|-------|
| Authorization | `Bearer ghp_YOUR_GITHUB_TOKEN` |
| Accept | `application/vnd.github.v3+json` |
| Content-Type | `application/json` |

### Request Body
```json
{"ref":"master","inputs":{"command":"auto"}}
```

---

## 2. GitHub Token

### How to Create
1. Go to: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Settings:
   - Note: `sp500-cron-job`
   - Expiration: 90 days
   - Scopes: `repo`, `workflow`
4. Copy token (starts with `ghp_...`)

### Token Expiration
- Current token expires: **March 29, 2026**
- Set a reminder to renew before expiration

---

## 3. GitHub Actions Workflow

### File Location
`.github/workflows/market_signals.yml`

### Trigger
- **Primary**: cron-job.org (workflow_dispatch)
- **Backup**: None (GitHub cron was removed due to unreliability)

### Smart Command Logic
The workflow automatically determines what to post based on current UTC time:

#### Main Posts (Every 15 min: :00, :15, :30, :45)

| UTC Hour | :00 | :15 | :30 | :45 |
|----------|-----|-----|-----|-----|
| 12 | Good Morning | Wisdom | Earnings/Week Ahead | Premarket |
| 13 | Morning Briefing | Calendar | News | Sector Watch |
| 14 | Theory | Technical | Market Open | Opening Analysis |
| 15 | Signal | Momentum | Sentiment | Trend |
| 16 | Signal | History | Risk | Tip |
| 17 | Midday Recap | Theory | News | Why Market Moved |
| 18 | Signal | Factors | Economic | Simulation |
| 19 | Signal | Volume | Trend | Wisdom |
| 20 | Power Hour | Momentum | Sentiment | Positions |
| 21 | Market Close | Recap | Simulation | Journal |
| 22 | Tomorrow/Weekly | After Hours | Tip | Wisdom |
| 23 | Good Night | - | - | - |

#### Elite Scans (Every 5 min between main posts)
- Minutes: :05, :10, :20, :25, :35, :40, :50, :55
- During market hours (14:00-21:00 UTC)
- Only posts if ML confidence >= 70%

---

## 4. GitHub Secrets

### Required Secrets
Located at: https://github.com/lkiwan/sp500-telegram-bot/settings/secrets/actions

| Secret | Description |
|--------|-------------|
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather |
| `TELEGRAM_CHAT_ID` | Channel ID (@lkiwanSP500) |
| `FRED_API_KEY` | Federal Reserve Economic Data API |
| `FINNHUB_KEY` | Finnhub market data API |

---

## 5. Posting Schedule Summary

### Daily Posts (Monday-Friday)

| Time (ET) | Time (UTC) | Time (Morocco) | Posts |
|-----------|------------|----------------|-------|
| 7:00 AM - 9:30 AM | 12:00 - 14:30 | 12:00 - 14:30 | Pre-market (10 posts) |
| 9:30 AM - 12:00 PM | 14:30 - 17:00 | 14:30 - 17:00 | Market Open (10 posts) |
| 12:00 PM - 2:00 PM | 17:00 - 19:00 | 17:00 - 19:00 | Midday (8 posts) |
| 2:00 PM - 4:00 PM | 19:00 - 21:00 | 19:00 - 21:00 | Power Hour (8 posts) |
| 4:00 PM - 6:00 PM | 21:00 - 23:00 | 21:00 - 23:00 | After Hours (8 posts) |

### Total Daily Posts
- **Main posts**: ~44 posts (every 15 min)
- **Elite scans**: ~88 checks (every 5 min, posts only on high confidence)
- **Estimated actual posts**: 50-60 per day

---

## 6. Post Types

| Command | Description |
|---------|-------------|
| `gm` | Good Morning message |
| `gn` | Good Night message |
| `wisdom` | Trading wisdom quote |
| `theory` | Educational trading concept |
| `technical` | Technical analysis with chart |
| `signal` | ML-based trading signal |
| `elite` | High-confidence ML signal (70%+) |
| `news` | Market news summary |
| `sentiment` | Fear & Greed, VIX analysis |
| `economic` | Economic dashboard |
| `open` | Market open post |
| `close` | Market close recap |
| `simulation` | Portfolio simulation update |
| `momentum` | Momentum indicators |
| `history` | Historical market events |
| `why` | Explains market movements |
| `weekly` | Friday weekly report |

---

## 7. Troubleshooting

### cron-job.org not triggering
1. Check if cron job is enabled
2. Verify GitHub token hasn't expired
3. Check cron-job.org logs for errors

### GitHub Actions failing
1. Check Actions tab for error logs
2. Common issues:
   - Bash octal error (fixed with `+%-H` format)
   - Missing secrets
   - API rate limits

### No posts in Telegram
1. Verify bot is admin in channel
2. Check TELEGRAM_BOT_TOKEN is valid
3. Check TELEGRAM_CHAT_ID is correct

---

## 8. Maintenance

### Weekly
- Check Telegram channel for post quality
- Review signal performance

### Monthly
- Check GitHub token expiration
- Review cron-job.org logs
- Update trading wisdom/theory content

### Quarterly
- Renew GitHub token if needed
- Review and update ML model
- Analyze signal win rate

---

## 9. Files Structure

```
sp500-telegram-bot/
├── .github/
│   └── workflows/
│       └── market_signals.yml    # GitHub Actions workflow
├── bot.py                        # Main bot logic
├── chart_generator.py            # Creates charts
├── content_database.py           # Wisdom, theory, history content
├── predictor.py                  # ML signal prediction
├── fundamental_analysis.py       # Economic analysis
├── data/
│   └── signals.json              # Signal tracking data
├── models/
│   └── sp500_complete_20251113.pkl  # ML model
├── AUTOMATION_SETUP.md           # This file
└── POSTING_STRATEGY.md           # Content strategy
```

---

## 10. Quick Reference

### URLs
- GitHub Repo: https://github.com/lkiwan/sp500-telegram-bot
- GitHub Actions: https://github.com/lkiwan/sp500-telegram-bot/actions
- cron-job.org: https://cron-job.org
- Telegram Channel: https://t.me/lkiwanSP500

### Time Zones
- **UTC**: Server time
- **ET (Eastern)**: US market time (UTC-5)
- **Morocco (WET)**: Same as UTC in winter

### Market Hours
- US Market Open: 9:30 AM ET = 14:30 UTC
- US Market Close: 4:00 PM ET = 21:00 UTC

---

*Last updated: December 29, 2025*
