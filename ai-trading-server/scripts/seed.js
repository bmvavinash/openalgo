/**
 * Seed script — creates a demo admin user and sample IPOs.
 * Run: node scripts/seed.js
 */

import mongoose from 'mongoose';
import dotenv from 'dotenv';
dotenv.config();

import User from '../src/database/models/User.js';
import IPO from '../src/database/models/IPO.js';

async function seed() {
  await mongoose.connect(process.env.MONGODB_URI || 'mongodb://localhost:27017/openalgo_trading');
  console.log('Connected to MongoDB');

  // ── Admin user ─────────────────────────────────────────────────────────────
  const existing = await User.findOne({ email: 'admin@openalgo.in' });
  if (!existing) {
    await User.create({
      name: 'Admin',
      email: 'admin@openalgo.in',
      password: 'OpenAlgo@2026',
      role: 'admin',
      preferences: {
        riskPerTrade: 1,
        maxPositions: 10,
        paperTrading: true,
        aiEnabled: true,
      },
      capitalAllocation: { total: 1000000, equity: 60, options: 30, cash: 10 },
    });
    console.log('Created admin user: admin@openalgo.in / OpenAlgo@2026');
  } else {
    console.log('Admin user already exists');
  }

  // ── Sample IPOs ────────────────────────────────────────────────────────────
  const sampleIPOs = [
    {
      companyName: 'TechVenture India Ltd',
      symbol: 'TECHVENT',
      exchange: 'NSE',
      ipoType: 'MAINBOARD',
      priceRange: { min: 400, max: 420 },
      lotSize: 35,
      totalIssueSize: 2000,
      freshIssue: 1500,
      offerForSale: 500,
      dates: {
        open: new Date('2026-10-01'),
        close: new Date('2026-10-03'),
        allotment: new Date('2026-10-06'),
        listing: new Date('2026-10-09'),
      },
      subscription: { total: 45, qib: 28, nii: 12, retail: 5 },
      gmp: 63,
      financials: { revenue: 8500, profit: 1200, eps: 24, pe: 17.5, roe: 22, roce: 25, debtToEquity: 0.4 },
      qualitative: {
        sector: 'Technology',
        promoterHolding: 62,
        strengths: ['Asset-light SaaS model', 'Recurring revenue 70%', 'Pan-India presence'],
        risks: ['Competition from global players', 'Customer concentration risk'],
      },
      status: 'UPCOMING',
    },
    {
      companyName: 'GreenPower Renewables',
      symbol: 'GREENPOWER',
      exchange: 'BOTH',
      ipoType: 'MAINBOARD',
      priceRange: { min: 150, max: 160 },
      lotSize: 93,
      dates: {
        open: new Date('2026-10-10'),
        close: new Date('2026-10-13'),
        allotment: new Date('2026-10-16'),
        listing: new Date('2026-10-19'),
      },
      subscription: { total: 0, qib: 0, nii: 0, retail: 0 },
      gmp: 20,
      financials: { revenue: 3200, profit: -200, eps: -3, pe: null, roe: -5, debtToEquity: 2.8 },
      qualitative: {
        sector: 'Renewable Energy',
        promoterHolding: 55,
        strengths: ['Government policy tailwind', 'Large order book'],
        risks: ['Currently loss-making', 'High debt', 'Capital intensive'],
      },
      status: 'UPCOMING',
    },
  ];

  for (const data of sampleIPOs) {
    const exists = await IPO.findOne({ companyName: data.companyName });
    if (!exists) {
      await IPO.create(data);
      console.log(`Created IPO: ${data.companyName}`);
    }
  }

  console.log('\nSeed complete.');
  await mongoose.disconnect();
}

seed().catch(err => {
  console.error('Seed failed:', err.message);
  process.exit(1);
});
