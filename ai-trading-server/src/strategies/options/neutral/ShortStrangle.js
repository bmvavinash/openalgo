import BaseStrategy from '../../base/BaseStrategy.js';
import { black76 } from '../OptionsBase.js';

/**
 * Short Strangle — Expiry Day Theta Decay Strategy
 * NSE weekly expiry: Enter 09:20-09:45, sell 1-SD OTM CE + PE
 * Exit by 14:30 IST. Target 50% of premium received. SL = 2× either leg.
 * Research: 68-72% win rate on low-VIX expiry days.
 */
export class ShortStrangle extends BaseStrategy {
  get minBars() { return 5; }

  constructor() {
    super('SHORT_STRANGLE', { deltaTarget: 0.15, dteDays: 1 });
    this.type = 'OPTIONS';
    this.direction = 'NEUTRAL';
    this.instrumentType = 'CE+PE';
    this.description = 'Expiry day short strangle — sell OTM call + put, exit by 14:30 with 50% profit target';
  }

  analyze({ spotPrice, futurePrice, chain, expiry, lotSize = 50, ivRank, indiaVix, isExpiryDay }) {
    if (!spotPrice || !chain || !expiry) return this.noSignal('Need spotPrice, chain, expiry');

    // Only on expiry day or 1 DTE
    if (!isExpiryDay && this.params.dteDays > 1) return this.noSignal('Not expiry day — Short Strangle requires expiry day');

    // VIX filter: aggressive size only when VIX < 16; still trade up to VIX 20
    if (indiaVix && indiaVix > 20) return this.noSignal(`India VIX too high (${indiaVix}) — gamma risk elevated`);

    const F = futurePrice || spotPrice;

    // Calculate 1-SD move using IV
    const avgIV = 0.15; // fallback if chain IV not available
    const iv = chain?.atmIV || avgIV;
    const T = 1 / 365;  // expiry day = 1 day DTE
    const sdMove = F * iv * Math.sqrt(T);  // 1-SD move

    // Select strikes
    const shortCallStrike = Math.round((F + sdMove) / 50) * 50;   // round to 50-point grid
    const shortPutStrike  = Math.round((F - sdMove) / 50) * 50;

    // Price legs using Black-76
    const r = 0.065;
    const callResult = black76('CE', F, shortCallStrike, T, r, iv);
    const putResult  = black76('PE', F, shortPutStrike,  T, r, iv);

    if (!callResult || !putResult) return this.noSignal('Could not price options');

    const callPremium = callResult.price;
    const putPremium  = putResult.price;
    const totalCredit = (callPremium + putPremium) * lotSize;
    const profitTarget = totalCredit * 0.5;

    // R:R: max profit = totalCredit, max theoretical loss = unlimited (use 3× credit as practical SL)
    let conf = 68;
    if (indiaVix && indiaVix < 14) conf += 7;   // very low VIX = theta dominant
    if (indiaVix && indiaVix > 18) conf -= 10;
    conf = Math.min(Math.max(conf, 50), 88);

    return {
      strategy: this.name,
      type: this.type,
      direction: this.direction,
      action: 'SELL_STRANGLE',
      confidence: conf,
      timestamp: new Date().toISOString(),
      legs: [
        {
          action: 'SELL', optionType: 'CE', strike: shortCallStrike, expiry,
          premium: callPremium, delta: callResult.delta, lotSize,
          stopLoss: callPremium * 2,
        },
        {
          action: 'SELL', optionType: 'PE', strike: shortPutStrike, expiry,
          premium: putPremium, delta: putResult.delta, lotSize,
          stopLoss: putPremium * 2,
        },
      ],
      summary: {
        spotPrice, futurePrice: F, sdMove: sdMove.toFixed(2), iv: (iv * 100).toFixed(1) + '%',
        totalCredit: totalCredit.toFixed(2), profitTarget: profitTarget.toFixed(2),
        breakeven: { upper: shortCallStrike + callPremium + putPremium, lower: shortPutStrike - callPremium - putPremium },
        exitRule: 'Close by 14:30 IST or at 50% profit target. SL if either leg doubles.',
        riskReward: 0.5,
      },
    };
  }
}
