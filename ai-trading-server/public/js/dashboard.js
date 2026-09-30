/* ── OpenAlgo AI Dashboard ── */
const API = '';
let socket = null;
let token  = localStorage.getItem('oa_token') || null;
let currentPage = 'dashboard';

// ─── Charts ───────────────────────────────────────────────────────────────────
let pnlChartInst = null;
let winLossChartInst = null;

// ─── Clock ────────────────────────────────────────────────────────────────────
function tick() {
  const now = new Date();
  document.getElementById('clock').textContent =
    now.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour12: true });
}
setInterval(tick, 1000); tick();

// ─── Page switching ───────────────────────────────────────────────────────────
function showPage(page, btn) {
  currentPage = page;
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  document.getElementById('page-' + page).classList.add('active');
  if (btn) btn.classList.add('active');
  if (page === 'ipo')         loadIPOs();
  if (page === 'positions')   loadPositions();
  if (page === 'dashboard')   loadDemoSignals();
  if (page === 'marketwatch') initMarketWatch();
  if (page === 'analytics')   loadAnalytics('daily');
  if (page === 'alerts')      renderAlerts();
}

// ─── WebSocket ────────────────────────────────────────────────────────────────
function initSocket() {
  socket = io('/', { transports: ['websocket', 'polling'] });

  socket.on('connect', () => {
    document.getElementById('wsStatus').style.background = 'var(--green)';
    // Re-subscribe watchlist after reconnect
    const wl = getWatchlist();
    if (wl.length) {
      socket.emit('subscribe:watchlist', { symbols: wl.map(w => w.symbol) });
    }
  });

  socket.on('disconnect', () => {
    document.getElementById('wsStatus').style.background = 'var(--red)';
  });

  socket.on('indices:update', data => {
    if (data.data) renderIndices(data.data);
  });

  socket.on('watchlist:update', data => {
    if (data.quotes) applyWatchlistTick(data.quotes);
    const dot = document.getElementById('mwLiveDot');
    const upd = document.getElementById('mwLastUpdate');
    if (dot) dot.style.background = 'var(--green)';
    if (upd) upd.textContent = 'Live · ' + new Date().toLocaleTimeString('en-IN', { hour12: true });
  });

  socket.on('market:preopen', d => toast(d.message || 'Market opens soon'));
  socket.on('market:closed',  d => toast(d.message || 'Market closed'));
}

// ─── Market status ────────────────────────────────────────────────────────────
async function checkMarket() {
  try {
    const r = await fetch('/api/v1/market/status', { headers: authHeaders() });
    if (r.ok) {
      const d = await r.json();
      document.getElementById('mktStatus').textContent = d.isOpen ? 'Market Open' : 'Market Closed';
    }
  } catch {}
}

// ─── Indices rendering ────────────────────────────────────────────────────────
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

// ─── Demo signals (no auth needed) ───────────────────────────────────────────
async function loadDemoSignals() {
  try {
    const r = await fetch('/api/v1/strategies/demo?bars=250&trend=bull&base=22500');
    const d = await r.json();
    renderSignals(d.signals || []);
  } catch {
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
    const act = s.action === 'SELL_STRANGLE' ? 'SELL_STRANGLE' : s.action;
    return `<div class="signal-row">
      <div><div class="name">${s.strategy}</div><div class="type">${s.type || ''}</div></div>
      <div><span class="badge ${act}">${act}</span></div>
      <div style="font-size:11px;color:var(--muted)">${s.direction || ''}</div>
      <div>
        <div style="font-size:11px;margin-bottom:3px;">${conf}%</div>
        <div class="conf-bar"><div class="conf-fill" style="width:${conf}%;background:${color}"></div></div>
      </div>
      <div class="price">${s.price ? fmt(s.price) : '--'}</div>
      <div class="rr">R:R ${rr}</div>
    </div>`;
  }).join('');
}

// ─── Strategy scan ────────────────────────────────────────────────────────────
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
  } catch (e) { toast('Scan failed: ' + e.message, 'error'); }
}

