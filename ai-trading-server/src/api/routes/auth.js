import { Router } from 'express';
import { body, validationResult } from 'express-validator';
import { v4 as uuidv4 } from 'uuid';
import User from '../../database/models/User.js';
import { generateToken, protect } from '../../middleware/auth.js';

const router = Router();

// POST /api/auth/register
router.post('/register', [
  body('name').trim().notEmpty().withMessage('Name required'),
  body('email').isEmail().normalizeEmail(),
  body('password').isLength({ min: 8 }).withMessage('Password min 8 chars'),
], async (req, res) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) return res.status(400).json({ errors: errors.array() });

  try {
    const existing = await User.findOne({ email: req.body.email });
    if (existing) return res.status(409).json({ error: 'Email already registered' });

    const user = await User.create({
      name: req.body.name,
      email: req.body.email,
      password: req.body.password,
      apiKey: uuidv4().replace(/-/g, ''),
    });

    const token = generateToken(user._id);
    res.status(201).json({ token, user: user.toPublic() });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// POST /api/auth/login
router.post('/login', [
  body('email').isEmail().normalizeEmail(),
  body('password').notEmpty(),
], async (req, res) => {
  const errors = validationResult(req);
  if (!errors.isEmpty()) return res.status(400).json({ errors: errors.array() });

  try {
    const user = await User.findOne({ email: req.body.email }).select('+password');
    if (!user || !(await user.comparePassword(req.body.password))) {
      return res.status(401).json({ error: 'Invalid credentials' });
    }

    user.lastLogin = new Date();
    await user.save();

    const token = generateToken(user._id);
    res.json({ token, user: user.toPublic() });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// GET /api/auth/me
router.get('/me', protect, (req, res) => {
  res.json({ user: req.user.toPublic() });
});

// PUT /api/auth/preferences
router.put('/preferences', protect, async (req, res) => {
  try {
    const allowed = ['riskPerTrade', 'maxPositions', 'paperTrading', 'aiEnabled', 'notifications'];
    const updates = {};
    for (const key of allowed) {
      if (req.body[key] !== undefined) updates[`preferences.${key}`] = req.body[key];
    }
    const user = await User.findByIdAndUpdate(req.user._id, { $set: updates }, { new: true });
    res.json({ user: user.toPublic() });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// PUT /api/auth/capital
router.put('/capital', protect, async (req, res) => {
  try {
    const { total, equity, options, cash } = req.body;
    const user = await User.findByIdAndUpdate(req.user._id, {
      $set: { capitalAllocation: { total, equity, options, cash } },
    }, { new: true });
    res.json({ user: user.toPublic() });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

// POST /api/auth/regenerate-api-key
router.post('/regenerate-api-key', protect, async (req, res) => {
  try {
    const newKey = uuidv4().replace(/-/g, '');
    await User.findByIdAndUpdate(req.user._id, { apiKey: newKey });
    res.json({ apiKey: newKey });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

export default router;
