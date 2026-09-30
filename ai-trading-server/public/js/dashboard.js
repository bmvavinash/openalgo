/* ── OpenAlgo AI Dashboard ── */
const API = '';   // same origin
let socket = null;
let token  = localStorage.getItem('oa_token') || null;
let currentPage = 'dashboard';

/* ── Clock ── */
function tick() {
  const now = new Date();
  document.getElementById('clock').textContent = now.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour12: true });
}
setInterval(tick, 1000); tick();

/* ── Page switching ── */
function showPage(page) {
  currentPage = page;
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  document.getElementById('page-' + page).classList.add('active');
  event.target.classList.add('active');
  if (page === 'ipo')       loadIPOs();
  if (page === 'positions') loadPositions();
  if (page === 'dashboard') loadDemoSignals();
}

/* ── WebSocket ── */
function initSocket() {
  socket = io('/', { transports: ['websocket', 'polling'] });
  socket.on('connect', () => {
    document.getElementById('wsStatus').style.background = 'var(--green)';
  });
  socket.on('disconnect', () => {
    document.getElementById('wsStatus').style.background = 'var(--red)';
  });
  socket.on('indices:update', data => {
    if (data.data) renderIndices(data.data);
  });
}

/* ── Market status ── */
async function checkMarket() {
  try {
    const r = await fetch('/api/v1/market/status', { headers: authHeaders() });
    if (r.ok) {
      const d = await r.json();
      document.getElementById('mktStatus').textContent = d.isOpen ? 'Market Open' : 'Market Closed';
      document.getElementById('wsStatus').style.background = d.isOpen ? 'var(--green)' : 'var(--yellow)';
    }
  } catch {}
}

/* ── Indices rendering ── */
function renderIndices(indices) {
  const map = { 'NIFTY 50': 'nifty50', 'BANKNIFTY': 'banknifty', 'FINNIFTY': 'finnifty', 'MIDCAP 50': 'midcap', 'SENSEX': 'sensex' };
  indices.forEach(idx => {
    const key = map[idx.name];
    if (!key) return;
    const el = document.getElementById(key);
    const cel = document.getElementById(key + 'c');
    if (el) el.textContent = fmt(idx.ltp);
    if (cel) {
      const chg = idx.change || 0, pct = idx.changePct || 0;
      cel.textContent = `${chg >= 0 ? '+' : ''}${fmt(chg)} (${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%)`;
      cel.style.color = chg >= 0 ? 'var(--green)' : 'var(--red)';
    }
  });
}

/* ── Demo signals (no auth needed) ── */
async function loadDemoSignals() {
  try {
    const r = await fetch('/api/v1/strategies/demo?bars=250&trend=bull&base=22500');
    const d = await r.json();
    renderSignals(d.signals || []);
  } catch (e) {
    document.getElementById('signalsList').innerHTML = '<div class="empty">Could not load signals</div>';
  }
}

function renderSignals(signals) {
  const el = document.getElementById('signalsList');
  if (!signals.length) { el.innerHTML = '<div class="empty">No actionable signals right now</div>'; return; }
  el.innerHTML = signals.map(s => {
    const conf = s.confidence || 0;
    const color = conf >= 75 ? 'var(--green)' : conf >= 50 ? 'var(--yellow)' : 'var(--red)';
    const rr = s.riskReward ? s.riskReward.toFixed(2) : '--';
    return `<div class="signal-row">
      <div><div class="name">${s.strategy}</div><div class="type">${s.type || ''}</div></div>
      <div><span class="badge ${s.action}">${s.action}</span></div>
      <div>${s.direction || ''}</div>
      <div>
        <div style="font-size:11px;margin-bottom:3px;">${conf}%</div>
        <div class="conf-bar"><div class="conf-fill" style="width:${conf}%;background:${color}"></div></div>
      </div>
      <div class="price">${s.price ? fmt(s.price) : '--'}</div>
      <div class="rr">R:R ${rr}</div>
    </div>`;
  }).join('');
}

/* ── Strategy scan ── */
async function runScan() {
  const sym = document.getElementById('scanSymbol').value.trim().toUpperCase() || 'NIFTY';
  const exc = document.getElementById('scanExchange').value;
  const int = document.getElementById('scanInterval').value;
  const typ = document.getElementById('scanType').value;

  document.getElementById('scanResults').innerHTML = '<div class="empty">Scanning…</div>';

  try {
    const r = await fetch('/api/v1/strategies/scan', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ symbol: sym, exchange: exc, interval: int, type: typ || null })
    });
    if (r.status === 401) { toast('Login required for live scan. Use Demo instead.'); return; }
    const d = await r.json();
    renderScanResults(d);
  } catch (e) { toast('Scan failed: ' + e.message); }
}

