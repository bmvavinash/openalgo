import { BaseStrategy } from '../../base/BaseStrategy.js';
import { rsi, bollingerBands, atrValue, sma, pivotLevels } from '../../../market/indicators/technical.js';

/**
 * Swing Trading Positional Strategy (Bull + Bear)
 *
 * Bull: Buy at support zones on pullbacks in an uptrend
 *   - Price pulling back to 50 SMA or lower BB in uptrend
 *   - RSI crossing back above 40 from below (oversold recovery)
 *   - Positive risk structure (higher highs, higher lows)
 *
 * Bear: Short at resistance on rallies in downtrend
 *   - Price rallying to 50 SMA or upper BB in downtrend
 *   - RSI crossing below 60 from above
 *
 * Hold time: 5–15 trading days
 */
export class SwingTradingBull extends BaseStrategy {
  constructor(params = {}) {
    super('SWING_TRADING_BULL', {
      smaPeriod: 50,
      rsiPeriod: 14, rsiEntry: 40,
      bbPeriod: 20, bbStdDev: 2,
      atrPeriod: 14, slMultiplier: 2, tgtMultiplier: 4,
      ...params,
    });
    this.type = 'POSITIONAL';
    this.direction = 'BULLISH';
  }

  get minBars() { return 100; }

  analyze(bars) {
    const { valid, reason } = this.validate(bars);
    if (!valid) return this.noSignal(reason);

    const cl = this.closes(bars);
    const hi = this.highs(bars);
    const lo = this.lows(bars);
    const price = cl.at(-1);

    const smaVals = sma(cl, this.params.smaPeriod);
    const smaCurr = smaVals.at(-1);

    // Uptrend structure: price above 50 SMA on the longer view
    // We check that at least the last 10 closes mostly traded above SMA
    const last10AboveSMA = cl.slice(-10).filter((c, i) => c > smaVals.at(-(10 - i))).length;
    if (last10AboveSMA < 5) return this.noSignal('Not enough uptrend evidence');

    const rsiVals = rsi(cl, this.params.rsiPeriod);
    const prevRsi = rsiVals.at(-2);
    const currRsi = rsiVals.at(-1);

    // RSI crossing back above the 40 level (end of pullback)
    const rsiRecovery = prevRsi < this.params.rsiEntry && currRsi >= this.params.rsiEntry;
    if (!rsiRecovery) return this.noSignal('RSI not recovering from oversold pullback');

    // Price should be near 50 SMA or lower BB
    const bbVals = bollingerBands(cl, this.params.bbPeriod, this.params.bbStdDev);
    const bb = bbVals.at(-1);
    const nearSupport = price <= smaCurr * 1.03 || price <= bb.middle;

    const atr = atrValue(hi, lo, cl, this.params.atrPeriod);
    const pivot = pivotLevels(hi.at(-1), lo.at(-1), cl.at(-1));

    const stopLoss = Math.min(
      price - this.params.slMultiplier * atr,
      pivot.s2,
      lo.slice(-5).reduce((a, b) => Math.min(a, b), Infinity)
    );
    const target = price + this.params.tgtMultiplier * atr;

    const confidence = nearSupport ? 75 : 62;

    return this.signal('BUY', price, stopLoss, target, confidence, {
      sma50: smaCurr, rsi: currRsi, bbLower: bb.lower, nearSupport, atr, pivot,
    });
  }
}

export class SwingTradingBear extends BaseStrategy {
  constructor(params = {}) {
    super('SWING_TRADING_BEAR', {
      smaPeriod: 50,
      rsiPeriod: 14, rsiEntry: 60,
      bbPeriod: 20, bbStdDev: 2,
      atrPeriod: 14, slMultiplier: 2, tgtMultiplier: 4,
      ...params,
    });
    this.type = 'POSITIONAL';
    this.direction = 'BEARISH';
  }

  get minBars() { return 100; }

  analyze(bars) {
    const { valid, reason } = this.validate(bars);
    if (!valid) return this.noSignal(reason);

    const cl = this.closes(bars);
    const hi = this.highs(bars);
    const lo = this.lows(bars);
    const price = cl.at(-1);

    const smaVals = sma(cl, this.params.smaPeriod);
    const smaCurr = smaVals.at(-1);

    const last10BelowSMA = cl.slice(-10).filter((c, i) => c < smaVals.at(-(10 - i))).length;
    if (last10BelowSMA < 5) return this.noSignal('Not in downtrend');

    const rsiVals = rsi(cl, this.params.rsiPeriod);
    const prevRsi = rsiVals.at(-2);
    const currRsi = rsiVals.at(-1);

    const rsiFade = prevRsi > this.params.rsiEntry && currRsi <= this.params.rsiEntry;
    if (!rsiFade) return this.noSignal('RSI not fading from overbought bounce');

    const bbVals = bollingerBands(cl, this.params.bbPeriod, this.params.bbStdDev);
    const bb = bbVals.at(-1);
    const nearResistance = price >= smaCurr * 0.97 || price >= bb.middle;

    const atr = atrValue(hi, lo, cl, this.params.atrPeriod);
    const pivot = pivotLevels(hi.at(-1), lo.at(-1), cl.at(-1));

    const stopLoss = Math.max(
      price + this.params.slMultiplier * atr,
      pivot.r2,
      hi.slice(-5).reduce((a, b) => Math.max(a, b), 0)
    );
    const target = price - this.params.tgtMultiplier * atr;

    const confidence = nearResistance ? 75 : 62;

    return this.signal('SELL', price, stopLoss, target, confidence, {
      sma50: smaCurr, rsi: currRsi, bbUpper: bb.upper, nearResistance, atr, pivot,
    });
  }
}
