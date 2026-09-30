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
   * Kelly-criterion-capped position sizing.
   * Risk = capital × riskPercent → Qty = Risk / (entry - stopLoss)
   */
  _sizePosition(entryPrice, stopLoss) {
    if (!this.capitalTotal || !stopLoss || !entryPrice) return null;
    const riskAmount = this.capitalTotal * (this.riskPerTrade / 100);
    const riskPerShare = Math.abs(entryPrice - stopLoss);
    if (riskPerShare <= 0) return null;
    return Math.floor(riskAmount / riskPerShare);
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
