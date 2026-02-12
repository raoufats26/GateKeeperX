/* ═══════════════════════════════════════════════════════
   SENTINELSHIELD  ·  main.js
   Wires every backend route:
     GET  /health
     GET  /api/test        ← attack simulator target
     GET  /api/metrics     ← live dashboard poll
     GET  /api/summary     ← summary tab
     GET  /api/status      ← status panel
     POST /api/reset       ← reset button
═══════════════════════════════════════════════════════ */
"use strict";

/* ─── Config ──────────────────────────────────── */
const POLL_MS     = 1000;
const GRAPH_SLOTS = 30;

/* ─── State ───────────────────────────────────── */
let prev       = { total: 0, allowed: 0, blocked: 0 };
let graphAllow = new Array(GRAPH_SLOTS).fill(0);
let graphBlock = new Array(GRAPH_SLOTS).fill(0);
let prevTotalForRps = 0;
let startTime  = Date.now();
let connected  = null;          // null = unknown, true, false
let pollTimer  = null;

// Simulator state
let simRunning   = false;
let simAbort     = false;
let simSent      = 0;
let simAllowed   = 0;
let simBlocked   = 0;
let simErrors    = 0;
let continuousId = null;

/* ─── $ shorthand ─────────────────────────────── */
const $  = id => document.getElementById(id);

/* ─── Element refs ────────────────────────────── */
const E = {
  // Header
  connDot:      $("connDot"),
  connLabel:    $("connLabel"),
  uptime:       $("uptime"),
  resetBtn:     $("resetBtn"),
  tbText:       $("tbText"),
  tbTime:       $("tbTime"),
  tbIcon:       $("tbIcon"),
  threatBanner: $("threatBanner"),

  // KPI
  totalReq:     $("totalRequests"),
  allowedReq:   $("allowedRequests"),
  blockedReq:   $("blockedRequests"),
  costSaved:    $("costSaved"),
  rps:          $("rpsValue"),
  passRate:     $("passRate"),
  blockRate:    $("blockRate"),
  kpiBarTotal:  $("kpiBarTotal"),
  kpiBarAllowed:$("kpiBarAllowed"),
  kpiBarBlocked:$("kpiBarBlocked"),
  kpiBarCost:   $("kpiBarCost"),

  // Threat
  ringArc:      $("ringArc"),
  ringLabel:    $("ringLabel"),
  attackBadge:  $("attackBadge"),
  tierLow:      $("tierLow"),
  tierMedium:   $("tierMedium"),
  tierHigh:     $("tierHigh"),

  // Efficiency
  effNum:       $("effNum"),
  effFill:      $("effFill"),
  effGlow:      $("effGlow"),

  // Feed
  activityFeed: $("activityFeed"),
  lastPoll:     $("lastPoll"),

  // Blocked IPs
  blockedList:  $("blockedList"),
  blockedCount: $("blockedCount"),

  // Top IPs
  topIpsList:   $("topIpsList"),

  // Graph
  canvas:       $("reqGraph"),

  // Footer
  footerTime:   $("footerTime"),
  toastStack:   $("toastStack"),

  // Simulator
  simEndpoint:    $("simEndpoint"),
  simBurst:       $("simBurst"),
  simDelay:       $("simDelay"),
  simConcurrency: $("simConcurrency"),
  simMode:        $("simMode"),
  simStartBtn:    $("simStartBtn"),
  simStopBtn:     $("simStopBtn"),
  simStatusBadge: $("simStatusBadge"),
  simLog:         $("simLog"),
  simSentEl:      $("simSent"),
  simAllowedEl:   $("simAllowed"),
  simBlockedEl:   $("simBlocked"),
  simErrorsEl:    $("simErrors"),
  clearLogBtn:    $("clearLogBtn"),

  // Summary
  sumName:        $("sumName"),
  sumVersion:     $("sumVersion"),
  sumTotal:       $("sumTotal"),
  sumBlocked:     $("sumBlocked"),
  sumEff:         $("sumEff"),
  sumCost:        $("sumCost"),
  refreshSummary: $("refreshSummaryBtn"),
  refreshHealth:  $("refreshHealthBtn"),
  refreshStatus:  $("refreshStatusBtn"),
  healthIcon:     $("healthIcon"),
  healthLabel:    $("healthLabel"),
  statusRows:     $("statusRows"),
};