async function runDemo() {
  const sym = document.getElementById('scanSymbol').value.trim().toUpperCase() || 'NIFTY';
  document.getElementById('scanResults').innerHTML = '<div class="empty">Running demo scan…</div>';
  const r = await fetch(`/api/v1/strategies/demo?bars=250&trend=bull&base=22500`);
  const d = await r.json();
  document.getElementById('scanResults').innerHTML = `
    <div style="margin-bottom:12px;font-size:12px;color:var(--muted)">
      Demo mode — ${d.params.bars} synthetic bars | Intraday: ${d.summary.intraday.total} signals | Positional: ${d.summary.positional.total} signals
    </div>
    <div class="results-grid">${(d.signals || []).map(s => `
      <div class="result-chip">
        <div class="rs" style="color:${s.action==='BUY'?'var(--green)':s.action==='SELL'?'var(--red)':'var(--muted)'}">${s.action} — ${s.strategy}</div>
        <div class="rd">${s.type} | Conf: ${s.confidence}%</div>
        <div class="rd">Price: ${fmt(s.price)} | SL: ${fmt(s.stopLoss)}</div>
        <div class="rd">R:R: ${s.riskReward?.toFixed(2) || '--'}</div>
      </div>`).join('') || '<div class="empty">No signals triggered</div>'}</div>`;
}

function renderScanResults(d) {
  if (!d.signals || !d.signals.length) {
    document.getElementById('scanResults').innerHTML = '<div class="empty">No actionable signals for this scan</div>';
    return;
  }
  document.getElementById('scanResults').innerHTML = `
    <div style="margin-bottom:12px;font-size:12px;color:var(--muted)">${d.barsLoaded} bars loaded | ${d.actionableSignals} actionable / ${d.totalSignals} total</div>
    <div class="results-grid">${d.signals.map(s => `
      <div class="result-chip">
        <div class="rs" style="color:${s.action==='BUY'?'var(--green)':'var(--red)'}">${s.action} — ${s.strategy}</div>
        <div class="rd">Conf: ${s.confidence}% | R:R: ${s.riskReward?.toFixed(2)||'--'}</div>
        <div class="rd">Entry: ${fmt(s.price)} | SL: ${fmt(s.stopLoss)}</div>
        <div class="rd">Target: ${fmt(s.target)}</div>
      </div>`).join('')}</div>`;
}

/* ── AI Analysis ── */
async function runAI() {
  const btn = document.getElementById('aiBtn');
  btn.disabled = true; btn.textContent = 'Analyzing…';
  document.getElementById('aiOutput').innerHTML = '<div class="empty" style="padding:20px 0">AI thinking…</div>';
  try {
    const r = await fetch('/api/v1/ai/market-overview', { headers: authHeaders() });
    if (r.status === 401) {
      document.getElementById('aiOutput').innerHTML = '<div class="empty" style="padding:20px 0;color:var(--yellow)">Login required for AI analysis.<br>Add ANTHROPIC_API_KEY to .env</div>';
      return;
    }
    const d = await r.json();
    renderAI(d);
  } catch (e) {
    document.getElementById('aiOutput').innerHTML = '<div class="empty" style="padding:20px 0;color:var(--red)">' + e.message + '</div>';
  } finally {
    btn.disabled = false; btn.textContent = 'Run AI Analysis';
  }
}

function renderAI(d) {
  const data = d.data || d;
  let html = '';
  if (data.trend)       html += `<div class="ai-section"><div class="ai-label">Market Trend</div><div>${data.trend}</div></div>`;
  if (data.sentiment)   html += `<div class="ai-section"><div class="ai-label">Sentiment</div><div>${data.sentiment}</div></div>`;
  if (data.action)      html += `<div class="ai-section"><div class="ai-label">Recommended Action</div><div class="ai-action">${data.action}</div></div>`;
  if (data.reasoning)   html += `<div class="ai-section"><div class="ai-label">Reasoning</div><div>${data.reasoning}</div></div>`;
  if (data.keyLevels)   html += `<div class="ai-section"><div class="ai-label">Key Levels</div><div>${JSON.stringify(data.keyLevels)}</div></div>`;
  if (data.risks)       html += `<div class="ai-section"><div class="ai-label">Risks</div><div>${Array.isArray(data.risks) ? data.risks.join(', ') : data.risks}</div></div>`;
  if (!html) html = `<pre style="font-size:11px;white-space:pre-wrap">${JSON.stringify(data, null, 2)}</pre>`;
  document.getElementById('aiOutput').innerHTML = html;
}

/* ── Parse external signal ── */
async function parseSignal() {
  const text = document.getElementById('extSignal').value.trim();
  if (!text) { toast('Paste a signal first'); return; }
  const result = document.getElementById('parseResult');
  result.style.display = 'block';
  result.innerHTML = '<span style="color:var(--muted)">Analyzing…</span>';
  try {
    const r = await fetch('/api/v1/ai/parse-recommendation', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ text })
    });
    if (r.status === 401) { result.innerHTML = '<span style="color:var(--yellow)">Login required</span>'; return; }
    const d = await r.json();
    const rec = d.data || d;
    result.innerHTML = `
      <div style="background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:10px;">
        <div style="font-weight:700;color:${rec.action==='BUY'?'var(--green)':rec.action==='SELL'?'var(--red)':'var(--muted)'};margin-bottom:6px">${rec.action} — ${rec.symbol || 'N/A'}</div>
        <div style="color:var(--muted);font-size:11px">${rec.reasoning || rec.rationale || ''}</div>
        <div style="margin-top:6px;font-size:11px">Confidence: <b>${rec.confidence || '--'}%</b></div>
      </div>`;
  } catch (e) { result.innerHTML = `<span style="color:var(--red)">${e.message}</span>`; }
}

