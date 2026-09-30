import { AnthropicAgent } from './AnthropicAgent.js';
import { OllamaAgent } from './OllamaAgent.js';
import { listStrategies, runAll } from '../strategies/index.js';
import { compositeSignal } from '../market/indicators/technical.js';
import { IPOAnalyzer } from '../strategies/ipo/IPOAnalyzer.js';
import AIDecision from '../database/models/AIDecision.js';
import { logger } from '../config/logger.js';
import { config } from '../config/index.js';

/**
 * DecisionEngine — orchestrates AI + rule-based analysis into actionable decisions.
 *
 * Flow:
 *   1. Run all applicable rule-based strategies → collect signals
 *   2. Compute composite technical score
 *   3. Feed everything to AI (Anthropic or OLLAMA) for deeper context
 *   4. Merge and return a final decision with confidence
 *   5. Persist decision to DB
 */
export class DecisionEngine {
  constructor() {
    this.anthropic = new AnthropicAgent();
    this.ollama    = new OllamaAgent();
  }

  // ── Equity Analysis ────────────────────────────────────────────────────────

  async analyzeEquity({ symbol, exchange = 'NSE', bars, timeframe = 'INTRADAY', userId }) {
    if (!bars || bars.length < 30) {
      return { error: 'Insufficient price data', symbol };
    }

    const closes  = bars.map(b => b.close);
    const highs   = bars.map(b => b.high);
    const lows    = bars.map(b => b.low);
    const volumes = bars.map(b => b.volume);

    // 1. Composite technical signal
    let composite;
    try {
      composite = compositeSignal(closes, highs, lows, volumes);
    } catch (e) {
      composite = { score: 0, direction: 'NEUTRAL', components: {} };
    }

    // 2. Rule-based strategy signals
    const strategyType = timeframe === 'INTRADAY' ? 'INTRADAY' : 'POSITIONAL';
    const signals = runAll(strategyType, bars);
    const topSignals = signals.slice(0, 5);

    // 3. AI analysis
    let aiResult = null;
    try {
      if (config.ai.enabled) {
        const aiInput = {
          symbol, exchange, bars,
          indicators: composite.components,
          existingSignals: topSignals,
          marketContext: { timeframe, strategyType, compositeScore: composite.score },
        };

        const ollamaAvail = await this.ollama.isAvailable();
        if (ollamaAvail) {
          aiResult = await this.ollama.analyzeEquity({ ...aiInput, recentBars: bars.slice(-10) });
        }

        // Anthropic as primary (or fallback if OLLAMA failed/unavailable)
        if (!aiResult?.success) {
          aiResult = await this.anthropic.analyzeEquity(aiInput);
        }
      }
    } catch (err) {
      logger.error(`DecisionEngine.analyzeEquity AI error: ${err.message}`);
    }

    // 4. Merge rule-based + AI
    const finalDecision = this._mergeEquityDecision(composite, topSignals, aiResult, symbol);

    // 5. Persist
    await this._persistDecision({
      userId, symbol, exchange,
      decisionType: 'ENTRY',
      action: finalDecision.action,
      confidence: finalDecision.confidence,
      direction: finalDecision.direction,
      reasoning: finalDecision.reasoning,
      summary: finalDecision.summary,
      suggestedEntry: finalDecision.suggestedEntry,
      suggestedStopLoss: finalDecision.suggestedStopLoss,
      suggestedTarget: finalDecision.suggestedTarget,
      riskRewardRatio: finalDecision.riskReward,
      source: aiResult?.source || 'rule_based',
      model: aiResult?.model,
      promptTokens: aiResult?.usage?.input,
      completionTokens: aiResult?.usage?.output,
      marketContext: { composite, topSignals },
    });

    return finalDecision;
  }

  // ── IPO Analysis ───────────────────────────────────────────────────────────

  async analyzeIPO(ipo, userId) {
    // Rule-based scoring first
    const analyzer = new IPOAnalyzer();
    const ruleResult = analyzer.analyze(ipo);

    let aiResult = null;
    try {
      if (config.ai.enabled) {
        const ollamaAvail = await this.ollama.isAvailable();
        if (ollamaAvail) {
          aiResult = await this.ollama.analyzeIPO(ipo);
        }
        if (!aiResult?.success) {
          aiResult = await this.anthropic.analyzeIPO(ipo);
        }
      }
    } catch (err) {
      logger.error(`DecisionEngine.analyzeIPO AI error: ${err.message}`);
    }

    const aiData = aiResult?.data || {};
    const finalRec = aiData.recommendation || ruleResult.recommendation;

    const decision = {
      recommendation: finalRec,
      confidence: Math.round((ruleResult.confidence + (aiData.confidence || ruleResult.confidence)) / 2),
      compositeScore: ruleResult.compositeScore,
      fundamentalScore: aiData.fundamentalScore || ruleResult.scores?.profitability,
      valuationScore: aiData.valuationScore || ruleResult.scores?.valuation,
      industryScore: aiData.industryScore || ruleResult.scores?.growth,
      riskScore: aiData.riskScore,
      summary: aiData.summary || ruleResult.summary,
      detailedAnalysis: aiData.detailedAnalysis,
      strengths: [...new Set([...(ruleResult.strengths || []), ...(aiData.strengths || [])])],
      risks: [...new Set([...(ruleResult.risks || []), ...(aiData.risks || [])])],
      listingGainExpectation: aiData.listingGainExpectation,
      longTermOutlook: aiData.longTermOutlook,
    };

    await this._persistDecision({
      userId, symbol: ipo.symbol, exchange: ipo.exchange,
      decisionType: 'IPO_ANALYSIS',
      action: finalRec === 'APPLY' ? 'BUY' : finalRec === 'AVOID' ? 'SELL' : 'HOLD',
      confidence: decision.confidence,
      direction: finalRec === 'APPLY' ? 'BULLISH' : 'NEUTRAL',
      summary: decision.summary,
      source: aiResult?.source || 'rule_based',
      model: aiResult?.model,
      ipoAnalysis: {
        gmpPremium: ipo.gmp,
        subscriptionStatus: `Total: ${ipo.subscription?.total}×`,
        fundamentalScore: decision.fundamentalScore,
        recommendation: finalRec,
        listingExpectation: decision.listingGainExpectation,
      },
    });

    return decision;
  }

