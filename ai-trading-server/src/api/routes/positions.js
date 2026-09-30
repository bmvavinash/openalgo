import { Router } from 'express';
import { body, validationResult } from 'express-validator';
import { protect } from '../../middleware/auth.js';
import { PositionManager } from '../../market/PositionManager.js';
import { RiskManager } from '../../market/RiskManager.js';
import Position from '../../database/models/Position.js';

const router = Router();
const positionMgr = new PositionManager();

// GET /api/positions — all open positions for the user
router.get('/', protect, async (req, res) => {
  try {
    const positions = await positionMgr.getOpenPositions(req.user._id);
    res.json({ count: positions.length, positions });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/positions/summary — portfolio summary with unrealized P&L
router.get('/summary', protect, async (req, res) => {
  try {
    const summary = await positionMgr.getPortfolioSummary(req.user._id);
    res.json(summary);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/positions/history — closed positions
router.get('/history', protect, async (req, res) => {
  try {
    const { page = 1, limit = 50, symbol } = req.query;
    const filter = { userId: req.user._id, status: 'CLOSED' };
    if (symbol) filter.symbol = symbol.toUpperCase();

    const total = await Position.countDocuments(filter);
    const positions = await Position.find(filter)
      .sort({ closeTime: -1 })
      .skip((page - 1) * limit)
      .limit(parseInt(limit));

    res.json({ total, page: parseInt(page), positions });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/positions/:id — single position
router.get('/:id', protect, async (req, res) => {
  try {
    const pos = await Position.findOne({ _id: req.params.id, userId: req.user._id });
    if (!pos) return res.status(404).json({ error: 'Position not found' });
    res.json(pos);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// POST /api/positions — open a new position (paper or live)
router.post('/', protect, [
  body('symbol').notEmpty().toUpperCase(),
  body('direction').isIn(['LONG', 'SHORT']),
  body('quantity').isInt({ min: 1 }),
  body('entryPrice').isFloat({ min: 0.01 }),
  body('strategyType').isIn(['INTRADAY', 'POSITIONAL', 'OPTIONS', 'IPO']),
], async (req, res) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) return res.status(400).json({ errors: errors.array() });

  try {
    const rm = new RiskManager({
      maxPositions: req.user.preferences?.maxPositions,
      riskPerTrade: req.user.preferences?.riskPerTrade,
      capitalTotal: req.user.capitalAllocation?.total,
    });

    const riskCheck = await rm.check(req.user._id, {
      symbol: req.body.symbol,
      price: req.body.entryPrice,
      stopLoss: req.body.stopLoss,
    });

    if (!riskCheck.allowed) {
      return res.status(400).json({ error: riskCheck.reason });
    }

    const pos = await positionMgr.openPosition(req.user._id, {
      ...req.body,
      paperTrade: req.user.preferences?.paperTrading ?? true,
    });

    res.status(201).json({ position: pos, suggestedQty: riskCheck.suggestedQty });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// PUT /api/positions/:id/close — close a position
router.put('/:id/close', protect, async (req, res) => {
  try {
    const pos = await Position.findOne({ _id: req.params.id, userId: req.user._id });
    if (!pos) return res.status(404).json({ error: 'Position not found' });
    if (pos.status !== 'OPEN') return res.status(400).json({ error: 'Position is not open' });

    const { exitPrice, exitReason } = req.body;
    if (!exitPrice) return res.status(400).json({ error: 'exitPrice required' });

    const closed = await positionMgr.closePosition(req.params.id, exitPrice, exitReason || 'MANUAL');
    res.json({ position: closed, message: `Closed at ₹${exitPrice}` });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// PUT /api/positions/:id — update SL/target/trailing
router.put('/:id', protect, async (req, res) => {
  try {
    const allowed = ['stopLoss', 'target', 'trailingStop', 'notes'];
    const updates = {};
    for (const k of allowed) if (req.body[k] !== undefined) updates[k] = req.body[k];

    const pos = await Position.findOneAndUpdate(
      { _id: req.params.id, userId: req.user._id, status: 'OPEN' },
      { $set: updates },
      { new: true }
    );
    if (!pos) return res.status(404).json({ error: 'Position not found or not open' });
    res.json(pos);
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// POST /api/positions/square-off-intraday — close all intraday positions
router.post('/square-off-intraday', protect, async (req, res) => {
  try {
    const results = await positionMgr.squareOffIntraday(req.user._id);
    res.json({ results, count: results.length });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

export default router;
