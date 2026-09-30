import { Router } from 'express';
import { protect } from '../../middleware/auth.js';
import { DecisionEngine } from '../../ai/DecisionEngine.js';
import { MarketDataService } from '../../market/MarketDataService.js';
import AIDecision from '../../database/models/AIDecision.js';

const router = Router();
const engine = new DecisionEngine();
const marketData = new MarketDataService();

// POST /api/ai/analyze/equity — AI analysis for a stock/index
router.post('/analyze/equity', protect, async (req, res) => {
  try {
    const { symbol, exchange = 'NSE', interval = '5m', timeframe = 'INTRADAY', bars } = req.body;
    if (!symbol && !bars) return res.status(400).json({ error: 'symbol or bars required' });

    const ohlcv = bars || await marketData.getHistoricalData(symbol, exchange, interval, 250);
    if (ohlcv.length < 30) return res.status(400).json({ error: 'Insufficient historical data' });

    const decision = await engine.analyzeEquity({
      symbol, exchange, bars: ohlcv, timeframe,
      userId: req.user._id,
    });

    res.json({ symbol, exchange, decision });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// POST /api/ai/analyze/options — AI options strategy recommendation
router.post('/analyze/options', protect, async (req, res) => {
  try {
    const { symbol, exchange = 'NFO', expiry, lotSize, baseSignal, ivRank } = req.body;
    if (!symbol) return res.status(400).json({ error: 'symbol required' });

    const chain  = await marketData.getOptionsChain(symbol, exchange, expiry);
    const quote  = await marketData.getQuote(symbol, 'NSE');

    const result = await engine.analyzeOptions?.({
      symbol, exchange,
      spotPrice: quote?.ltp || req.body.spotPrice,
      futurePrice: req.body.futurePrice,
      chain, expiry, lotSize: lotSize || 50, baseSignal, ivRank,
    }) || { error: 'Options AI analysis not yet configured' };

    res.json({ symbol, result });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// POST /api/ai/analyze/ipo — AI IPO analysis
router.post('/analyze/ipo', protect, async (req, res) => {
  try {
    const ipoData = req.body;
    if (!ipoData.companyName && !ipoData.symbol) {
      return res.status(400).json({ error: 'IPO company name or symbol required' });
    }

    const decision = await engine.analyzeIPO(ipoData, req.user._id);
    res.json({ decision });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// POST /api/ai/parse-recommendation — Parse external trading recommendation
router.post('/parse-recommendation', protect, async (req, res) => {
  try {
    const { rawText, source, symbol } = req.body;
    if (!rawText) return res.status(400).json({ error: 'rawText required' });

    const result = await engine.parseExternalRecommendation({
      rawText, source, symbol,
      userId: req.user._id,
    });

    res.json(result);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/ai/market-overview — AI market overview
router.get('/market-overview', protect, async (req, res) => {
  try {
    const indices = await marketData.getIndices();
    const result = await engine.getMarketOverview({
      niftyData: indices.NIFTY,
      bankNiftyData: indices.BANKNIFTY,
    }, req.user._id);
    res.json(result);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// POST /api/ai/scan-watchlist — AI scan multiple symbols
router.post('/scan-watchlist', protect, async (req, res) => {
  try {
    const { symbols, exchange = 'NSE', timeframe = 'INTRADAY' } = req.body;
    if (!Array.isArray(symbols) || symbols.length === 0) {
      return res.status(400).json({ error: 'symbols array required' });
    }
    if (symbols.length > 10) return res.status(400).json({ error: 'Max 10 symbols per scan' });

    const results = await Promise.allSettled(
      symbols.map(async symbol => {
        const bars = await marketData.getHistoricalData(symbol, exchange, '5m', 200);
        if (bars.length < 30) return { symbol, error: 'Insufficient data' };
        const decision = await engine.analyzeEquity({ symbol, exchange, bars, timeframe, userId: req.user._id });
        return { symbol, decision };
      })
    );

    const output = results.map((r, i) =>
      r.status === 'fulfilled' ? r.value : { symbol: symbols[i], error: r.reason?.message }
    );

    const actionable = output.filter(r => r.decision?.action && r.decision.action !== 'HOLD' && r.decision.confidence > 55);
    res.json({ total: output.length, actionable: actionable.length, results: output });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/ai/decisions — history of AI decisions for the user
router.get('/decisions', protect, async (req, res) => {
  try {
    const { page = 1, limit = 20, symbol, type } = req.query;
    const filter = { userId: req.user._id };
    if (symbol) filter.symbol = symbol.toUpperCase();
    if (type) filter.decisionType = type;

    const total = await AIDecision.countDocuments(filter);
    const decisions = await AIDecision.find(filter)
      .sort({ createdAt: -1 })
      .skip((page - 1) * limit)
      .limit(parseInt(limit));

    res.json({ total, page: parseInt(page), decisions });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

export default router;
