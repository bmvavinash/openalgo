import { Router } from 'express';
import { protect } from '../../middleware/auth.js';
import { MarketDataService } from '../../market/MarketDataService.js';
import Trade from '../../database/models/Trade.js';

const router = Router();
const marketData = new MarketDataService();

// GET /api/market/status — is market open
router.get('/status', protect, (req, res) => {
  res.json({
    isOpen: marketData.isMarketOpen(),
    isPreMarket: marketData.isPreMarket(),
    timezone: 'Asia/Kolkata',
    marketHours: '09:15 – 15:30 IST (Mon–Fri, excluding holidays)',
  });
});

// GET /api/market/quote/:symbol — live quote
router.get('/quote/:symbol', protect, async (req, res) => {
  try {
    const quote = await marketData.getQuote(req.params.symbol, req.query.exchange || 'NSE');
    if (!quote) return res.status(404).json({ error: 'Quote not available' });
    res.json(quote);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/market/history/:symbol — historical OHLCV
router.get('/history/:symbol', protect, async (req, res) => {
  try {
    const { exchange = 'NSE', interval = '5m', bars = 200 } = req.query;
    const data = await marketData.getHistoricalData(req.params.symbol, exchange, interval, parseInt(bars));
    res.json({ symbol: req.params.symbol, exchange, interval, count: data.length, bars: data });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/market/indices — all major NSE indices
router.get('/indices', protect, async (req, res) => {
  try {
    const indices = await marketData.getIndices();
    res.json(indices);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/market/option-chain/:symbol — options chain
router.get('/option-chain/:symbol', protect, async (req, res) => {
  try {
    const { exchange = 'NFO', expiry } = req.query;
    const chain = await marketData.getOptionsChain(req.params.symbol, exchange, expiry);
    res.json({ symbol: req.params.symbol, exchange, count: chain.length, chain });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/market/trades — trade history with P&L
router.get('/trades', protect, async (req, res) => {
  try {
    const { page = 1, limit = 50, symbol, from, to } = req.query;
    const filter = { userId: req.user._id };
    if (symbol) filter.symbol = symbol.toUpperCase();
    if (from || to) {
      filter.tradeTime = {};
      if (from) filter.tradeTime.$gte = new Date(from);
      if (to)   filter.tradeTime.$lte = new Date(to);
    }

    const total = await Trade.countDocuments(filter);
    const trades = await Trade.find(filter)
      .sort({ tradeTime: -1 })
      .skip((page - 1) * limit)
      .limit(parseInt(limit));

    const totalPnl = await Trade.aggregate([
      { $match: filter },
      { $group: { _id: null, total: { $sum: '$pnl' }, count: { $sum: 1 } } },
    ]);

    res.json({
      total, page: parseInt(page), trades,
      summary: totalPnl[0] || { total: 0, count: 0 },
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/market/pnl-report — daily/monthly P&L report
router.get('/pnl-report', protect, async (req, res) => {
  try {
    const { period = 'daily' } = req.query;
    const groupId = period === 'monthly'
      ? { year: { $year: '$tradeTime' }, month: { $month: '$tradeTime' } }
      : { year: { $year: '$tradeTime' }, month: { $month: '$tradeTime' }, day: { $dayOfMonth: '$tradeTime' } };

    const report = await Trade.aggregate([
      { $match: { userId: req.user._id } },
      {
        $group: {
          _id: groupId,
          pnl: { $sum: '$pnl' },
          trades: { $sum: 1 },
          wins: { $sum: { $cond: [{ $gt: ['$pnl', 0] }, 1, 0] } },
          charges: { $sum: '$charges.total' },
        },
      },
      { $sort: { '_id.year': -1, '_id.month': -1, '_id.day': -1 } },
      { $limit: 90 },
    ]);

    res.json({ period, report });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/v1/market/watchlist-demo?symbols=RELIANCE,TCS,INFY — simulated real-time quotes (no auth)
// Generates NSE-realistic prices with small random ticks, suitable for UI demos.
const BASE_PRICES = {
  NIFTY: 22500, BANKNIFTY: 48200, FINNIFTY: 21300, MIDCPNIFTY: 13200,
  SENSEX: 74000, RELIANCE: 2920, TCS: 4350, INFY: 1870, HDFCBANK: 1720,
  ICICIBANK: 1290, WIPRO: 595, BHARTIARTL: 1850, LT: 3680, ADANIENT: 3100,
  SBIN: 840, KOTAKBANK: 1950, AXISBANK: 1190, BAJFINANCE: 7450, MARUTI: 13200,
  TATAMOTORS: 1020, TITAN: 3680, NESTLEIND: 2450, SUNPHARMA: 1890,
  POWERGRID: 335, NTPC: 395, COALINDIA: 500, HINDUNILVR: 2680, ITC: 495,
  BAJAJFINSV: 1890, TECHM: 1680, HCLTECH: 1920, ULTRACEMCO: 11500,
};

router.get('/watchlist-demo', (req, res) => {
  const symbols = (req.query.symbols || '')
    .split(',')
    .map(s => s.trim().toUpperCase())
    .filter(Boolean)
    .slice(0, 30);

  if (!symbols.length) return res.status(400).json({ error: 'symbols query param required (comma-separated)' });

  const quotes = symbols.map(sym => {
    const base = BASE_PRICES[sym] || (500 + Math.abs(sym.charCodeAt(0) * 7 + sym.charCodeAt(1) * 13) % 3000);
    const seed = (Date.now() / 5000 | 0) + sym.charCodeAt(0);
    const pct = ((Math.sin(seed) * 0.003) + (Math.cos(seed * 1.7) * 0.002));
    const ltp = parseFloat((base * (1 + pct)).toFixed(2));
    const open = parseFloat((base * (1 + (Math.sin(seed * 0.5) * 0.005))).toFixed(2));
    const high = parseFloat(Math.max(ltp, open, base * 1.008).toFixed(2));
    const low  = parseFloat(Math.min(ltp, open, base * 0.992).toFixed(2));
    const change = parseFloat((ltp - base).toFixed(2));
    const changePct = parseFloat(((change / base) * 100).toFixed(2));
    return {
      symbol: sym,
      ltp, open, high, low, close: base,
      change, changePct,
      volume: Math.floor((Math.abs(Math.sin(seed * 3)) * 900000) + 100000),
      avgVolume: 500000,
      week52High: parseFloat((base * 1.35).toFixed(2)),
      week52Low: parseFloat((base * 0.72).toFixed(2)),
      marketCap: base > 1000 ? 'Large Cap' : base > 300 ? 'Mid Cap' : 'Small Cap',
      sector: ['IT', 'BANKING', 'ENERGY', 'PHARMA', 'AUTO', 'FMCG'][sym.charCodeAt(0) % 6],
      lastUpdated: new Date().toISOString(),
    };
  });

  res.json({ count: quotes.length, ts: Date.now(), quotes });
});

export default router;
