/**
 * Strategy Registry
 * All strategies registered here, accessible by name.
 */

import { MACDCrossoverBull, MACDCrossoverBear } from './equity/intraday/MACDCrossover.js';
import { RSIBull, RSIBear } from './equity/intraday/RSIStrategy.js';
import { VWAPBull, VWAPBear } from './equity/intraday/VWAPStrategy.js';
import { ORBBull, ORBBear } from './equity/intraday/ORBStrategy.js';
import { MomentumBull, MomentumBear } from './equity/intraday/MomentumStrategy.js';
import { SuperTrendBull, SuperTrendBear } from './equity/intraday/SuperTrend.js';
import { CPRBull, CPRBear } from './equity/intraday/CPRStrategy.js';
import { GoldenCross, DeathCross } from './equity/positional/GoldenCross.js';
import { TrendFollowingBull, TrendFollowingBear } from './equity/positional/TrendFollowing.js';
import { SwingTradingBull, SwingTradingBear } from './equity/positional/SwingTrading.js';
import { EMADivergenceBull, EMADivergenceBear } from './equity/positional/EMADivergence.js';
import { BullCallSpread } from './options/bullish/BullCallSpread.js';
import { BearPutSpread } from './options/bearish/BearPutSpread.js';
import { IronCondor } from './options/neutral/IronCondor.js';
import { ShortStraddle, LongStraddle } from './options/neutral/Straddle.js';
import { ShortStrangle } from './options/neutral/ShortStrangle.js';
import { IPOAnalyzer } from './ipo/IPOAnalyzer.js';
import { ListingDayStrategy } from './ipo/ListingDayStrategy.js';

const registry = new Map();

function register(StrategyClass, params = {}) {
  const instance = new StrategyClass(params);
  registry.set(instance.name, instance);
}

// ── Equity Intraday ───────────────────────────────────────────────────────────
register(MACDCrossoverBull);
register(MACDCrossoverBear);
register(RSIBull);
register(RSIBear);
register(VWAPBull);
register(VWAPBear);
register(ORBBull);
register(ORBBear);
register(MomentumBull);
register(MomentumBear);
register(SuperTrendBull);
register(SuperTrendBear);
register(CPRBull);
register(CPRBear);

// ── Equity Positional ─────────────────────────────────────────────────────────
register(GoldenCross);
register(DeathCross);
register(TrendFollowingBull);
register(TrendFollowingBear);
register(SwingTradingBull);
register(SwingTradingBear);
register(EMADivergenceBull);
register(EMADivergenceBear);

// ── Options ───────────────────────────────────────────────────────────────────
register(BullCallSpread);
register(BearPutSpread);
register(IronCondor);
register(ShortStraddle);
register(LongStraddle);
register(ShortStrangle);

// ── IPO ───────────────────────────────────────────────────────────────────────
register(ListingDayStrategy);

export const strategies = registry;

export function getStrategy(name) {
  return registry.get(name);
}

export function listStrategies(filter = {}) {
  const all = [...registry.values()];
  let result = all;
  if (filter.type) result = result.filter(s => s.type === filter.type);
  if (filter.direction) result = result.filter(s => s.direction === filter.direction);
  return result.map(s => ({
    name: s.name,
    type: s.type,
    direction: s.direction,
    instrumentType: s.instrumentType,
    minBars: s.minBars,
    params: s.params,
  }));
}

/**
 * Run all registered strategies of a given type against provided data.
 * Returns all signals (including HOLD/no signal), sorted by confidence.
 */
export function runAll(type, data) {
  const matching = [...registry.values()].filter(s => !type || s.type === type);
  const results = matching.map(s => {
    try {
      return s.analyze(data);
    } catch (err) {
      return { strategy: s.name, action: 'HOLD', error: err.message, confidence: 0 };
    }
  });
  return results
    .filter(r => r.action !== 'HOLD' || r.confidence > 0)
    .sort((a, b) => (b.confidence || 0) - (a.confidence || 0));
}

export default { strategies, getStrategy, listStrategies, runAll };