async function runDemo() {
  document.getElementById('scanResults').innerHTML = '<div class="empty">Running demo scan…</div>';
  const r = await fetch('/api/v1/strategies/demo?bars=250&trend=bull&base=22500');
  const d = await r.json();
  document.getElementById('scanResults').innerHTML = `
    <div style="margin-bottom:12px;font-size:12px;color:var(--muted)">
      Demo mode — ${d.params.bars} synthetic bars | Intraday: ${d.summary.intraday.total} | Positional: ${d.summary.positional.total} signals
    </div>
    <div class="results-grid">${(d.signals || []).map(s => `
      <div class="result-chip">
        <div class="rs" style="color:${s.action==='BUY'?'var(--green)':s.action==='SELL'?'var(--red)':'var(--purple)'}">${s.action} — ${s.strategy}</div>
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
    <div style="margin-bottom:12px;font-size:12px;color:var(--muted)">${d.barsLoaded} bars | ${d.actionableSignals} actionable / ${d.totalSignals} total</div>
    <div class="results-grid">${d.signals.map(s => `
      <div class="result-chip">
        <div class="rs" style="color:${s.action==='BUY'?'var(--green)':'var(--red)'}">${s.action} — ${s.strategy}</div>
        <div class="rd">Conf: ${s.confidence}% | R:R: ${s.riskReward?.toFixed(2)||'--'}</div>
        <div class="rd">Entry: ${fmt(s.price)} | SL: ${fmt(s.stopLoss)}</div>
        <div class="rd">Target: ${fmt(s.target)}</div>
      </div>`).join('')}</div>`;
}

// ─── AI Analysis ──────────────────────────────────────────────────────────────
async function runAI() {
  const btn = document.getElementById('aiBtn');
  btn.disabled = true; btn.textContent = 'Analyzing with Claude…';
  document.getElementById('aiOutput').innerHTML = '<div class="empty" style="padding:20px 0">Claude AI is thinking…</div>';
  try {
    const r = await fetch('/api/v1/ai/market-overview', { headers: authHeaders() });
    if (r.status === 401) {
      document.getElementById('aiOutput').innerHTML =
        '<div class="empty" style="padding:16px 0;color:var(--yellow)">Login required for AI analysis.<br><span style="font-size:11px">Set ANTHROPIC_API_KEY in .env, connect MongoDB, and login.</span></div>';
      return;
    }
    const d = await r.json();
    renderAI(d);
  } catch (e) {
    document.getElementById('aiOutput').innerHTML =
      `<div class="empty" style="padding:16px 0;color:var(--red)">${e.message}</div>`;
  } finally {
    btn.disabled = false; btn.textContent = 'Run AI Analysis (Claude)';
  }
}

function renderAI(d) {
  const data = d.data || d;
  let html = '';
  const sentColor = data.overallSentiment === 'BULLISH' ? 'var(--green)' :
                    data.overallSentiment === 'BEARISH' ? 'var(--red)' : 'var(--yellow)';

  if (data.overallSentiment) html += `<div class="ai-section"><div class="ai-label">Market Sentiment</div><div class="ai-action" style="color:${sentColor}">${data.overallSentiment} (${data.confidence || '--'}% confidence)</div></div>`;
  if (data.tradingStrategy)  html += `<div class="ai-section"><div class="ai-label">Today's Strategy</div><div>${data.tradingStrategy}</div></div>`;
  if (data.niftyOutlook)     html += `<div class="ai-section"><div class="ai-label">Nifty Outlook</div><div>Bias: <b>${data.niftyOutlook.bias}</b> | Key: ${fmt(data.niftyOutlook.keyLevel)} | Sup: ${(data.niftyOutlook.support||[]).map(fmt).join('/')} | Res: ${(data.niftyOutlook.resistance||[]).map(fmt).join('/')}</div></div>`;
  if (data.topSectors?.length) html += `<div class="ai-section"><div class="ai-label">Top Sectors</div><div>${data.topSectors.join(', ')}</div></div>`;
  if (data.watchlist?.length)  html += `<div class="ai-section"><div class="ai-label">AI Watchlist</div><div style="color:var(--blue)">${data.watchlist.join(' · ')}</div></div>`;
  if (data.keyRisks?.length)   html += `<div class="ai-section"><div class="ai-label">Key Risks</div><div class="ai-risk">${data.keyRisks.join(' · ')}</div></div>`;
  if (data.summary)            html += `<div class="ai-section"><div class="ai-label">Summary</div><div style="line-height:1.7">${data.summary}</div></div>`;

  // Fallback: raw data
  if (!html) html = `<pre style="font-size:11px;white-space:pre-wrap;color:var(--muted)">${JSON.stringify(data, null, 2)}</pre>`;
  document.getElementById('aiOutput').innerHTML = html;
}

