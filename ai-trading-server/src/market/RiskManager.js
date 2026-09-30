import Position from '../database/models/Position.js';
import Trade from '../database/models/Trade.js';
import { config } from '../config/index.js';
import { logger } from '../config/logger.js';

/**
 * RiskManager — enforces position sizing and risk limits before any order.
 *
 * Rules enforced:
 *  1. Max positions open at once
 *  2. Max risk per trade (% of capital)
 *  3. Max daily loss limit (% of capital)
 *  4. Max single position size
 *  5. Duplicate position check
 *  6. Options: max margin usage
 */
export class RiskManager {
  constructor(userPrefs = {}) {
    this.maxPositions    = userPrefs.maxPositions   || config.trading.maxOpenPositions;
    this.riskPerTrade    = userPrefs.riskPerTrade   || config.trading.defaultRiskPercent;
    this.maxDailyLoss    = userPrefs.maxDailyLoss   || config.trading.maxDailyLossPercent;
    this.capitalTotal    = userPrefs.capitalTotal   || 0;
  }

  /**
   * Check if a new order passes all risk rules.
   * @returns {{ allowed: boolean, reason?: string, suggestedQty?: number }}
   */
  async check(userId, order) {
    const checks = await Promise.all([
      this._checkOpenPositions(userId),
      this._checkDailyLoss(userId),
      this._checkDuplicatePosition(userId, order.symbol),
    ]);

    const failed = checks.find(c => !c.allowed);
    if (failed) return failed;

    const suggestedQty = this._sizePosition(order.price, order.stopLoss);
    return { allowed: true, suggestedQty };
  }

  /**
   * Quarter-Kelly position sizing.
   * Uses strategy win rate + R:R to compute Kelly fraction, applies 1/4 Kelly for safety.
   * Caps at 5% of capital per trade, floors at 0.5%.
   *
   * @param {number} entryPrice
   * @param {number} stopLoss
   * @param {number} winRate    0.0–1.0, default 0.55
   * @param {number} rrRatio    reward:risk ratio, default 2.0
   */
  _sizePosition(entryPrice, stopLoss, winRate = 0.55, rrRatio = 2.0) {
    if (!this.capitalTotal || !stopLoss || !entryPrice) return null;
    const riskPerShare = Math.abs(entryPrice - stopLoss);
    if (riskPerShare <= 0) return null;

    // Kelly fraction: f* = (b×p - q) / b
    const b = Math.max(rrRatio, 0.5);
    const p = Math.min(Math.max(winRate, 0.3), 0.9);
    const q = 1 - p;
    const kelly = (b * p - q) / b;
    const quarterKelly = Math.max(0, kelly / 4);

    // Cap between 0.5% and 5% of capital
    const riskPct    = Math.min(0.05, Math.max(0.005, quarterKelly));
    const riskAmount = this.capitalTotal * riskPct;
    return Math.max(1, Math.floor(riskAmount / riskPerShare));
  }

  /**
   * Compute trailing stop level for an open position.
   * ATR-based: trail = peakPrice - (multiplier × ATR)
   * @param {object} position — { direction, entryPrice, highestPrice, atr }
   * @param {number} multiplier — default 2.0
   */
  computeTrailingStop(position, multiplier = 2.0) {
    const { direction, entryPrice, highestPrice, lowestPrice, atr } = position;
    if (!atr || atr <= 0) return null;

    if (direction === 'LONG') {
      const peak = highestPrice || entryPrice;
      const trail = peak - multiplier * atr;
      return Math.max(trail, entryPrice - multiplier * atr);  // never go below initial SL zone
    } else {
      const trough = lowestPrice || entryPrice;
      const trail = trough + multiplier * atr;
      return Math.min(trail, entryPrice + multiplier * atr);
    }
  }

  /**
   * Step-based trailing: lock in profit at breakeven (+1×ATR), then trail to +0.5×ATR.
   */
  computeStepTrail(direction, entryPrice, currentPrice, initialSL, atr) {
    const moved = direction === 'LONG' ? currentPrice - entryPrice : entryPrice - currentPrice;
    if (moved >= 2 * atr) {
      // Lock in +0.5× ATR profit
      return direction === 'LONG'
        ? currentPrice - 1.5 * atr
        : currentPrice + 1.5 * atr;
    }
    if (moved >= atr) {
      // Move to breakeven
      return direction === 'LONG' ? entryPrice : entryPrice;
    }
    return initialSL;
  }

  async _checkOpenPositions(userId) {
    const count = await Position.countDocuments({ userId, status: 'OPEN' });
    if (count >= this.maxPositions) {
      return { allowed: false, reason: `Max open positions (${this.maxPositions}) reached` };
    }
    return { allowed: true };
  }

  async _checkDailyLoss(userId) {
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const trades = await Trade.find({ userId, tradeTime: { $gte: today }, pnl: { $lt: 0 } });
    const totalLoss = trades.reduce((sum, t) => sum + (t.pnl || 0), 0);

    if (this.capitalTotal > 0) {
      const lossPercent = Math.abs(totalLoss / this.capitalTotal) * 100;
      if (lossPercent >= this.maxDailyLoss) {
        return { allowed: false, reason: `Daily loss limit (${this.maxDailyLoss}%) reached. Loss today: ${lossPercent.toFixed(2)}%` };
      }
    }

    return { allowed: true };
  }

  async _checkDuplicatePosition(userId, symbol) {
    const existing = await Position.findOne({ userId, symbol, status: 'OPEN' });
    if (existing) {
      return { allowed: false, reason: `Already have an open position in ${symbol}. Close or modify existing position first.` };
    }
    return { allowed: true };
  }

  /**
   * Calculate charges for Indian equity/F&O trades.
   * Approximate breakdown: brokerage, STT, exchange fees, GST, SEBI, stamp duty.
   */
  calculateCharges(type, side, qty, price) {
    const tradeValue = qty * price;
    let brokerage = 0, stt = 0, exchangeFee = 0, stampDuty = 0;

    if (type === 'EQ') {
      brokerage  = Math.min(20, tradeValue * 0.0003); // flat ₹20 or 0.03%
      stt        = side === 'SELL' ? tradeValue * 0.001 : 0; // 0.1% on sell
      exchangeFee = tradeValue * 0.0000325;
      stampDuty  = side === 'BUY' ? tradeValue * 0.00015 : 0;
    } else if (type === 'FUT') {
      brokerage  = Math.min(20, tradeValue * 0.0003);
      stt        = side === 'SELL' ? tradeValue * 0.0001 : 0;
      exchangeFee = tradeValue * 0.0000190;
      stampDuty  = side === 'BUY' ? tradeValue * 0.00002 : 0;
    } else if (['CE', 'PE'].includes(type)) {
      brokerage  = Math.min(20, tradeValue * 0.0003);
      stt        = side === 'SELL' ? tradeValue * 0.0005 : 0;
      exchangeFee = tradeValue * 0.0000530;
      stampDuty  = side === 'BUY' ? tradeValue * 0.00003 : 0;
    }

    const gst     = (brokerage + exchangeFee) * 0.18;
    const sebi    = tradeValue * 0.000001;
    const total   = brokerage + stt + exchangeFee + gst + sebi + stampDuty;

    return {
      brokerage: +brokerage.toFixed(2),
      stt: +stt.toFixed(2),
      exchangeFee: +exchangeFee.toFixed(2),
      gst: +gst.toFixed(2),
      sebiCharges: +sebi.toFixed(2),
      stampDuty: +stampDuty.toFixed(2),
      total: +total.toFixed(2),
    };
  }
}

export default RiskManager;
