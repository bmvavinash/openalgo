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

export default router;
