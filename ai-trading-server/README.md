# OpenAlgo Trading Server

Production-ready Node.js trading backend with AI-powered strategy execution, full position management, database persistence, and comprehensive strategy library.

## Features

- **16+ trading strategies** across equity intraday, positional, options (bull/bear/neutral), and IPO
- **AI-powered analysis** via Anthropic Claude (Opus) + OLLAMA (local, offline)
- **MongoDB** persistence for positions, trades, orders, IPOs, AI decisions
- **Real-time WebSocket** updates via Socket.io
- **Risk management** — position sizing, daily loss limits, duplicate position checks
- **Black-76 options pricing** (correct model for Indian index options)
- **IPO analyzer** with 5-factor scoring + AI deep analysis
- **Third-party recommendation parser** — paste any signal text and AI validates it
- **OpenAlgo API integration** for live market data and order placement

## Quick Start

```bash
# 1. Install dependencies
npm install

# 2. Configure environment
cp .env.example .env
# Edit .env — add MONGODB_URI and ANTHROPIC_API_KEY

# 3. Start MongoDB (if local)
# mongod --dbpath /data/db

# 4. Seed the database
node scripts/seed.js

# 5. Start the server
npm run dev    # development (auto-reload)
npm start      # production
```

## API Overview

Base URL: `http://localhost:5000/api/v1`

### Authentication
| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/register` | Register user |
| POST | `/auth/login` | Login, get JWT |
| GET | `/auth/me` | Current user |
| PUT | `/auth/preferences` | Update trading preferences |
| PUT | `/auth/capital` | Set capital allocation |

### Strategies
| Method | Path | Description |
|--------|------|-------------|
| GET | `/strategies` | List all strategies |
| GET | `/strategies/:name` | Strategy details |
| POST | `/strategies/:name/analyze` | Run one strategy |
| POST | `/strategies/scan` | Scan all strategies for a symbol |
| POST | `/strategies/options/analyze` | Options strategy analysis |

### Positions
| Method | Path | Description |
|--------|------|-------------|
| GET | `/positions` | Open positions |
| GET | `/positions/summary` | Portfolio P&L summary |
| GET | `/positions/history` | Closed positions |
| POST | `/positions` | Open new position |
| PUT | `/positions/:id/close` | Close position |
| PUT | `/positions/:id` | Update SL/target |
| POST | `/positions/square-off-intraday` | EOD square off |

### AI
| Method | Path | Description |
|--------|------|-------------|
| POST | `/ai/analyze/equity` | AI equity analysis |
| POST | `/ai/analyze/ipo` | AI IPO analysis |
| POST | `/ai/parse-recommendation` | Parse external signal |
| POST | `/ai/scan-watchlist` | Scan up to 10 symbols |
| GET | `/ai/market-overview` | Daily AI market overview |
| GET | `/ai/decisions` | AI decision history |

### IPO
| Method | Path | Description |
|--------|------|-------------|
| GET | `/ipo` | All IPOs |
| GET | `/ipo/upcoming` | Upcoming/open IPOs |
| GET | `/ipo/:id` | IPO detail + scoring |
| POST | `/ipo` | Add IPO |
| PUT | `/ipo/:id` | Update IPO data |
| POST | `/ipo/:id/ai-analyze` | Full AI IPO analysis |
| POST | `/ipo/:id/listing-strategy` | Listing day signals |

### Market
| Method | Path | Description |
|--------|------|-------------|
| GET | `/market/status` | Market open/closed |
| GET | `/market/quote/:symbol` | Live quote |
| GET | `/market/history/:symbol` | OHLCV bars |
| GET | `/market/indices` | NIFTY, BANKNIFTY, etc. |
| GET | `/market/option-chain/:symbol` | Options chain |
| GET | `/market/trades` | Trade history + P&L |
| GET | `/market/pnl-report` | Daily/monthly P&L |

## Strategies

### Equity Intraday (Bull + Bear)
- `MACD_CROSSOVER_BULL` / `MACD_CROSSOVER_BEAR` — histogram crossover + EMA trend filter
- `RSI_MEAN_REVERSION_BULL` / `BEAR` — RSI oversold/overbought + Bollinger Band confirmation
- `VWAP_BULL` / `VWAP_BEAR` — VWAP cross with volume confirmation + EMA(9) trend
- `ORB_BULL` / `ORB_BEAR` — Opening Range Breakout with volume confirmation
- `MOMENTUM_BULL` / `MOMENTUM_BEAR` — Multi-indicator momentum (RSI + MACD + ADX + EMA stack)

### Equity Positional (Bull + Bear)
- `GOLDEN_CROSS` — 50/200 SMA golden cross
- `DEATH_CROSS` — 50/200 SMA death cross
- `TREND_FOLLOWING_BULL` / `BEAR` — EMA 20/50/200 stack + ADX trending
- `SWING_TRADING_BULL` / `BEAR` — Pullback/bounce entries with RSI recovery

### Options
- `BULL_CALL_SPREAD` — ATM + OTM call debit spread for bullish bias
- `BEAR_PUT_SPREAD` — ATM + OTM put debit spread for bearish bias
- `IRON_CONDOR` — Sell OTM call + put spreads for range-bound market
- `SHORT_STRADDLE` — Sell ATM call + put in high IV
- `LONG_STRADDLE` — Buy ATM call + put before big events

### IPO
- `IPO_ANALYZER` — 5-factor scoring (valuation, growth, profitability, subscription, GMP)
- `LISTING_DAY` — Listing day entry/exit rules based on opening price vs issue price

## AI Configuration

### Anthropic Claude (Recommended)
Set `ANTHROPIC_API_KEY` in `.env`. Uses `claude-opus-5-5` by default for maximum analysis quality.

### OLLAMA (Local/Offline)
1. Install OLLAMA from https://ollama.ai
2. Pull a model: `ollama pull llama3.2`
3. Set `OLLAMA_ENABLED=true` in `.env`

OLLAMA is used as the primary AI when available (for privacy/cost), Anthropic as fallback.

## Testing

```bash
node tests/strategies.test.js   # 32 strategy unit tests
```

## Database

MongoDB is required. Free cloud option: [MongoDB Atlas](https://cloud.mongodb.com)

Set `MONGODB_URI_PROD` for Atlas, `MONGODB_URI` for local.

## Risk Disclaimer

This software is for educational and research purposes. Always use paper trading mode (`PAPER_TRADING=true`) until you have thoroughly tested your strategies. Never risk capital you cannot afford to lose.