/* ─── Canvas Setup ────────────────────────────── */
const ctx = E.canvas.getContext("2d");
let dpr   = window.devicePixelRatio || 1;

function sizeCanvas() {
  dpr = window.devicePixelRatio || 1;
  const w = E.canvas.parentElement.clientWidth;
  E.canvas.width  = w * dpr;
  E.canvas.height = 155 * dpr;
  E.canvas.style.width  = w + "px";
  E.canvas.style.height = "155px";
}
sizeCanvas();
window.addEventListener("resize", () => { sizeCanvas(); drawGraph(); });

/* ─── Tabs ────────────────────────────────────── */
document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll(".tab-content").forEach(c => c.classList.remove("active"));
    btn.classList.add("active");
    $("tab-" + btn.dataset.tab).classList.add("active");

    // Auto-fetch summary when switching to that tab
    if (btn.dataset.tab === "summary") fetchSummary();
  });
});

/* ─── Clock / Uptime ──────────────────────────── */
function tick() {
  const now = new Date();
  const ts  = now.toLocaleTimeString("en-GB", { hour12: false });
  E.footerTime.textContent = ts;
  E.tbTime.textContent     = ts;
  E.lastPoll.textContent   = ts;

  const secs  = Math.floor((Date.now() - startTime) / 1000);
  const h     = String(Math.floor(secs / 3600)).padStart(2, "0");
  const m     = String(Math.floor((secs % 3600) / 60)).padStart(2, "0");
  const s     = String(secs % 60).padStart(2, "0");
  E.uptime.textContent = `${h}:${m}:${s}`;
}
setInterval(tick, 1000);
tick();

/* ─── API fetch helper ────────────────────────── */
async function api(path, opts = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const err = new Error(`HTTP ${res.status}`);
    err.status = res.status;
    throw err;
  }
  return res.json();
}

/* ─── Connection state ────────────────────────── */
function setConn(ok) {
  if (connected === ok) return;
  connected = ok;
  if (ok) {
    E.connDot.className   = "status-dot live";
    E.connLabel.textContent = "LIVE";
    toast("Backend connected", "ok");
  } else {
    E.connDot.className   = "status-dot dead";
    E.connLabel.textContent = "OFFLINE";
    toast("Backend unreachable — retrying...", "err");
  }
}

/* ─── Number animation ────────────────────────── */
function setNum(el, val, formatter) {
  const text = formatter ? formatter(val) : val.toLocaleString();
  if (el.textContent === text) return;
  el.classList.remove("num-flash");
  void el.offsetWidth;
  el.classList.add("num-flash");
  el.textContent = text;
}

/* ─── Flash bar ───────────────────────────────── */
function flashBar(el) {
  el.className = el.className.replace(" flash", "") + " flash";
  setTimeout(() => (el.className = el.className.replace(" flash", "")), 160);
}

/* ═══════ METRICS POLL ════════════════════════ */
async function fetchMetrics() {
  try {
    const d = await api("/api/metrics");
    setConn(true);
    updateDashboard(d);
  } catch (_) {
    setConn(false);
  }
}

