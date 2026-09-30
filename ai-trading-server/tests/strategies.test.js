/**
 * End-to-end strategy tests (no external dependencies, pure unit tests).
 * Run with: node tests/strategies.test.js
 */

import { MACDCrossoverBull, MACDCrossoverBear } from '../src/strategies/equity/intraday/MACDCrossover.js';
import { RSIBull, RSIBear } from '../src/strategies/equity/intraday/RSIStrategy.js';
import { VWAPBull, VWAPBear } from '../src/strategies/equity/intraday/VWAPStrategy.js';
import { ORBBull, ORBBear } from '../src/strategies/equity/intraday/ORBStrategy.js';
import { MomentumBull, MomentumBear } from '../src/strategies/equity/intraday/MomentumStrategy.js';
import { GoldenCross, DeathCross } from '../src/strategies/equity/positional/GoldenCross.js';
import { TrendFollowingBull, TrendFollowingBear } from '../src/strategies/equity/positional/TrendFollowing.js';
import { SwingTradingBull, SwingTradingBear } from '../src/strategies/equity/positional/SwingTrading.js';
import { IPOAnalyzer } from '../src/strategies/ipo/IPOAnalyzer.js';
import { ListingDayStrategy } from '../src/strategies/ipo/ListingDayStrategy.js';
import { listStrategies, runAll } from '../src/strategies/index.js';
import { black76, impliedVolatility } from '../src/strategies/options/OptionsBase.js';
import { compositeSignal } from '../src/market/indicators/technical.js';

let passed = 0, failed = 0;

function test(name, fn) {
  try {
    fn();
    console.log(`  PASS  ${name}`);
    passed++;
  } catch (err) {
    console.log(`  FAIL  ${name}: ${err.message}`);
    failed++;
  }
}

function assert(condition, msg) {
  if (!condition) throw new Error(msg || 'Assertion failed');
}

function assertEqual(a, b, msg) {
  if (a !== b) throw new Error(msg || `Expected ${b}, got ${a}`);
}

// ── Generate synthetic price bars ─────────────────────────────────────────────

function makeBullBars(count = 250, basePrice = 18000, trend = 0.001) {
  const bars = [];
  let price = basePrice;
  for (let i = 0; i < count; i++) {
    const drift = price * trend;
    const noise = price * 0.005;
    const open  = price + (Math.random() - 0.4) * noise;
    const close = open + drift + (Math.random() - 0.4) * noise;
    const high  = Math.max(open, close) + Math.random() * noise * 0.5;
    const low   = Math.min(open, close) - Math.random() * noise * 0.5;
    bars.push({ time: new Date(Date.now() - (count - i) * 300000).toISOString(), open, high, low, close, volume: 500000 + Math.random() * 500000 });
    price = close;
  }
  return bars;
}

function makeBearBars(count = 250, basePrice = 20000) {
  return makeBullBars(count, basePrice, -0.001);
}

// ── Strategy Registry Tests ───────────────────────────────────────────────────

console.log('\n=== Strategy Registry ===');
test('listStrategies returns all strategies', () => {
  const list = listStrategies();
  assert(list.length >= 15, `Expected >= 15 strategies, got ${list.length}`);
});

test('listStrategies filters by type', () => {
  const intraday = listStrategies({ type: 'INTRADAY' });
  assert(intraday.length >= 5, 'Should have >= 5 intraday strategies');
  assert(intraday.every(s => s.type === 'INTRADAY'), 'All should be INTRADAY');
});

test('listStrategies filters by direction', () => {
  const bullish = listStrategies({ direction: 'BULLISH' });
  assert(bullish.every(s => s.direction === 'BULLISH'), 'All should be BULLISH');
});

// ── MACD Tests ────────────────────────────────────────────────────────────────

console.log('\n=== MACD Crossover ===');
test('MACDCrossoverBull.analyze returns signal shape', () => {
  const strat = new MACDCrossoverBull();
  const bars = makeBullBars(200);
  const result = strat.analyze(bars);
  assert('strategy' in result, 'Missing strategy key');
  assert('action' in result, 'Missing action key');
  assert('confidence' in result, 'Missing confidence key');
});

test('MACDCrossoverBull.analyze with too few bars returns noSignal', () => {
  const strat = new MACDCrossoverBull();
  const result = strat.analyze(makeBullBars(10));
  assertEqual(result.action, 'HOLD', 'Should return HOLD for insufficient data');
  assert(result.confidence === 0, 'Confidence should be 0');
});

test('MACDCrossoverBear.analyze returns signal shape', () => {
  const strat = new MACDCrossoverBear();
  const result = strat.analyze(makeBearBars(200));
  assert('action' in result, 'Missing action key');
});

// ── RSI Tests ─────────────────────────────────────────────────────────────────

