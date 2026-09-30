import { BaseStrategy } from '../../base/BaseStrategy.js';
import { black76, dte, dteYears } from '../OptionsBase.js';

/**
 * Bull Call Spread (Debit Spread)
 *
 * Setup: Buy lower-strike CE, Sell higher-strike CE (same expiry)
 * Outlook: Moderately bullish
 * Max Profit : (Width of spread - Net Debit) × Lot Size
 * Max Loss   : Net Debit × Lot Size
 * Breakeven  : Lower Strike + Net Debit
 *
 * When to use:
 *   - Bullish bias but limited upside expected
 *   - IV is elevated (debit spread benefits from IV crush vs naked long call)
 *   - Strong support holding, resistance visible above
 *
 * Entry criteria:
 *   - Composite signal is BULLISH
 *   - DTE 15–45 days (avoid gamma risk)
 *   - IV below 80th percentile (prefer debit spread in normal/low IV)
 */
export class BullCallSpread extends BaseStrategy {
  constructor(params = {}) {
    super('BULL_CALL_SPREAD', {
      dteMin: 15, dteMax: 45,
      riskRewardMin: 0.5,   // min 1:2 implied
      otmPercent: 0.02,     // sell strike ~2% OTM from current
      riskFreeRate: 0.065,
      ...params,
    });
    this.type = 'OPTIONS';
    this.direction = 'BULLISH';
    this.instrumentType = 'CE';
  }

  /**
   * Analyze options chain and generate a Bull Call Spread setup.
   * @param {object} input
   * @param {number} input.spotPrice   - Current spot price
   * @param {number} input.futurePrice - Near-month futures price
   * @param {Array}  input.chain       - Options chain: [{ strike, CE_ltp, PE_ltp, CE_iv, PE_iv, CE_oi, PE_oi }]
   * @param {Date}   input.expiry      - Expiry date
   * @param {number} input.lotSize     - Contract lot size
   * @param {object} input.baseSignal  - Result from an equity strategy (BULLISH)
   */
  analyze({ spotPrice, futurePrice, chain, expiry, lotSize, baseSignal } = {}) {
    if (!spotPrice || !chain || chain.length === 0) {
      return this.noSignal('Missing options chain data');
    }
    if (baseSignal?.action !== 'BUY' && baseSignal?.direction !== 'BULLISH') {
      return this.noSignal('Base equity signal is not bullish');
    }

    const days = dte(expiry);
    if (days < this.params.dteMin || days > this.params.dteMax) {
      return this.noSignal(`DTE ${days.toFixed(0)} outside optimal range ${this.params.dteMin}-${this.params.dteMax}`);
    }

    const F = futurePrice || spotPrice;
    const T = dteYears(expiry);
    const r = this.params.riskFreeRate;

    // Find ATM and OTM strikes
    const atm = chain.reduce((best, s) =>
      Math.abs(s.strike - F) < Math.abs(best.strike - F) ? s : best, chain[0]);

    const otmStrike = atm.strike * (1 + this.params.otmPercent);
    const sellLeg = chain.reduce((best, s) =>
      s.strike > atm.strike && Math.abs(s.strike - otmStrike) < Math.abs(best.strike - otmStrike) ? s : best,
      chain.find(s => s.strike > atm.strike) || chain[chain.length - 1]);

    const buyPremium  = atm.CE_ltp   || black76('CE', F, atm.strike, T, r, atm.CE_iv || 0.2).price;
    const sellPremium = sellLeg.CE_ltp || black76('CE', F, sellLeg.strike, T, r, sellLeg.CE_iv || 0.2).price;

    const netDebit    = buyPremium - sellPremium;
    const spreadWidth = sellLeg.strike - atm.strike;
    const maxProfit   = (spreadWidth - netDebit) * lotSize;
    const maxLoss     = netDebit * lotSize;
    const breakeven   = atm.strike + netDebit;
    const riskReward  = maxProfit / maxLoss;

    if (riskReward < this.params.riskRewardMin) {
      return this.noSignal(`R:R ${riskReward.toFixed(2)} below minimum ${this.params.riskRewardMin}`);
    }

    const confidence = Math.min(88, 55 + riskReward * 10 + (baseSignal?.confidence || 0) * 0.2);

    return this.signal('BUY', spotPrice, spotPrice * 0.97, spotPrice * 1.05, Math.round(confidence), {
      strategy: 'BULL_CALL_SPREAD',
      legs: [
        { action: 'BUY',  strike: atm.strike,      expiry, type: 'CE', premium: buyPremium,  qty: lotSize },
        { action: 'SELL', strike: sellLeg.strike,   expiry, type: 'CE', premium: sellPremium, qty: lotSize },
      ],
      netDebit, maxProfit, maxLoss, breakeven, spreadWidth, riskReward, days,
    });
  }
}