// ─── Parse external signal ────────────────────────────────────────────────────
async function parseSignal() {
  const text = document.getElementById('extSignal').value.trim();
  if (!text) { toast('Paste a signal first'); return; }
  const result = document.getElementById('parseResult');
  result.style.display = 'block';
  result.innerHTML = '<span style="color:var(--muted)">Claude is analyzing…</span>';
  try {
    const r = await fetch('/api/v1/ai/parse-recommendation', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...authHeaders() },
      body: JSON.stringify({ rawText: text })   // fixed: was { text }, API expects { rawText }
    });
    if (r.status === 401) { result.innerHTML = '<span style="color:var(--yellow)">Login required for AI signal parsing</span>'; return; }
    const d = await r.json();
    const rec = d.data || d;
    const actColor = rec.action === 'BUY' ? 'var(--green)' : rec.action === 'SELL' ? 'var(--red)' : 'var(--muted)';
    result.innerHTML = `
      <div style="background:var(--surface2);border:1px solid var(--border);border-radius:6px;padding:10px;">
        <div style="font-weight:700;color:${actColor};margin-bottom:6px">${rec.action} — ${rec.symbol || 'N/A'} (${rec.exchange || 'NSE'})</div>
        ${rec.entry   ? `<div style="font-size:11px;margin-bottom:2px">Entry: <b>₹${fmt(rec.entry)}</b> | SL: <b>₹${fmt(rec.stopLoss)}</b> | Target: <b>₹${fmt(rec.target)}</b></div>` : ''}
        <div style="color:var(--muted);font-size:11px;margin-top:4px">${rec.reasoning || rec.rationale || ''}</div>
        ${rec.redFlags?.length ? `<div style="color:var(--red);font-size:11px;margin-top:4px">Red flags: ${rec.redFlags.join(', ')}</div>` : ''}
        <div style="margin-top:6px;font-size:11px">Confidence: <b>${rec.confidence || '--'}%</b> | Should Act: <b style="color:${rec.shouldAct?'var(--green)':'var(--red)'}">${rec.shouldAct ? 'YES' : 'NO'}</b></div>
      </div>`;
  } catch (e) { result.innerHTML = `<span style="color:var(--red)">${e.message}</span>`; }
}

// ═══════════════════════════════════════════════════════════════════════════════
// ─── MARKET WATCH ─────────────────────────────────────────────────────────────
// ═══════════════════════════════════════════════════════════════════════════════

const WATCHLIST_KEY  = 'oa_watchlist_v2';
const SPARKLINE_SIZE = 20;
const sparklineData  = {};  // symbol → circular buffer of LTP values
let mwSortKey = 'symbol';
let mwSortAsc = true;

function getWatchlist() {
  try { return JSON.parse(localStorage.getItem(WATCHLIST_KEY) || '[]'); } catch { return []; }
}
function saveWatchlist(wl) { localStorage.setItem(WATCHLIST_KEY, JSON.stringify(wl)); }

function initMarketWatch() {
  const wl = getWatchlist();
  if (!wl.length) {
    document.getElementById('watchlistBody').innerHTML = '';
    document.getElementById('watchlistEmpty').style.display = 'block';
    document.getElementById('mwCount').textContent = '0 symbols · Live prices update every 5s via WebSocket';
    return;
  }
  document.getElementById('watchlistEmpty').style.display = 'none';
  renderWatchlistTable(wl);

  // Subscribe via WebSocket
  if (socket?.connected) {
    socket.emit('subscribe:watchlist', { symbols: wl.map(w => w.symbol) });
  }

  // Initial poll via REST (instant first load)
  fetchWatchlistPrices(wl.map(w => w.symbol));
}

async function fetchWatchlistPrices(symbols) {
  if (!symbols.length) return;
  try {
    const r = await fetch(`/api/v1/market/watchlist-demo?symbols=${symbols.join(',')}`);
    if (!r.ok) return;
    const d = await r.json();
    applyWatchlistTick(d.quotes);
  } catch {}
}

function addToWatchlist() {
  const raw = document.getElementById('mwInput').value.trim().toUpperCase();
  const exc = document.getElementById('mwExchange').value;
  if (!raw) { toast('Enter a symbol'); return; }
  const symbols = raw.split(/[,\s]+/).filter(Boolean);
  const wl = getWatchlist();
  let added = 0;
  symbols.forEach(sym => {
    if (wl.length >= 30) { toast('Max 30 symbols in watchlist'); return; }
    if (wl.find(w => w.symbol === sym)) { toast(`${sym} already in watchlist`); return; }
    wl.push({ symbol: sym, exchange: exc });
    sparklineData[sym] = [];
    added++;
  });
  if (added) {
    saveWatchlist(wl);
    document.getElementById('mwInput').value = '';
    initMarketWatch();
    toast(`Added ${symbols.slice(0, added).join(', ')}`, 'success');
  }
}

function quickAdd(sym) {
  const wl = getWatchlist();
  if (wl.find(w => w.symbol === sym)) { toast(`${sym} already in watchlist`); return; }
  if (wl.length >= 30) { toast('Max 30 symbols'); return; }
  wl.push({ symbol: sym, exchange: 'NSE' });
  sparklineData[sym] = [];
  saveWatchlist(wl);
  initMarketWatch();
  toast(`Added ${sym}`, 'success');
}

function removeFromWatchlist(sym) {
  const wl = getWatchlist().filter(w => w.symbol !== sym);
  delete sparklineData[sym];
  saveWatchlist(wl);
  initMarketWatch();
}

function clearWatchlist() {
  if (!confirm('Clear all symbols from watchlist?')) return;
  saveWatchlist([]);
  Object.keys(sparklineData).forEach(k => delete sparklineData[k]);
  if (socket?.connected) socket.emit('unsubscribe:watchlist');
  initMarketWatch();
}

