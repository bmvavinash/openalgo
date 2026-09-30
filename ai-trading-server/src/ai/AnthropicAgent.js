import Anthropic from '@anthropic-ai/sdk';
import { config } from '../config/index.js';
import { logger } from '../config/logger.js';

/**
 * Anthropic Claude AI agent for trading analysis.
 * Uses Claude Opus for deep analysis and decision making.
 */
export class AnthropicAgent {
  constructor() {
    this.client = new Anthropic({ apiKey: config.ai.anthropicKey });
    this.model = config.ai.model;
    this.enabled = config.ai.enabled && !!config.ai.anthropicKey;
  }

  /**
   * Analyze a stock/index and recommend a trade.
   */
  async analyzeEquity({ symbol, exchange, bars, indicators, existingSignals, marketContext }) {
    if (!this.enabled) return this._unavailable();

    const prompt = `You are an expert Indian equity trader and quant analyst with 20+ years of experience.

Analyze the following market data for **${symbol}** (${exchange}) and provide a trading recommendation.

## Market Context
${JSON.stringify(marketContext || {}, null, 2)}

## Technical Indicators (latest values)
${JSON.stringify(indicators || {}, null, 2)}

## Rule-Based Strategy Signals
${JSON.stringify(existingSignals || [], null, 2)}

## Recent Price Action (last 10 bars)
${JSON.stringify((bars || []).slice(-10), null, 2)}

Provide your analysis in the following JSON format ONLY (no other text):
{
  "action": "BUY" | "SELL" | "HOLD" | "AVOID",
  "direction": "BULLISH" | "BEARISH" | "NEUTRAL",
  "confidence": 0-100,
  "summary": "2-3 sentence summary of the key thesis",
  "reasoning": "detailed multi-paragraph analysis",
  "suggestedEntry": number or null,
  "suggestedStopLoss": number or null,
  "suggestedTarget": number or null,
  "riskRewardRatio": number or null,
  "timeframe": "INTRADAY" | "SWING" | "POSITIONAL",
  "keyRisks": ["risk1", "risk2"],
  "catalysts": ["catalyst1", "catalyst2"],
  "volumeAnalysis": "string",
  "supportLevels": [number],
  "resistanceLevels": [number]
}`;

    return this._call(prompt, `equity_analysis_${symbol}`);
  }

  /**
   * Analyze options chain and recommend a strategy.
   */
  async analyzeOptions({ symbol, spotPrice, futurePrice, chain, expiry, ivRank, baseSignal }) {
    if (!this.enabled) return this._unavailable();

    const prompt = `You are an expert Indian options trader specializing in NSE/BSE derivatives.

Analyze the options setup for **${symbol}** and recommend the best strategy.

## Spot Price: ${spotPrice}
## Futures Price: ${futurePrice}
## Expiry: ${expiry}
## IV Rank: ${ivRank}%
## Base Signal: ${JSON.stringify(baseSignal || {}, null, 2)}

## Options Chain (key strikes)
${JSON.stringify((chain || []).slice(0, 20), null, 2)}

Important: Indian options use Black-76 pricing off the synthetic future (not Black-Scholes on spot).

Recommend the single best options strategy in this JSON format ONLY:
{
  "strategy": "strategy name",
  "action": "BUY" | "SELL" | "HOLD",
  "confidence": 0-100,
  "summary": "brief thesis",
  "legs": [{ "action": "BUY"|"SELL", "strike": number, "type": "CE"|"PE", "targetPremium": number }],
  "maxProfit": number,
  "maxLoss": number,
  "breakevens": [number],
  "idealExitDTE": number,
  "greekRationale": "string explaining delta/theta/vega thesis",
  "riskManagement": "string",
  "keyRisks": ["risk1", "risk2"]
}`;

    return this._call(prompt, `options_analysis_${symbol}`);
  }

  /**
   * Analyze an IPO for application recommendation.
   */
  async analyzeIPO(ipo) {
    if (!this.enabled) return this._unavailable();

    const prompt = `You are an expert IPO analyst covering Indian primary markets.

Analyze this IPO and provide a detailed recommendation.

## IPO Details
${JSON.stringify(ipo, null, 2)}

Consider:
1. Valuation — P/E vs sector peers, P/B, revenue multiple
2. Business quality — moat, growth runway, sector tailwinds/headwinds
3. Financials — revenue growth, margin trends, cash flow, debt
4. Promoter quality and stake retention
5. Grey market premium and subscription status (if available)
6. Listing day expectations

Respond in this JSON format ONLY:
{
  "recommendation": "APPLY" | "AVOID" | "WATCHLIST",
  "confidence": 0-100,
  "fundamentalScore": 0-10,
  "valuationScore": 0-10,
  "industryScore": 0-10,
  "riskScore": 0-10,
  "summary": "3-4 sentence executive summary",
  "detailedAnalysis": "comprehensive analysis",
  "strengths": ["s1", "s2", "s3"],
  "risks": ["r1", "r2", "r3"],
  "listingGainExpectation": "LOW" | "MODERATE" | "HIGH",
  "longTermOutlook": "POSITIVE" | "NEUTRAL" | "NEGATIVE",
  "suggestedAllocationPercent": number
}`;

    return this._call(prompt, `ipo_analysis_${ipo.companyName || ipo._id}`);
  }

