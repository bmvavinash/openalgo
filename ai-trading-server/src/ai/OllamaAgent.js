import axios from 'axios';
import { config } from '../config/index.js';
import { logger } from '../config/logger.js';

/**
 * OLLAMA local AI agent — privacy-first, offline trading analysis.
 * Requires OLLAMA running locally with a compatible model (llama3.2, mistral, etc.)
 */
export class OllamaAgent {
  constructor() {
    this.baseUrl = config.ai.ollama.baseUrl;
    this.model   = config.ai.ollama.model;
    this.enabled = config.ai.ollama.enabled;
  }

  async isAvailable() {
    if (!this.enabled) return false;
    try {
      await axios.get(`${this.baseUrl}/api/tags`, { timeout: 3000 });
      return true;
    } catch {
      return false;
    }
  }

  async analyzeEquity({ symbol, indicators, existingSignals, recentBars }) {
    if (!this.enabled) return this._unavailable();

    const prompt = `You are a trading analyst. Analyze ${symbol} and give a JSON recommendation.

Technical indicators: ${JSON.stringify(indicators || {})}
Strategy signals: ${JSON.stringify(existingSignals || [])}
Recent bars: ${JSON.stringify((recentBars || []).slice(-5))}

Respond ONLY with valid JSON:
{"action":"BUY"|"SELL"|"HOLD","confidence":0-100,"summary":"string","suggestedEntry":null,"suggestedStopLoss":null,"suggestedTarget":null,"direction":"BULLISH"|"BEARISH"|"NEUTRAL"}`;

    return this._call(prompt, `equity_${symbol}`);
  }

  async analyzeIPO(ipo) {
    if (!this.enabled) return this._unavailable();

    const prompt = `Analyze this IPO and give a recommendation as JSON only:
${JSON.stringify(ipo)}

Respond ONLY with valid JSON:
{"recommendation":"APPLY"|"AVOID"|"WATCHLIST","confidence":0-100,"summary":"string","fundamentalScore":0-10,"risks":[],"strengths":[]}`;

    return this._call(prompt, `ipo_${ipo.companyName}`);
  }

  async parseRecommendation({ rawText, symbol }) {
    if (!this.enabled) return this._unavailable();

    const prompt = `Extract the trading recommendation from this text and validate it.
Text: "${rawText}"

Respond ONLY with valid JSON:
{"valid":true|false,"action":"BUY"|"SELL"|"HOLD","symbol":"string","entry":null,"stopLoss":null,"target":null,"confidence":0-100,"shouldAct":true|false}`;

    return this._call(prompt, `rec_${symbol}`);
  }

  // ── Private ────────────────────────────────────────────────────────────────

  async _call(prompt, label) {
    try {
      const resp = await axios.post(`${this.baseUrl}/api/generate`, {
        model: this.model,
        prompt,
        stream: false,
        options: { temperature: 0.3, num_predict: 512 },
      }, { timeout: 60000 });

      const text = resp.data?.response || '';
      let parsed;
      try {
        const jsonMatch = text.match(/\{[\s\S]+\}/) || [];
        parsed = JSON.parse(jsonMatch[0] || text);
      } catch {
        parsed = { raw: text, parseError: true };
      }

      return { success: true, source: 'ollama', model: this.model, data: parsed };
    } catch (err) {
      logger.error(`OllamaAgent [${label}]: ${err.message}`);
      return { success: false, error: err.message, source: 'ollama' };
    }
  }

  _unavailable() {
    return { success: false, error: 'OLLAMA not enabled', source: 'ollama' };
  }
}

export default OllamaAgent;