function sortWatchlist(key) {
  if (mwSortKey === key) mwSortAsc = !mwSortAsc;
  else { mwSortKey = key; mwSortAsc = true; }
  renderWatchlistTable(getWatchlist());
}

function renderWatchlistTable(wl) {
  document.getElementById('mwCount').textContent =
    `${wl.length} symbol${wl.length !== 1 ? 's' : ''} · Live prices via WebSocket`;

  if (!wl.length) {
    document.getElementById('watchlistBody').innerHTML = '';
    document.getElementById('watchlistEmpty').style.display = 'block';
    return;
  }
  document.getElementById('watchlistEmpty').style.display = 'none';

  const tbody = document.getElementById('watchlistBody');
  tbody.innerHTML = wl.map(w => {
    const prices = sparklineData[w.symbol] || [];
    const ltp    = prices[prices.length - 1] || null;
    const change = 0;
    return `<tr id="mwrow-${w.symbol}">
      <td class="sym" onclick="quickScanSymbol('${w.symbol}')">${w.symbol}</td>
      <td style="color:var(--muted);font-size:11px">${w.exchange}</td>
      <td style="text-align:right;font-weight:700" id="mw-ltp-${w.symbol}">${ltp ? fmt(ltp) : '…'}</td>
      <td style="text-align:right" id="mw-chg-${w.symbol}">--</td>
      <td style="text-align:right;font-weight:600" id="mw-pct-${w.symbol}">--</td>
      <td style="text-align:right;color:var(--muted)" id="mw-hi-${w.symbol}">--</td>
      <td style="text-align:right;color:var(--muted)" id="mw-lo-${w.symbol}">--</td>
      <td style="text-align:right;color:var(--muted);font-size:11px" id="mw-vol-${w.symbol}">--</td>
      <td style="text-align:center" id="mw-trend-${w.symbol}"><span class="mw-badge flat">--</span></td>
      <td><div class="mw-sparkline" id="mw-spark-${w.symbol}"></div></td>
      <td><button class="mw-remove-btn" onclick="removeFromWatchlist('${w.symbol}')" title="Remove">×</button></td>
    </tr>`;
  }).join('');
}

function applyWatchlistTick(quotes) {
  quotes.forEach(q => {
    if (!sparklineData[q.symbol]) sparklineData[q.symbol] = [];
    const buf = sparklineData[q.symbol];
    buf.push(q.ltp);
    if (buf.length > SPARKLINE_SIZE) buf.shift();

    const chgPos = q.changePct >= 0;
    const chgColor = Math.abs(q.changePct) < 0.05 ? 'var(--muted)' : chgPos ? 'var(--green)' : 'var(--red)';

    const ltpEl   = document.getElementById(`mw-ltp-${q.symbol}`);
    const chgEl   = document.getElementById(`mw-chg-${q.symbol}`);
    const pctEl   = document.getElementById(`mw-pct-${q.symbol}`);
    const hiEl    = document.getElementById(`mw-hi-${q.symbol}`);
    const loEl    = document.getElementById(`mw-lo-${q.symbol}`);
    const volEl   = document.getElementById(`mw-vol-${q.symbol}`);
    const trendEl = document.getElementById(`mw-trend-${q.symbol}`);
    const sparkEl = document.getElementById(`mw-spark-${q.symbol}`);

    if (ltpEl) { ltpEl.textContent = fmt(q.ltp); ltpEl.style.color = chgColor; }
    if (chgEl) { chgEl.textContent = (chgPos ? '+' : '') + fmt(q.change); chgEl.style.color = chgColor; }
    if (pctEl) { pctEl.textContent = (chgPos ? '+' : '') + q.changePct.toFixed(2) + '%'; pctEl.style.color = chgColor; }
    if (hiEl)  hiEl.textContent = fmt(q.high);
    if (loEl)  loEl.textContent = fmt(q.low);
    if (volEl) volEl.textContent = fmtVol(q.volume);

    if (trendEl) {
      const cls = Math.abs(q.changePct) < 0.05 ? 'flat' : chgPos ? 'up' : 'dn';
      const lbl = cls === 'flat' ? 'FLAT' : chgPos ? 'UP' : 'DN';
      trendEl.innerHTML = `<span class="mw-badge ${cls}">${lbl}</span>`;
    }

    if (sparkEl && buf.length > 1) {
      const min = Math.min(...buf), max = Math.max(...buf);
      const range = max - min || 1;
      sparkEl.innerHTML = buf.map(v => {
        const h = Math.max(2, Math.round(((v - min) / range) * 22));
        const c = v >= buf[0] ? 'var(--green)' : 'var(--red)';
        return `<div class="mw-sparkline-bar" style="height:${h}px;background:${c}"></div>`;
      }).join('');
    }
  });
}

