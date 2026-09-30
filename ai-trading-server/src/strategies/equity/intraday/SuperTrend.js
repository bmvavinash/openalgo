import BaseStrategy from '../../base/BaseStrategy.js';
import { atr } from '../../../market/indicators/technical.js';

/**
 * SuperTrend Strategy — most widely used intraday trend-following indicator in Indian markets.
 * Formula: Upper Band = (High+Low)/2 + multiplier × ATR
 *          Lower Band = (High+Low)/2 - multiplier × ATR
 * Trend = BULLISH when close > Upper Band, BEARISH when close < Lower Band.
 * Params: period=10, multiplier=3 (Zerodha Varsity default for 5-min bars)
 */
function computeSuperTrend(bars, period = 10, multiplier = 3) {
  if (bars.length < period + 1) return null;

  const atrValues = atr(bars.map(b => b.high), bars.map(b => b.low), bars.map(b => b.close), period);
  if (!atrValues || atrValues.length < 2) return null;

  const offset = bars.length - atrValues.length;
  const n = atrValues.length;

  const upperBand = new Array(n);
  const lowerBand = new Array(n);
  const superTrend = new Array(n);
  const trend = new Array(n);   // 1 = bullish, -1 = bearish

  for (let i = 0; i < n; i++) {
    const bar = bars[i + offset];
    const hl2 = (bar.high + bar.low) / 2;
    upperBand[i] = hl2 + multiplier * atrValues[i];
    lowerBand[i] = hl2 - multiplier * atrValues[i];
  }

  // Smooth bands and determine trend
  superTrend[0] = upperBand[0];
  trend[0] = -1;

  for (let i = 1; i < n; i++) {
    const prevClose = bars[i + offset - 1].close;
    const close = bars[i + offset].close;

    // Upper band: only move down, never up (prevents band flip noise)
    upperBand[i] = upperBand[i] < upperBand[i - 1] || prevClose > upperBand[i - 1]
      ? upperBand[i]
      : upperBand[i - 1];

    // Lower band: only move up, never down
    lowerBand[i] = lowerBand[i] > lowerBand[i - 1] || prevClose < lowerBand[i - 1]
      ? lowerBand[i]
      : lowerBand[i - 1];

    if (trend[i - 1] === -1) {
      trend[i] = close > upperBand[i] ? 1 : -1;
    } else {
      trend[i] = close < lowerBand[i] ? -1 : 1;
    }

    superTrend[i] = trend[i] === 1 ? lowerBand[i] : upperBand[i];
  }

  return { trend, superTrend, upperBand, lowerBand, n };
}

export class SuperTrendBull extends BaseStrategy {
  get minBars() { return 30; }

  constructor() {
    super('SUPERTREND_BULL', { period: 10, multiplier: 3 });
    this.type = 'INTRADAY';
    this.direction = 'BULLISH';
    this.instrumentType = 'EQ';
    this.description = 'SuperTrend bullish crossover — trend flips from bearish to bullish';
  }

  analyze(bars) {
    if (!this.validate(bars)) return this.noSignal('Insufficient bars');

    const st = computeSuperTrend(bars, this.params.period, this.params.multiplier);
    if (!st) return this.noSignal('SuperTrend calculation failed');

    const { trend, superTrend, n } = st;
    const prev = trend[n - 2];
    const curr = trend[n - 1];
    const close = bars[bars.length - 1].close;
    const stLine = superTrend[n - 1];

    // Fresh bullish crossover: trend was -1, now +1
    if (prev === -1 && curr === 1) {
      const atrVal = close - stLine;
      const stopLoss = stLine;  // SuperTrend line IS the stop loss
      const target   = close + atrVal * 2;
      let conf = 75;

      // Bonus: volume above average
      const avgVol = bars.slice(-20).reduce((s, b) => s + b.volume, 0) / 20;
      if (bars[bars.length - 1].volume > avgVol * 1.3) conf += 10;

      // Bonus: gap between price and ST line is healthy (>0.5% of price)
      if (atrVal / close > 0.005) conf += 5;

      conf = Math.min(conf, 95);
      return this.signal('BUY', close, stopLoss, target, conf, { superTrendLine: stLine, freshCross: true });
    }

    // Trend is already bullish — continuation signal (lower confidence)
    if (curr === 1) {
      const stopLoss = stLine;
      const target   = close + (close - stLine) * 1.5;
      return this.signal('BUY', close, stopLoss, target, 55, { superTrendLine: stLine, freshCross: false, reason: 'continuation' });
    }

    return this.noSignal('SuperTrend bearish');
  }
}

export class SuperTrendBear extends BaseStrategy {
  get minBars() { return 30; }

  constructor() {
    super('SUPERTREND_BEAR', { period: 10, multiplier: 3 });
    this.type = 'INTRADAY';
    this.direction = 'BEARISH';
    this.instrumentType = 'EQ';
    this.description = 'SuperTrend bearish crossover — trend flips from bullish to bearish';
  }

  analyze(bars) {
    if (!this.validate(bars)) return this.noSignal('Insufficient bars');

    const st = computeSuperTrend(bars, this.params.period, this.params.multiplier);
    if (!st) return this.noSignal('SuperTrend calculation failed');

    const { trend, superTrend, n } = st;
    const prev = trend[n - 2];
    const curr = trend[n - 1];
    const close = bars[bars.length - 1].close;
    const stLine = superTrend[n - 1];

    if (prev === 1 && curr === -1) {
      const atrVal = stLine - close;
      const stopLoss = stLine;
      const target   = close - atrVal * 2;
      let conf = 75;
      const avgVol = bars.slice(-20).reduce((s, b) => s + b.volume, 0) / 20;
      if (bars[bars.length - 1].volume > avgVol * 1.3) conf += 10;
      if (atrVal / close > 0.005) conf += 5;
      conf = Math.min(conf, 95);
      return this.signal('SELL', close, stopLoss, target, conf, { superTrendLine: stLine, freshCross: true });
    }

    if (curr === -1) {
      const stopLoss = stLine;
      const target   = close - (stLine - close) * 1.5;
      return this.signal('SELL', close, stopLoss, target, 55, { superTrendLine: stLine, freshCross: false });
    }

    return this.noSignal('SuperTrend bullish');
  }
}
