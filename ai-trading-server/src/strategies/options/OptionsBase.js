/**
 * Options pricing and greeks helpers (Black-76 for Indian index options).
 * Indian index options pricing uses Black-76 off the synthetic future,
 * not Black-Scholes on spot.
 */

const SQRT_2PI = Math.sqrt(2 * Math.PI);

function normPDF(x) {
  return Math.exp(-0.5 * x * x) / SQRT_2PI;
}

function normCDF(x) {
  const a1 = 0.254829592, a2 = -0.284496736, a3 = 1.421413741;
  const a4 = -1.453152027, a5 = 1.061405429, p = 0.3275911;
  const sign = x < 0 ? -1 : 1;
  const t = 1 / (1 + p * Math.abs(x));
  const y = 1 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * Math.exp(-x * x);
  return 0.5 * (1 + sign * y);
}

/**
 * Black-76 model for options on futures (standard for NSE index options).
 * @param {string} type - 'CE' or 'PE'
 * @param {number} F  - Futures price (synthetic future)
 * @param {number} K  - Strike price
 * @param {number} T  - Time to expiry in years
 * @param {number} r  - Risk-free rate (decimal, e.g. 0.065)
 * @param {number} sigma - Implied volatility (decimal, e.g. 0.20)
 */
export function black76(type, F, K, T, r, sigma) {
  if (T <= 0) {
    const intrinsic = type === 'CE' ? Math.max(F - K, 0) : Math.max(K - F, 0);
    return { price: intrinsic, delta: 0, gamma: 0, theta: 0, vega: 0 };
  }

  const d1 = (Math.log(F / K) + 0.5 * sigma * sigma * T) / (sigma * Math.sqrt(T));
  const d2 = d1 - sigma * Math.sqrt(T);
  const discount = Math.exp(-r * T);

  let price, delta;
  if (type === 'CE') {
    price = discount * (F * normCDF(d1) - K * normCDF(d2));
    delta = discount * normCDF(d1);
  } else {
    price = discount * (K * normCDF(-d2) - F * normCDF(-d1));
    delta = -discount * normCDF(-d1);
  }

  const gamma = discount * normPDF(d1) / (F * sigma * Math.sqrt(T));
  const vega  = F * discount * normPDF(d1) * Math.sqrt(T) / 100;
  const theta = (-F * discount * normPDF(d1) * sigma / (2 * Math.sqrt(T))
    - r * K * discount * (type === 'CE' ? normCDF(d2) : normCDF(-d2))) / 365;

  return { price, delta, gamma, theta, vega, d1, d2 };
}

/**
 * Approximate IV from observed premium using Newton-Raphson.
 */
export function impliedVolatility(type, F, K, T, r, marketPrice, maxIter = 100, tol = 1e-6) {
  if (T <= 0) return 0;
  let sigma = 0.3;
  for (let i = 0; i < maxIter; i++) {
    const { price, vega } = black76(type, F, K, T, r, sigma);
    const diff = price - marketPrice;
    if (Math.abs(diff) < tol) break;
    if (Math.abs(vega) < 1e-10) break;
    sigma -= diff / (vega * 100);
    sigma = Math.max(0.001, Math.min(sigma, 5));
  }
  return sigma;
}

/**
 * Days-to-expiry helper.
 */
export function dte(expiryDate) {
  const now = new Date();
  const expiry = new Date(expiryDate);
  return Math.max(0, (expiry - now) / (1000 * 60 * 60 * 24));
}

export function dteYears(expiryDate) {
  return dte(expiryDate) / 365;
}

/**
 * Max loss, max profit, breakeven for common spreads.
 */
export function spreadPayoff(legs) {
  // legs: [{ type, strike, premium, action, qty }]
  // Returns max profit, max loss, breakevens (approximate)
  const netCredit = legs.reduce((acc, l) => {
    const sign = l.action === 'SELL' ? 1 : -1;
    return acc + sign * l.premium * l.qty;
  }, 0);
  return { netCredit, maxProfit: netCredit > 0 ? netCredit : null };
}