function updateDashboard(d) {
  const {
    total_requests               = 0,
    allowed_requests             = 0,
    blocked_requests             = 0,
    estimated_cost_saved         = 0,
    top_ips                      = [],
    active_blocked_ips           = {},
    threat_level                 = "LOW",
    attack_detected              = false,
    protection_efficiency_percent = 0,
  } = d;

  /* KPI counters */
  const prevTotal = prev.total;
  setNum(E.totalReq,   total_requests);
  setNum(E.allowedReq, allowed_requests);
  setNum(E.blockedReq, blocked_requests);
  setNum(E.costSaved,  estimated_cost_saved, v => "$" + v.toFixed(8));

  /* Flash bars on new traffic */
  if (total_requests   > prev.total)   { flashBar(E.kpiBarTotal);   }
  if (allowed_requests > prev.allowed) { flashBar(E.kpiBarAllowed); }
  if (blocked_requests > prev.blocked) { flashBar(E.kpiBarBlocked); }
  if (estimated_cost_saved > 0)        { flashBar(E.kpiBarCost);    }

  /* RPS */
  const delta = Math.max(0, total_requests - prevTotalForRps);
  setNum(E.rps, delta);
  prevTotalForRps = total_requests;

  /* Rates */
  const passR  = total_requests > 0 ? ((allowed_requests / total_requests) * 100).toFixed(1) : "100";
  const blockR = total_requests > 0 ? ((blocked_requests / total_requests) * 100).toFixed(1) : "0";
  E.passRate.textContent  = passR  + "%";
  E.blockRate.textContent = blockR + "%";

  /* Efficiency */
  const eff = protection_efficiency_percent;
  setNum(E.effNum, eff, v => v.toFixed(1));
  E.effFill.style.width = eff + "%";
  E.effGlow.style.width = eff + "%";

  /* Threat */
  updateThreat(threat_level, attack_detected, blocked_requests);

  /* Blocked IPs */
  renderBlockedIps(active_blocked_ips);

  /* Top IPs */
  renderTopIps(top_ips);

  /* Activity log */
  const newAllow = allowed_requests - prev.allowed;
  const newBlock = blocked_requests - prev.blocked;
  pushFeed(newAllow, newBlock, active_blocked_ips);

  /* Graph */
  graphAllow.push(Math.max(0, newAllow));
  graphBlock.push(Math.max(0, newBlock));
  if (graphAllow.length > GRAPH_SLOTS) graphAllow.shift();
  if (graphBlock.length > GRAPH_SLOTS) graphBlock.shift();
  drawGraph();

  /* Attack mode */
  document.body.classList.toggle("attacking", attack_detected);

  prev = { total: total_requests, allowed: allowed_requests, blocked: blocked_requests };
}

/* ─── Threat level ────────────────────────────── */
const CIRC = 389.56; // 2π × 62

function updateThreat(level, detected, blocked) {
  E.tierLow.classList.remove("active");
  E.tierMedium.classList.remove("active");
  E.tierHigh.classList.remove("active");

  if (level === "LOW") {
    E.ringArc.style.stroke          = "var(--green)";
    E.ringArc.style.strokeDashoffset = CIRC * 0.88;
    E.ringLabel.style.fill          = "var(--green)";
    E.ringLabel.textContent         = "LOW";
    E.threatBanner.className        = "threat-banner";
    E.tbText.textContent            = "SYSTEM SECURE — No active threats detected";
    E.attackBadge.className         = "badge";
    E.attackBadge.textContent       = "INACTIVE";
    E.tierLow.classList.add("active");

  } else if (level === "MEDIUM") {
    E.ringArc.style.stroke          = "var(--gold)";
    E.ringArc.style.strokeDashoffset = CIRC * 0.44;
    E.ringLabel.style.fill          = "var(--gold)";
    E.ringLabel.textContent         = "MED";
    E.threatBanner.className        = "threat-banner medium";
    E.tbText.textContent            = `⚠ MEDIUM THREAT — ${blocked} requests blocked`;
    E.attackBadge.className         = "badge warn";
    E.attackBadge.textContent       = "ACTIVE";
    E.tierMedium.classList.add("active");

  } else {
    E.ringArc.style.stroke          = "var(--red)";
    E.ringArc.style.strokeDashoffset = CIRC * 0.04;
    E.ringLabel.style.fill          = "var(--red)";
    E.ringLabel.textContent         = "HIGH";
    E.threatBanner.className        = "threat-banner high";
    E.tbText.textContent            = `🔴 HIGH THREAT — FLOOD DETECTED — ${blocked} blocked`;
    E.attackBadge.className         = "badge alert";
    E.attackBadge.textContent       = "FLOOD";
    E.tierHigh.classList.add("active");
  }
}

/* ─── Blocked IPs ─────────────────────────────── */
function renderBlockedIps(active) {
  const entries = Object.entries(active);
  E.blockedCount.textContent = entries.length;

  if (!entries.length) {
    E.blockedList.innerHTML = `<div class="list-empty">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
      </svg>No blocked IPs</div>`;
    return;
  }

  E.blockedList.innerHTML = entries
    .sort((a, b) => b[1] - a[1])
    .map(([ip, rem]) => `
      <div class="blocked-row">
        <span class="blocked-ip">${esc(ip)}</span>
        <span class="blocked-ttl">${rem.toFixed(1)}s</span>
      </div>`)
    .join("");
}

