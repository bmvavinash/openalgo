import { BaseStrategy } from '../../base/BaseStrategy.js';
import { rsi, macd, ema, atrValue, adxSignal } from '../../../market/indicators/technical.js';

/**
 * Multi-Indicator Momentum Intraday Strategy
 *
 * Bull: Strong upward momentum confirmed by:
 *   • RSI 50–70 range (momentum zone, not overextended)
 *   • MACD histogram positive and growing
 *   • ADX > 25 (trending), +DI > -DI
 *   • Price above EMA(9), EMA(21), EMA(50) stacked bullishly
 *
 * Bear: Mirror conditions on downside
 */
export class MomentumBull extends BaseStrategy {
  constructor(params = {}) {
    super('MOMENTUM_BULL', {
      rsiPeriod: 14, rsiMin: 50, rsiMax: 72,
      adxPeriod: 14, adxMin: 25,
      emas: [9, 21, 50],
      atrPeriod: 14, slMultiplier: 1.5, tgtMultiplier: 3,
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
    const price = cl.at(-1);

    // RSI check
    const rsiVals = rsi(cl, this.params.rsiPeriod);
    const currRsi = rsiVals.at(-1);
    if (currRsi < this.params.rsiMin || currRsi > this.params.rsiMax) {
      return this.noSignal(`RSI ${currRsi.toFixed(1)} not in momentum zone (${this.params.rsiMin}-${this.params.rsiMax})`);
    }

    // MACD — histogram positive and growing
    const macdVals = macd(cl);
    const prevM = macdVals.at(-2);
    const currM = macdVals.at(-1);
    if (!currM) return this.noSignal('Not enough MACD data');
    const currH = currM.histogram ?? (currM.MACD - currM.signal);
    const prevH = prevM.histogram ?? (prevM.MACD - prevM.signal);
    if (currH <= 0 || currH <= prevH) return this.noSignal('MACD histogram not positive and growing');

    // ADX trending
    const adxInfo = adxSignal(hi, lo, cl, this.params.adxPeriod);
    if (!adxInfo.trending) return this.noSignal(`ADX ${adxInfo.strength?.toFixed(1)} below threshold`);
    if (adxInfo.direction !== 'BULLISH') return this.noSignal('ADX direction not bullish');

    // EMA stack: price > ema9 > ema21 > ema50
    const emaVals = this.params.emas.map(p => ema(cl, p).at(-1));
    const [ema9, ema21, ema50] = emaVals;
    if (!(price > ema9 && ema9 > ema21 && ema21 > ema50)) {
      return this.noSignal('EMA stack not bullishly aligned');
    }

    const atr = atrValue(hi, lo, cl, this.params.atrPeriod);
    const stopLoss = price - this.params.slMultiplier * atr;
    const target   = price + this.params.tgtMultiplier * atr;

    const confidence = Math.min(92, 60 + (currRsi - 50) + adxInfo.strength * 0.5);

    return this.signal('BUY', price, stopLoss, target, Math.round(confidence), {
      rsi: currRsi, macdHistogram: currH, adx: adxInfo.strength,
      ema9, ema21, ema50, atr,
    });
  }
}

export class MomentumBear extends BaseStrategy {
  constructor(params = {}) {
    super('MOMENTUM_BEAR', {
      rsiPeriod: 14, rsiMin: 28, rsiMax: 50,
      adxPeriod: 14, adxMin: 25,
      emas: [9, 21, 50],
      atrPeriod: 14, slMultiplier: 1.5, tgtMultiplier: 3,
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
    const price = cl.at(-1);

    const rsiVals = rsi(cl, this.params.rsiPeriod);
    const currRsi = rsiVals.at(-1);
    if (currRsi < this.params.rsiMin || currRsi > this.params.rsiMax) {
      return this.noSignal(`RSI ${currRsi.toFixed(1)} not in bearish momentum zone`);
    }

    const macdVals = macd(cl);
    const prevM = macdVals.at(-2);
    const currM = macdVals.at(-1);
    if (!currM) return this.noSignal('Not enough MACD data');
    const currH = currM.histogram ?? (currM.MACD - currM.signal);
    const prevH = prevM.histogram ?? (prevM.MACD - prevM.signal);
    if (currH >= 0 || currH >= prevH) return this.noSignal('MACD histogram not negative and falling');

    const adxInfo = adxSignal(hi, lo, cl, this.params.adxPeriod);
    if (!adxInfo.trending) return this.noSignal('ADX not trending');
    if (adxInfo.direction !== 'BEARISH') return this.noSignal('ADX direction not bearish');

    const emaVals = this.params.emas.map(p => ema(cl, p).at(-1));
    const [ema9, ema21, ema50] = emaVals;
    if (!(price < ema9 && ema9 < ema21 && ema21 < ema50)) {
      return this.noSignal('EMA stack not bearishly aligned');
    }

    const atr = atrValue(hi, lo, cl, this.params.atrPeriod);
    const stopLoss = price + this.params.slMultiplier * atr;
    const target   = price - this.params.tgtMultiplier * atr;

    const confidence = Math.min(92, 60 + (50 - currRsi) + adxInfo.strength * 0.5);

    return this.signal('SELL', price, stopLoss, target, Math.round(confidence), {
      rsi: currRsi, macdHistogram: currH, adx: adxInfo.strength, ema9, ema21, ema50, atr,
    });
  }
}