  // ── Third-party Recommendation Parser ─────────────────────────────────────

  async parseExternalRecommendation({ rawText, source, symbol, userId }) {
    let aiResult = null;
    try {
      const ollamaAvail = await this.ollama.isAvailable();
      if (ollamaAvail) {
        aiResult = await this.ollama.parseRecommendation({ rawText, symbol });
      }
      if (!aiResult?.success) {
        aiResult = await this.anthropic.parseRecommendation({ rawText, source, symbol });
      }
    } catch (err) {
      logger.error(`DecisionEngine.parseRecommendation error: ${err.message}`);
      return { success: false, error: err.message };
    }

    const data = aiResult?.data || {};

    if (data.shouldAct && data.valid) {
      await this._persistDecision({
        userId, symbol: data.symbol || symbol, exchange: data.exchange || 'NSE',
        decisionType: 'ENTRY',
        action: data.action,
        confidence: data.confidence,
        direction: data.action === 'BUY' ? 'BULLISH' : data.action === 'SELL' ? 'BEARISH' : 'NEUTRAL',
        summary: `External signal from ${source}: ${data.action} ${data.symbol}`,
        reasoning: data.reasoning,
        suggestedEntry: data.entry || data.adjustedEntry,
        suggestedStopLoss: data.stopLoss || data.adjustedStopLoss,
        suggestedTarget: data.target || data.adjustedTarget,
        source: aiResult.source,
        model: aiResult.model,
      });
    }

    return { success: true, data, source: aiResult?.source };
  }

  // ── Market Overview ────────────────────────────────────────────────────────

  async getMarketOverview(marketData, userId) {
    let aiResult = null;
    try {
      aiResult = await this.anthropic.marketOverview(marketData);
    } catch (err) {
      logger.error(`DecisionEngine.marketOverview error: ${err.message}`);
    }

    return {
      success: !!aiResult?.success,
      data: aiResult?.data || {},
      source: aiResult?.source,
    };
  }

  // ── Private helpers ────────────────────────────────────────────────────────

  _mergeEquityDecision(composite, signals, aiResult, symbol) {
    const aiData = aiResult?.data || {};

    const actions = signals
      .filter(s => s.action !== 'HOLD')
      .map(s => s.action);

    const bullCount = actions.filter(a => a === 'BUY').length;
    const bearCount = actions.filter(a => a === 'SELL').length;

    let ruleAction = 'HOLD';
    if (bullCount > bearCount && bullCount >= 2) ruleAction = 'BUY';
    else if (bearCount > bullCount && bearCount >= 2) ruleAction = 'SELL';

    const action    = aiData.action    || ruleAction;
    const direction = aiData.direction || composite.direction;
    const avgRuleConfidence = signals.length
      ? signals.reduce((s, x) => s + (x.confidence || 0), 0) / signals.length : 0;
    const confidence = Math.round(
      (avgRuleConfidence + (aiData.confidence || avgRuleConfidence)) / 2
    );

    const topSignal = signals[0] || {};

    return {
      symbol, action, direction, confidence,
      reasoning: aiData.reasoning || `Rule-based: ${bullCount} bull, ${bearCount} bear signals. Composite: ${composite.score.toFixed(1)}`,
      summary: aiData.summary || `${symbol}: ${action} — ${direction} bias with ${confidence}% confidence`,
      suggestedEntry: aiData.suggestedEntry || topSignal.price,
      suggestedStopLoss: aiData.suggestedStopLoss || topSignal.stopLoss,
      suggestedTarget: aiData.suggestedTarget || topSignal.target,
      riskReward: aiData.riskRewardRatio || topSignal.riskReward,
      supportLevels: aiData.supportLevels || [],
      resistanceLevels: aiData.resistanceLevels || [],
      keyRisks: aiData.keyRisks || [],
      catalysts: aiData.catalysts || [],
      topStrategies: signals.slice(0, 3).map(s => s.strategy),
      aiEnhanced: !!aiResult?.success,
    };
  }

  async _persistDecision(data) {
    try {
      const doc = new AIDecision({
        ...data,
        expiresAt: new Date(Date.now() + 24 * 60 * 60 * 1000), // 24h TTL
      });
      await doc.save();
      return doc._id;
    } catch (err) {
      logger.error(`DecisionEngine: failed to persist decision — ${err.message}`);
    }
  }
}

export default DecisionEngine;