/* ─── Top IPs ─────────────────────────────────── */
function renderTopIps(ips) {
  if (!ips.length) {
    E.topIpsList.innerHTML = `<div class="list-empty">
      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1">
        <circle cx="12" cy="12" r="10"/>
        <line x1="2" y1="12" x2="22" y2="12"/>
        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
      </svg>No IP data yet</div>`;
    return;
  }
  const max = ips[0].requests || 1;
  E.topIpsList.innerHTML = ips.map((item, i) => {
    const bw = Math.round((item.requests / max) * 72);
    return `<div class="topip-row">
      <span class="iprank">${i + 1}</span>
      <span class="ipaddr">${esc(item.ip)}</span>
      <div class="ipbar" style="width:${bw}px"></div>
      <span class="ipcount">${item.requests}</span>
    </div>`;
  }).join("");
}

/* ─── Activity feed ───────────────────────────── */
const MAX_FEED = 40;

function pushFeed(newAllow, newBlock, active) {
  const ts = new Date().toLocaleTimeString("en-GB", { hour12: false });

  function add(cls, text) {
    E.activityFeed.querySelector(".feed-empty")?.remove();
    const div = document.createElement("div");
    div.className = `feed-entry ${cls}`;
    div.innerHTML = `<span class="feed-time">${ts}</span><span>${text}</span>`;
    E.activityFeed.insertBefore(div, E.activityFeed.firstChild);
    while (E.activityFeed.children.length > MAX_FEED)
      E.activityFeed.lastChild.remove();
  }

  if (newBlock > 0) {
    const ip = Object.keys(active)[0] || "";
    add("block", `BLOCKED ${newBlock} req${ip ? "  ·  " + ip : ""}`);
  }
  if (newAllow > 0) {
    add("allow", `ALLOWED ${newAllow} request${newAllow > 1 ? "s" : ""}`);
  }
}

