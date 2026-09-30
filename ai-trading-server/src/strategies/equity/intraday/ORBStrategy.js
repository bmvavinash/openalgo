import { BaseStrategy } from '../../base/BaseStrategy.js';
import { atrValue, openingRange } from '../../../market/indicators/technical.js';

/**
 * Opening Range Breakout (ORB) Strategy
 *
 * Concept: First N minutes after market open define the range (High/Low).
 * Breakout above ORB High → BUY signal.
 * Breakdown below ORB Low  → SELL signal.
 *
 * Best on 5-min and 15-min charts for NSE equities and index futures.
 * Typically traded from 09:30 IST onwards.
 *
 * Risk: SL = opposite side of ORB; Target = ORB range * multiplier
 */
export class ORBBull extends BaseStrategy {
  constructor(params = {}) {
    super('ORB_BULL', {
      orbMinutes: 15,       // opening range duration
      tgtMultiplier: 2,     // target = range × multiplier
      volumeConfirm: true,
      volumeThreshold: 1.5,
      atrPeriod: 14,
      ...params,
    });
    this.type = 'INTRADAY';
    this.direction = 'BULLISH';
  }

  get minBars() { return 10; }

  analyze(bars) {
    if (!bars || bars.length < 4) return this.noSignal('Not enough bars');

    const { high: orbHigh, low: orbLow, range } = openingRange(bars, this.params.orbMinutes);
    const latestBar = bars.at(-1);
    const price = latestBar.close;

    // Price must break above ORB High
    if (price <= orbHigh) return this.noSignal(`Price ${price} not above ORB High ${orbHigh.toFixed(2)}`);

    // Volume confirmation
    if (this.params.volumeConfirm) {
      const avgVolume = bars.slice(0, -1).reduce((s, b) => s + b.volume, 0) / (bars.length - 1);
      const currVol = latestBar.volume;
      if (currVol < avgVolume * this.params.volumeThreshold) {
        return this.noSignal('Volume insufficient for ORB breakout confirmation');
      }
    }

    const hi = bars.map(b => b.high);
    const lo = bars.map(b => b.low);
    const cl = bars.map(b => b.close);
    const atr = atrValue(hi, lo, cl, this.params.atrPeriod);

    const stopLoss = orbLow; // SL at ORB low
    const target   = orbHigh + range * this.params.tgtMultiplier;

    const breakoutStrength = ((price - orbHigh) / range) * 100;
    const confidence = Math.min(85, 60 + breakoutStrength * 0.5);

    return this.signal('BUY', price, stopLoss, target, Math.round(confidence), {
      orbHigh, orbLow, range, breakoutStrength: breakoutStrength.toFixed(2),
      atr,
    });
  }
}

export class ORBBear extends BaseStrategy {
  constructor(params = {}) {
    super('ORB_BEAR', {
      orbMinutes: 15, tgtMultiplier: 2, volumeConfirm: true,
      volumeThreshold: 1.5, atrPeriod: 14,
      ...params,
    });
    this.type = 'INTRADAY';
    this.direction = 'BEARISH';
  }

  get minBars() { return 10; }

  analyze(bars) {
    if (!bars || bars.length < 4) return this.noSignal('Not enough bars');

    const { high: orbHigh, low: orbLow, range } = openingRange(bars, this.params.orbMinutes);
    const latestBar = bars.at(-1);
    const price = latestBar.close;

    if (price >= orbLow) return this.noSignal(`Price ${price} not below ORB Low ${orbLow.toFixed(2)}`);

    if (this.params.volumeConfirm) {
      const avgVolume = bars.slice(0, -1).reduce((s, b) => s + b.volume, 0) / (bars.length - 1);
      if (latestBar.volume < avgVolume * this.params.volumeThreshold) {
        return this.noSignal('Volume insufficient for ORB breakdown confirmation');
      }
    }

    const stopLoss = orbHigh;
    const target   = orbLow - range * this.params.tgtMultiplier;

    const breakdownStrength = ((orbLow - price) / range) * 100;
    const confidence = Math.min(85, 60 + breakdownStrength * 0.5);

    return this.signal('SELL', price, stopLoss, target, Math.round(confidence), {
      orbHigh, orbLow, range, breakdownStrength: breakdownStrength.toFixed(2),
    });
  }
}
