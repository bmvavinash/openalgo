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

  // Simulated quote generator — deterministic ticks so the UI feels live in dev
  const QUOTE_BASE = {
    NIFTY: 22500, BANKNIFTY: 48200, FINNIFTY: 21300, SENSEX: 74000,
    RELIANCE: 2920, TCS: 4350, INFY: 1870, HDFCBANK: 1720, ICICIBANK: 1290,
    WIPRO: 595, BHARTIARTL: 1850, LT: 3680, SBIN: 840, KOTAKBANK: 1950,
    AXISBANK: 1190, BAJFINANCE: 7450, MARUTI: 13200, TATAMOTORS: 1020,
    TITAN: 3680, NESTLEIND: 2450, SUNPHARMA: 1890, ITC: 495, HCLTECH: 1920,
    TECHM: 1680, COALINDIA: 500, NTPC: 395, POWERGRID: 335,
  };

  function genQuote(sym) {
    const base = QUOTE_BASE[sym] || (500 + Math.abs(sym.charCodeAt(0) * 7) % 2000);
    const seed = (Date.now() / 5000 | 0) + sym.charCodeAt(0);
    const pct = Math.sin(seed) * 0.003 + Math.cos(seed * 1.7) * 0.002;
    const ltp = parseFloat((base * (1 + pct)).toFixed(2));
    const change = parseFloat((ltp - base).toFixed(2));
    return {
      symbol: sym, ltp, change,
      changePct: parseFloat(((change / base) * 100).toFixed(2)),
      high: parseFloat((ltp * 1.008).toFixed(2)),
      low: parseFloat((ltp * 0.992).toFixed(2)),
      volume: Math.floor((Math.abs(Math.sin(seed * 3)) * 900000) + 100000),
    };
  }

  // Track per-socket watchlist subscriptions
  const watchlistSubs = new Map(); // socketId → [symbol, ...]

  io.on('connection', socket => {
    logger.debug(`WS client connected: ${socket.id}`);

    socket.on('subscribe:quote', ({ symbol, exchange }) => {
      socket.join(`quote:${symbol}`);
      logger.debug(`WS subscribe quote: ${symbol}`);
    });

    socket.on('subscribe:positions', ({ userId }) => {
      socket.join(`positions:${userId}`);
    });

    // Client subscribes to a watchlist of symbols for live ticks
    socket.on('subscribe:watchlist', ({ symbols }) => {
      if (!Array.isArray(symbols)) return;
      const clean = symbols.map(s => String(s).toUpperCase().slice(0, 20)).slice(0, 30);
      watchlistSubs.set(socket.id, clean);
      logger.debug(`WS watchlist [${socket.id}]: ${clean.join(',')}`);
      // Immediately emit first tick
      socket.emit('watchlist:update', {
        quotes: clean.map(genQuote),
        ts: Date.now(),
      });
    });

    socket.on('unsubscribe:watchlist', () => {
      watchlistSubs.delete(socket.id);
    });

    socket.on('disconnect', () => {
      watchlistSubs.delete(socket.id);
      logger.debug(`WS client disconnected: ${socket.id}`);
    });
  });

  // Push watchlist ticks every 5s to subscribed clients
  setInterval(() => {
    watchlistSubs.forEach((symbols, socketId) => {
      const sock = io.sockets.sockets.get(socketId);
      if (!sock) { watchlistSubs.delete(socketId); return; }
      sock.emit('watchlist:update', {
        quotes: symbols.map(genQuote),
        ts: Date.now(),
      });
    });
  }, 5000);

  // Broadcast live indices every 15s during market hours
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
