import { BaseStrategy } from '../../base/BaseStrategy.js';
import { black76, dte, dteYears } from '../OptionsBase.js';

/**
 * Iron Condor — Neutral Range Strategy
 *
 * Setup:
 *   Sell OTM Call + Buy further OTM Call (Bear Call Spread)
 *   Sell OTM Put  + Buy further OTM Put  (Bull Put Spread)
 *   All same expiry.
 *
 * Profit: Both spreads expire worthless (price stays between short strikes)
 * Max Profit = Net Credit received
 * Max Loss   = Width of wider spread - Net Credit
 * Breakeven  = Short Call - Credit (upside) / Short Put + Credit (downside)
 *
 * Entry criteria:
 *   - Low directional bias (ADX < 20 or choppy market)
 *   - IV elevated (>= 50th percentile) — sell premium in high IV
 *   - DTE 20–45 days (theta decay sweet spot)
 *   - Short strikes at ~1 SD from current price
 */
export class IronCondor extends BaseStrategy {
  constructor(params = {}) {
    super('IRON_CONDOR', {
      dteMin: 20, dteMax: 45,
      sdMultiplier: 1.0,    // short strikes at 1 SD
      wingWidth: 2,         // index of strikes for long legs from short legs
      riskFreeRate: 0.065,
      ivMin: 0.15,
      ...params,
    });
    this.type = 'OPTIONS';
    this.direction = 'NEUTRAL';
  }

  analyze({ spotPrice, futurePrice, chain, expiry, lotSize, ivRank } = {}) {
    if (!spotPrice || !chain || chain.length < 6) {
      return this.noSignal('Need at least 6 strikes in chain');
    }

    const days = dte(expiry);
    if (days < this.params.dteMin || days > this.params.dteMax) {
      return this.noSignal(`DTE ${days.toFixed(0)} outside 20-45 range`);
    }

    // Prefer high IV environment for premium selling
    if (ivRank !== undefined && ivRank < 40) {
      return this.noSignal(`IV Rank ${ivRank} too low for premium selling (need >= 40)`);
    }

    const F = futurePrice || spotPrice;
    const T = dteYears(expiry);
    const r = this.params.riskFreeRate;

    // Standard deviation estimate from IV
    const atmStrike = chain.reduce((best, s) =>
      Math.abs(s.strike - F) < Math.abs(best.strike - F) ? s : best, chain[0]);
    const iv = (atmStrike.CE_iv + atmStrike.PE_iv) / 2 || 0.2;
    const sdMove = F * iv * Math.sqrt(T);

    const shortCallStrike = F + sdMove * this.params.sdMultiplier;
    const shortPutStrike  = F - sdMove * this.params.sdMultiplier;

    const findStrike = (target, filterFn) =>
      chain
        .filter(filterFn)
        .reduce((best, s) => Math.abs(s.strike - target) < Math.abs(best.strike - target) ? s : best,
          chain.filter(filterFn)[0]);

    const shortCall = findStrike(shortCallStrike, s => s.strike > F);
    const shortPut  = findStrike(shortPutStrike,  s => s.strike < F);

    // Long legs (further OTM)
    const callIdx  = chain.indexOf(shortCall);
    const putIdx   = chain.indexOf(shortPut);
    const longCall = chain[Math.min(chain.length - 1, callIdx + this.params.wingWidth)];
    const longPut  = chain[Math.max(0, putIdx  - this.params.wingWidth)];

    if (!longCall || !longPut) return this.noSignal('Cannot find wing strikes');

    // Premiums
    const pShortCall = shortCall.CE_ltp || black76('CE', F, shortCall.strike, T, r, iv).price;
    const pLongCall  = longCall.CE_ltp  || black76('CE', F, longCall.strike,  T, r, iv).price;
    const pShortPut  = shortPut.PE_ltp  || black76('PE', F, shortPut.strike,  T, r, iv).price;
    const pLongPut   = longPut.PE_ltp   || black76('PE', F, longPut.strike,   T, r, iv).price;

    const netCredit   = (pShortCall - pLongCall + pShortPut - pLongPut);
    const callWidth   = longCall.strike - shortCall.strike;
    const putWidth    = shortPut.strike - longPut.strike;
    const maxLoss     = (Math.max(callWidth, putWidth) - netCredit) * lotSize;
    const maxProfit   = netCredit * lotSize;
    const beHigh      = shortCall.strike + netCredit;
    const beLow       = shortPut.strike  - netCredit;

    if (netCredit <= 0) return this.noSignal('Net credit is zero or negative');

    const riskReward = maxProfit / maxLoss;
    const confidence = Math.min(82, 50 + riskReward * 30 + (ivRank || 50) * 0.3);

    return this.signal('HOLD', spotPrice, null, null, Math.round(confidence), {
      strategy: 'IRON_CONDOR',
      legs: [
        { action: 'SELL', strike: shortCall.strike, expiry, type: 'CE', premium: pShortCall, qty: lotSize },
        { action: 'BUY',  strike: longCall.strike,  expiry, type: 'CE', premium: pLongCall,  qty: lotSize },
        { action: 'SELL', strike: shortPut.strike,  expiry, type: 'PE', premium: pShortPut,  qty: lotSize },
        { action: 'BUY',  strike: longPut.strike,   expiry, type: 'PE', premium: pLongPut,   qty: lotSize },
      ],
      netCredit, maxProfit, maxLoss, riskReward, beHigh, beLow, days, ivRank,
      profitRange: `${beLow.toFixed(0)} – ${beHigh.toFixed(0)}`,
    });
  }
}
