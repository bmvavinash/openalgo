import { BaseStrategy } from '../../base/BaseStrategy.js';
import { black76, dte, dteYears } from '../OptionsBase.js';

/**
 * Short Straddle — Extreme Neutral Strategy (Sell Volatility)
 *
 * Setup: Sell ATM CE + Sell ATM PE (same strike, same expiry)
 * Profit: If price stays near the strike (IV crush or time decay)
 * Risk: Unlimited on both sides — requires active management
 *
 * Long Straddle — Buy Volatility
 * Setup: Buy ATM CE + Buy ATM PE
 * Profit: If price makes a big move in either direction
 *
 * Entry criteria (Short):
 *   - IV Rank > 70 (selling expensive premium)
 *   - DTE 20–40 days (fast theta decay)
 *   - No major events expected (earnings, budget)
 *
 * Entry criteria (Long):
 *   - IV Rank < 30 (buying cheap premium)
 *   - Big event expected: budget, RBI policy, earnings
 *   - DTE 5–15 days (event capture)
 */
export class ShortStraddle extends BaseStrategy {
  constructor(params = {}) {
    super('SHORT_STRADDLE', {
      dteMin: 20, dteMax: 40, ivRankMin: 70,
      riskFreeRate: 0.065, slMultiplier: 2,
      ...params,
    });
    this.type = 'OPTIONS';
    this.direction = 'NEUTRAL';
  }

  analyze({ spotPrice, futurePrice, chain, expiry, lotSize, ivRank } = {}) {
    if (!spotPrice || !chain || chain.length === 0) return this.noSignal('Missing chain');

    const days = dte(expiry);
    if (days < this.params.dteMin || days > this.params.dteMax) {
      return this.noSignal(`DTE ${days.toFixed(0)} not in 20–40 range`);
    }
    if ((ivRank ?? 100) < this.params.ivRankMin) {
      return this.noSignal(`IV Rank ${ivRank} too low for short straddle (need >= ${this.params.ivRankMin})`);
    }

    const F = futurePrice || spotPrice;
    const T = dteYears(expiry);
    const r = this.params.riskFreeRate;

    const atm = chain.reduce((best, s) =>
      Math.abs(s.strike - F) < Math.abs(best.strike - F) ? s : best, chain[0]);
    const iv = (atm.CE_iv + atm.PE_iv) / 2 || 0.2;

    const callPrem = atm.CE_ltp || black76('CE', F, atm.strike, T, r, iv).price;
    const putPrem  = atm.PE_ltp || black76('PE', F, atm.strike, T, r, iv).price;

    const totalCredit = (callPrem + putPrem);
    const beHigh = atm.strike + totalCredit;
    const beLow  = atm.strike - totalCredit;
    const maxProfit = totalCredit * lotSize;

    // Soft stop: if position moves 2× premium on either side
    const slPrice = atm.strike;
    const confidence = Math.min(80, 45 + (ivRank || 70) * 0.4);

    return this.signal('HOLD', spotPrice, null, null, Math.round(confidence), {
      strategy: 'SHORT_STRADDLE',
      legs: [
        { action: 'SELL', strike: atm.strike, expiry, type: 'CE', premium: callPrem, qty: lotSize },
        { action: 'SELL', strike: atm.strike, expiry, type: 'PE', premium: putPrem,  qty: lotSize },
      ],
      totalCredit, maxProfit, beHigh, beLow, days, ivRank,
      profitRange: `${beLow.toFixed(0)} – ${beHigh.toFixed(0)}`,
      risk: 'UNLIMITED_BOTH_SIDES',
    });
  }
}

export class LongStraddle extends BaseStrategy {
  constructor(params = {}) {
    super('LONG_STRADDLE', {
      dteMin: 5, dteMax: 15, ivRankMax: 35,
      riskFreeRate: 0.065,
      ...params,
    });
    this.type = 'OPTIONS';
    this.direction = 'NEUTRAL';
  }

  analyze({ spotPrice, futurePrice, chain, expiry, lotSize, ivRank, eventExpected } = {}) {
    if (!spotPrice || !chain || chain.length === 0) return this.noSignal('Missing chain');

    const days = dte(expiry);
    if (days < this.params.dteMin || days > this.params.dteMax) {
      return this.noSignal(`DTE ${days.toFixed(0)} not in 5–15 range`);
    }
    if ((ivRank ?? 0) > this.params.ivRankMax && !eventExpected) {
      return this.noSignal(`IV Rank ${ivRank} too high for long straddle without known event`);
    }

    const F = futurePrice || spotPrice;
    const T = dteYears(expiry);
    const r = this.params.riskFreeRate;

    const atm = chain.reduce((best, s) =>
      Math.abs(s.strike - F) < Math.abs(best.strike - F) ? s : best, chain[0]);
    const iv = (atm.CE_iv + atm.PE_iv) / 2 || 0.2;

    const callPrem = atm.CE_ltp || black76('CE', F, atm.strike, T, r, iv).price;
    const putPrem  = atm.PE_ltp || black76('PE', F, atm.strike, T, r, iv).price;

    const totalDebit = callPrem + putPrem;
    const beHigh = atm.strike + totalDebit;
    const beLow  = atm.strike - totalDebit;
    const maxLoss = totalDebit * lotSize;

    const confidence = eventExpected ? 72 : Math.min(65, 40 + (35 - (ivRank || 25)) * 0.8);

    return this.signal('HOLD', spotPrice, null, null, Math.round(confidence), {
      strategy: 'LONG_STRADDLE',
      legs: [
        { action: 'BUY', strike: atm.strike, expiry, type: 'CE', premium: callPrem, qty: lotSize },
        { action: 'BUY', strike: atm.strike, expiry, type: 'PE', premium: putPrem,  qty: lotSize },
      ],
      totalDebit, maxLoss, beHigh, beLow, days, ivRank, eventExpected,
      breakEvenRange: `${beLow.toFixed(0)} – ${beHigh.toFixed(0)}`,
    });
  }
}