  /**
   * Analyze a third-party recommendation (from external signal provider, broker research, etc.)
   */
  async parseRecommendation({ rawText, source, symbol }) {
    if (!this.enabled) return this._unavailable();

    const prompt = `You are analyzing a trading recommendation from an external source.

Source: ${source || 'Unknown'}
Symbol: ${symbol || 'Unknown'}

Raw recommendation text:
"""
${rawText}
"""

Extract and validate this recommendation. Cross-check the reasoning with standard technical analysis principles.

Respond in this JSON format ONLY:
{
  "valid": true | false,
  "action": "BUY" | "SELL" | "HOLD",
  "symbol": "string",
  "exchange": "NSE" | "BSE" | "NFO",
  "confidence": 0-100,
  "entry": number or null,
  "stopLoss": number or null,
  "target": number or null,
  "timeframe": "INTRADAY" | "SWING" | "POSITIONAL",
  "reasoning": "extracted and validated reasoning",
  "redFlags": ["any concerns or contradictions"],
  "validationNotes": "your independent assessment",
  "shouldAct": true | false,
  "adjustedTarget": number or null,
  "adjustedStopLoss": number or null
}`;

    return this._call(prompt, `rec_parse_${symbol || 'unknown'}`);
  }

  /**
   * Generate daily market overview.
   */
  async marketOverview({ niftyData, bankNiftyData, sectorData, globalCues, fiiDiiData }) {
    if (!this.enabled) return this._unavailable();

    const prompt = `You are a senior market analyst providing the daily morning briefing.

## Nifty50 Data
${JSON.stringify(niftyData || {}, null, 2)}

## BankNifty Data
${JSON.stringify(bankNiftyData || {}, null, 2)}

## Sector Performance
${JSON.stringify(sectorData || {}, null, 2)}

## Global Cues
${JSON.stringify(globalCues || {}, null, 2)}

## FII/DII Activity
${JSON.stringify(fiiDiiData || {}, null, 2)}

Provide the market overview in this JSON format ONLY:
{
  "overallSentiment": "BULLISH" | "BEARISH" | "NEUTRAL",
  "confidence": 0-100,
  "niftyOutlook": {
    "bias": "BULLISH" | "BEARISH" | "NEUTRAL",
    "support": [number, number],
    "resistance": [number, number],
    "keyLevel": number
  },
  "bankNiftyOutlook": {
    "bias": "BULLISH" | "BEARISH" | "NEUTRAL",
    "support": [number, number],
    "resistance": [number, number]
  },
  "topSectors": ["sector1", "sector2"],
  "avoidSectors": ["sector1"],
  "tradingStrategy": "string — recommended approach for the day",
  "watchlist": ["SYMBOL1", "SYMBOL2", "SYMBOL3"],
  "keyRisks": ["risk1", "risk2"],
  "summary": "comprehensive 3-4 paragraph market overview"
}`;

    return this._call(prompt, 'market_overview');
  }

  // ── Private helpers ────────────────────────────────────────────────────────

  async _call(prompt, label) {
    try {
      const resp = await this.client.messages.create({
        model: this.model,
        max_tokens: 2048,
        messages: [{ role: 'user', content: prompt }],
      });

      const text = resp.content[0]?.text || '';
      let parsed;
      try {
        // Extract JSON even if wrapped in markdown code fences
        const jsonMatch = text.match(/```(?:json)?\s*([\s\S]+?)```/) || [null, text];
        parsed = JSON.parse(jsonMatch[1].trim());
      } catch {
        logger.warn(`AnthropicAgent [${label}]: failed to parse JSON response`);
        parsed = { raw: text, parseError: true };
      }

      return {
        success: true,
        source: 'anthropic',
        model: this.model,
        data: parsed,
        usage: { input: resp.usage?.input_tokens, output: resp.usage?.output_tokens },
      };
    } catch (err) {
      logger.error(`AnthropicAgent [${label}]: ${err.message}`);
      return { success: false, error: err.message, source: 'anthropic' };
    }
  }

  _unavailable() {
    return { success: false, error: 'Anthropic AI not configured or disabled', source: 'anthropic' };
  }
}

export default AnthropicAgent;
