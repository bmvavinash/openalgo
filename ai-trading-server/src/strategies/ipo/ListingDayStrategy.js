import { BaseStrategy } from '../base/BaseStrategy.js';

/**
 * IPO Listing Day Strategy
 *
 * Trading IPOs on listing day is high-risk but can be profitable with discipline.
 *
 * Rule-based scenarios:
 *
 * STRONG LISTING (price > issue price + 15%):
 *   - If allotment received: book partial profit at open, hold rest with trailing SL
 *   - If no allotment: do NOT chase — wait for 10-15 min consolidation, enter on pullback
 *
 * MODERATE LISTING (issue price to +15%):
 *   - Allotment holders: hold with SL at issue price
 *   - Non-allotment: wait for dip to issue price, buy if volume supports
 *
 * WEAK LISTING (price < issue price):
 *   - Allotment holders with SL plan: exit at issue price (pre-planned)
 *   - Non-allotment: SHORT if price rejection at issue price is confirmed + volume
 *
 * ABSORPTION CHECK:
 *   - First 15 min volume vs average → if >3× average, strong absorption → continue trend
 *   - If < average → reversal risk
 */
export class ListingDayStrategy extends BaseStrategy {
  constructor(params = {}) {
    super('LISTING_DAY', {
      strongListingThreshold: 0.15,  // +15% from issue price
      weakListingThreshold: 0.00,    // below issue price
      trailingStopPercent: 0.05,    // 5% trailing SL
      quickProfitPercent: 0.08,     // book 50% at 8% gain
      volumeMultiplier: 3,
      ...params,
    });
    this.type = 'IPO';
    this.direction = 'NEUTRAL';
  }

  get minBars() { return 3; }

  /**
   * @param {object} input
   * @param {number} input.issuePrice    - IPO issue price
   * @param {number} input.currentPrice  - Current trading price
   * @param {number} input.openPrice     - First print at listing
   * @param {boolean} input.gotAllotment - Whether the trader got allotment
   * @param {Array}  input.bars          - 1-min or 5-min bars since listing (at least 3)
   * @param {number} input.lotSize       - Lot size for sizing
   */
  analyze({ issuePrice, currentPrice, openPrice, gotAllotment, bars, lotSize } = {}) {
    if (!issuePrice || !currentPrice) return this.noSignal('Issue price or current price missing');

    const listingGainPct = (openPrice - issuePrice) / issuePrice;
    const priceFromOpen  = (currentPrice - openPrice) / openPrice;

    let action = 'HOLD';
    let confidence = 50;
    let stopLoss = null, target = null;
    let notes = '';

    // First-bar volume check
    const avgVolume = bars && bars.length > 1
      ? bars.slice(1).reduce((s, b) => s + b.volume, 0) / (bars.length - 1)
      : null;
    const firstBarVol = bars?.[0]?.volume ?? 0;
    const strongAbsorption = avgVolume ? firstBarVol > avgVolume * this.params.volumeMultiplier : null;

    // ── STRONG LISTING ────────────────────────────────────────────────────────
    if (listingGainPct >= this.params.strongListingThreshold) {
      if (gotAllotment) {
        // Already in — protect profits
        stopLoss = issuePrice; // hard floor
        target = currentPrice * 1.10;
        action = 'HOLD';
        notes = `Strong listing (+${(listingGainPct * 100).toFixed(1)}%). Hold with SL at issue price. Consider booking 50% at +${(this.params.quickProfitPercent * 100)}%.`;
        confidence = 72;
      } else {
        // Non-allotment: don't chase
        if (priceFromOpen < -0.03 && strongAbsorption) {
          // Pullback with strong absorption → entry
          action = 'BUY';
          stopLoss = openPrice * 0.97;
          target   = openPrice * 1.15;
          confidence = 68;
          notes = 'Pullback entry after strong listing. First-bar absorption confirmed.';
        } else {
          return this.noSignal('Do not chase a strong listing without pullback — risk too high');
        }
      }

    // ── MODERATE LISTING ──────────────────────────────────────────────────────
    } else if (listingGainPct >= this.params.weakListingThreshold) {
      if (gotAllotment) {
        action = 'HOLD';
        stopLoss = issuePrice * 0.995;
        target   = issuePrice * 1.15;
        confidence = 60;
        notes = `Moderate listing (+${(listingGainPct * 100).toFixed(1)}%). Hold with SL just below issue price.`;
      } else {
        if (currentPrice <= issuePrice * 1.02 && strongAbsorption) {
          action = 'BUY';
          stopLoss = issuePrice * 0.97;
          target   = issuePrice * 1.12;
          confidence = 62;
          notes = 'Near issue price dip with volume support.';
        } else {
          return this.noSignal('Moderate listing — wait for dip to issue price');
        }
      }

    // ── WEAK LISTING ──────────────────────────────────────────────────────────
    } else {
      if (gotAllotment) {
        action = 'SELL';
        confidence = 80;
        notes = `Weak listing (${(listingGainPct * 100).toFixed(1)}%). Exit at market to limit further loss.`;
      } else {
        // Potential short if price bouncing to issue price and rejecting
        const bouncedToIssuePrice = currentPrice >= issuePrice * 0.99;
        const rejecting = bars && bars.length >= 2 && bars.at(-1).close < bars.at(-2).close;
        if (bouncedToIssuePrice && rejecting && strongAbsorption === false) {
          action = 'SELL';
          stopLoss = issuePrice * 1.02;
          target   = openPrice * 0.90;
          confidence = 65;
          notes = 'Rejection at issue price on weak listing — short opportunity.';
        } else {
          return this.noSignal('Weak listing — non-allotment holders avoid unless clear short setup');
        }
      }
    }

    return this.signal(action, currentPrice, stopLoss, target, confidence, {
      issuePrice, openPrice, listingGainPct: (listingGainPct * 100).toFixed(2),
      gotAllotment, strongAbsorption, notes,
    });
  }
}

export default ListingDayStrategy;
