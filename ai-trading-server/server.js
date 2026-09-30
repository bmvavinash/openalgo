import express from 'express';
import { createServer } from 'http';
import { Server as SocketIO } from 'socket.io';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import rateLimit from 'express-rate-limit';
import cron from 'node-cron';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __dirname = dirname(fileURLToPath(import.meta.url));

import { config } from './src/config/index.js';
import { logger } from './src/config/logger.js';
import { connectDB } from './src/database/connection.js';
import apiRouter from './src/api/router.js';
import { MarketDataService } from './src/market/MarketDataService.js';
import { PositionManager } from './src/market/PositionManager.js';

// ─── Bootstrap ────────────────────────────────────────────────────────────────

async function bootstrap() {
  await connectDB();

  const app  = express();
  const http = createServer(app);
  const io   = new SocketIO(http, {
    cors: { origin: '*', methods: ['GET', 'POST'] },
  });

  // ── Middleware ──────────────────────────────────────────────────────────────
  app.use(helmet({ contentSecurityPolicy: false }));
  app.use(cors({ origin: '*', credentials: true }));
  app.use(express.json({ limit: '2mb' }));
  app.use(express.urlencoded({ extended: true }));
  app.use(morgan(config.server.isDev ? 'dev' : 'combined', {
    stream: { write: msg => logger.info(msg.trim()) },
  }));

  // Serve dashboard UI
  app.use(express.static(join(__dirname, 'public')));

  // Rate limiting
  app.use('/api/', rateLimit({
    windowMs: config.rateLimit.windowMs,
    max: config.rateLimit.max,
    standardHeaders: true,
    message: { error: 'Too many requests — please slow down' },
  }));

  // ── API Routes ──────────────────────────────────────────────────────────────
  app.use('/api/v1', apiRouter);

  // Root info
  app.get('/', (req, res) => {
    res.json({
      name: 'OpenAlgo Trading Server',
      version: '1.0.0',
      status: 'running',
      docs: '/api/v1/health',
      endpoints: [
        '/api/v1/auth',
        '/api/v1/strategies',
        '/api/v1/positions',
        '/api/v1/ai',
        '/api/v1/ipo',
        '/api/v1/market',
      ],
    });
  });

  // 404
  app.use((req, res) => res.status(404).json({ error: 'Route not found' }));

  // Global error handler
  app.use((err, req, res, next) => {
    logger.error(err.stack || err.message);
    res.status(err.status || 500).json({ error: err.message || 'Internal server error' });
  });

  // ── WebSocket ───────────────────────────────────────────────────────────────
  const mdService = new MarketDataService();
  const posMgr    = new PositionManager();

  io.on('connection', socket => {
    logger.debug(`WS client connected: ${socket.id}`);

    socket.on('subscribe:quote', async ({ symbol, exchange }) => {
      socket.join(`quote:${symbol}`);
      logger.debug(`WS subscribe quote: ${symbol}`);
    });

    socket.on('subscribe:positions', ({ userId }) => {
      socket.join(`positions:${userId}`);
    });

    socket.on('disconnect', () => {
      logger.debug(`WS client disconnected: ${socket.id}`);
    });
  });

  // Broadcast live quotes every 15s during market hours
  setInterval(async () => {
    if (!mdService.isMarketOpen()) return;
    try {
      const indices = await mdService.getIndices();
      io.emit('indices:update', { data: indices, ts: Date.now() });
    } catch {}
  }, 15000);

  // ── Scheduled Jobs ──────────────────────────────────────────────────────────

  // EOD square-off for intraday positions at 15:25 IST
  cron.schedule('25 15 * * 1-5', async () => {
    logger.info('Running EOD intraday square-off...');
    // In production: fetch all users with open intraday positions and close them
  }, { timezone: 'Asia/Kolkata' });

  // Market open briefing at 09:00 IST
  cron.schedule('0 9 * * 1-5', () => {
    logger.info('Market pre-open: generating morning briefing...');
    io.emit('market:preopen', { message: 'Market opens in 15 minutes', ts: Date.now() });
  }, { timezone: 'Asia/Kolkata' });

  // Market close at 15:31 IST
  cron.schedule('31 15 * * 1-5', () => {
    logger.info('Market closed for the day');
    io.emit('market:closed', { message: 'Market closed', ts: Date.now() });
  }, { timezone: 'Asia/Kolkata' });

  // ── Start ───────────────────────────────────────────────────────────────────
  http.listen(config.server.port, () => {
    logger.info(`OpenAlgo Trading Server running on port ${config.server.port}`);
    logger.info(`Environment: ${config.server.env}`);
    logger.info(`AI: Anthropic ${config.ai.enabled ? 'enabled' : 'disabled'} | OLLAMA ${config.ai.ollama.enabled ? 'enabled' : 'disabled'}`);
    logger.info(`Paper trading: ${config.trading.paperTrading}`);
  });

  // Graceful shutdown
  process.on('SIGTERM', () => {
    logger.info('SIGTERM received — shutting down gracefully');
    http.close(() => process.exit(0));
  });
}

bootstrap().catch(err => {
  console.error('Fatal startup error:', err);
  process.exit(1);
});
