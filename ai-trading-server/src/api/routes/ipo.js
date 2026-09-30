import { Router } from 'express';
import { body, validationResult } from 'express-validator';
import { protect } from '../../middleware/auth.js';
import IPO from '../../database/models/IPO.js';
import { IPOAnalyzer } from '../../strategies/ipo/IPOAnalyzer.js';
import { DecisionEngine } from '../../ai/DecisionEngine.js';

const router = Router();
const engine = new DecisionEngine();

// GET /api/ipo — list IPOs (filter by status)
router.get('/', protect, async (req, res) => {
  try {
    const { status, page = 1, limit = 20 } = req.query;
    const filter = status ? { status } : {};
    const total = await IPO.countDocuments(filter);
    const ipos = await IPO.find(filter)
      .sort({ 'dates.listing': -1 })
      .skip((page - 1) * limit)
      .limit(parseInt(limit));
    res.json({ total, page: parseInt(page), ipos });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/ipo/upcoming — upcoming IPOs
router.get('/upcoming', protect, async (req, res) => {
  try {
    const ipos = await IPO.find({ status: { $in: ['UPCOMING', 'OPEN'] } })
      .sort({ 'dates.open': 1 }).limit(20);
    res.json({ count: ipos.length, ipos });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/ipo/:id — single IPO detail with scoring
router.get('/:id', protect, async (req, res) => {
  try {
    const ipo = await IPO.findById(req.params.id);
    if (!ipo) return res.status(404).json({ error: 'IPO not found' });

    const analyzer = new IPOAnalyzer();
    const analysis = analyzer.analyze(ipo.toObject());

    res.json({ ipo, analysis });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// POST /api/ipo — create a new IPO entry
router.post('/', protect, [
  body('companyName').notEmpty(),
  body('priceRange.max').isFloat({ min: 1 }),
], async (req, res) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) return res.status(400).json({ errors: errors.array() });

  try {
    const ipo = await IPO.create(req.body);
    res.status(201).json({ ipo });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// PUT /api/ipo/:id — update IPO (subscription, GMP, listing data)
router.put('/:id', protect, async (req, res) => {
  try {
    const ipo = await IPO.findByIdAndUpdate(req.params.id, req.body, { new: true, runValidators: true });
    if (!ipo) return res.status(404).json({ error: 'IPO not found' });
    res.json({ ipo });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// POST /api/ipo/:id/ai-analyze — run AI analysis on the IPO
router.post('/:id/ai-analyze', protect, async (req, res) => {
  try {
    const ipo = await IPO.findById(req.params.id);
    if (!ipo) return res.status(404).json({ error: 'IPO not found' });

    const decision = await engine.analyzeIPO(ipo.toObject(), req.user._id);

    // Update IPO with AI analysis result
    await IPO.findByIdAndUpdate(req.params.id, {
      'aiAnalysis.recommendation': decision.recommendation,
      'aiAnalysis.confidence': decision.confidence,
      'aiAnalysis.fundamentalScore': decision.fundamentalScore,
      'aiAnalysis.valuationScore': decision.valuationScore,
      'aiAnalysis.industryScore': decision.industryScore,
      'aiAnalysis.summary': decision.summary,
      'aiAnalysis.lastAnalyzed': new Date(),
    });

    res.json({ ipoId: req.params.id, decision });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// POST /api/ipo/:id/listing-strategy — get listing day strategy
router.post('/:id/listing-strategy', protect, async (req, res) => {
  try {
    const ipo = await IPO.findById(req.params.id);
    if (!ipo) return res.status(404).json({ error: 'IPO not found' });

    const { ListingDayStrategy } = await import('../../strategies/ipo/ListingDayStrategy.js');
    const strat = new ListingDayStrategy();

    const result = strat.analyze({
      issuePrice: ipo.priceRange?.max || ipo.priceRange?.min,
      currentPrice: req.body.currentPrice,
      openPrice: req.body.openPrice,
      gotAllotment: req.body.gotAllotment ?? false,
      bars: req.body.bars || [],
      lotSize: ipo.lotSize || 1,
    });

    res.json({ ipoId: req.params.id, company: ipo.companyName, signal: result });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

export default router;
