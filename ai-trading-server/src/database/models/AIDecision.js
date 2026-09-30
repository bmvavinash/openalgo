import mongoose from 'mongoose';

const aiDecisionSchema = new mongoose.Schema({
  userId: { type: mongoose.Schema.Types.ObjectId, ref: 'User', index: true },
  symbol: { type: String, uppercase: true },
  exchange: { type: String, default: 'NSE' },

  decisionType: {
    type: String,
    enum: ['ENTRY', 'EXIT', 'HOLD', 'SCALE_IN', 'SCALE_OUT', 'HEDGE', 'IPO_ANALYSIS', 'MARKET_ANALYSIS'],
    required: true,
  },

  action: { type: String, enum: ['BUY', 'SELL', 'HOLD', 'AVOID', 'WATCH'] },
  confidence: { type: Number, min: 0, max: 100 },
  direction: { type: String, enum: ['BULLISH', 'BEARISH', 'NEUTRAL'] },

  reasoning: { type: String },
  summary: { type: String },

  suggestedEntry: { type: Number },
  suggestedStopLoss: { type: Number },
  suggestedTarget: { type: Number },
  suggestedQuantity: { type: Number },
  riskRewardRatio: { type: Number },

  marketContext: {
    trend: { type: String },
    volatility: { type: String, enum: ['LOW', 'MEDIUM', 'HIGH'] },
    sentiment: { type: String, enum: ['BULLISH', 'BEARISH', 'NEUTRAL'] },
    keyLevels: [Number],
    indicators: { type: Map, of: mongoose.Schema.Types.Mixed },
  },

  ipoAnalysis: {
    gmpPremium: { type: Number },
    subscriptionStatus: { type: String },
    listingExpectation: { type: String },
    fundamentalScore: { type: Number, min: 0, max: 10 },
    recommendation: { type: String, enum: ['APPLY', 'AVOID', 'WATCHLIST'] },
  },

  source: { type: String, enum: ['anthropic', 'ollama', 'hybrid', 'rule_based'] },
  model: { type: String },
  promptTokens: { type: Number },
  completionTokens: { type: Number },

  executed: { type: Boolean, default: false },
  executedOrderId: { type: mongoose.Schema.Types.ObjectId, ref: 'Order' },

  expiresAt: { type: Date },
}, { timestamps: true });

aiDecisionSchema.index({ userId: 1, createdAt: -1 });
aiDecisionSchema.index({ symbol: 1, createdAt: -1 });

export default mongoose.model('AIDecision', aiDecisionSchema);
