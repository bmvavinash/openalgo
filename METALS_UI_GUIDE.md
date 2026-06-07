# Metals (Gold & Silver) Strategies – UI Guide

This guide explains **where** to find metals features in the OpenAlgo UI and **how** to use them.

---

## Trade hours and instrument types

- **MCX (Commodity):** 9:00 AM – 11:30 PM IST (23:30). Gold/Silver futures on MCX.
- **ETF (NSE):** 9:15 AM – **3:15 PM IST (15:15)**. Gold/Silver ETFs (e.g. GOLDBEES, SILVERETF) on NSE.

**Sell before market close:** For **ETF**, it is **recommended** to turn ON “Sell before market closes” so positions are squared off a few minutes before 3:15 PM and you avoid broker auto square-off and overnight risk. For MCX it is optional.

---

## 1. How to open the Metals section

### Option A: From the top navigation bar (recommended)

1. Log in to OpenAlgo at **http://127.0.0.1:5000** (or your server URL).
2. In the **top menu bar**, click **"Metals"** (between "Strategy" and "API Analyzer").
3. You will land on the **Metals Trading** dashboard.

### Option B: From the mobile/sidebar menu

1. On small screens, tap the **hamburger menu** (☰) to open the sidebar.
2. In the sidebar, click **"Metals (Gold & Silver)"**.
3. You will land on the same Metals Trading dashboard.

### Option C: Direct URL

- Open: **http://127.0.0.1:5000/metals**  
- You must be logged in; otherwise you will be redirected to the login page.

---

## 2. Metals Dashboard (`/metals`)

**URL:** `http://127.0.0.1:5000/metals`

**What you see:**

| Section | What it shows |
|--------|----------------|
| **Header** | Title "Metals Trading", subtitle "Gold & Silver trading with adaptive stop-loss", **Backtest Analysis** button, and **New Strategy** button. |
| **Stats (4 cards)** | **Gold Strategies** count, **Silver Strategies** count, **Open Trades** count, **Total Strategies** count. |
| **Open Positions** | Table of current open metals positions: Metal, Symbol, Action (BUY/SELL), Entry Price, Stop Loss, Current P&L, Entry Time. (Only visible if you have open trades.) |
| **Your Strategies** | List of your metals strategies. Each row shows: name, metal type (GOLD/SILVER), status (Active/Inactive), trading mode, and a **View** button. |
| **Recent Trades** | Last 10 trades: Metal, Action, Entry/Exit prices, P&L, Exit Reason, Date. Link **"View All"** goes to full trade history. |
| **Metals Trading Guide** | Short tips for Gold and Silver trading and adaptive stop-loss. |

**How to use it:**

- Click **Backtest Analysis** to run historical backtests for all strategies and see performance summary.
- Click **New Strategy** to create a Gold or Silver strategy.
- Click **View** on a strategy to open its detail page.
- Click **View All** next to Recent Trades to see full trade history.

---

## 3. Backtest Analysis (`/metals/analysis`)

**How to get there:** From the Metals dashboard, click **"Backtest Analysis"**, or open **http://127.0.0.1:5000/metals/analysis**.

**What you see:**

- **Run Historical Backtests:** Form with Start Date, End Date, Timeframe. Button **"Run Backtests for All Strategies"** runs backtests for all your metals strategies (uses historical data; works when market is closed). Results are saved and shown below and on each strategy page.
- **Latest Backtest by Strategy:** Table with Strategy name, Metal, Type (MCX/ETF), Period, Trades, Win Rate, P&L, P&L %, Max DD %, Sharpe, Profit Factor, Status, and **Run Backtest** link per strategy.

**How to check performance via UI:**

1. Go to **Metals** → **Backtest Analysis**.
2. Set Start/End date (e.g. last 30 days) and Timeframe (e.g. 5m).
3. Click **Run Backtests for All Strategies**. Wait for completion (flash message shows completed/errors).
4. Review the table: Win Rate, P&L, Sharpe, Profit Factor indicate how each strategy performed.
5. Click a strategy name to see full detail and **Recent Backtests**; or click **Run Backtest** for a single strategy with custom dates.

---

## 4. Create a new strategy (`/metals/strategy/new`)

