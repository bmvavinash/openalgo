import { Router } from 'express';
import { protect } from '../../middleware/auth.js';
import { listStrategies, getStrategy, runAll } from '../../strategies/index.js';
import { MarketDataService } from '../../market/MarketDataService.js';
import { config } from '../../config/index.js';

const router = Router();
const marketData = new MarketDataService();

// GET /api/v1/strategies/demo — dev-only: run all strategies on synthetic bars, no auth needed
router.get('/demo', (req, res) => {
  if (!config.server.isDev) return res.status(403).json({ error: 'Demo only available in development' });

  const count = parseInt(req.query.bars) || 250;
  const trend = req.query.trend === 'bear' ? -0.001 : 0.001;
  const base  = parseFloat(req.query.base) || 22500;

  const bars = [];
  let price = base;
  for (let i = 0; i < count; i++) {
    const drift = price * trend;
    const noise = price * 0.005;
    const open  = price + (Math.random() - 0.4) * noise;
    const close = open + drift + (Math.random() - 0.4) * noise;
    const high  = Math.max(open, close) + Math.random() * noise * 0.5;
    const low   = Math.min(open, close) - Math.random() * noise * 0.5;
    bars.push({ time: new Date(Date.now() - (count - i) * 300000).toISOString(), open, high, low, close, volume: 500000 + Math.random() * 500000 });
    price = close;
  }

  const intradaySignals   = runAll('INTRADAY', bars);
  const positionalSignals = runAll('POSITIONAL', bars);
  const allSignals = [...intradaySignals, ...positionalSignals];

  res.json({
    note: 'Demo mode — synthetic price bars, no real market data',
    params: { bars: count, trend: req.query.trend || 'bull', basePrice: base },
    summary: {
      intraday:   { total: intradaySignals.length,   buy: intradaySignals.filter(s => s.action === 'BUY').length,  sell: intradaySignals.filter(s => s.action === 'SELL').length },
      positional: { total: positionalSignals.length, buy: positionalSignals.filter(s => s.action === 'BUY').length, sell: positionalSignals.filter(s => s.action === 'SELL').length },
    },
    signals: allSignals.sort((a, b) => b.confidence - a.confidence),
  });
});

// GET /api/strategies — list all available strategies
router.get('/', protect, (req, res) => {
  const { type, direction } = req.query;
  const list = listStrategies({ type, direction });
  res.json({ count: list.length, strategies: list });
});

// GET /api/strategies/:name — get a single strategy's metadata
router.get('/:name', protect, (req, res) => {
  const strategy = getStrategy(req.params.name);
  if (!strategy) return res.status(404).json({ error: 'Strategy not found' });
  res.json({
    name: strategy.name,
    type: strategy.type,
    direction: strategy.direction,
    instrumentType: strategy.instrumentType,
    minBars: strategy.minBars,
    params: strategy.params,
  });
});

// POST /api/strategies/:name/analyze — run a strategy against provided bars or live data
router.post('/:name/analyze', protect, async (req, res) => {
  try {
    const strategy = getStrategy(req.params.name);
    if (!strategy) return res.status(404).json({ error: 'Strategy not found' });

    let bars = req.body.bars;
    if (!bars) {
      const { symbol, exchange, interval } = req.body;
      if (!symbol) return res.status(400).json({ error: 'Provide bars or symbol' });
      bars = await marketData.getHistoricalData(symbol, exchange || 'NSE', interval || '5m', 200);
    }

    const signal = strategy.analyze(bars);
    res.json({ strategy: req.params.name, signal, barsUsed: bars.length });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// POST /api/strategies/scan — run all strategies for a symbol
router.post('/scan', protect, async (req, res) => {
  try {
    const { symbol, exchange, interval, type } = req.body;
    if (!symbol) return res.status(400).json({ error: 'symbol required' });

    const bars = await marketData.getHistoricalData(
      symbol, exchange || 'NSE', interval || '5m', 250
    );

    const signals = runAll(type || null, bars);
    const actionable = signals.filter(s => s.action !== 'HOLD' && s.confidence > 50);

    res.json({
      symbol, exchange, interval,
      barsLoaded: bars.length,
      totalSignals: signals.length,
      actionableSignals: actionable.length,
      signals: actionable,
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// POST /api/strategies/options/analyze — run options strategy analysis
router.post('/options/analyze', protect, async (req, res) => {
  try {
    const { symbol, exchange, strategyName } = req.body;
    if (!symbol) return res.status(400).json({ error: 'symbol required' });

    const strategy = getStrategy(strategyName);
    if (!strategy || strategy.type !== 'OPTIONS') {
      return res.status(400).json({ error: 'Invalid options strategy name' });
    }

    const chain = await marketData.getOptionsChain(symbol, exchange || 'NFO');
    const quote = await marketData.getQuote(symbol, exchange || 'NSE');

    const result = strategy.analyze({
      spotPrice: quote?.ltp || req.body.spotPrice,
      futurePrice: quote?.futurePrice || req.body.futurePrice,
      chain,
      expiry: req.body.expiry,
      lotSize: req.body.lotSize || 50,
      baseSignal: req.body.baseSignal,
      ivRank: req.body.ivRank,
    });

    res.json({ symbol, strategy: strategyName, result });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

export default router;
