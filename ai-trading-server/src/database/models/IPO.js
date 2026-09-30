import mongoose from 'mongoose';

const ipoSchema = new mongoose.Schema({
  companyName: { type: String, required: true, trim: true },
  symbol: { type: String, uppercase: true, trim: true },
  exchange: { type: String, enum: ['NSE', 'BSE', 'BOTH'], default: 'BOTH' },

  ipoType: { type: String, enum: ['MAINBOARD', 'SME'], default: 'MAINBOARD' },

  priceRange: {
    min: { type: Number },
    max: { type: Number },
  },
  lotSize: { type: Number },
  totalIssueSize: { type: Number },
  freshIssue: { type: Number },
  offerForSale: { type: Number },

  dates: {
    open: { type: Date },
    close: { type: Date },
    allotment: { type: Date },
    listing: { type: Date },
  },

  subscription: {
    total: { type: Number, default: 0 },
    qib: { type: Number, default: 0 },
    nii: { type: Number, default: 0 },
    retail: { type: Number, default: 0 },
    employee: { type: Number, default: 0 },
  },

  gmp: { type: Number, default: 0 },

  financials: {
    revenue: { type: Number },
    profit: { type: Number },
    eps: { type: Number },
    pe: { type: Number },
    roe: { type: Number },
    roce: { type: Number },
    debtToEquity: { type: Number },
  },

  qualitative: {
    sector: { type: String },
    businessDescription: { type: String },
    promoterHolding: { type: Number },
    anchorsAllotment: { type: Number },
    strengths: [String],
    risks: [String],
  },

  listingData: {
    listingPrice: { type: Number },
    listingGain: { type: Number },
    listingGainPercent: { type: Number },
    firstDayHigh: { type: Number },
    firstDayLow: { type: Number },
    firstDayClose: { type: Number },
  },

  aiAnalysis: {
    recommendation: { type: String, enum: ['APPLY', 'AVOID', 'WATCHLIST', 'PENDING'] },
    confidence: { type: Number, min: 0, max: 100 },
    fundamentalScore: { type: Number, min: 0, max: 10 },
    valuationScore: { type: Number, min: 0, max: 10 },
    industryScore: { type: Number, min: 0, max: 10 },
    riskScore: { type: Number, min: 0, max: 10 },
    summary: { type: String },
    lastAnalyzed: { type: Date },
  },

  status: {
    type: String,
    enum: ['UPCOMING', 'OPEN', 'CLOSED', 'ALLOTMENT', 'LISTED'],
    default: 'UPCOMING',
  },

  sources: [{ url: String, label: String }],
}, { timestamps: true });

ipoSchema.index({ 'dates.listing': -1 });
ipoSchema.index({ status: 1 });
ipoSchema.index({ symbol: 1 });

export default mongoose.model('IPO', ipoSchema);
