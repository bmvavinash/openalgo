import { Router } from 'express';
import { protect } from '../../middleware/auth.js';
import Alert from '../../database/models/Alert.js';

const router = Router();

// GET /api/v1/alerts — list active alerts for the logged-in user
router.get('/', protect, async (req, res) => {
  try {
    const { status = 'active' } = req.query;
    const filter = { userId: req.user._id };
    if (status === 'active')    filter.isActive = true;
    if (status === 'triggered') { filter.triggered = true; filter.isActive = false; }

    const alerts = await Alert.find(filter).sort({ createdAt: -1 }).limit(100);
    res.json({ total: alerts.length, alerts });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// POST /api/v1/alerts — create a new price/strategy alert
router.post('/', protect, async (req, res) => {
  try {
    const { symbol, exchange = 'NSE', alertType, condition, message, severity, channels } = req.body;
    if (!symbol)    return res.status(400).json({ error: 'symbol required' });
    if (!alertType) return res.status(400).json({ error: 'alertType required' });
    if (!message)   return res.status(400).json({ error: 'message required' });

    const validTypes = ['PRICE_ABOVE', 'PRICE_BELOW', 'VOLUME_SPIKE', 'STRATEGY_SIGNAL',
                        'POSITION_PNL', 'DAILY_LOSS_LIMIT', 'AI_SIGNAL', 'IPO_UPDATE'];
    if (!validTypes.includes(alertType)) {
      return res.status(400).json({ error: `alertType must be one of: ${validTypes.join(', ')}` });
    }

    const alert = await Alert.create({
      userId: req.user._id,
      symbol: symbol.toUpperCase(),
      exchange,
      alertType,
      condition: condition || {},
      message,
      severity: severity || 'INFO',
      channels: { console: true, ...(channels || {}) },
    });

    res.status(201).json({ alert });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// DELETE /api/v1/alerts/:id — deactivate an alert
router.delete('/:id', protect, async (req, res) => {
  try {
    const alert = await Alert.findOneAndUpdate(
      { _id: req.params.id, userId: req.user._id },
      { isActive: false },
      { new: true }
    );
    if (!alert) return res.status(404).json({ error: 'Alert not found' });
    res.json({ success: true });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// PUT /api/v1/alerts/:id/trigger — mark alert as triggered (called by monitoring job)
router.put('/:id/trigger', protect, async (req, res) => {
  try {
    const alert = await Alert.findOneAndUpdate(
      { _id: req.params.id, userId: req.user._id },
      { triggered: true, triggeredAt: new Date(), $inc: { triggerCount: 1 }, isActive: false },
      { new: true }
    );
    if (!alert) return res.status(404).json({ error: 'Alert not found' });
    res.json({ alert });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/v1/alerts/check — check if any active alerts would fire given current prices (no-auth demo)
router.get('/check-demo', async (req, res) => {
  const { symbol, price } = req.query;
  if (!symbol || !price) return res.status(400).json({ error: 'symbol and price required' });
  // In production this would query DB; for demo just echo
  res.json({
    symbol: symbol.toUpperCase(),
    price: parseFloat(price),
    triggered: [],
    message: 'Connect MongoDB and login to enable live alert checking',
  });
});

export default router;
