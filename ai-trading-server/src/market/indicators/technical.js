/**
 * Technical indicator wrappers around the `technicalindicators` library.
 * All functions accept plain arrays of OHLCV data or price arrays and return
 * the computed series (latest value last).
 */

import {
  RSI, MACD, BollingerBands, EMA, SMA, ATR, Stochastic,
  VWAP, OBV, ADX, CCI, WilliamsR, ROC, MFI,
} from 'technicalindicators';

// ─── Moving Averages ──────────────────────────────────────────────────────────

export function sma(closes, period) {
  return SMA.calculate({ period, values: closes });
}

export function ema(closes, period) {
  return EMA.calculate({ period, values: closes });
}

// ─── RSI ──────────────────────────────────────────────────────────────────────

export function rsi(closes, period = 14) {
  return RSI.calculate({ period, values: closes });
}

export function rsiSignal(closes, period = 14, oversold = 30, overbought = 70) {
  const vals = rsi(closes, period);
  const last = vals.at(-1);
  if (last <= oversold) return { signal: 'OVERSOLD', value: last };
  if (last >= overbought) return { signal: 'OVERBOUGHT', value: last };
  return { signal: 'NEUTRAL', value: last };
}

// ─── MACD ─────────────────────────────────────────────────────────────────────

export function macd(closes, fastPeriod = 12, slowPeriod = 26, signalPeriod = 9) {
  return MACD.calculate({
    values: closes,
    fastPeriod,
    slowPeriod,
    signalPeriod,
    SimpleMAOscillator: false,
    SimpleMASignal: false,
  });
}

export function macdSignal(closes, fastPeriod = 12, slowPeriod = 26, signalPeriod = 9) {
  const vals = macd(closes, fastPeriod, slowPeriod, signalPeriod);
  if (vals.length < 2) return { signal: 'NEUTRAL', crossover: null };
  const prev = vals.at(-2);
  const curr = vals.at(-1);
  const prevHistogram = prev.histogram ?? (prev.MACD - prev.signal);
  const currHistogram = curr.histogram ?? (curr.MACD - curr.signal);

  let crossover = null;
  if (prevHistogram < 0 && currHistogram >= 0) crossover = 'BULLISH';
  if (prevHistogram > 0 && currHistogram <= 0) crossover = 'BEARISH';

  return {
    signal: crossover || (currHistogram > 0 ? 'BULLISH' : 'BEARISH'),
    crossover,
    macd: curr.MACD,
    signal: curr.signal,
    histogram: currHistogram,
  };
}

// ─── Bollinger Bands ──────────────────────────────────────────────────────────

export function bollingerBands(closes, period = 20, stdDev = 2) {
  return BollingerBands.calculate({ period, values: closes, stdDev });
}

export function bbSignal(closes, period = 20, stdDev = 2) {
  const vals = bollingerBands(closes, period, stdDev);
  const last = vals.at(-1);
  const price = closes.at(-1);
  const bandwidth = (last.upper - last.lower) / last.middle;
  const pctB = (price - last.lower) / (last.upper - last.lower);

  let signal = 'NEUTRAL';
  if (price <= last.lower) signal = 'OVERSOLD';
  else if (price >= last.upper) signal = 'OVERBOUGHT';

  return { signal, upper: last.upper, middle: last.middle, lower: last.lower, bandwidth, pctB };
}

// ─── ATR ──────────────────────────────────────────────────────────────────────

export function atr(highs, lows, closes, period = 14) {
  return ATR.calculate({ high: highs, low: lows, close: closes, period });
}

export function atrValue(highs, lows, closes, period = 14) {
  const vals = atr(highs, lows, closes, period);
  return vals.at(-1) ?? 0;
}

// ─── Stochastic ───────────────────────────────────────────────────────────────

export function stochastic(highs, lows, closes, kPeriod = 14, dPeriod = 3, smooth = 3) {
  return Stochastic.calculate({ high: highs, low: lows, close: closes, period: kPeriod, signalPeriod: dPeriod });
}