/* ── IPO ── */
async function loadIPOs() {
  try {
    const r = await fetch('/api/v1/ipo/upcoming', { headers: authHeaders() });
    if (!r.ok) { document.getElementById('ipoGrid').innerHTML = '<div class="empty">Connect MongoDB to see IPO data</div>'; return; }
    const d = await r.json();
    renderIPOs(d.ipos || d);
  } catch { document.getElementById('ipoGrid').innerHTML = '<div class="empty">Connect MongoDB to see IPO data</div>'; }
}

function renderIPOs(ipos) {
  const el = document.getElementById('ipoGrid');
  if (!ipos.length) { el.innerHTML = '<div class="empty">No IPOs found</div>'; return; }
  el.innerHTML = ipos.map(ipo => {
    const score = ipo.aiAnalysis?.compositeScore || 0;
    const rec   = ipo.aiAnalysis?.recommendation || 'WATCHLIST';
    const gmp   = ipo.gmp || 0;
    const pct   = ipo.priceRange?.max ? ((gmp / ipo.priceRange.max) * 100).toFixed(1) : '--';
    const scoreColor = score >= 6.5 ? 'var(--green)' : score >= 4 ? 'var(--yellow)' : 'var(--red)';
    return `<div class="ipo-card">
      <div class="company">${ipo.companyName}</div>
      <div style="font-size:11px;color:var(--muted);margin-bottom:8px">${ipo.exchange} | ${ipo.ipoType} | ${ipo.status}</div>
      <div class="ipo-meta">
        <span>Price Range</span><span class="val">₹${ipo.priceRange?.min || '--'} – ₹${ipo.priceRange?.max || '--'}</span>
        <span>Lot Size</span><span class="val">${ipo.lotSize || '--'} shares</span>
        <span>GMP</span><span class="val" style="color:${gmp>=0?'var(--green)':'var(--red)'}">₹${gmp} (${pct}%)</span>
        <span>Subscription</span><span class="val">${ipo.subscription?.total || 0}×</span>
        <span>P/E</span><span class="val">${ipo.financials?.pe || '--'}</span>
        <span>Open</span><span class="val">${ipo.dates?.open ? new Date(ipo.dates.open).toLocaleDateString('en-IN') : '--'}</span>
      </div>
      <div class="ipo-score-bar">
        <div class="ipo-score-label">
          <span>AI Score: <b style="color:${scoreColor}">${score.toFixed(1)}/10</b></span>
          <span class="rec-${rec}">${rec}</span>
        </div>
        <div class="ipo-score-track"><div class="ipo-score-fill" style="width:${score*10}%;background:${scoreColor}"></div></div>
      </div>
    </div>`;
  }).join('');
}

/* ── Positions ── */
async function loadPositions() {
  try {
    const r = await fetch('/api/v1/positions', { headers: authHeaders() });
    if (!r.ok) { document.getElementById('positionsTable').innerHTML = '<div class="empty">Login required to view positions</div>'; return; }
    const d = await r.json();
    renderPositions(d.positions || d);
  } catch { document.getElementById('positionsTable').innerHTML = '<div class="empty">Connect MongoDB and login to track positions</div>'; }
}

function renderPositions(positions) {
  const el = document.getElementById('positionsTable');
  if (!positions.length) { el.innerHTML = '<div class="empty">No open positions</div>'; return; }
  el.innerHTML = `<table class="pos-table">
    <thead><tr><th>Symbol</th><th>Type</th><th>Dir</th><th>Qty</th><th>Entry</th><th>LTP</th><th>P&L</th><th>Strategy</th></tr></thead>
    <tbody>${positions.map(p => {
      const pnl = p.unrealizedPnl || 0;
      return `<tr>
        <td><b>${p.symbol}</b></td>
        <td>${p.instrumentType}</td>
        <td>${p.direction}</td>
        <td>${p.quantity}</td>
        <td>₹${fmt(p.entryPrice)}</td>
        <td>₹${fmt(p.currentPrice)}</td>
        <td class="${pnl>=0?'pnl-pos':'pnl-neg'}">₹${fmt(pnl)}</td>
        <td style="color:var(--muted)">${p.strategy || '--'}</td>
      </tr>`;
    }).join('')}</tbody></table>`;
}

/* ── Helpers ── */
function authHeaders() {
  return token ? { Authorization: 'Bearer ' + token } : {};
}

function fmt(n) {
  if (n == null || n === undefined) return '--';
  return Number(n).toLocaleString('en-IN', { maximumFractionDigits: 2 });
}

function toast(msg, dur = 3000) {
  const el = document.getElementById('toast');
  el.textContent = msg; el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), dur);
}

/* ── Init ── */
initSocket();
checkMarket();
loadDemoSignals();
setInterval(checkMarket, 30000);
setInterval(loadDemoSignals, 60000);
