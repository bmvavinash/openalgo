/**
 * BaseStrategy — all strategy classes extend this.
 * Provides uniform interface: analyze(bars) → SignalResult
 */

export class BaseStrategy {
  constructor(name, params = {}) {
    this.name = name;
    this.params = params;
    this.type = 'BASE'; // INTRADAY | POSITIONAL | OPTIONS | IPO
    this.direction = 'NEUTRAL'; // BULLISH | BEARISH | NEUTRAL
    this.instrumentType = 'EQ';
  }

  // ─── Must override ────────────────────────────────────────────────────────
  // bars: Array<{ time, open, high, low, close, volume }>
  analyze(bars) {
    throw new Error(`${this.name}: analyze() not implemented`);
  }

  // ─── Helpers ──────────────────────────────────────────────────────────────

  closes(bars) { return bars.map(b => b.close); }
  opens(bars)  { return bars.map(b => b.open);  }
  highs(bars)  { return bars.map(b => b.high);  }
  lows(bars)   { return bars.map(b => b.low);   }
  volumes(bars){ return bars.map(b => b.volume);}

  /** Minimum number of bars this strategy needs. Override if needed. */
  get minBars() { return 50; }

  validate(bars) {
    if (!Array.isArray(bars) || bars.length < this.minBars) {
      return { valid: false, reason: `Need at least ${this.minBars} bars; got ${bars?.length ?? 0}` };
    }
    return { valid: true };
  }

  /** Build a uniform signal result. */
  signal(action, price, stopLoss, target, confidence, extras = {}) {
    const riskReward = stopLoss && target
      ? Math.abs((target - price) / (price - stopLoss))
      : null;
    return {
      strategy: this.name,
      type: this.type,
      direction: this.direction,
      action,           // BUY | SELL | HOLD
      price,
      stopLoss,
      target,
      confidence,       // 0–100
      riskReward,
      timestamp: new Date().toISOString(),
      ...extras,
    };
  }

  noSignal(reason = '') {
    return { strategy: this.name, action: 'HOLD', confidence: 0, reason };
  }
}

export default BaseStrategy;
