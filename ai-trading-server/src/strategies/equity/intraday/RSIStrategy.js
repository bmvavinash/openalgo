import { BaseStrategy } from '../../base/BaseStrategy.js';
import { rsi, ema, atrValue, bollingerBands } from '../../../market/indicators/technical.js';

/**
 * RSI Mean-Reversion Intraday Strategy
 *
 * Bull: RSI crosses back ABOVE oversold (30) from below + price within lower BB
 * Bear: RSI crosses back BELOW overbought (70) from above + price near upper BB
 *
 * Risk management: ATR-based SL, 2:1 R:R minimum
 */
export class RSIBull extends BaseStrategy {
  constructor(params = {}) {
    super('RSI_MEAN_REVERSION_BULL', {
      rsiPeriod: 14, oversold: 30, overbought: 70,
      emaTrend: 50, atrPeriod: 14, slMultiplier: 1.5, tgtMultiplier: 2.5,
      bbPeriod: 20, bbStdDev: 2,
      ...params,
    });
    this.type = 'INTRADAY';
    this.direction = 'BULLISH';
  }

  get minBars() { return 60; }

  analyze(bars) {
    const { valid, reason } = this.validate(bars);
    if (!valid) return this.noSignal(reason);

    const cl = this.closes(bars);
    const hi = this.highs(bars);
    const lo = this.lows(bars);

    const rsiVals = rsi(cl, this.params.rsiPeriod);
    if (rsiVals.length < 2) return this.noSignal('Not enough RSI data');

    const prevRsi = rsiVals.at(-2);
    const currRsi = rsiVals.at(-1);

    // Confirm RSI was below oversold and now crossing back above
    if (!(prevRsi < this.params.oversold && currRsi >= this.params.oversold)) {
      return this.noSignal('RSI not crossing from oversold');
    }

    const price = cl.at(-1);
    const emaVals = ema(cl, this.params.emaTrend);
    // Price should still be in valid range (not too far from trend)
    const bbVals = bollingerBands(cl, this.params.bbPeriod, this.params.bbStdDev);
    const bb = bbVals.at(-1);

    // Better signal if price is near or below lower BB
    const nearLowerBB = price <= bb.lower * 1.02;

    const atr = atrValue(hi, lo, cl, this.params.atrPeriod);
    const stopLoss = Math.min(price - this.params.slMultiplier * atr, lo.at(-1) - atr * 0.5);
    const target   = price + this.params.tgtMultiplier * atr;

    // Higher confidence if BB confirmation also present
    const confidence = nearLowerBB ? 80 : 60;

    return this.signal('BUY', price, stopLoss, target, confidence, {
      rsi: currRsi, prevRsi, atr, nearLowerBB,
      bbLower: bb.lower, bbMiddle: bb.middle, ema: emaVals.at(-1),
    });
  }
}

export class RSIBear extends BaseStrategy {
  constructor(params = {}) {
    super('RSI_MEAN_REVERSION_BEAR', {
      rsiPeriod: 14, oversold: 30, overbought: 70,
      emaTrend: 50, atrPeriod: 14, slMultiplier: 1.5, tgtMultiplier: 2.5,
      bbPeriod: 20, bbStdDev: 2,
      ...params,
    });
    this.type = 'INTRADAY';
    this.direction = 'BEARISH';
  }

  get minBars() { return 60; }

  analyze(bars) {
    const { valid, reason } = this.validate(bars);
    if (!valid) return this.noSignal(reason);

    const cl = this.closes(bars);
    const hi = this.highs(bars);
    const lo = this.lows(bars);

    const rsiVals = rsi(cl, this.params.rsiPeriod);
    if (rsiVals.length < 2) return this.noSignal('Not enough RSI data');

    const prevRsi = rsiVals.at(-2);
    const currRsi = rsiVals.at(-1);

    if (!(prevRsi > this.params.overbought && currRsi <= this.params.overbought)) {
      return this.noSignal('RSI not crossing from overbought');
    }

    const price = cl.at(-1);
    const bbVals = bollingerBands(cl, this.params.bbPeriod, this.params.bbStdDev);
    const bb = bbVals.at(-1);
    const nearUpperBB = price >= bb.upper * 0.98;

    const atr = atrValue(hi, lo, cl, this.params.atrPeriod);
    const stopLoss = Math.max(price + this.params.slMultiplier * atr, hi.at(-1) + atr * 0.5);
    const target   = price - this.params.tgtMultiplier * atr;

    const confidence = nearUpperBB ? 80 : 60;

    return this.signal('SELL', price, stopLoss, target, confidence, {
      rsi: currRsi, prevRsi, atr, nearUpperBB,
      bbUpper: bb.upper, bbMiddle: bb.middle,
    });
  }
}
