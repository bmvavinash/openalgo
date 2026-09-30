import { BaseStrategy } from '../../base/BaseStrategy.js';
import { sma, ema, atrValue, adxSignal } from '../../../market/indicators/technical.js';

/**
 * Golden Cross / Death Cross Positional Strategy
 *
 * Golden Cross (Bull): 50 SMA crosses above 200 SMA.
 *   Confirmation: ADX > 20, price above 50 SMA.
 *   This is a strong long-term uptrend signal.
 *
 * Death Cross (Bear): 50 SMA crosses below 200 SMA.
 *   Confirmation: ADX > 20, price below 50 SMA.
 *
 * Suitable for daily charts on large-cap equities and indices.
 * Target: 10-15% swing; SL at previous swing low/high.
 */
export class GoldenCross extends BaseStrategy {
  constructor(params = {}) {
    super('GOLDEN_CROSS', {
      fastPeriod: 50, slowPeriod: 200,
      adxPeriod: 14, adxMin: 20,
      atrPeriod: 14, slMultiplier: 2, tgtMultiplier: 5,
      ...params,
    });
    this.type = 'POSITIONAL';
    this.direction = 'BULLISH';
  }

  get minBars() { return 220; }

  analyze(bars) {
    const { valid, reason } = this.validate(bars);
    if (!valid) return this.noSignal(reason);

    const cl = this.closes(bars);
    const hi = this.highs(bars);
    const lo = this.lows(bars);

    const fastSMA = sma(cl, this.params.fastPeriod);
    const slowSMA = sma(cl, this.params.slowPeriod);

    if (fastSMA.length < 2 || slowSMA.length < 2) return this.noSignal('Not enough SMA data');

    const prevFast = fastSMA.at(-2), currFast = fastSMA.at(-1);
    const prevSlow = slowSMA.at(-2), currSlow = slowSMA.at(-1);

    // Golden cross: fast crosses above slow
    const crossed = prevFast <= prevSlow && currFast > currSlow;
    if (!crossed) {
      // Already crossed — check if still in uptrend for continuation
      const inUptrend = currFast > currSlow && cl.at(-1) > currFast;
      if (!inUptrend) return this.noSignal('No golden cross and not in established uptrend');
    }

    const price = cl.at(-1);
    if (price < currFast) return this.noSignal('Price below 50 SMA — wait for pullback to reclaim');

    const adxInfo = adxSignal(hi, lo, cl, this.params.adxPeriod);
    const atr = atrValue(hi, lo, cl, this.params.atrPeriod);

    const stopLoss = Math.min(price - this.params.slMultiplier * atr, currSlow * 0.97);
    const target   = price + this.params.tgtMultiplier * atr;

    const freshCross = crossed ? 20 : 0;
    const confidence = Math.min(88, 55 + freshCross + (adxInfo.strength ?? 0) * 0.6);

    return this.signal('BUY', price, stopLoss, target, Math.round(confidence), {
      fastSMA: currFast, slowSMA: currSlow, freshCross: crossed,
      adx: adxInfo.strength, atr,
    });
  }
}

export class DeathCross extends BaseStrategy {
  constructor(params = {}) {
    super('DEATH_CROSS', {
      fastPeriod: 50, slowPeriod: 200,
      adxPeriod: 14, adxMin: 20,
      atrPeriod: 14, slMultiplier: 2, tgtMultiplier: 5,
      ...params,
    });
    this.type = 'POSITIONAL';
    this.direction = 'BEARISH';
  }

  get minBars() { return 220; }

  analyze(bars) {
    const { valid, reason } = this.validate(bars);
    if (!valid) return this.noSignal(reason);

    const cl = this.closes(bars);
    const hi = this.highs(bars);
    const lo = this.lows(bars);

    const fastSMA = sma(cl, this.params.fastPeriod);
    const slowSMA = sma(cl, this.params.slowPeriod);

    if (fastSMA.length < 2 || slowSMA.length < 2) return this.noSignal('Not enough SMA data');

    const prevFast = fastSMA.at(-2), currFast = fastSMA.at(-1);
    const prevSlow = slowSMA.at(-2), currSlow = slowSMA.at(-1);

    const crossed = prevFast >= prevSlow && currFast < currSlow;
    if (!crossed) {
      const inDowntrend = currFast < currSlow && cl.at(-1) < currFast;
      if (!inDowntrend) return this.noSignal('No death cross and not in downtrend');
    }

    const price = cl.at(-1);
    if (price > currFast) return this.noSignal('Price above 50 SMA — wait for rejection');

    const adxInfo = adxSignal(hi, lo, cl, this.params.adxPeriod);
    const atr = atrValue(hi, lo, cl, this.params.atrPeriod);

    const stopLoss = Math.max(price + this.params.slMultiplier * atr, currSlow * 1.03);
    const target   = price - this.params.tgtMultiplier * atr;

    const freshCross = crossed ? 20 : 0;
    const confidence = Math.min(88, 55 + freshCross + (adxInfo.strength ?? 0) * 0.6);

    return this.signal('SELL', price, stopLoss, target, Math.round(confidence), {
      fastSMA: currFast, slowSMA: currSlow, freshCross: crossed,
      adx: adxInfo.strength, atr,
    });
  }
}
