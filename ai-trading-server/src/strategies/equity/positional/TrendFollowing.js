import { BaseStrategy } from '../../base/BaseStrategy.js';
import { ema, atrValue, adxSignal, rsi } from '../../../market/indicators/technical.js';

/**
 * EMA Trend Following Positional Strategy
 *
 * Bull: Price > EMA(20) > EMA(50) > EMA(200) with ADX > 25
 *   Enter on pullback to EMA(20) or EMA(50) in uptrend
 *   RSI 40-65 on entry (not overextended)
 *
 * Bear: Price < EMA(20) < EMA(50) < EMA(200) with ADX > 25
 *   Enter on bounce to EMA(20) or EMA(50) in downtrend
 *
 * This is the core positional trend-following strategy.
 * Typical hold: 2–8 weeks; trailing stop with 2×ATR.
 */
export class TrendFollowingBull extends BaseStrategy {
  constructor(params = {}) {
    super('TREND_FOLLOWING_BULL', {
      emas: [20, 50, 200],
      adxPeriod: 14, adxMin: 25,
      rsiPeriod: 14, rsiMin: 40, rsiMax: 68,
      atrPeriod: 14, slMultiplier: 2, tgtMultiplier: 6,
      pullbackThreshold: 0.02, // price within 2% of EMA(20)
      ...params,
    });
    this.type = 'POSITIONAL';
    this.direction = 'BULLISH';
  }

  get minBars() { return 210; }

  analyze(bars) {
    const { valid, reason } = this.validate(bars);
    if (!valid) return this.noSignal(reason);

    const cl = this.closes(bars);
    const hi = this.highs(bars);
    const lo = this.lows(bars);
    const price = cl.at(-1);

    const [ema20, ema50, ema200] = this.params.emas.map(p => ema(cl, p));
    const [e20, e50, e200] = [ema20.at(-1), ema50.at(-1), ema200.at(-1)];

    // Bullish EMA stack
    if (!(price > e20 && e20 > e50 && e50 > e200)) {
      return this.noSignal('EMAs not in bullish stack alignment');
    }

    // ADX trending
    const adxInfo = adxSignal(hi, lo, cl, this.params.adxPeriod);
    if (adxInfo.strength < this.params.adxMin) {
      return this.noSignal(`ADX ${adxInfo.strength?.toFixed(1)} below minimum ${this.params.adxMin}`);
    }
    if (adxInfo.direction !== 'BULLISH') {
      return this.noSignal('ADX direction not bullish');
    }

    // RSI not overextended
    const rsiVals = rsi(cl, this.params.rsiPeriod);
    const currRsi = rsiVals.at(-1);
    if (currRsi < this.params.rsiMin || currRsi > this.params.rsiMax) {
      return this.noSignal(`RSI ${currRsi?.toFixed(1)} outside entry range`);
    }

    const atr = atrValue(hi, lo, cl, this.params.atrPeriod);
    const stopLoss = Math.max(e50 - atr, price - this.params.slMultiplier * atr);
    const target   = price + this.params.tgtMultiplier * atr;

    // Pullback bonus: price near EMA(20) gives better R:R
    const pullbackPct = (price - e20) / e20;
    const pullbackBonus = pullbackPct < this.params.pullbackThreshold ? 15 : 0;
    const confidence = Math.min(88, 50 + adxInfo.strength * 0.8 + pullbackBonus);

    return this.signal('BUY', price, stopLoss, target, Math.round(confidence), {
      ema20: e20, ema50: e50, ema200: e200, adx: adxInfo.strength,
      rsi: currRsi, pullbackPct: (pullbackPct * 100).toFixed(2), atr,
    });
  }
}

export class TrendFollowingBear extends BaseStrategy {
  constructor(params = {}) {
    super('TREND_FOLLOWING_BEAR', {
      emas: [20, 50, 200],
      adxPeriod: 14, adxMin: 25,
      rsiPeriod: 14, rsiMin: 32, rsiMax: 60,
      atrPeriod: 14, slMultiplier: 2, tgtMultiplier: 6,
      pullbackThreshold: 0.02,
      ...params,
    });
    this.type = 'POSITIONAL';
    this.direction = 'BEARISH';
  }

  get minBars() { return 210; }

  analyze(bars) {
    const { valid, reason } = this.validate(bars);
    if (!valid) return this.noSignal(reason);

    const cl = this.closes(bars);
    const hi = this.highs(bars);
    const lo = this.lows(bars);
    const price = cl.at(-1);

    const [ema20, ema50, ema200] = this.params.emas.map(p => ema(cl, p));
    const [e20, e50, e200] = [ema20.at(-1), ema50.at(-1), ema200.at(-1)];

    if (!(price < e20 && e20 < e50 && e50 < e200)) {
      return this.noSignal('EMAs not in bearish stack alignment');
    }

    const adxInfo = adxSignal(hi, lo, cl, this.params.adxPeriod);
    if (adxInfo.strength < this.params.adxMin) return this.noSignal('ADX too weak');
    if (adxInfo.direction !== 'BEARISH') return this.noSignal('ADX direction not bearish');

    const rsiVals = rsi(cl, this.params.rsiPeriod);
    const currRsi = rsiVals.at(-1);
    if (currRsi < this.params.rsiMin || currRsi > this.params.rsiMax) {
      return this.noSignal('RSI outside bearish entry range');
    }

    const atr = atrValue(hi, lo, cl, this.params.atrPeriod);
    const stopLoss = Math.min(e50 + atr, price + this.params.slMultiplier * atr);
    const target   = price - this.params.tgtMultiplier * atr;

    const bounceFromEMA = (e20 - price) / e20;
    const bounceBonus = bounceFromEMA < this.params.pullbackThreshold ? 15 : 0;
    const confidence = Math.min(88, 50 + adxInfo.strength * 0.8 + bounceBonus);

    return this.signal('SELL', price, stopLoss, target, Math.round(confidence), {
      ema20: e20, ema50: e50, ema200: e200, adx: adxInfo.strength,
      rsi: currRsi, atr,
    });
  }
}
