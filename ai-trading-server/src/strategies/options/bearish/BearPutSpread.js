import { BaseStrategy } from '../../base/BaseStrategy.js';
import { black76, dte, dteYears } from '../OptionsBase.js';

/**
 * Bear Put Spread (Debit Spread)
 *
 * Setup: Buy higher-strike PE, Sell lower-strike PE (same expiry)
 * Outlook: Moderately bearish
 * Max Profit : (Width of spread - Net Debit) × Lot Size
 * Max Loss   : Net Debit × Lot Size
 * Breakeven  : Higher Strike - Net Debit
 *
 * Entry criteria:
 *   - Base signal is BEARISH
 *   - DTE 15–45 days
 *   - IV not extreme (debit strategy — avoid in IV crush environment)
 */
export class BearPutSpread extends BaseStrategy {
  constructor(params = {}) {
    super('BEAR_PUT_SPREAD', {
      dteMin: 15, dteMax: 45,
      riskRewardMin: 0.5,
      otmPercent: 0.02,
      riskFreeRate: 0.065,
      ...params,
    });
    this.type = 'OPTIONS';
    this.direction = 'BEARISH';
    this.instrumentType = 'PE';
  }

  analyze({ spotPrice, futurePrice, chain, expiry, lotSize, baseSignal } = {}) {
    if (!spotPrice || !chain || chain.length === 0) {
      return this.noSignal('Missing options chain data');
    }
    if (baseSignal?.action !== 'SELL' && baseSignal?.direction !== 'BEARISH') {
      return this.noSignal('Base equity signal is not bearish');
    }

    const days = dte(expiry);
    if (days < this.params.dteMin || days > this.params.dteMax) {
      return this.noSignal(`DTE ${days.toFixed(0)} outside optimal range`);
    }

    const F = futurePrice || spotPrice;
    const T = dteYears(expiry);
    const r = this.params.riskFreeRate;

    const atm = chain.reduce((best, s) =>
      Math.abs(s.strike - F) < Math.abs(best.strike - F) ? s : best, chain[0]);

    const otmStrike = atm.strike * (1 - this.params.otmPercent);
    const sellLeg = chain.reduce((best, s) =>
      s.strike < atm.strike && Math.abs(s.strike - otmStrike) < Math.abs(best.strike - otmStrike) ? s : best,
      chain.find(s => s.strike < atm.strike) || chain[0]);

    const buyPremium  = atm.PE_ltp   || black76('PE', F, atm.strike, T, r, atm.PE_iv || 0.2).price;
    const sellPremium = sellLeg.PE_ltp || black76('PE', F, sellLeg.strike, T, r, sellLeg.PE_iv || 0.2).price;

    const netDebit    = buyPremium - sellPremium;
    const spreadWidth = atm.strike - sellLeg.strike;
    const maxProfit   = (spreadWidth - netDebit) * lotSize;
    const maxLoss     = netDebit * lotSize;
    const breakeven   = atm.strike - netDebit;
    const riskReward  = maxProfit / maxLoss;

    if (riskReward < this.params.riskRewardMin) {
      return this.noSignal(`R:R ${riskReward.toFixed(2)} below minimum`);
    }

    const confidence = Math.min(88, 55 + riskReward * 10 + (baseSignal?.confidence || 0) * 0.2);

    return this.signal('SELL', spotPrice, spotPrice * 1.03, spotPrice * 0.95, Math.round(confidence), {
      strategy: 'BEAR_PUT_SPREAD',
      legs: [
        { action: 'BUY',  strike: atm.strike,      expiry, type: 'PE', premium: buyPremium,  qty: lotSize },
        { action: 'SELL', strike: sellLeg.strike,   expiry, type: 'PE', premium: sellPremium, qty: lotSize },
      ],
      netDebit, maxProfit, maxLoss, breakeven, spreadWidth, riskReward, days,
    });
  }
}
