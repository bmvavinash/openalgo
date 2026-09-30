import { Router } from 'express';
import authRoutes from './routes/auth.js';
import strategiesRoutes from './routes/strategies.js';
import positionsRoutes from './routes/positions.js';
import aiRoutes from './routes/ai.js';
import ipoRoutes from './routes/ipo.js';
import marketRoutes from './routes/market.js';

const router = Router();

router.use('/auth',       authRoutes);
router.use('/strategies', strategiesRoutes);
router.use('/positions',  positionsRoutes);
router.use('/ai',         aiRoutes);
router.use('/ipo',        ipoRoutes);
router.use('/market',     marketRoutes);

// Health check
router.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

export default router;