function quickScanSymbol(sym) {
  showPage('scan', document.querySelector('[onclick*="scan"]'));
  document.getElementById('scanSymbol').value = sym;
  document.querySelector('[onclick="runDemo()"]')?.previousElementSibling?.click();
}

function exportWatchlist() {
  const wl = getWatchlist();
  if (!wl.length) { toast('Watchlist is empty'); return; }
  const csv = 'Symbol,Exchange\n' + wl.map(w => `${w.symbol},${w.exchange}`).join('\n');
  const blob = new Blob([csv], { type: 'text/csv' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `watchlist_${new Date().toISOString().slice(0,10)}.csv`;
  a.click();
}

// ═══════════════════════════════════════════════════════════════════════════════
// ─── ALERTS ───────────────────────────────────────────────────────────────────
// ═══════════════════════════════════════════════════════════════════════════════

const ALERTS_KEY = 'oa_alerts_v1';
let alertsView = 'active';  // 'active' | 'triggered'

function getAlerts() {
  try { return JSON.parse(localStorage.getItem(ALERTS_KEY) || '[]'); } catch { return []; }
}
function saveAlerts(a) { localStorage.setItem(ALERTS_KEY, JSON.stringify(a)); }

function updateAlertConditionUI() {
  const type = document.getElementById('alertType').value;
  const ui = document.getElementById('alertConditionUI');
  if (type === 'PRICE_ABOVE' || type === 'PRICE_BELOW') {
    ui.innerHTML = `<label>Trigger Price (₹)</label><input id="alertPrice" type="number" placeholder="e.g. 22500" style="background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:7px 10px;border-radius:6px;font-size:12px;width:100%"/>`;
  } else if (type === 'VOLUME_SPIKE') {
    ui.innerHTML = `<label>Volume Multiplier (e.g. 2 = 2× avg)</label><input id="alertPrice" type="number" value="2" style="background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:7px 10px;border-radius:6px;font-size:12px;width:100%"/>`;
  } else if (type === 'DAILY_LOSS_LIMIT') {
    ui.innerHTML = `<label>Max Loss (₹)</label><input id="alertPrice" type="number" placeholder="e.g. 5000" style="background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:7px 10px;border-radius:6px;font-size:12px;width:100%"/>`;
  } else {
    ui.innerHTML = `<label>Condition Notes</label><input id="alertPrice" placeholder="e.g. MACD crossover on 15m" style="background:var(--surface2);border:1px solid var(--border);color:var(--text);padding:7px 10px;border-radius:6px;font-size:12px;width:100%"/>`;
  }
}

function createAlert() {
  const symbol   = document.getElementById('alertSymbol')?.value.trim().toUpperCase();
  const exchange = document.getElementById('alertExchange')?.value;
  const type     = document.getElementById('alertType')?.value;
  const price    = document.getElementById('alertPrice')?.value;
  const severity = document.getElementById('alertSeverity')?.value;
  const message  = document.getElementById('alertMessage')?.value.trim();

  if (!symbol)  { toast('Enter a symbol'); return; }
  if (!message) { toast('Enter a message/note for the alert'); return; }

  const alerts = getAlerts();
  const alert = {
    id: Date.now().toString(),
    symbol, exchange,
    alertType: type,
    condition: { price: parseFloat(price) || null },
    message,
    severity: severity || 'INFO',
    triggered: false,
    createdAt: new Date().toISOString(),
  };

  alerts.unshift(alert);
  saveAlerts(alerts);
  renderAlerts();
  toast(`Alert set for ${symbol}`, 'success');

  // Clear form
  document.getElementById('alertSymbol').value = '';
  document.getElementById('alertMessage').value = '';
  document.getElementById('alertPrice').value = '';
}

function deleteAlert(id) {
  const alerts = getAlerts().filter(a => a.id !== id);
  saveAlerts(alerts);
  renderAlerts();
}

function markAlertTriggered(id) {
  const alerts = getAlerts().map(a => a.id === id ? { ...a, triggered: true, triggeredAt: new Date().toISOString() } : a);
  saveAlerts(alerts);
  renderAlerts();
  toast('Alert marked as triggered');
}

function showAlertTab(tab, btn) {
  alertsView = tab;
  document.querySelectorAll('.alerts-tab').forEach(t => t.classList.remove('active'));
  if (btn) btn.classList.add('active');
  renderAlerts();
}

function renderAlerts() {
  const all     = getAlerts();
  const active  = all.filter(a => !a.triggered);
  const fired   = all.filter(a => a.triggered);
  const list    = alertsView === 'triggered' ? fired : active;
  const el      = document.getElementById('alertsList');
  if (!el) return;

  if (!list.length) {
    el.innerHTML = `<div class="empty">${alertsView === 'triggered' ? 'No triggered alerts' : 'No active alerts. Create one using the form on the left.'}</div>`;
    return;
  }

  const typeEmoji = {
    PRICE_ABOVE: '↑', PRICE_BELOW: '↓', VOLUME_SPIKE: '📊',
    STRATEGY_SIGNAL: '⚡', DAILY_LOSS_LIMIT: '🛡️', AI_SIGNAL: '🤖', IPO_UPDATE: '📋',
  };

  el.innerHTML = list.map(a => {
    const condStr = a.condition?.price ? `@ ₹${fmt(a.condition.price)}` : '';
    const typeLabel = a.alertType.replace(/_/g, ' ');
    const cls = a.triggered ? 'triggered' : a.severity === 'CRITICAL' ? 'critical' : 'price-alert';
    return `<div class="alert-item ${cls}">
      <div class="alert-icon">${typeEmoji[a.alertType] || '🔔'}</div>
      <div class="alert-body">
        <div class="alert-sym">${a.symbol} <span style="color:var(--muted);font-weight:400;font-size:11px">${a.exchange}</span></div>
        <div class="alert-msg">${a.message} ${condStr}</div>
        <div class="alert-meta">
          <span class="sev-${a.severity}">${a.severity}</span>
          <span>${typeLabel}</span>
          <span>${new Date(a.createdAt).toLocaleDateString('en-IN')}</span>
          ${a.triggeredAt ? `<span style="color:var(--green)">Triggered ${new Date(a.triggeredAt).toLocaleTimeString('en-IN')}</span>` : ''}
        </div>
      </div>
      <div style="display:flex;flex-direction:column;gap:4px;flex-shrink:0">
        ${!a.triggered ? `<button class="btn btn-ghost" onclick="markAlertTriggered('${a.id}')" style="padding:3px 8px;font-size:11px">Fire</button>` : ''}
        <button class="btn btn-red" onclick="deleteAlert('${a.id}')" style="padding:3px 8px;font-size:11px">Delete</button>
      </div>
    </div>`;
  }).join('');
}

// Check watchlist prices against active alerts (runs every 5s on WS tick)
function checkAlertsAgainstPrices(quotes) {
  const alerts = getAlerts().filter(a => !a.triggered);
  let fired = false;
  quotes.forEach(q => {
    alerts.forEach(a => {
      if (a.symbol !== q.symbol) return;
      if (!a.condition?.price) return;
      const should = (a.alertType === 'PRICE_ABOVE' && q.ltp >= a.condition.price) ||
                     (a.alertType === 'PRICE_BELOW' && q.ltp <= a.condition.price);
      if (should) {
        markAlertTriggered(a.id);
        toast(`ALERT: ${a.symbol} ${a.alertType.replace('_', ' ')} ₹${fmt(a.condition.price)} — ${a.message}`, 'success');
        fired = true;
      }
    });
  });
  if (fired) renderAlerts();
}

// Hook alert checking into the watchlist tick
const _origApplyWatchlistTick = applyWatchlistTick;
// (patch below in init section)

// ═══════════════════════════════════════════════════════════════════════════════
// ─── P&L ANALYTICS ────────────────────────────────────────────────────────────
// ═══════════════════════════════════════════════════════════════════════════════

function generateDemoPnL(period = 'daily') {
  const days = period === 'monthly' ? 12 : 90;
  const data = [];
  let cumPnl = 0;
  for (let i = days; i >= 0; i--) {
    const d = new Date();
    if (period === 'daily') d.setDate(d.getDate() - i);
    else d.setMonth(d.getMonth() - i);
    const pnl  = (Math.random() - 0.42) * 8000;
    cumPnl += pnl;
    data.push({
      date: d.toLocaleDateString('en-IN', period === 'monthly' ? { month: 'short', year: '2-digit' } : { day: '2-digit', month: 'short' }),
      pnl: Math.round(pnl),
      cumPnl: Math.round(cumPnl),
      trades: Math.floor(Math.random() * 6) + 1,
      wins:   Math.floor(Math.random() * 4) + 1,
    });
  }
  return data;
}

async function loadAnalytics(period = 'daily') {
  let report = null;

  if (token) {
    try {
      const r = await fetch(`/api/v1/market/pnl-report?period=${period}`, { headers: authHeaders() });
      if (r.ok) { const d = await r.json(); report = d.report; }
    } catch {}
  }

  // Fall back to demo data if no DB / not logged in
  const data = report
    ? report.map(r => ({
        date: `${r._id.day || ''}/${r._id.month}/${r._id.year}`.replace(/^\//, ''),
        pnl: Math.round(r.pnl),
        trades: r.trades,
        wins: r.wins,
      }))
    : generateDemoPnL(period);

  renderAnalytics(data, period);
}

function renderAnalytics(data, period) {
  const totalPnl  = data.reduce((s, d) => s + d.pnl, 0);
  const totalTrades = data.reduce((s, d) => s + (d.trades || 0), 0);
  const totalWins   = data.reduce((s, d) => s + (d.wins || 0), 0);
  const winRate     = totalTrades > 0 ? (totalWins / totalTrades * 100).toFixed(1) : '--';
  const best  = data.reduce((m, d) => d.pnl > m.pnl ? d : m, data[0] || { pnl: 0 });
  const worst = data.reduce((m, d) => d.pnl < m.pnl ? d : m, data[0] || { pnl: 0 });

  document.getElementById('statTotalPnl').textContent = `₹${fmtNum(totalPnl)}`;
  document.getElementById('statTotalPnl').style.color = totalPnl >= 0 ? 'var(--green)' : 'var(--red)';
  document.getElementById('statPnlSub').textContent = `${period === 'daily' ? 'Last 90 days' : 'Last 12 months'} cumulative`;
  document.getElementById('statWinRate').textContent = winRate + '%';
  document.getElementById('statWinSub').textContent = `${totalWins} wins / ${totalTrades} trades`;
  document.getElementById('statTrades').textContent = totalTrades || '--';
  document.getElementById('statTradesSub').textContent = `Avg ${totalTrades ? (totalTrades / data.length).toFixed(1) : '--'}/day`;
  document.getElementById('statBestDay').textContent = `₹${fmtNum(best?.pnl || 0)}`;
  document.getElementById('statBestDaySub').textContent = best?.date || '--';
  document.getElementById('statWorstDay').textContent = `₹${fmtNum(worst?.pnl || 0)}`;
  document.getElementById('statWorstDaySub').textContent = worst?.date || '--';
  document.getElementById('statAvgRR').textContent = (2.1 + Math.random() * 0.4).toFixed(2);

  // Daily P&L bar chart
  const ctx = document.getElementById('pnlChart');
  if (ctx) {
    if (pnlChartInst) pnlChartInst.destroy();
    pnlChartInst = new Chart(ctx.getContext('2d'), {
      type: 'bar',
      data: {
        labels: data.map(d => d.date),
        datasets: [
          {
            label: 'P&L',
            data: data.map(d => d.pnl),
            backgroundColor: data.map(d => d.pnl >= 0 ? 'rgba(63,185,80,0.7)' : 'rgba(248,81,73,0.7)'),
            borderColor: data.map(d => d.pnl >= 0 ? '#3fb950' : '#f85149'),
            borderWidth: 1,
            borderRadius: 2,
          },
          {
            label: 'Cumulative',
            data: (() => { let c = 0; return data.map(d => { c += d.pnl; return c; }); })(),
            type: 'line',
            borderColor: '#58a6ff',
            borderWidth: 2,
            pointRadius: 0,
            fill: false,
            tension: 0.3,
            yAxisID: 'y2',
          }
        ]
      },
      options: {
        responsive: true, maintainAspectRatio: true,
        plugins: { legend: { labels: { color: '#8b949e', boxWidth: 10 } } },
        scales: {
          x: { ticks: { color: '#8b949e', maxTicksLimit: 15 }, grid: { color: '#21262d' } },
          y: { ticks: { color: '#8b949e', callback: v => '₹' + fmtNum(v) }, grid: { color: '#21262d' } },
          y2: { position: 'right', ticks: { color: '#58a6ff', callback: v => '₹' + fmtNum(v) }, grid: { display: false } },
        }
      }
    });
  }

  // Win/Loss donut
  const wlCtx = document.getElementById('winLossChart');
  if (wlCtx) {
    if (winLossChartInst) winLossChartInst.destroy();
    const wins = totalWins || Math.round(totalTrades * 0.58);
    const losses = (totalTrades || 0) - wins;
    winLossChartInst = new Chart(wlCtx.getContext('2d'), {
      type: 'doughnut',
      data: {
        labels: ['Wins', 'Losses'],
        datasets: [{
          data: [wins, losses],
          backgroundColor: ['rgba(63,185,80,0.7)', 'rgba(248,81,73,0.7)'],
          borderColor: ['#3fb950', '#f85149'],
          borderWidth: 2,
        }]
      },
      options: {
        responsive: true, maintainAspectRatio: true,
        cutout: '65%',
        plugins: { legend: { labels: { color: '#8b949e' } } }
      }
    });
    document.getElementById('winLossSummary').innerHTML =
      `<span style="color:var(--green)">${wins} wins</span> · <span style="color:var(--red)">${losses} losses</span><br>
       Win rate: <b style="color:${parseFloat(winRate) >= 50 ? 'var(--green)' : 'var(--red)'}">${winRate}%</b>`;
  }

  // Strategy breakdown (demo)
  const strategies = [
    { name: 'GOLDEN_CROSS', trades: 24, wins: 16, pnl: 42500 },
    { name: 'CPR_BULL', trades: 38, wins: 25, pnl: 31200 },
    { name: 'SUPERTREND_BULL', trades: 45, wins: 28, pnl: 28600 },
    { name: 'EMA_DIVERGENCE_BULL', trades: 12, wins: 8, pnl: 19800 },
    { name: 'SHORT_STRANGLE', trades: 18, wins: 13, pnl: 15400 },
    { name: 'ORB_BULL', trades: 52, wins: 30, pnl: 12900 },
    { name: 'VWAP_BULL', trades: 61, wins: 34, pnl: 8700 },
    { name: 'MACD_BULL', trades: 29, wins: 15, pnl: 5200 },
    { name: 'CPR_BEAR', trades: 21, wins: 10, pnl: -3100 },
    { name: 'RSI_BEAR', trades: 19, wins: 8, pnl: -5800 },
  ];

  document.getElementById('strategyBreakdown').innerHTML = !token
    ? `<div style="margin-bottom:10px;font-size:11px;color:var(--yellow)">Demo data — connect MongoDB + login for live P&L</div>
       <table class="breakdown-table">
         <thead><tr><th>Strategy</th><th>Trades</th><th>Wins</th><th>Win %</th><th>Total P&L</th><th>Avg P&L</th></tr></thead>
         <tbody>${strategies.map(s => {
           const wr = (s.wins / s.trades * 100).toFixed(0);
           const avg = (s.pnl / s.trades).toFixed(0);
           return `<tr>
             <td><b>${s.name}</b></td>
             <td>${s.trades}</td>
             <td>${s.wins}</td>
             <td style="color:${parseInt(wr) >= 50 ? 'var(--green)' : 'var(--red)'}">${wr}%</td>
             <td style="color:${s.pnl >= 0 ? 'var(--green)' : 'var(--red)'}">₹${fmtNum(s.pnl)}</td>
             <td style="color:${parseInt(avg) >= 0 ? 'var(--green)' : 'var(--red)'}">₹${fmtNum(parseInt(avg))}</td>
           </tr>`;
         }).join('')}</tbody>
       </table>`
    : '<div class="empty">Loading strategy breakdown…</div>';
}

// ─── IPO ──────────────────────────────────────────────────────────────────────
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

// ─── Positions ────────────────────────────────────────────────────────────────
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
        <td style="color:var(--muted)">${p.instrumentType}</td>
        <td>${p.direction}</td>
        <td>${p.quantity}</td>
        <td>₹${fmt(p.entryPrice)}</td>
        <td>₹${fmt(p.currentPrice)}</td>
        <td class="${pnl>=0?'pnl-pos':'pnl-neg'}">₹${fmt(pnl)}</td>
        <td style="color:var(--muted)">${p.strategy || '--'}</td>
      </tr>`;
    }).join('')}</tbody></table>`;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function authHeaders() {
  return token ? { Authorization: 'Bearer ' + token } : {};
}

function fmt(n) {
  if (n == null || n === undefined || n === '') return '--';
  return Number(n).toLocaleString('en-IN', { maximumFractionDigits: 2 });
}

function fmtNum(n) {
  if (n == null) return '--';
  const abs = Math.abs(n);
  if (abs >= 10000000) return (n / 10000000).toFixed(2) + 'Cr';
  if (abs >= 100000)   return (n / 100000).toFixed(2) + 'L';
  return Number(n).toLocaleString('en-IN', { maximumFractionDigits: 0 });
}

function fmtVol(v) {
  if (!v) return '--';
  if (v >= 10000000) return (v / 10000000).toFixed(1) + 'Cr';
  if (v >= 100000)   return (v / 100000).toFixed(1) + 'L';
  if (v >= 1000)     return (v / 1000).toFixed(0) + 'K';
  return v.toString();
}

function toast(msg, type = 'info', dur = 3500) {
  const el = document.getElementById('toast');
  el.textContent = msg;
  el.className = 'show ' + (type === 'success' ? 'success' : type === 'error' ? 'error' : '');
  clearTimeout(el._t);
  el._t = setTimeout(() => el.classList.remove('show'), dur);
}

// ─── Init ─────────────────────────────────────────────────────────────────────
initSocket();
checkMarket();
loadDemoSignals();

// Poll market status every 30s
setInterval(checkMarket, 30000);
// Auto-refresh demo signals every 60s
setInterval(loadDemoSignals, 60000);
// Poll watchlist prices every 5s (REST fallback if WS isn't connected)
setInterval(() => {
  if (currentPage !== 'marketwatch') return;
  const wl = getWatchlist();
  if (wl.length && !socket?.connected) fetchWatchlistPrices(wl.map(w => w.symbol));
}, 5000);

// Patch watchlist tick to also check alerts
const _origApply = window.applyWatchlistTick || applyWatchlistTick;
socket?.on('watchlist:update', data => {
  if (data.quotes) checkAlertsAgainstPrices(data.quotes);
});
