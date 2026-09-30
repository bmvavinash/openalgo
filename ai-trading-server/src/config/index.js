import dotenv from 'dotenv';
dotenv.config();

export const config = {
  server: {
    port: parseInt(process.env.PORT) || 5000,
    env: process.env.NODE_ENV || 'development',
    isDev: process.env.NODE_ENV !== 'production',
  },
  db: {
    uri: process.env.NODE_ENV === 'production'
      ? process.env.MONGODB_URI_PROD
      : process.env.MONGODB_URI || 'mongodb://localhost:27017/openalgo_trading',
  },
  jwt: {
    secret: process.env.JWT_SECRET || 'change_this_in_production',
    expiresIn: process.env.JWT_EXPIRES_IN || '7d',
  },
  openalgo: {
    apiUrl: process.env.OPENALGO_API_URL || 'http://localhost:5000',
    apiKey: process.env.OPENALGO_API_KEY || '',
  },
  ai: {
    anthropicKey: process.env.ANTHROPIC_API_KEY || '',
    model: process.env.AI_MODEL || 'claude-opus-5-5',
    enabled: process.env.AI_ANALYSIS_ENABLED !== 'false',
    ollama: {
      baseUrl: process.env.OLLAMA_BASE_URL || 'http://localhost:11434',
      model: process.env.OLLAMA_MODEL || 'llama3.2',
      enabled: process.env.OLLAMA_ENABLED === 'true',
    },
  },
  market: {
    timezone: process.env.MARKET_TIMEZONE || 'Asia/Kolkata',
    // NSE market hours IST
    openTime: '09:15',
    closeTime: '15:30',
    preMarketStart: '09:00',
    postMarketEnd: '16:00',
  },
  trading: {
    defaultRiskPercent: parseFloat(process.env.DEFAULT_RISK_PER_TRADE) || 1,
    maxOpenPositions: parseInt(process.env.MAX_OPEN_POSITIONS) || 10,
    maxDailyLossPercent: parseFloat(process.env.MAX_DAILY_LOSS_PERCENT) || 3,
    paperTrading: process.env.PAPER_TRADING !== 'false',
  },
  alerts: {
    webhookUrl: process.env.ALERT_WEBHOOK_URL || '',
    telegram: {
      botToken: process.env.TELEGRAM_BOT_TOKEN || '',
      chatId: process.env.TELEGRAM_CHAT_ID || '',
    },
  },
  rateLimit: {
    windowMs: parseInt(process.env.RATE_LIMIT_WINDOW_MS) || 900000,
    max: parseInt(process.env.RATE_LIMIT_MAX) || 100,
  },
};

export default config;