**How to get there:** From the Metals dashboard, click **"New Strategy"**.

**What you can set:**

- **Strategy name**
- **Metal type:** GOLD, SILVER, PLATINUM, or COPPER
- **Exchange:** e.g. MCX
- **Symbol:** e.g. GOLDM, SILVERM (depends on metal type)
- **Product type:** e.g. MIS
- **Quantity**
- **Trading mode:** LONG or SHORT
- **Stop loss:** Type (FIXED, TRAILING, ATR_BASED, **ADAPTIVE**), percentage, trailing %, ATR multiplier
- **Take profit:** On/Off and percentage
- **Trading window:** Start time, End time
- **Alerts:** Telegram, WhatsApp (if configured)

**How to check:** After filling the form and submitting, you are redirected to the **strategy detail** page for that strategy.

---

## 5. Strategy detail page (`/metals/strategy/<id>`)

**How to get there:** From the Metals dashboard, click **View** on a strategy.

**What you see:**

| Section | What it shows |
|--------|----------------|
| **Header** | Strategy name, Active/Inactive badge, metal type (GOLD/SILVER), trading mode. Buttons: **Start/Stop Strategy**, **Run Backtest**, **Delete**. |
| **Performance Summary** | Total Trades, Win Rate %, Total P&L. |
| **Open Positions** | Open trades for this strategy (if any). |
| **Trade History** | Recent trades for this strategy. |
| **Backtests** | List of backtest runs and their results. |

**How to check:**

- **Start/Stop:** Toggle strategy active/inactive.
- **Run Backtest:** Opens the backtest form (date range, timeframe); after running, results appear on this page.
- **Delete:** Removes the strategy (with confirmation).

---

## 6. Trade history (`/metals/trades`)

**How to get there:**

- From the Metals dashboard, click **"View All"** next to **Recent Trades**, or  
- Open: **http://127.0.0.1:5000/metals/trades**

**What you see:**

- **Summary:** Total Trades, Winning Trades, Win Rate %, Total P&L.
- **Table:** All metals trades – Metal, Symbol, Action, Entry/Exit, P&L, Exit Reason, Date.

Use this to review all gold and silver trades in one place.

---

## 7. Open positions (`/metals/positions`)

**How to get there:** Open **http://127.0.0.1:5000/metals/positions**

**What you see:**

- Count of open positions.
- Table of all open metals positions: Metal, Symbol, Action, Entry Price, Stop Loss, Current P&L, Entry Time.

Use this to monitor current exposure in metals.

---

## 8. Run backtest (`/metals/strategy/<id>/backtest`)

**How to get there:** On a strategy’s detail page, click **"Run Backtest"**.

**What you do:**

- Set **Start Date** and **End Date**.
- Choose **Timeframe** (e.g. 5m, 15m, 1h).
- Click **Run Backtest**.

**What you get:** After the run, you are sent back to the strategy detail page where backtest results (trades, win rate, P&L, drawdown, Sharpe, etc.) appear in the **Backtests** section.

---

## 9. Quick reference – URLs

| Page | URL |
|------|-----|
| Metals dashboard | `/metals` or `http://127.0.0.1:5000/metals` |
| New strategy | `/metals/strategy/new` |
| Strategy detail | `/metals/strategy/<strategy_id>` |
| Trade history | `/metals/trades` |
| Open positions | `/metals/positions` |
| Run backtest | `/metals/strategy/<strategy_id>/backtest` |

---

## 10. Summary – “Where do I see what?”

- **Gold/Silver strategy list and counts** → Metals dashboard (`/metals`).
- **Create Gold/Silver strategy** → **New Strategy** → form with metal type (Gold/Silver, etc.).
- **Single strategy details and performance** → **View** on dashboard → strategy detail page.
- **All metals trades** → **View All** (dashboard) or `/metals/trades`.
- **Current metals positions** → `/metals/positions`.
- **Backtest a strategy** → Strategy detail → **Run Backtest** → set dates and timeframe → results on same strategy page.

If something is still unclear, say which screen you are on and what you want to do (e.g. “see only gold strategies” or “see P&L for last month”), and the steps can be narrowed down to that.
