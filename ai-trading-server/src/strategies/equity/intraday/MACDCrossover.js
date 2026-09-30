import { BaseStrategy } from '../../base/BaseStrategy.js';
import { macd, ema, atrValue } from '../../../market/indicators/technical.js';

/**
 * MACD Crossover Intraday Strategy (Bull + Bear)
 *
 * Entry:
 *   Bull — MACD line crosses ABOVE signal line while histogram turns positive.
 *           Price above 21 EMA (trend filter).
 *   Bear — MACD line crosses BELOW signal line while histogram turns negative.
 *           Price below 21 EMA.
 *
 * Stop Loss : 1.5 × ATR(14) below/above entry
 * Target    : 3 × ATR(14) above/below entry  (1:2 R:R minimum)
 */
export class MACDCrossoverBull extends BaseStrategy {
  constructor(params = {}) {
    super('MACD_CROSSOVER_BULL', {
      fastPeriod: 12, slowPeriod: 26, signalPeriod: 9,
      emaTrend: 21, atrPeriod: 14, slMultiplier: 1.5, tgtMultiplier: 3,
      ...params,
    });
    this.type = 'INTRADAY';
    this.direction = 'BULLISH';
    this.instrumentType = 'EQ';
  }

  get minBars() { return 60; }

  analyze(bars) {
    const { valid, reason } = this.validate(bars);
    if (!valid) return this.noSignal(reason);

    const cl = this.closes(bars);
    const hi = this.highs(bars);
    const lo = this.lows(bars);

    const macdVals = macd(cl, this.params.fastPeriod, this.params.slowPeriod, this.params.signalPeriod);
    if (macdVals.length < 2) return this.noSignal('Not enough MACD data');

    const prev = macdVals.at(-2);
    const curr = macdVals.at(-1);
    const prevH = prev.histogram ?? (prev.MACD - prev.signal);
    const currH = curr.histogram ?? (curr.MACD - curr.signal);

    // Bullish crossover: histogram flips positive
    const crossover = prevH <= 0 && currH > 0;
    if (!crossover) return this.noSignal('No bullish MACD crossover');

    // Trend filter: price above 21 EMA
    const emaVals = ema(cl, this.params.emaTrend);
    const price = cl.at(-1);
    if (price < emaVals.at(-1)) return this.noSignal('Price below 21 EMA — not in uptrend');

    const atr = atrValue(hi, lo, cl, this.params.atrPeriod);
    const stopLoss = price - this.params.slMultiplier * atr;
    const target   = price + this.params.tgtMultiplier * atr;

    const strength = Math.min(100, 50 + (currH / atr) * 200);

    return this.signal('BUY', price, stopLoss, target, Math.round(strength), {
      atr, ema: emaVals.at(-1), macdHistogram: currH,
    });
  }
}

export class MACDCrossoverBear extends BaseStrategy {
  constructor(params = {}) {
    super('MACD_CROSSOVER_BEAR', {
      fastPeriod: 12, slowPeriod: 26, signalPeriod: 9,
      emaTrend: 21, atrPeriod: 14, slMultiplier: 1.5, tgtMultiplier: 3,
      ...params,
    });
    this.type = 'INTRADAY';
    this.direction = 'BEARISH';
    this.instrumentType = 'EQ';
  }

  get minBars() { return 60; }

  analyze(bars) {
    const { valid, reason } = this.validate(bars);
    if (!valid) return this.noSignal(reason);

    const cl = this.closes(bars);
    const hi = this.highs(bars);
    const lo = this.lows(bars);

    const macdVals = macd(cl, this.params.fastPeriod, this.params.slowPeriod, this.params.signalPeriod);
    if (macdVals.length < 2) return this.noSignal('Not enough MACD data');

    const prev = macdVals.at(-2);
    const curr = macdVals.at(-1);
    const prevH = prev.histogram ?? (prev.MACD - prev.signal);
    const currH = curr.histogram ?? (curr.MACD - curr.signal);

    // Bearish crossover: histogram flips negative
    const crossover = prevH >= 0 && currH < 0;
    if (!crossover) return this.noSignal('No bearish MACD crossover');

    const emaVals = ema(cl, this.params.emaTrend);
    const price = cl.at(-1);
    if (price > emaVals.at(-1)) return this.noSignal('Price above 21 EMA — not in downtrend');

    const atr = atrValue(hi, lo, cl, this.params.atrPeriod);
    const stopLoss = price + this.params.slMultiplier * atr;
    const target   = price - this.params.tgtMultiplier * atr;

    const strength = Math.min(100, 50 + (Math.abs(currH) / atr) * 200);

    return this.signal('SELL', price, stopLoss, target, Math.round(strength), {
      atr, ema: emaVals.at(-1), macdHistogram: currH,
    });
  }
}
