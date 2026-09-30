import BaseStrategy from '../../base/BaseStrategy.js';
import { ema, rsi, atrValue } from '../../../market/indicators/technical.js';

/**
 * 200 EMA + RSI Divergence Strategy (positional)
 * Price above 200 EMA = macro bull. RSI bullish divergence near 200 EMA = high-probability entry.
 * Research: 58-65% win rate on daily charts; 8-25% average winner.
 */

function detectBullishDivergence(closes, rsiValues, lookback = 15) {
  // Find local price lows and RSI lows in last `lookback` bars
  const n = Math.min(closes.length, rsiValues.length);
  if (n < lookback) return false;

  const priceSlice = closes.slice(n - lookback);
  const rsiSlice   = rsiValues.slice(rsiValues.length - lookback);

  // Find two swing lows in price
  let low1Idx = -1, low2Idx = -1;
  for (let i = 2; i < lookback - 2; i++) {
    if (priceSlice[i] < priceSlice[i - 1] && priceSlice[i] < priceSlice[i + 1]) {
      if (low1Idx === -1) low1Idx = i;
      else low2Idx = i;
    }
  }

  if (low1Idx === -1 || low2Idx === -1) return false;

  // Bullish divergence: price makes lower low but RSI makes higher low
  const priceDiverges = priceSlice[low2Idx] < priceSlice[low1Idx];
  const rsiDiverges   = rsiSlice[low2Idx]   > rsiSlice[low1Idx];

  return priceDiverges && rsiDiverges && rsiSlice[low2Idx] < 45;
}

function detectBearishDivergence(closes, rsiValues, lookback = 15) {
  const n = Math.min(closes.length, rsiValues.length);
  if (n < lookback) return false;

  const priceSlice = closes.slice(n - lookback);
  const rsiSlice   = rsiValues.slice(rsiValues.length - lookback);

  let high1Idx = -1, high2Idx = -1;
  for (let i = 2; i < lookback - 2; i++) {
    if (priceSlice[i] > priceSlice[i - 1] && priceSlice[i] > priceSlice[i + 1]) {
      if (high1Idx === -1) high1Idx = i;
      else high2Idx = i;
    }
  }

  if (high1Idx === -1 || high2Idx === -1) return false;

  const priceDiverges = priceSlice[high2Idx] > priceSlice[high1Idx];
  const rsiDiverges   = rsiSlice[high2Idx]   < rsiSlice[high1Idx];

  return priceDiverges && rsiDiverges && rsiSlice[high2Idx] > 55;
}

export class EMADivergenceBull extends BaseStrategy {
  get minBars() { return 215; }

  constructor() {
    super('EMA_DIVERGENCE_BULL', { emaPeriod: 200, rsiPeriod: 14 });
    this.type = 'POSITIONAL';
    this.direction = 'BULLISH';
    this.instrumentType = 'EQ';
    this.description = '200 EMA macro trend + RSI bullish divergence — high-probability positional entry';
  }

  analyze(bars) {
    if (!this.validate(bars)) return this.noSignal('Insufficient bars (need 215+)');

    const closes = this.closes(bars);
    const ema200  = ema(closes, 200);
    const rsiVals = rsi(closes, this.params.rsiPeriod);

    if (!ema200?.length || !rsiVals?.length) return this.noSignal('Indicator calculation failed');

    const close     = closes[closes.length - 1];
    const ema200Now = ema200[ema200.length - 1];
    const rsiNow    = rsiVals[rsiVals.length - 1];

    // Macro trend gate: price must be above 200 EMA
    if (close <= ema200Now) return this.noSignal('Price below 200 EMA — not in bull macro trend');

    // Near 200 EMA: within 5% above (pullback zone)
    const distFromEMA = (close - ema200Now) / ema200Now;
    if (distFromEMA > 0.05) return this.noSignal(`Price too far from 200 EMA (${(distFromEMA*100).toFixed(1)}% above)`);

    // RSI must be recovering (cross above 40 from below)
    const prevRsi = rsiVals[rsiVals.length - 2] || 50;
    const rsiRecovering = prevRsi < 40 && rsiNow >= 40;

    // Check RSI divergence
    const hasDivergence = detectBullishDivergence(closes, rsiVals);

    if (!rsiRecovering && !hasDivergence) return this.noSignal('No RSI recovery or divergence');

    const atrVal   = atrValue(bars.map(b => b.high), bars.map(b => b.low), closes, 14);
    const stopLoss = Math.max(ema200Now * 0.97, close - atrVal * 1.5);  // 3% below 200 EMA or 1.5×ATR
    const target   = close + (close - stopLoss) * 2.5;  // 2.5:1 R:R

    let conf = 62;
    if (hasDivergence) conf += 12;
    if (rsiRecovering) conf += 8;
    if (distFromEMA < 0.01) conf += 5;  // very close to 200 EMA = textbook setup
    conf = Math.min(conf, 92);

    return this.signal('BUY', close, stopLoss, target, conf, {
      ema200: ema200Now, rsi: rsiNow.toFixed(1), distFromEMA: (distFromEMA * 100).toFixed(2) + '%',
      hasDivergence, rsiRecovering, atr: atrVal.toFixed(2),
    });
  }
}

export class EMADivergenceBear extends BaseStrategy {
  get minBars() { return 215; }

  constructor() {
    super('EMA_DIVERGENCE_BEAR', { emaPeriod: 200, rsiPeriod: 14 });
    this.type = 'POSITIONAL';
    this.direction = 'BEARISH';
    this.instrumentType = 'EQ';
    this.description = '200 EMA macro bear + RSI bearish divergence — high-probability short entry';
  }

  analyze(bars) {
    if (!this.validate(bars)) return this.noSignal('Insufficient bars (need 215+)');

    const closes = this.closes(bars);
    const ema200  = ema(closes, 200);
    const rsiVals = rsi(closes, this.params.rsiPeriod);

    if (!ema200?.length || !rsiVals?.length) return this.noSignal('Indicator calculation failed');

    const close     = closes[closes.length - 1];
    const ema200Now = ema200[ema200.length - 1];
    const rsiNow    = rsiVals[rsiVals.length - 1];

    if (close >= ema200Now) return this.noSignal('Price above 200 EMA — not in bear macro trend');

    const distFromEMA = (ema200Now - close) / ema200Now;
    if (distFromEMA > 0.05) return this.noSignal(`Price too far below 200 EMA (${(distFromEMA*100).toFixed(1)}%)`);

    const prevRsi = rsiVals[rsiVals.length - 2] || 50;
    const rsiRejecting = prevRsi > 60 && rsiNow <= 60;
    const hasDivergence = detectBearishDivergence(closes, rsiVals);

    if (!rsiRejecting && !hasDivergence) return this.noSignal('No RSI rejection or divergence');

    const atrVal   = atrValue(bars.map(b => b.high), bars.map(b => b.low), closes, 14);
    const stopLoss = Math.min(ema200Now * 1.03, close + atrVal * 1.5);
    const target   = close - (stopLoss - close) * 2.5;

    let conf = 62;
    if (hasDivergence) conf += 12;
    if (rsiRejecting) conf += 8;
    if (distFromEMA < 0.01) conf += 5;
    conf = Math.min(conf, 92);

    return this.signal('SELL', close, stopLoss, target, conf, {
      ema200: ema200Now, rsi: rsiNow.toFixed(1), distFromEMA: (distFromEMA * 100).toFixed(2) + '%',
      hasDivergence, rsiRejecting, atr: atrVal.toFixed(2),
    });
  }
}
