/**
 * IPO Analyzer — fundamental + quantitative scoring
 *
 * Scores an IPO on 5 dimensions and produces a BUY/AVOID/WATCHLIST recommendation.
 * Can be called standalone or fed to the AI agent for deeper analysis.
 */
export class IPOAnalyzer {
  constructor(params = {}) {
    this.weights = {
      valuation: 0.25,
      growth: 0.20,
      profitability: 0.20,
      subscription: 0.20,
      gmp: 0.15,
      ...params.weights,
    };
    this.applyThreshold = params.applyThreshold ?? 6.5;
    this.avoidThreshold = params.avoidThreshold ?? 4.0;
  }

  /**
   * Score the IPO and return recommendation.
   * @param {object} ipo — IPO document (from the IPO model)
   */
  analyze(ipo) {
    const scores = {};

    // ── Valuation score (0–10) ───────────────────────────────────────────────
    scores.valuation = this._valuationScore(ipo);

    // ── Growth score (0–10) ──────────────────────────────────────────────────
    scores.growth = this._growthScore(ipo);

    // ── Profitability score (0–10) ───────────────────────────────────────────
    scores.profitability = this._profitabilityScore(ipo);

    // ── Subscription score (0–10) ────────────────────────────────────────────
    scores.subscription = this._subscriptionScore(ipo);

    // ── GMP score (0–10) ─────────────────────────────────────────────────────
    scores.gmp = this._gmpScore(ipo);

    const composite = Object.entries(this.weights).reduce((sum, [key, w]) => {
      return sum + (scores[key] ?? 5) * w;
    }, 0);

    const recommendation = composite >= this.applyThreshold
      ? 'APPLY'
      : composite >= this.avoidThreshold
        ? 'WATCHLIST'
        : 'AVOID';

    const strengths = this._extractStrengths(ipo, scores);
    const risks = this._extractRisks(ipo, scores);

    return {
      recommendation,
      confidence: Math.min(95, Math.round(50 + (composite - 5) * 15)),
      compositeScore: Math.round(composite * 10) / 10,
      scores,
      strengths,
      risks,
      summary: this._buildSummary(ipo, recommendation, composite, scores),
    };
  }

  _valuationScore(ipo) {
    const pe = ipo.financials?.pe;
    if (!pe) return 5;
    // Sector-adjusted P/E — simplified without sector DB
    if (pe < 20) return 9;
    if (pe < 35) return 7.5;
    if (pe < 50) return 6;
    if (pe < 80) return 4;
    return 2;
  }

  _growthScore(ipo) {
    const rev = ipo.financials?.revenue;
    const profit = ipo.financials?.profit;
    if (!rev || !profit) return 5;
    // Without prior year, score on absolute profitability
    const margin = (profit / rev) * 100;
    if (margin > 20) return 9;
    if (margin > 10) return 7;
    if (margin > 5)  return 5.5;
    if (margin > 0)  return 3.5;
    return 1; // loss-making
  }

  _profitabilityScore(ipo) {
    const { roe, roce, debtToEquity } = ipo.financials || {};
    let score = 5;
    if (roe !== undefined) {
      score += roe > 20 ? 2 : roe > 15 ? 1 : roe > 10 ? 0 : -1;
    }
    if (roce !== undefined) {
      score += roce > 20 ? 1.5 : roce > 15 ? 0.5 : 0;
    }
    if (debtToEquity !== undefined) {
      score += debtToEquity < 0.5 ? 1.5 : debtToEquity < 1 ? 0.5 : debtToEquity < 2 ? -0.5 : -2;
    }
    return Math.max(0, Math.min(10, score));
  }

  _subscriptionScore(ipo) {
    const total = ipo.subscription?.total ?? 0;
    const qib   = ipo.subscription?.qib   ?? 0;
    if (total >= 100 && qib >= 50) return 10;
    if (total >= 50  && qib >= 20) return 8;
    if (total >= 20  && qib >= 10) return 6.5;
    if (total >= 10)               return 5;
    if (total >= 3)                return 3.5;
    if (total >= 1)                return 2;
    return 1; // below 1x
  }

  _gmpScore(ipo) {
    const gmp = ipo.gmp ?? 0;
    const issuePrice = ipo.priceRange?.max ?? ipo.priceRange?.min ?? 0;
    if (!issuePrice) return 5;
    const gmpPct = (gmp / issuePrice) * 100;
    if (gmpPct >= 50)  return 10;
    if (gmpPct >= 30)  return 8;
    if (gmpPct >= 15)  return 6.5;
    if (gmpPct >= 5)   return 5;
    if (gmpPct >= 0)   return 3.5;
    return 1; // negative GMP
  }

  _extractStrengths(ipo, scores) {
    const s = [];
    if (scores.valuation >= 7) s.push('Attractive valuation vs sector peers');
    if (scores.growth >= 7)    s.push('Strong revenue and profit margins');
    if (scores.profitability >= 7) s.push('High ROE/ROCE with manageable debt');
    if (scores.subscription >= 8) s.push('Strong institutional (QIB) demand');
    if (scores.gmp >= 7) s.push(`Grey market premium indicates listing gain expected`);
    if (ipo.qualitative?.promoterHolding > 50) s.push('Promoters retaining majority stake post-IPO');
    return s.concat(ipo.qualitative?.strengths ?? []);
  }

  _extractRisks(ipo, scores) {
    const r = [];
    if (scores.valuation <= 4) r.push('Stretched valuation relative to earnings');
    if (scores.growth <= 3) r.push('Low or negative profitability margins');
    if ((ipo.financials?.debtToEquity ?? 0) > 2) r.push('High leverage / debt burden');
    if (scores.subscription <= 3) r.push('Weak subscription interest, especially from QIBs');
    if (scores.gmp <= 2) r.push('Negative or negligible grey market premium');
    if ((ipo.qualitative?.promoterHolding ?? 100) < 30) r.push('Promoters significantly diluting stake');
    return r.concat(ipo.qualitative?.risks ?? []);
  }

  _buildSummary(ipo, recommendation, score, scores) {
    const name = ipo.companyName || 'This IPO';
    const action = recommendation === 'APPLY'
      ? 'recommended for application'
      : recommendation === 'AVOID'
        ? 'not recommended — significant risks outweigh potential gains'
        : 'placed on watchlist — monitor subscription and GMP closer to closing';

    return `${name} is ${action}. Composite score: ${score.toFixed(1)}/10. ` +
      `Valuation: ${scores.valuation?.toFixed(1)}, ` +
      `Subscription: ${scores.subscription?.toFixed(1)}, ` +
      `Profitability: ${scores.profitability?.toFixed(1)}, ` +
      `GMP: ${scores.gmp?.toFixed(1)}.`;
  }
}

export default IPOAnalyzer;
