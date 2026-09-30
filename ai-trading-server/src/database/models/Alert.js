import mongoose from 'mongoose';

const alertSchema = new mongoose.Schema({
  userId: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true, index: true },
  symbol: { type: String, uppercase: true },
  exchange: { type: String, default: 'NSE' },

  alertType: {
    type: String,
    enum: ['PRICE_ABOVE', 'PRICE_BELOW', 'VOLUME_SPIKE', 'STRATEGY_SIGNAL',
           'POSITION_PNL', 'DAILY_LOSS_LIMIT', 'AI_SIGNAL', 'IPO_UPDATE'],
    required: true,
  },
  condition: { type: mongoose.Schema.Types.Mixed },

  message: { type: String, required: true },
  severity: { type: String, enum: ['INFO', 'WARNING', 'CRITICAL'], default: 'INFO' },

  channels: {
    console: { type: Boolean, default: true },
    email: { type: Boolean, default: false },
    telegram: { type: Boolean, default: false },
    webhook: { type: Boolean, default: false },
  },

  triggered: { type: Boolean, default: false },
  triggeredAt: { type: Date },
  triggerCount: { type: Number, default: 0 },
  maxTriggers: { type: Number, default: 1 },

  isActive: { type: Boolean, default: true },
  expiresAt: { type: Date },
}, { timestamps: true });

alertSchema.index({ userId: 1, isActive: 1 });
alertSchema.index({ symbol: 1, alertType: 1 });

export default mongoose.model('Alert', alertSchema);
