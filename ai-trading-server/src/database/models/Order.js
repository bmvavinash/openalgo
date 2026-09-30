import mongoose from 'mongoose';

const orderSchema = new mongoose.Schema({
  userId: { type: mongoose.Schema.Types.ObjectId, ref: 'User', required: true, index: true },
  positionId: { type: mongoose.Schema.Types.ObjectId, ref: 'Position' },

  symbol: { type: String, required: true, uppercase: true },
  exchange: { type: String, enum: ['NSE', 'BSE', 'NFO', 'BFO', 'MCX'], default: 'NSE' },
  instrumentType: { type: String, enum: ['EQ', 'FUT', 'CE', 'PE', 'IPO'], default: 'EQ' },

  side: { type: String, enum: ['BUY', 'SELL'], required: true },
  orderType: { type: String, enum: ['MARKET', 'LIMIT', 'SL', 'SL-M'], default: 'MARKET' },
  productType: { type: String, enum: ['MIS', 'CNC', 'NRML', 'BO', 'CO'], default: 'MIS' },

  quantity: { type: Number, required: true },
  price: { type: Number, default: 0 },
  triggerPrice: { type: Number, default: 0 },
  disclosedQuantity: { type: Number, default: 0 },

  status: {
    type: String,
    enum: ['PENDING', 'PLACED', 'OPEN', 'COMPLETE', 'REJECTED', 'CANCELLED', 'MODIFIED'],
    default: 'PENDING',
  },
  filledQuantity: { type: Number, default: 0 },
  avgFilledPrice: { type: Number, default: 0 },

  validity: { type: String, enum: ['DAY', 'IOC', 'GTC'], default: 'DAY' },

  strategyName: { type: String },
  openAlgoOrderId: { type: String },
  brokerOrderId: { type: String },

  aiGenerated: { type: Boolean, default: false },
  aiRationale: { type: String },

  paperTrade: { type: Boolean, default: true },
  rejectionReason: { type: String },
  placedAt: { type: Date },
  filledAt: { type: Date },
}, { timestamps: true });

orderSchema.index({ userId: 1, status: 1 });
orderSchema.index({ symbol: 1, createdAt: -1 });

export default mongoose.model('Order', orderSchema);