console.log('\n=== RSI Strategy ===');
test('RSIBull requires sufficient bars', () => {
  const strat = new RSIBull();
  const result = strat.analyze(makeBullBars(20));
  assertEqual(result.action, 'HOLD');
});

test('RSIBear.analyze returns a result', () => {
  const strat = new RSIBear();
  const result = strat.analyze(makeBearBars(200));
  assert(['BUY','SELL','HOLD'].includes(result.action), `Unexpected action: ${result.action}`);
});

// ── VWAP Tests ────────────────────────────────────────────────────────────────

console.log('\n=== VWAP Strategy ===');
test('VWAPBull returns valid signal shape', () => {
  const strat = new VWAPBull();
  const result = strat.analyze(makeBullBars(100));
  assert(['BUY','HOLD'].includes(result.action));
});

test('VWAPBear returns valid signal shape', () => {
  const strat = new VWAPBear();
  const result = strat.analyze(makeBearBars(100));
  assert(['SELL','HOLD'].includes(result.action));
});

// ── ORB Tests ─────────────────────────────────────────────────────────────────

console.log('\n=== Opening Range Breakout ===');
test('ORBBull handles small bar count', () => {
  const strat = new ORBBull();
  const bars = makeBullBars(20);
  const result = strat.analyze(bars);
  assert('action' in result);
});

test('ORBBear handles small bar count', () => {
  const strat = new ORBBear();
  const result = strat.analyze(makeBearBars(20));
  assert('action' in result);
});

// ── Momentum Tests ────────────────────────────────────────────────────────────

console.log('\n=== Momentum Strategy ===');
test('MomentumBull returns signal with confidence', () => {
  const strat = new MomentumBull();
  const result = strat.analyze(makeBullBars(200));
  assert(typeof result.confidence === 'number');
  assert(result.confidence >= 0 && result.confidence <= 100);
});

// ── Positional Tests ──────────────────────────────────────────────────────────

console.log('\n=== Positional Strategies ===');
test('GoldenCross requires 220+ bars', () => {
  const strat = new GoldenCross();
  const result = strat.analyze(makeBullBars(100));
  assertEqual(result.action, 'HOLD');
});

test('GoldenCross with 240 bars returns signal', () => {
  const strat = new GoldenCross();
  const result = strat.analyze(makeBullBars(240));
  assert(['BUY','HOLD'].includes(result.action));
});

test('TrendFollowingBull requires 210 bars', () => {
  const strat = new TrendFollowingBull();
  const result = strat.analyze(makeBullBars(50));
  assertEqual(result.action, 'HOLD');
});

test('TrendFollowingBull with 220 bars returns result', () => {
  const strat = new TrendFollowingBull();
  const result = strat.analyze(makeBullBars(220));
  assert('action' in result);
});

test('SwingTradingBull returns result', () => {
  const strat = new SwingTradingBull();
  const result = strat.analyze(makeBullBars(150));
  assert(['BUY','HOLD'].includes(result.action));
});

test('SwingTradingBear returns result', () => {
  const strat = new SwingTradingBear();
  const result = strat.analyze(makeBearBars(150));
  assert(['SELL','HOLD'].includes(result.action));
});

// ── IPO Tests ─────────────────────────────────────────────────────────────────

console.log('\n=== IPO Analyzer ===');
test('IPOAnalyzer.analyze returns recommendation', () => {
  const analyzer = new IPOAnalyzer();
  const result = analyzer.analyze({
    companyName: 'Test Corp',
    priceRange: { max: 500 },
    financials: { pe: 25, roe: 18, roce: 20, debtToEquity: 0.3 },
    subscription: { total: 50, qib: 25, nii: 15, retail: 10 },
    gmp: 75,
  });
  assert(['APPLY', 'AVOID', 'WATCHLIST'].includes(result.recommendation));
  assert(typeof result.compositeScore === 'number');
  assert(result.compositeScore >= 0 && result.compositeScore <= 10);
  assert(Array.isArray(result.strengths));
  assert(Array.isArray(result.risks));
  console.log(`    IPO score: ${result.compositeScore}/10 → ${result.recommendation}`);
});

test('IPOAnalyzer returns AVOID for very high PE loss-making IPO', () => {
  const analyzer = new IPOAnalyzer();
  const result = analyzer.analyze({
    companyName: 'BadCo IPO',
    priceRange: { max: 1000 },
    financials: { pe: 200, revenue: 1000, profit: -100, debtToEquity: 5 },
    subscription: { total: 0.5, qib: 0 },
    gmp: -50,
  });
  assert(result.recommendation === 'AVOID', `Expected AVOID, got ${result.recommendation}`);
});

