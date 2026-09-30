import mongoose from 'mongoose';

const tradeSchema = new mongoose.Schema({
  userId: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true, index: true },
  positionId: { type: mongoose.Schema.Types.ObjectId, ref: 'Position' },
  orderId: { type: mongoose.Schema.Types.ObjectId, ref: 'Order' },

  symbol: { type: String, required: true, uppercase: true },
  exchange: { type: String, enum: ['NSE', 'BSE', 'NFO', 'BFO', 'MCX'], default: 'NSE' },
  instrumentType: { type: String, enum: ['EQ', 'FUT', 'CE', 'PE', 'IPO'], default: 'EQ' },

  side: { type: String, enum: ['BUY', 'SELL'], required: true },
  quantity: { type: Number, required: true },
  price: { type: Number, required: true },
  value: { type: Number },

  strategyName: { type: String },
  strategyType: { type: String },

  // P&L (filled on exit leg)
  pnl: { type: Number },
  pnlPercent: { type: Number },
  holdingDays: { type: Number },

  // Charges breakdown
  charges: {
    brokerage: { type: Number, default: 0 },
    stt: { type: Number, default: 0 },
    exchangeFee: { type: Number, default: 0 },
    gst: { type: Number, default: 0 },
    sebiCharges: { type: Number, default: 0 },
    stampDuty: { type: Number, default: 0 },
    total: { type: Number, default: 0 },
  },

  openAlgoOrderId: { type: String },
  paperTrade: { type: Boolean, default: true },
  tradeTime: { type: Date, default: Date.now },
}, { timestamps: true });

tradeSchema.pre('save', function (next) {
  this.value = this.price * this.quantity;
  next();
});

tradeSchema.index({ userId: 1, tradeTime: -1 });
tradeSchema.index({ symbol: 1, tradeTime: -1 });

export default mongoose.model('Trade', tradeSchema);
