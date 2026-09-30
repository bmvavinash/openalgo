import { BaseStrategy } from '../../base/BaseStrategy.js';
import { vwap, atrValue, ema } from '../../../market/indicators/technical.js';

/**
 * VWAP Reversion / Breakout Intraday Strategy
 *
 * Bull: Price dips below VWAP → bounces back above VWAP + EMA(9) rising
 *       OR Price breaks above VWAP with high volume after extended time below
 * Bear: Price spikes above VWAP → falls back below VWAP + EMA(9) falling
 *       OR Price breaks below VWAP with high volume after extended time above
 *
 * Typically on 5-min timeframe (NSE equities, Nifty/BankNifty futures)
 */
export class VWAPBull extends BaseStrategy {
  constructor(params = {}) {
    super('VWAP_BULL', {
      emaPeriod: 9, atrPeriod: 14, slMultiplier: 1.2, tgtMultiplier: 2.5,
      volumeThreshold: 1.5, // volume must be >= 1.5x average
      ...params,
    });
    this.type = 'INTRADAY';
    this.direction = 'BULLISH';
  }

  get minBars() { return 30; }

  analyze(bars) {
    const { valid, reason } = this.validate(bars);
    if (!valid) return this.noSignal(reason);

    const cl = this.closes(bars);
    const hi = this.highs(bars);
    const lo = this.lows(bars);
    const vo = this.volumes(bars);

    const vwapVals = vwap(hi, lo, cl, vo);
    if (vwapVals.length < 2) return this.noSignal('Not enough VWAP data');

    const prevVwap = vwapVals.at(-2);
    const currVwap = vwapVals.at(-1);
    const prevClose = cl.at(-2);
    const currClose = cl.at(-1);

    // Price crosses from below VWAP to above
    const crossedAbove = prevClose <= prevVwap && currClose > currVwap;
    if (!crossedAbove) return this.noSignal('Price not crossing VWAP to upside');

    // Volume confirmation
    const avgVolume = vo.slice(-20).reduce((a, b) => a + b, 0) / 20;
    const currVolume = vo.at(-1);
    if (currVolume < avgVolume * this.params.volumeThreshold) {
      return this.noSignal('Insufficient volume on VWAP cross');
    }

    // EMA trend confirmation
    const emaVals = ema(cl, this.params.emaPeriod);
    const prevEma = emaVals.at(-2);
    const currEma = emaVals.at(-1);
    if (currEma < prevEma) return this.noSignal('EMA(9) not rising');

    const atr = atrValue(hi, lo, cl, this.params.atrPeriod);
    const price = currClose;
    const stopLoss = Math.min(currVwap - atr * 0.5, price - this.params.slMultiplier * atr);
    const target   = price + this.params.tgtMultiplier * atr;

    const volumeRatio = currVolume / avgVolume;
    const confidence = Math.min(90, 55 + volumeRatio * 10);

    return this.signal('BUY', price, stopLoss, target, Math.round(confidence), {
      vwap: currVwap, atr, volumeRatio: volumeRatio.toFixed(2),
      ema: currEma,
    });
  }
}

export class VWAPBear extends BaseStrategy {
  constructor(params = {}) {
    super('VWAP_BEAR', {
      emaPeriod: 9, atrPeriod: 14, slMultiplier: 1.2, tgtMultiplier: 2.5,
      volumeThreshold: 1.5,
      ...params,
    });
    this.type = 'INTRADAY';
    this.direction = 'BEARISH';
  }

  get minBars() { return 30; }

  analyze(bars) {
    const { valid, reason } = this.validate(bars);
    if (!valid) return this.noSignal(reason);

    const cl = this.closes(bars);
    const hi = this.highs(bars);
    const lo = this.lows(bars);
    const vo = this.volumes(bars);

    const vwapVals = vwap(hi, lo, cl, vo);
    if (vwapVals.length < 2) return this.noSignal('Not enough VWAP data');

    const prevVwap = vwapVals.at(-2);
    const currVwap = vwapVals.at(-1);
    const prevClose = cl.at(-2);
    const currClose = cl.at(-1);

    // Price crosses from above VWAP to below
    const crossedBelow = prevClose >= prevVwap && currClose < currVwap;
    if (!crossedBelow) return this.noSignal('Price not crossing VWAP to downside');

    const avgVolume = vo.slice(-20).reduce((a, b) => a + b, 0) / 20;
    const currVolume = vo.at(-1);
    if (currVolume < avgVolume * this.params.volumeThreshold) {
      return this.noSignal('Insufficient volume on VWAP cross');
    }

    const emaVals = ema(cl, this.params.emaPeriod);
    const prevEma = emaVals.at(-2);
    const currEma = emaVals.at(-1);
    if (currEma > prevEma) return this.noSignal('EMA(9) not falling');

    const atr = atrValue(hi, lo, cl, this.params.atrPeriod);
    const price = currClose;
    const stopLoss = Math.max(currVwap + atr * 0.5, price + this.params.slMultiplier * atr);
    const target   = price - this.params.tgtMultiplier * atr;

    const volumeRatio = currVolume / avgVolume;
    const confidence = Math.min(90, 55 + volumeRatio * 10);

    return this.signal('SELL', price, stopLoss, target, Math.round(confidence), {
      vwap: currVwap, atr, volumeRatio: volumeRatio.toFixed(2), ema: currEma,
    });
  }
}
