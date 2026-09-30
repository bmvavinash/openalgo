import mongoose from 'mongoose';
import bcrypt from 'bcryptjs';

const userSchema = new mongoose.Schema({
  name: { type: String, required: true, trim: true },
  email: { type: String, required: true, unique: true, lowercase: true, trim: true },
  password: { type: String, required: true, select: false },
  role: { type: String, enum: ['trader', 'admin'], default: 'trader' },
  apiKey: { type: String, select: false },
  openalgoConfig: {
    apiUrl: { type: String, default: 'http://localhost:5000' },
    apiKey: { type: String, select: false },
    broker: { type: String, default: '' },
  },
  preferences: {
    riskPerTrade: { type: Number, default: 1, min: 0.1, max: 10 },
    maxPositions: { type: Number, default: 10 },
    paperTrading: { type: Boolean, default: true },
    aiEnabled: { type: Boolean, default: true },
    notifications: {
      email: { type: Boolean, default: true },
      telegram: { type: Boolean, default: false },
      webhook: { type: Boolean, default: false },
    },
  },
  capitalAllocation: {
    total: { type: Number, default: 0 },
    equity: { type: Number, default: 60 },
    options: { type: Number, default: 30 },
    cash: { type: Number, default: 10 },
  },
  isActive: { type: Boolean, default: true },
  lastLogin: { type: Date },
}, { timestamps: true });

userSchema.pre('save', async function (next) {
  if (!this.isModified('password')) return next();
  this.password = await bcrypt.hash(this.password, 12);
  next();
});

userSchema.methods.comparePassword = async function (candidate) {
  return bcrypt.compare(candidate, this.password);
};

userSchema.methods.toPublic = function () {
  const obj = this.toObject();
  delete obj.password;
  delete obj.apiKey;
  delete obj.__v;
  return obj;
};

export default mongoose.model('User', userSchema);
