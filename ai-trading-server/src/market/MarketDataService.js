import axios from 'axios';
import { config } from '../config/index.js';
import { logger } from '../config/logger.js';

/**
 * MarketDataService — fetches OHLCV data via OpenAlgo API.
 *
 * OpenAlgo exposes broker-agnostic market data endpoints.
 * This service wraps those endpoints with caching and error handling.
 */
export class MarketDataService {
  constructor() {
    this.baseUrl = config.openalgo.apiUrl;
    this.apiKey  = config.openalgo.apiKey;
    this.cache   = new Map(); // symbol:tf → { data, ts }
    this.cacheTTL = 30 * 1000; // 30s for intraday, 5m for EOD
  }

  get headers() {
    return { 'X-API-KEY': this.apiKey, 'Content-Type': 'application/json' };
  }

  /**
   * Get historical OHLCV bars.
   * @param {string} symbol
   * @param {string} exchange  - NSE | BSE | NFO
   * @param {string} interval  - 1m | 5m | 15m | 1h | 1d
   * @param {number} bars      - number of bars (default 200)
   */
  async getHistoricalData(symbol, exchange, interval = '5m', bars = 200) {
    const cacheKey = `${symbol}:${exchange}:${interval}`;
    const cached = this.cache.get(cacheKey);
    const ttl = interval === '1d' ? 5 * 60 * 1000 : this.cacheTTL;
    if (cached && Date.now() - cached.ts < ttl) return cached.data;

    try {
      const resp = await axios.get(`${this.baseUrl}/api/v1/marketdata/history`, {
        headers: this.headers,
        params: { symbol, exchange, interval, count: bars },
        timeout: 10000,
      });

      const data = this._normalizeOHLCV(resp.data?.data || resp.data || []);
      this.cache.set(cacheKey, { data, ts: Date.now() });
      return data;
    } catch (err) {
      logger.warn(`MarketDataService.getHistoricalData [${symbol}]: ${err.message}`);
      return this._fallbackData(symbol, exchange, interval, bars);
    }
  }

  /**
   * Get live quote (LTP + OHLC for the day).
   */
  async getQuote(symbol, exchange = 'NSE') {
    try {
      const resp = await axios.get(`${this.baseUrl}/api/v1/marketdata/quote`, {
        headers: this.headers,
        params: { symbol, exchange },
        timeout: 5000,
      });
      return resp.data?.data || resp.data;
    } catch (err) {
      logger.warn(`MarketDataService.getQuote [${symbol}]: ${err.message}`);
      return null;
    }
  }

  /**
   * Get options chain for an index/stock.
   */
  async getOptionsChain(symbol, exchange = 'NFO', expiry = null) {
    try {
      const resp = await axios.get(`${this.baseUrl}/api/v1/marketdata/option-chain`, {
        headers: this.headers,
        params: { symbol, exchange, expiry },
        timeout: 15000,
      });
      return resp.data?.data || resp.data || [];
    } catch (err) {
      logger.warn(`MarketDataService.getOptionsChain [${symbol}]: ${err.message}`);
      return [];
    }
  }

  /**
   * Get indices data (NIFTY50, BANKNIFTY, etc.)
   */
  async getIndices() {
    const indices = ['NIFTY', 'BANKNIFTY', 'FINNIFTY', 'MIDCPNIFTY'];
    const results = {};
    await Promise.allSettled(
      indices.map(async idx => {
        try {
          const q = await this.getQuote(idx, 'NSE');
          if (q) results[idx] = q;
        } catch {}
      })
    );
    return results;
  }

  /**
   * Check if the market is currently open (NSE hours IST).
   */
  isMarketOpen() {
    const now = new Date();
    const ist = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
    const day = ist.getDay();
    if (day === 0 || day === 6) return false; // Weekend
    const h = ist.getHours();
    const m = ist.getMinutes();
    const time = h * 60 + m;
    return time >= 9 * 60 + 15 && time <= 15 * 60 + 30;
  }

  isPreMarket() {
    const now = new Date();
    const ist = new Date(now.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' }));
    const h = ist.getHours(), m = ist.getMinutes();
    const time = h * 60 + m;
    return time >= 9 * 60 && time < 9 * 60 + 15;
  }

  // ── Private ────────────────────────────────────────────────────────────────

  _normalizeOHLCV(raw) {
    if (!Array.isArray(raw)) return [];
    return raw.map(b => ({
      time:   b.time   || b.timestamp || b.date,
      open:   parseFloat(b.open   || b.o || 0),
      high:   parseFloat(b.high   || b.h || 0),
      low:    parseFloat(b.low    || b.l || 0),
      close:  parseFloat(b.close  || b.c || 0),
      volume: parseInt(b.volume   || b.v || 0, 10),
    })).filter(b => b.close > 0);
  }

  // Generate synthetic price data for development/testing when no real data is available
  _fallbackData(symbol, exchange, interval, bars) {
    logger.debug(`MarketDataService: using synthetic data for ${symbol}`);
    const seed = symbol.charCodeAt(0) + symbol.charCodeAt(symbol.length - 1);
    const basePrice = 1000 + (seed * 23) % 19000;
    const data = [];
    let price = basePrice;

    for (let i = bars; i >= 0; i--) {
      const volatility = price * 0.005;
      const open  = price + (Math.random() - 0.5) * volatility;
      const close = open  + (Math.random() - 0.5) * volatility * 2;
      const high  = Math.max(open, close) + Math.random() * volatility;
      const low   = Math.min(open, close) - Math.random() * volatility;
      const vol   = Math.floor(100000 + Math.random() * 900000);
      data.push({ time: new Date(Date.now() - i * 300000).toISOString(), open, high, low, close, volume: vol });
      price = close;
    }
    return data;
  }
}

export default MarketDataService;
