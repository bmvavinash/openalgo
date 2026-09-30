import Position from '../database/models/Position.js';
import Trade from '../database/models/Trade.js';
import Order from '../database/models/Order.js';
import { RiskManager } from './RiskManager.js';
import { logger } from '../config/logger.js';

/**
 * PositionManager — CRUD for positions with P&L tracking.
 */
export class PositionManager {
  constructor() {}

  async openPosition(userId, positionData) {
    const pos = new Position({
      userId,
      ...positionData,
      status: 'OPEN',
      openTime: new Date(),
    });
    await pos.save();
    logger.info(`Position opened: ${positionData.direction} ${positionData.symbol} × ${positionData.quantity} @ ${positionData.entryPrice}`);
    return pos;
  }

  async closePosition(positionId, exitPrice, exitReason = 'MANUAL') {
    const pos = await Position.findById(positionId);
    if (!pos || pos.status !== 'OPEN') {
      throw new Error('Position not found or not open');
    }

    const multiplier = pos.direction === 'LONG' ? 1 : -1;
    const realizedPnl = multiplier * (exitPrice - pos.entryPrice) * pos.quantity;
    const rm = new RiskManager();
    const charges = rm.calculateCharges(pos.instrumentType, pos.direction === 'LONG' ? 'SELL' : 'BUY', pos.quantity, exitPrice);

    pos.exitPrice    = exitPrice;
    pos.exitReason   = exitReason;
    pos.closeTime    = new Date();
    pos.status       = 'CLOSED';
    pos.realizedPnl  = realizedPnl - charges.total;
    pos.charges      = charges.total;
    pos.currentPrice = exitPrice;

    await pos.save();

    // Create a trade record
    await new Trade({
      userId: pos.userId,
      positionId: pos._id,
      symbol: pos.symbol,
      exchange: pos.exchange,
      instrumentType: pos.instrumentType,
      side: pos.direction === 'LONG' ? 'SELL' : 'BUY',
      quantity: pos.quantity,
      price: exitPrice,
      strategyName: pos.strategyName,
      strategyType: pos.strategyType,
      pnl: pos.realizedPnl,
      pnlPercent: (pos.realizedPnl / (pos.entryPrice * pos.quantity)) * 100,
      holdingDays: Math.floor((pos.closeTime - pos.openTime) / (86400 * 1000)),
      charges,
      paperTrade: pos.paperTrade,
    }).save();

    logger.info(`Position closed: ${pos.symbol} @ ${exitPrice} | P&L: ₹${pos.realizedPnl.toFixed(2)}`);
    return pos;
  }

  async updatePrice(positionId, currentPrice) {
    const pos = await Position.findById(positionId);
    if (!pos || pos.status !== 'OPEN') return null;

    const multiplier = pos.direction === 'LONG' ? 1 : -1;
    pos.currentPrice = currentPrice;
    pos.unrealizedPnl = multiplier * (currentPrice - pos.entryPrice) * pos.quantity;
    pos.unrealizedPnlPercent = (pos.unrealizedPnl / (pos.entryPrice * pos.quantity)) * 100;

    // Check SL/Target triggers
    let triggered = null;
    if (pos.direction === 'LONG') {
      if (pos.stopLoss && currentPrice <= pos.stopLoss) triggered = 'STOPLOSS';
      if (pos.target   && currentPrice >= pos.target)   triggered = 'TARGET';
      if (pos.trailingStop && currentPrice <= pos.trailingStop) triggered = 'TRAILING';
    } else {
      if (pos.stopLoss && currentPrice >= pos.stopLoss) triggered = 'STOPLOSS';
      if (pos.target   && currentPrice <= pos.target)   triggered = 'TARGET';
    }

    await pos.save();
    return { pos, triggered };
  }

  async getOpenPositions(userId) {
    return Position.find({ userId, status: 'OPEN' }).sort({ openTime: -1 });
  }

  async getPortfolioSummary(userId) {
    const positions = await this.getOpenPositions(userId);
    const today = new Date(); today.setHours(0, 0, 0, 0);

    const todayTrades = await Trade.find({ userId, tradeTime: { $gte: today } });
    const dailyPnl = todayTrades.reduce((s, t) => s + (t.pnl || 0), 0);

    const totalUnrealizedPnl = positions.reduce((s, p) => s + (p.unrealizedPnl || 0), 0);
    const totalInvested = positions.reduce((s, p) => s + (p.entryPrice * p.quantity), 0);

    return {
      openPositions: positions.length,
      totalInvested,
      totalUnrealizedPnl,
      totalUnrealizedPct: totalInvested > 0 ? (totalUnrealizedPnl / totalInvested) * 100 : 0,
      dailyPnl,
      positions,
    };
  }

  // EOD squared off for MIS/intraday positions
  async squareOffIntraday(userId) {
    const positions = await Position.find({
      userId,
      status: 'OPEN',
      strategyType: 'INTRADAY',
    });

    const results = [];
    for (const pos of positions) {
      try {
        const result = await this.closePosition(pos._id, pos.currentPrice || pos.entryPrice, 'EOD');
        results.push({ symbol: pos.symbol, result: 'CLOSED', pnl: result.realizedPnl });
      } catch (err) {
        results.push({ symbol: pos.symbol, result: 'FAILED', error: err.message });
      }
    }
    return results;
  }

  async updateTrailingStop(positionId, newTrailingStop) {
    return Position.findByIdAndUpdate(positionId, { trailingStop: newTrailingStop }, { new: true });
  }
}

export default PositionManager;