test('IPOAnalyzer returns APPLY for strong IPO', () => {
  const analyzer = new IPOAnalyzer();
  const result = analyzer.analyze({
    companyName: 'GoodCo IPO',
    priceRange: { max: 200 },
    financials: { pe: 15, revenue: 5000, profit: 1500, roe: 25, roce: 28, debtToEquity: 0.1 },
    subscription: { total: 150, qib: 80, nii: 40, retail: 30 },
    gmp: 80,
    qualitative: { promoterHolding: 65 },
  });
  assert(result.recommendation === 'APPLY', `Expected APPLY, got ${result.recommendation}`);
});

// ── Listing Day Tests ─────────────────────────────────────────────────────────

console.log('\n=== Listing Day Strategy ===');
test('ListingDayStrategy for allotment holder on strong listing', () => {
  const strat = new ListingDayStrategy();
  const result = strat.analyze({
    issuePrice: 500, currentPrice: 620, openPrice: 650,
    gotAllotment: true, bars: [
      { time: 't1', open: 650, high: 680, low: 640, close: 660, volume: 5000000 },
      { time: 't2', open: 660, high: 670, low: 650, close: 655, volume: 2000000 },
    ], lotSize: 50,
  });
  assertEqual(result.action, 'HOLD');
});

test('ListingDayStrategy exits on weak listing for allotment holder', () => {
  const strat = new ListingDayStrategy();
  const result = strat.analyze({
    issuePrice: 500, currentPrice: 460, openPrice: 455,
    gotAllotment: true, bars: [], lotSize: 50,
  });
  assertEqual(result.action, 'SELL');
});

// ── Black-76 Options Tests ────────────────────────────────────────────────────

console.log('\n=== Black-76 Options Pricing ===');
test('Black-76 CE price is positive for ITM call', () => {
  const { price } = black76('CE', 18500, 18000, 30/365, 0.065, 0.18);
  assert(price > 0, `CE price should be > 0, got ${price}`);
  assert(price > 500, `ITM call should be > intrinsic (500), got ${price}`);
});

test('Black-76 PE price is positive for ITM put', () => {
  const { price } = black76('PE', 18000, 18500, 30/365, 0.065, 0.18);
  assert(price > 0);
  assert(price > 500);
});

test('Black-76 delta for CE is between 0 and 1', () => {
  const { delta } = black76('CE', 18500, 18500, 30/365, 0.065, 0.2);
  assert(delta >= 0 && delta <= 1, `CE delta ${delta} out of range`);
});

test('Black-76 put-call parity holds approximately', () => {
  const F = 18500, K = 18500, T = 30/365, r = 0.065, sigma = 0.2;
  const ce = black76('CE', F, K, T, r, sigma);
  const pe = black76('PE', F, K, T, r, sigma);
  const discount = Math.exp(-r * T);
  const parity = Math.abs(ce.price - pe.price - discount * (F - K));
  assert(parity < 1, `Put-call parity violated: ${parity}`);
});

test('Implied volatility back-calculation is accurate', () => {
  const F = 18500, K = 18500, T = 30/365, r = 0.065, trueIV = 0.22;
  const { price } = black76('CE', F, K, T, r, trueIV);
  const recoveredIV = impliedVolatility('CE', F, K, T, r, price);
  const error = Math.abs(recoveredIV - trueIV);
  assert(error < 0.001, `IV recovery error too large: ${error.toFixed(5)}`);
});

// ── Composite Signal ──────────────────────────────────────────────────────────

console.log('\n=== Composite Signal ===');
test('compositeSignal returns direction for bullish bars', () => {
  const bars = makeBullBars(100);
  const cl = bars.map(b => b.close);
  const hi = bars.map(b => b.high);
  const lo = bars.map(b => b.low);
  const vo = bars.map(b => b.volume);
  const result = compositeSignal(cl, hi, lo, vo);
  assert(['BULLISH','BEARISH','NEUTRAL'].includes(result.direction));
  assert(typeof result.score === 'number');
  console.log(`    Composite score: ${result.score.toFixed(1)} → ${result.direction}`);
});

// ── RunAll ─────────────────────────────────────────────────────────────────────

console.log('\n=== RunAll ===');
test('runAll INTRADAY returns array of signals', () => {
  const bars = makeBullBars(250);
  const signals = runAll('INTRADAY', bars);
  assert(Array.isArray(signals), 'Should be array');
  console.log(`    Got ${signals.length} intraday signals`);
});

test('runAll POSITIONAL returns array of signals', () => {
  const bars = makeBullBars(250);
  const signals = runAll('POSITIONAL', bars);
  assert(Array.isArray(signals));
  console.log(`    Got ${signals.length} positional signals`);
});

// ── Final Report ──────────────────────────────────────────────────────────────

console.log(`\n${'─'.repeat(50)}`);
console.log(`Results: ${passed} passed, ${failed} failed`);
if (failed > 0) {
  console.log('SOME TESTS FAILED');
  process.exit(1);
} else {
  console.log('ALL TESTS PASSED');
}