export function stochasticSignal(highs, lows, closes) {
  const vals = stochastic(highs, lows, closes);
  const last = vals.at(-1);
  if (!last) return { signal: 'NEUTRAL', k: 50, d: 50 };
  const { k, d } = last;
  let signal = 'NEUTRAL';
  if (k < 20 && d < 20) signal = 'OVERSOLD';
  else if (k > 80 && d > 80) signal = 'OVERBOUGHT';
  return { signal, k, d };
}

// ─── ADX ──────────────────────────────────────────────────────────────────────

export function adx(highs, lows, closes, period = 14) {
  return ADX.calculate({ high: highs, low: lows, close: closes, period });
}

export function adxSignal(highs, lows, closes, period = 14, threshold = 25) {
  const vals = adx(highs, lows, closes, period);
  const last = vals.at(-1);
  if (!last) return { trending: false, strength: 0, direction: 'NEUTRAL' };
  const trending = last.adx >= threshold;
  const direction = last.pdi > last.mdi ? 'BULLISH' : 'BEARISH';
  return { trending, strength: last.adx, direction, pdi: last.pdi, mdi: last.mdi };
}

// ─── VWAP ─────────────────────────────────────────────────────────────────────

export function vwap(highs, lows, closes, volumes) {
  return VWAP.calculate({ high: highs, low: lows, close: closes, volume: volumes });
}

export function vwapSignal(highs, lows, closes, volumes) {
  const vals = vwap(highs, lows, closes, volumes);
  const vwapVal = vals.at(-1) ?? 0;
  const price = closes.at(-1);
  const signal = price > vwapVal ? 'ABOVE_VWAP' : 'BELOW_VWAP';
  const deviation = ((price - vwapVal) / vwapVal) * 100;
  return { signal, vwap: vwapVal, price, deviationPct: deviation };
}

// ─── OBV ──────────────────────────────────────────────────────────────────────

export function obv(closes, volumes) {
  return OBV.calculate({ close: closes, volume: volumes });
}

// ─── CCI ──────────────────────────────────────────────────────────────────────

export function cci(highs, lows, closes, period = 20) {
  return CCI.calculate({ high: highs, low: lows, close: closes, period });
}

// ─── Support / Resistance ─────────────────────────────────────────────────────

export function pivotLevels(prevHigh, prevLow, prevClose) {
  const pp = (prevHigh + prevLow + prevClose) / 3;
  return {
    pp,
    r1: 2 * pp - prevLow,
    r2: pp + (prevHigh - prevLow),
    r3: prevHigh + 2 * (pp - prevLow),
    s1: 2 * pp - prevHigh,
    s2: pp - (prevHigh - prevLow),
    s3: prevLow - 2 * (prevHigh - pp),
  };
}

// ─── Opening Range ────────────────────────────────────────────────────────────

export function openingRange(bars, minutes = 15) {
  const orBars = bars.slice(0, Math.ceil(minutes / (bars[0]?.interval ?? 5)));
  const high = Math.max(...orBars.map(b => b.high));
  const low = Math.min(...orBars.map(b => b.low));
  return { high, low, range: high - low };
}

// ─── Aggregate signal strength ────────────────────────────────────────────────

export function compositeSignal(closes, highs, lows, volumes) {
  const signals = [];
  const r = rsiSignal(closes);
  signals.push(r.signal === 'OVERSOLD' ? 1 : r.signal === 'OVERBOUGHT' ? -1 : 0);

  const m = macdSignal(closes);
  signals.push(m.signal === 'BULLISH' ? 1 : m.signal === 'BEARISH' ? -1 : 0);

  const b = bbSignal(closes);
  signals.push(b.signal === 'OVERSOLD' ? 1 : b.signal === 'OVERBOUGHT' ? -1 : 0);

  const a = adxSignal(highs, lows, closes);
  if (a.trending) signals.push(a.direction === 'BULLISH' ? 1 : -1);

  const score = signals.reduce((s, v) => s + v, 0);
  const max = signals.length;
  const normalized = (score / max) * 100;

  return {
    score: normalized,
    direction: normalized > 20 ? 'BULLISH' : normalized < -20 ? 'BEARISH' : 'NEUTRAL',
    components: { rsi: r, macd: m, bb: b, adx: a },
  };
}
