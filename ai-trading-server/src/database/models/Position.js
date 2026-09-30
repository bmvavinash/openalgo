import mongoose from 'mongoose';

const positionSchema = new mongoose.Schema({
  userId: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true, index: true },
  symbol: { type: String, required: true, uppercase: true, trim: true },
  exchange: { type: String, enum: ['NSE', 'BSE', 'NFO', 'BFO', 'MCX'], default: 'NSE' },
  instrumentType: { type: String, enum: ['EQ', 'FUT', 'CE', 'PE', 'IPO'], default: 'EQ' },
  direction: { type: String, enum: ['LONG', 'SHORT'], required: true },
  quantity: { type: Number, required: true },
  entryPrice: { type: Number, required: true },
  currentPrice: { type: Number, default: 0 },
  stopLoss: { type: Number },
  target: { type: Number },
  trailingStop: { type: Number },

  // Options specific
  strikePrice: { type: Number },
  expiry: { type: Date },
  optionType: { type: String, enum: ['CE', 'PE'] },
  lotSize: { type: Number, default: 1 },

  // Strategy info
  strategyName: { type: String },
  strategyType: { type: String, enum: ['INTRADAY', 'POSITIONAL', 'OPTIONS', 'IPO'] },
  timeframe: { type: String },
  aiGenerated: { type: Boolean, default: false },
  aiConfidence: { type: Number, min: 0, max: 100 },

  // P&L
  unrealizedPnl: { type: Number, default: 0 },
  unrealizedPnlPercent: { type: Number, default: 0 },
  realizedPnl: { type: Number, default: 0 },
  charges: { type: Number, default: 0 },

  status: {
    type: String,
    enum: ['OPEN', 'CLOSED', 'PARTIAL', 'PENDING_EXIT'],
    default: 'OPEN',
  },
  openTime: { type: Date, default: Date.now },
  closeTime: { type: Date },
  exitPrice: { type: Number },
  exitReason: { type: String, enum: ['TARGET', 'STOPLOSS', 'MANUAL', 'EOD', 'AI_EXIT', 'TRAILING'] },

  tags: [String],
  notes: { type: String },
  paperTrade: { type: Boolean, default: true },
}, { timestamps: true });

positionSchema.virtual('pnlPercent').get(function () {
  if (!this.entryPrice || this.entryPrice === 0) return 0;
  const pnl = (this.currentPrice - this.entryPrice) * this.quantity;
  return (pnl / (this.entryPrice * this.quantity)) * 100;
});

positionSchema.index({ userId: 1, status: 1 });
positionSchema.index({ userId: 1, symbol: 1 });
positionSchema.index({ openTime: 1 });

export default mongoose.model('Position', positionSchema);