/* ─── Canvas graph ────────────────────────────── */
function drawGraph() {
  const W = E.canvas.width  / dpr;
  const H = E.canvas.height / dpr;
  ctx.clearRect(0, 0, E.canvas.width, E.canvas.height);

  // Grid
  ctx.save();
  ctx.scale(dpr, dpr);
  ctx.strokeStyle = "rgba(255,255,255,.04)";
  ctx.lineWidth   = 1;
  for (let i = 0; i <= 4; i++) {
    const y = (H / 4) * i;
    ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke();
  }
  ctx.restore();

  const maxVal  = Math.max(...graphAllow, ...graphBlock, 1);
  const slotW   = W / GRAPH_SLOTS;

  function line(data, color, glow) {
    if (data.every(v => v === 0)) return;

    // glow pass
    ctx.save(); ctx.scale(dpr, dpr);
    ctx.beginPath();
    data.forEach((v, i) => {
      const x = i * slotW + slotW / 2;
      const y = H - (v / maxVal) * (H - 12) - 6;
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.strokeStyle = glow; ctx.lineWidth = 7;
    ctx.shadowColor = glow; ctx.shadowBlur = 14;
    ctx.stroke(); ctx.restore();

    // main line
    ctx.save(); ctx.scale(dpr, dpr);
    ctx.beginPath();
    data.forEach((v, i) => {
      const x = i * slotW + slotW / 2;
      const y = H - (v / maxVal) * (H - 12) - 6;
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    });
    ctx.strokeStyle = color; ctx.lineWidth = 1.8;
    ctx.shadowColor = color; ctx.shadowBlur = 4;
    ctx.stroke();

    // area fill
    const last = data.length - 1;
    ctx.lineTo(last * slotW + slotW / 2, H);
    ctx.lineTo(slotW / 2, H);
    ctx.closePath();
    ctx.fillStyle = color === "#00e676" ? "rgba(0,230,118,.06)" : "rgba(255,59,92,.05)";
    ctx.fill();
    ctx.restore();

    // endpoint dot
    const lv = data[last];
    if (lv > 0) {
      const lx = last * slotW + slotW / 2;
      const ly = H - (lv / maxVal) * (H - 12) - 6;
      ctx.save(); ctx.scale(dpr, dpr);
      ctx.beginPath(); ctx.arc(lx, ly, 3, 0, Math.PI * 2);
      ctx.fillStyle   = color;
      ctx.shadowColor = color; ctx.shadowBlur = 10;
      ctx.fill(); ctx.restore();
    }
  }

  line(graphAllow, "#00e676", "rgba(0,230,118,.28)");
  line(graphBlock, "#ff3b5c", "rgba(255,59,92,.28)");
}

/* ═══════ RESET ═══════════════════════════════ */
E.resetBtn.addEventListener("click", async () => {
  try {
    await api("/api/reset", { method: "POST" });
    prev = { total: 0, allowed: 0, blocked: 0 };
    prevTotalForRps = 0;
    graphAllow = new Array(GRAPH_SLOTS).fill(0);
    graphBlock = new Array(GRAPH_SLOTS).fill(0);
    startTime  = Date.now();

    E.activityFeed.innerHTML = '<div class="feed-empty">Awaiting traffic...</div>';
    drawGraph();
    toast("Metrics reset successfully", "ok");
    fetchMetrics();
  } catch (_) {
    toast("Reset failed — check backend", "err");
  }
});

/* ═══════ ATTACK SIMULATOR ════════════════════ */

function simLog(cls, text) {
  E.simLog.querySelector(".feed-empty")?.remove();
  const ts  = new Date().toLocaleTimeString("en-GB", { hour12: false });
  const div = document.createElement("div");
  div.className = `sim-log-entry ${cls}`;
  div.innerHTML = `<span class="sim-log-time">${ts}</span><span>${text}</span>`;
  E.simLog.insertBefore(div, E.simLog.firstChild);
  while (E.simLog.children.length > 200) E.simLog.lastChild.remove();
}

function updateSimStats() {
  E.simSentEl.textContent    = simSent;
  E.simAllowedEl.textContent = simAllowed;
  E.simBlockedEl.textContent = simBlocked;
  E.simErrorsEl.textContent  = simErrors;
}

async function singleRequest(endpoint) {
  simSent++;
  try {
    const res = await fetch(endpoint);
    if (res.status === 429) {
      simBlocked++;
      simLog("err", `429 BLOCKED  →  ${endpoint}`);
    } else {
      simAllowed++;
      simLog("ok", `${res.status} ALLOWED  →  ${endpoint}`);
    }
  } catch (e) {
    simErrors++;
    simLog("inf", `ERROR  →  ${e.message}`);
  }
  updateSimStats();
}

async function runBurst(endpoint, burst, delay, concurrency) {
  let i = 0;
  async function worker() {
    while (i < burst && !simAbort) {
      i++;
      await singleRequest(endpoint);
      if (delay > 0) await sleep(delay);
    }
  }
  const workers = Array.from({ length: Math.min(concurrency, burst) }, worker);
  await Promise.all(workers);
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

E.simStartBtn.addEventListener("click", async () => {
  if (simRunning) return;

  const endpoint    = E.simEndpoint.value;
  const burst       = Math.max(1, parseInt(E.simBurst.value)       || 50);
  const delay       = Math.max(0, parseInt(E.simDelay.value)       || 0);
  const concurrency = Math.max(1, parseInt(E.simConcurrency.value) || 5);
  const mode        = E.simMode.value;

  // Reset sim counters
  simSent = simAllowed = simBlocked = simErrors = 0;
  updateSimStats();
  simAbort   = false;
  simRunning = true;

  E.simStartBtn.disabled        = true;
  E.simStopBtn.disabled         = false;
  E.simStatusBadge.className    = "badge alert";
  E.simStatusBadge.textContent  = "RUNNING";

  simLog("inf", `▶ ATTACK STARTED — endpoint: ${endpoint}, burst: ${burst}, delay: ${delay}ms, workers: ${concurrency}, mode: ${mode}`);

  if (mode === "burst") {
    await runBurst(endpoint, burst, delay, concurrency);
    simLog("inf", `■ BURST COMPLETE — sent: ${simSent}, allowed: ${simAllowed}, blocked: ${simBlocked}`);
    stopSim();

  } else {
    // continuous
    async function continuousLoop() {
      if (simAbort) { stopSim(); return; }
      await runBurst(endpoint, burst, delay, concurrency);
      if (!simAbort) {
        simLog("inf", `↺ BURST DONE — sent: ${simSent}  allowed: ${simAllowed}  blocked: ${simBlocked} — restarting...`);
        continuousId = setTimeout(continuousLoop, 200);
      } else {
        stopSim();
      }
    }
    continuousLoop();
  }
});

E.simStopBtn.addEventListener("click", () => {
  simAbort = true;
  clearTimeout(continuousId);
});

E.clearLogBtn.addEventListener("click", () => {
  E.simLog.innerHTML = '<div class="feed-empty">Launch an attack to see results...</div>';
});

function stopSim() {
  simRunning = false;
  simAbort   = false;
  E.simStartBtn.disabled       = false;
  E.simStopBtn.disabled        = true;
  E.simStatusBadge.className   = "badge";
  E.simStatusBadge.textContent = "IDLE";
  toast(`Attack finished — sent: ${simSent}, blocked: ${simBlocked}`, simBlocked > 0 ? "warn" : "ok");
}

/* ═══════ SUMMARY TAB ═════════════════════════ */
async function fetchSummary() {
  try {
    const d = await api("/api/summary");
    E.sumName.textContent    = d.system_name    || "—";
    E.sumVersion.textContent = d.version        || "—";
    E.sumTotal.textContent   = (d.requests_processed || 0).toLocaleString();
    E.sumBlocked.textContent = (d.threats_blocked    || 0).toLocaleString();
    E.sumEff.textContent     = (d.protection_efficiency_percent || 0).toFixed(2) + "%";
    E.sumCost.textContent    = "$" + (d.estimated_cost_saved || 0).toFixed(8);
  } catch (_) {
    toast("Summary fetch failed", "err");
  }
}

E.refreshSummary.addEventListener("click", fetchSummary);

/* ─── Health check: GET /health ─────────────── */
async function fetchHealth() {
  try {
    const d = await api("/health");
    if (d.status === "healthy") {
      E.healthIcon.className  = "health-icon ok";
      E.healthLabel.textContent = "HEALTHY";
      E.healthLabel.className = "health-label";
      E.healthLabel.style.color = "var(--green)";
    } else {
      E.healthIcon.className  = "health-icon bad";
      E.healthLabel.textContent = d.status || "UNKNOWN";
      E.healthLabel.style.color = "var(--red)";
    }
  } catch (_) {
    E.healthIcon.className  = "health-icon bad";
    E.healthLabel.textContent = "UNREACHABLE";
    E.healthLabel.style.color = "var(--red)";
  }
}

E.refreshHealth.addEventListener("click", fetchHealth);

/* ─── Status: GET /api/status ───────────────── */
async function fetchStatus() {
  try {
    const d = await api("/api/status");
    E.statusRows.innerHTML = Object.entries(d).map(([k, v]) => `
      <div class="status-row">
        <span class="sr-key">${esc(String(k)).toUpperCase()}</span>
        <span class="sr-val cyan">${esc(String(v))}</span>
      </div>`).join("");
  } catch (_) {
    toast("Status fetch failed", "err");
    E.statusRows.innerHTML = `<div class="list-empty">Unreachable</div>`;
  }
}

E.refreshStatus.addEventListener("click", fetchStatus);

/* ═══════ TOAST ═══════════════════════════════ */
function toast(msg, type = "info", ms = 3200) {
  const el  = document.createElement("div");
  el.className = `toast ${type}`;
  el.textContent = msg;
  E.toastStack.appendChild(el);
  setTimeout(() => {
    el.style.transition  = "opacity .28s, transform .28s";
    el.style.opacity     = "0";
    el.style.transform   = "translateX(12px)";
    setTimeout(() => el.remove(), 300);
  }, ms);
}

/* ═══════ UTIL ════════════════════════════════ */
function esc(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/* ═══════ INIT ════════════════════════════════ */
(function init() {
  // Draw empty graph
  sizeCanvas();
  drawGraph();

  // Boot message in feed
  const ts = new Date().toLocaleTimeString("en-GB", { hour12: false });
  E.activityFeed.innerHTML = `
    <div class="feed-entry sys">
      <span class="feed-time">${ts}</span>
      <span>SENTINELSHIELD DASHBOARD ONLINE</span>
    </div>`;

  // Start polling /api/metrics every second
  fetchMetrics();
  pollTimer = setInterval(fetchMetrics, POLL_MS);

  // Pre-load health on summary tab
  fetchHealth();
})();
