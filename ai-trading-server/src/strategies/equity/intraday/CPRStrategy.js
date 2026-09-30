import BaseStrategy from '../../base/BaseStrategy.js';
import { atrValue } from '../../../market/indicators/technical.js';

/**
 * Central Pivot Range (CPR) Strategy
 * CPR = (Pivot + BC + TC) zone — used heavily by NSE prop desks and retail traders.
 *
 * Pivot  = (High + Low + Close) / 3  [yesterday's values]
 * BC     = (High + Low) / 2          [Bottom of CPR]
 * TC     = (Pivot - BC) + Pivot      [Top of CPR]
 *
 * Narrow CPR (TC - BC < 0.3% of price): strong trend day expected.
 * Wide CPR  (TC - BC > 1% of price):    sideways/reversal day expected.
 *
 * Entry rules (trend day):
 *   BULL: price opens above TC, first pullback to CPR zone holds → BUY
 *   BEAR: price opens below BC, first rally to CPR zone fails → SELL
 *
 * Entry rules (sideways day):
 *   Fade at R1/S1: BUY at S1 with SL below S2, target Pivot
 *                  SELL at R1 with SL above R2, target Pivot
 */

function buildCPR(prevHigh, prevLow, prevClose) {
  const pivot = (prevHigh + prevLow + prevClose) / 3;
  const bc    = (prevHigh + prevLow) / 2;
  const tc    = (pivot - bc) + pivot;
  // Standard pivot levels
  const r1 = 2 * pivot - prevLow;
  const s1 = 2 * pivot - prevHigh;
  const r2 = pivot + (prevHigh - prevLow);
  const s2 = pivot - (prevHigh - prevLow);
  return { pivot, bc, tc, r1, s1, r2, s2, cprWidth: Math.abs(tc - bc) };
}

export class CPRBull extends BaseStrategy {
  get minBars() { return 20; }

  constructor() {
    super('CPR_BULL', {});
    this.type = 'INTRADAY';
    this.direction = 'BULLISH';
    this.instrumentType = 'EQ';
    this.description = 'CPR trend day bull — open above TC, pullback to CPR zone holds';
  }

  analyze(bars) {
    if (!this.validate(bars)) return this.noSignal('Insufficient bars');

    // Use yesterday's OHLC (last completed daily bar = last bar in set)
    const yesterday = bars[bars.length - 2];
    const today     = bars[bars.length - 1];
    if (!yesterday) return this.noSignal('Need at least 2 bars');

    const cpr = buildCPR(yesterday.high, yesterday.low, yesterday.close);
    const close = today.close;
    const open  = today.open;
    const cprWidthPct = cpr.cprWidth / close;

    // Narrow CPR = trend day (< 0.3% of price)
    const isNarrowCPR = cprWidthPct < 0.003;

    if (isNarrowCPR && open > cpr.tc) {
      // Strong bull setup: open above TC, price holding above BC
      if (close > cpr.bc) {
        const atr  = atrValue(bars.map(b => b.high), bars.map(b => b.low), bars.map(b => b.close), 14);
        const stopLoss = cpr.s1;
        const target   = cpr.r2;
        let conf = 72;
        if (close > cpr.tc) conf += 8;  // Still above full CPR = extra strength
        if (cprWidthPct < 0.001) conf += 5;  // Very narrow CPR = very high trend potential
        conf = Math.min(conf, 93);
        return this.signal('BUY', close, stopLoss, target, conf, {
          pivot: cpr.pivot, bc: cpr.bc, tc: cpr.tc, r1: cpr.r1, r2: cpr.r2, s1: cpr.s1,
          cprWidthPct: (cprWidthPct * 100).toFixed(3) + '%', isNarrowCPR,
        });
      }
    }

    // Wide CPR — fade at S1 (reversal strategy)
    if (!isNarrowCPR && close <= cpr.s1 * 1.002 && close >= cpr.s1 * 0.998) {
      return this.signal('BUY', close, cpr.s2, cpr.pivot, 62, {
        pivot: cpr.pivot, s1: cpr.s1, s2: cpr.s2, isNarrowCPR: false, reason: 'S1 bounce',
      });
    }

    return this.noSignal('CPR conditions not met for bull entry');
  }
}

export class CPRBear extends BaseStrategy {
  get minBars() { return 20; }

  constructor() {
    super('CPR_BEAR', {});
    this.type = 'INTRADAY';
    this.direction = 'BEARISH';
    this.instrumentType = 'EQ';
    this.description = 'CPR trend day bear — open below BC, rally to CPR fails';
  }

  analyze(bars) {
    if (!this.validate(bars)) return this.noSignal('Insufficient bars');

    const yesterday = bars[bars.length - 2];
    const today     = bars[bars.length - 1];
    if (!yesterday) return this.noSignal('Need at least 2 bars');

    const cpr = buildCPR(yesterday.high, yesterday.low, yesterday.close);
    const close = today.close;
    const open  = today.open;
    const cprWidthPct = cpr.cprWidth / close;
    const isNarrowCPR = cprWidthPct < 0.003;

    if (isNarrowCPR && open < cpr.bc) {
      if (close < cpr.tc) {
        const stopLoss = cpr.r1;
        const target   = cpr.s2;
        let conf = 72;
        if (close < cpr.bc) conf += 8;
        if (cprWidthPct < 0.001) conf += 5;
        conf = Math.min(conf, 93);
        return this.signal('SELL', close, stopLoss, target, conf, {
          pivot: cpr.pivot, bc: cpr.bc, tc: cpr.tc, r1: cpr.r1, s1: cpr.s1, s2: cpr.s2,
          cprWidthPct: (cprWidthPct * 100).toFixed(3) + '%', isNarrowCPR,
        });
      }
    }

    // Wide CPR — fade at R1
    if (!isNarrowCPR && close >= cpr.r1 * 0.998 && close <= cpr.r1 * 1.002) {
      return this.signal('SELL', close, cpr.r2, cpr.pivot, 62, {
        pivot: cpr.pivot, r1: cpr.r1, r2: cpr.r2, isNarrowCPR: false, reason: 'R1 rejection',
      });
    }

    return this.noSignal('CPR conditions not met for bear entry');
  }
}
