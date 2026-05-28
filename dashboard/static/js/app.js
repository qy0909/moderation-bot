// ── Login Guard ─────────────────────────────────
//    If the admin hasn't signed in, every dashboard page
//    (index.html, monitor.html, interventions.html) redirects to /login
(function guardDashboard() {
  // Skip guard on the login page itself
  if (
    location.pathname.endsWith("/login") ||
    location.pathname.endsWith("/login.html")
  )
    return;
  try {
    const raw = sessionStorage.getItem("modbot_auth");
    if (!raw) {
      window.location.href = "/login";
      return;
    }
    const { username } = JSON.parse(raw);
    if (username !== "admin") {
      window.location.href = "/login";
    }
  } catch {
    window.location.href = "/login";
  }
})();

// ── Logout function (clears session and redirects to login) ─────────────
function modbotLogout() {
  sessionStorage.removeItem("modbot_auth");
  window.location.href = "/login";
}

// ── Server ID (used in API calls) ─────────────────────────────────
const session = JSON.parse(sessionStorage.getItem("modbot_auth") || "{}");
const serverId = session.serverId || "—";

// ── Inline outline SVG icons ─────────────────────────────────
const ICON = {
  shield: `<svg viewBox="0 0 24 24"><path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6l8-3z"/></svg>`,
  alert: `<svg viewBox="0 0 24 24"><path d="M12 9v4M12 17h.01M10.3 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.7 3.86a2 2 0 00-3.4 0z"/></svg>`,
  skull: `<svg viewBox="0 0 24 24"><path d="M12 2a8 8 0 00-8 8v5l2 2v3h3v-2h6v2h3v-3l2-2v-5a8 8 0 00-8-8zM9 12h.01M15 12h.01"/></svg>`,
  smile: `<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M8 14s1.5 2 4 2 4-2 4-2M9 9h.01M15 9h.01"/></svg>`,
  meh: `<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M8 14h8M9 9h.01M15 9h.01"/></svg>`,
  frown: `<svg viewBox="0 0 24 24"><circle cx="12" cy="12" r="9"/><path d="M8 16s1.5-2 4-2 4 2 4 2M9 9h.01M15 9h.01"/></svg>`,
  pulse: `<svg viewBox="0 0 24 24"><path d="M3 12h4l3-9 4 18 3-9h4"/></svg>`,
  chat: `<svg viewBox="0 0 24 24"><path d="M21 11.5a8.38 8.38 0 01-.9 3.8 8.5 8.5 0 01-7.6 4.7 8.38 8.38 0 01-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 01-.9-3.8 8.5 8.5 0 014.7-7.6 8.38 8.38 0 013.8-.9h.5a8.48 8.48 0 018 8v.5z"/></svg>`,
};

// ── Score class helpers (consistent rules across app) ────────
function scoreClass(score) {
  if (score === null || score === undefined || isNaN(score)) return "";
  if (score >= 0.85) return "score-high";
  if (score >= 0.6) return "score-med";
  return "score-low";
}
function sentClass(score) {
  if (score === null || score === undefined || isNaN(score)) return "";
  if (score > 0.2) return "score-low";
  if (score < -0.2) return "score-high";
  return "score-med";
}
function toxIcon(score) {
  if (score === null || score === undefined || isNaN(score)) return "";
  if (score >= 0.85) return ICON.skull;
  if (score >= 0.6) return ICON.alert;
  return ICON.shield;
}
function sentIcon(score) {
  if (score === null || score === undefined || isNaN(score)) return "";
  if (score > 0.2) return ICON.smile;
  if (score < -0.2) return ICON.frown;
  return ICON.meh;
}
function fmt(val, decimals = 2) {
  if (val === null || val === undefined || isNaN(val)) return "—";
  return parseFloat(val).toFixed(decimals);
}
function timeAgo(ts) {
  if (!ts) return "—";
  const diff = Math.floor((Date.now() - new Date(ts)) / 1000);
  if (diff < 60) return diff + "s ago";
  if (diff < 3600) return Math.floor(diff / 60) + "m ago";
  if (diff < 86400) return Math.floor(diff / 3600) + "h ago";
  return Math.floor(diff / 86400) + "d ago";
}
function actionBadge(action) {
  return `<span class="action-${action || "ignore"}">${action || "—"}</span>`;
}
function severityBadge(level) {
  return `<span class="severity-${level || "low"}">${level || "—"}</span>`;
}

// ── Health badges (consistent with score rules) ──────────────
function toxicityHealthLabel(avg) {
  if (avg >= 0.85)
    return { text: "Critical — Intervention Likely", cls: "label-high" };
  if (avg >= 0.6)
    return { text: "Elevated — Monitor Closely", cls: "label-warn" };
  return { text: "Within Normal Range", cls: "label-safe" };
}
function sentimentHealthLabel(avg) {
  if (avg > 0.2) return { text: "Positive Atmosphere", cls: "label-safe" };
  if (avg < -0.2) return { text: "Negative Drift", cls: "label-high" };
  return { text: "Neutral / Mixed", cls: "label-warn" };
}
function riskLabel(avg) {
  if (avg >= 0.85) return '<span class="severity-critical">High Risk</span>';
  if (avg >= 0.6) return '<span class="severity-high">Elevated</span>';
  return '<span class="severity-low">Low Risk</span>';
}

// ── Live clock ───────────────────────────────────────────────
function startLiveClock() {
  const el = document.getElementById("live-clock");
  if (!el) return;
  const weekdays = [
    "Sunday",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
  ];
  function tick() {
    const d = new Date();
    const wd = weekdays[d.getDay()];
    const dd = String(d.getDate()).padStart(2, "0");
    const mo = String(d.getMonth() + 1).padStart(2, "0");
    const yy = d.getFullYear();

    // Time logic
    let hours = d.getHours();
    const minutes = String(d.getMinutes()).padStart(2, "0");
    const seconds = String(d.getSeconds()).padStart(2, "0");
    const ampm = hours >= 12 ? "PM" : "AM";

    // Convert 24h to 12h format
    hours = hours % 12;
    hours = hours ? hours : 12; // the hour '0' should be '12'
    const hh = String(hours).padStart(2, "0");

    const tz = -d.getTimezoneOffset() / 60;
    const tzStr = "UTC" + (tz >= 0 ? "+" : "") + tz;
    el.textContent = `${wd}, ${dd}/${mo}/${yy} · ${hh}:${minutes}:${seconds}${ampm} · ${tzStr}`;
  }
  tick();
  setInterval(tick, 1000);
}

// ── Typing effect (greeting subtitle) ────────────────────────
function startTyping(elId, text, speed = 55) {
  const el = document.getElementById(elId);
  if (!el) return;
  el.textContent = "";
  let i = 0;
  (function step() {
    if (i >= text.length) return;
    el.textContent += text.charAt(i++);
    setTimeout(step, speed);
  })();
}

// ── Auto-refresh countdown ───────────────────────────────────
function startAutoRefresh(callback, seconds = 30) {
  const el = document.getElementById("countdown");
  let c = seconds;
  if (el) el.textContent = c + "s";
  setInterval(() => {
    c--;
    if (el) el.textContent = c + "s";
    if (c <= 0) {
      c = seconds;
      try {
        callback();
      } catch (e) {
        console.error(e);
      }
    }
  }, 1000);
}

// ── Greeting photons ─────────────────────────────────────────
function spawnPhotons(container, count = 7) {
  if (!container) return;
  const colors = ["#44ff88", "#2bd76a", "#4fffd4"];
  for (let i = 0; i < count; i++) {
    const p = document.createElement("div");
    p.className = "photon";
    const size = Math.floor(Math.random() * 8) + 4;
    p.style.width = size + "px";
    p.style.height = size + "px";
    p.style.left = Math.random() * 100 + "%";
    p.style.top = Math.random() * 100 + "%";
    p.style.background = `radial-gradient(circle, ${colors[i % colors.length]} 0%, transparent 70%)`;
    p.style.animationDuration = 8 + Math.random() * 7 + "s";
    p.style.animationDelay = -Math.random() * 8 + "s";
    container.appendChild(p);
  }
}

// ── Particle burst on stat-card hover ────────────────────────
function attachParticleBurst() {
  const colors = ["#44ff88", "#ff4f6b", "#f7c94f"];
  document.addEventListener(
    "mouseenter",
    (e) => {
      if (!e.target.closest(".stat-card")) return;
      const card = e.target.closest(".stat-card");
      const colors = ["#44ff88", "#ff4f6b", "#f7c94f"];

      for (let i = 0; i < 6; i++) {
        // 12 → 6 particles
        const dot = document.createElement("div");
        dot.className = "particle";
        const size = Math.floor(Math.random() * 3) + 3; // 4-8px → 3-6px
        dot.style.width = size + "px";
        dot.style.height = size + "px";
        dot.style.left = "0%";
        dot.style.top = "100%";
        dot.style.background = colors[i % colors.length];
        dot.style.boxShadow = `0 0 4px ${colors[i % colors.length]}`; // softer glow
        dot.style.opacity = "0.5"; // start semi-transparent
        card.appendChild(dot);

        const angle = (i / 6) * Math.PI - Math.PI / 2 + Math.random() * 0.3; // fan rightward
        const dist = 25 + Math.random() * 20;
        const dx = Math.cos(angle) * dist;
        const dy = Math.sin(angle) * dist;

        requestAnimationFrame(() => {
          dot.style.transform = `translate(${dx}px, calc(-50% + ${dy}px)) scale(0.1)`;
          dot.style.opacity = "0";
        });
        setTimeout(() => dot.remove(), 900); // 650ms → 900ms slower fade
      }
    },
    true,
  );
}

// ── Live Feed (Monitor page) ─────────────────────────────────
let _feedData = [];
window._feedPage = 1;
const FEED_PAGE_SIZE = 10;

async function loadFeed() {
  try {
    const res = await fetch(`/api/${serverId}/feed`);
    _feedData = await res.json();
    _feedPage = 1;
    renderFeedPage();
  } catch (e) {
    console.error("Feed error:", e);
  }
}

function renderFeedPage() {
  const tbody = document.getElementById("feed-body");
  const countEl = document.getElementById("feed-count");
  const pagerEl = document.getElementById("feed-pagination");
  const indEl = document.getElementById("feed-page-indicator");
  if (!tbody) return;

  if (!_feedData.length) {
    tbody.innerHTML =
      '<tr><td colspan="7" class="loading-row">No messages yet.</td></tr>';
    if (countEl) countEl.textContent = "0 messages";
    if (pagerEl) pagerEl.innerHTML = "";
    if (indEl) indEl.textContent = "";
    return;
  }
  if (countEl) countEl.textContent = _feedData.length + " messages";

  const totalPages = Math.max(1, Math.ceil(_feedData.length / FEED_PAGE_SIZE));
  if (window._feedPage > totalPages) window._feedPage = totalPages;
  const start = (window._feedPage - 1) * FEED_PAGE_SIZE;
  const slice = _feedData.slice(start, start + FEED_PAGE_SIZE);
  tbody.innerHTML = slice
    .map(
      (row) => `
    <tr>
      <td><span class="user-cell">${row.username || "—"}</span></td>
      <td><div class="msg-content" title="${(row.message_content || "").replace(/"/g, "&quot;")}">${row.message_content || "—"}</div></td>
      <td><span class="score ${scoreClass(row.toxicity_score)}">${toxIcon(row.toxicity_score)}${fmt(row.toxicity_score)}</span></td>
      <td><span class="score ${sentClass(row.sentiment_score)}">${sentIcon(row.sentiment_score)}${fmt(row.sentiment_score)}</span></td>
      <td style="font-size:12px;color:var(--text-muted)">${row.emotion || "—"}</td>
      <td>${row.is_flagged ? '<span class="flag-yes">⚑ Yes</span>' : '<span class="flag-no">—</span>'}</td>
      <td style="font-size:12px;color:var(--text-muted);white-space:nowrap">${timeAgo(row.message_timestamp)}</td>
    </tr>
  `,
    )
    .join("");

  if (indEl) indEl.textContent = `Page ${window._feedPage} of ${totalPages}`;
  if (pagerEl)
    pagerEl.innerHTML = buildPaginationHTML(
      window._feedPage,
      totalPages,
      "_feedPage",
      "renderFeedPage",
    );
}

// ── Health stats (Overview page) ─────────────────────────────
async function loadHealth() {
  try {
    const res = await fetch(`/api/${serverId}/health`);
    const data = await res.json();

    const serverEl = document.getElementById("server-id");

    const tot = document.getElementById("total-messages");
    const tox = document.getElementById("avg-toxicity");
    const sen = document.getElementById("avg-sentiment");
    if (serverEl) serverEl.textContent = serverId;
    if (tot) tot.textContent = data.stats?.total_messages ?? "—";
    if (tox) tox.textContent = fmt(data.stats?.avg_toxicity);
    if (sen) sen.textContent = fmt(data.stats?.avg_sentiment);

    const toxVal = data.stats?.avg_toxicity;
    const senVal = data.stats?.avg_sentiment;
    if (toxVal != null) {
      const { text, cls } = toxicityHealthLabel(parseFloat(toxVal));
      const el = document.getElementById("tox-label");
      if (el) {
        el.textContent = text;
        el.className = `stat-label-badge ${cls}`;
      }
    }
    if (senVal != null) {
      const { text, cls } = sentimentHealthLabel(parseFloat(senVal));
      const el = document.getElementById("sent-label");
      if (el) {
        el.textContent = text;
        el.className = `stat-label-badge ${cls}`;
      }
    }
  } catch (e) {
    console.error("Health error:", e);
  }
}


// ── Users (Monitor: Top Flagged Users) ───────────────────────
async function loadFlaggedUsers() {
  try {
    const res = await fetch(`/api/${serverId}/top-flagged-users`);
    const data = await res.json();
    const users = data.top_flagged_users || [];
    const tbody = document.getElementById("flagged-users-body");
    if (!tbody) return;
    if (!users.length) {
      tbody.innerHTML =
        '<tr><td colspan="5" class="loading-row">No flagged users yet.</td></tr>';
      return;
    }
    tbody.innerHTML = users
      .map(
        (u, i) => `
      <tr>
        <td style="font-family:var(--font-mono);color:var(--text-muted)">#${i + 1}</td>
        <td class="user-cell">${u.username || "—"}</td>
        <td style="font-family:var(--font-mono)">${u.warning_count ?? 0}</td>
        <td><span class="score ${scoreClass(u.rolling_toxicity_avg)}">${toxIcon(u.rolling_toxicity_avg)}${fmt(u.rolling_toxicity_avg)}</span></td>
        <td>${riskLabel(parseFloat(u.rolling_toxicity_avg))}</td>
      </tr>
    `,
      )
      .join("");
  } catch (e) {
    console.error("Flagged users error:", e);
  }
}

// ── Interventions (Interventions page) ───────────────────────
let _intData = [];
window._intPage = 1;
const INT_PAGE_SIZE = 10;

async function loadInterventionHistory() {
  try {
    const res = await fetch(`/api/${serverId}/interventions`);
    _intData = await res.json();
    window._intPage = 1;
    renderInterventionPage();
  } catch (e) {
    console.error("Interventions error:", e);
  }
}

function renderInterventionPage() {
  const tbody = document.getElementById("interventions-body");
  const countEl = document.getElementById("intervention-count");
  const pagerEl = document.getElementById("int-pagination");
  const indEl = document.getElementById("int-page-indicator");
  if (!tbody) return;

  if (!_intData.length) {
    tbody.innerHTML =
      '<tr><td colspan="6" class="loading-row">No interventions yet.</td></tr>';
    if (countEl) countEl.textContent = "0 records";
    if (pagerEl) pagerEl.innerHTML = "";
    if (indEl) indEl.textContent = "";
    return;
  }
  if (countEl) countEl.textContent = _intData.length + " records";

  const totalPages = Math.max(1, Math.ceil(_intData.length / INT_PAGE_SIZE));
  if (window._intPage > totalPages) window._intPage = totalPages;
  const start = (window._intPage - 1) * INT_PAGE_SIZE;
  const slice = _intData.slice(start, start + INT_PAGE_SIZE);

  tbody.innerHTML = slice
    .map(
      (row) => `
    <tr>
      <td><div class="msg-content" title="${(row.message_content || "").replace(/"/g, "&quot;")}">${row.message_content || "—"}</div></td>
      <td class="user-cell">${row.username || "—"}</td>
      <td>${actionBadge(row.action_type)}</td>
      <td>${severityBadge(row.severity_level)}</td>
      <td><div class="msg-content" title="${(row.reasoning || "").replace(/"/g, "&quot;")}">${row.reasoning || "—"}</div></td>
      <td><div class="msg-content" title="${(row.generated_response || "").replace(/"/g, "&quot;")}">${row.generated_response || "—"}</div></td>
      <td style="font-size:12px;color:var(--text-muted);white-space:nowrap">${timeAgo(row.created_at)}</td>
    </tr>
  `,
    )
    .join("");

  if (indEl) indEl.textContent = `Page ${window._intPage} of ${totalPages}`;
  if (pagerEl)
    pagerEl.innerHTML = buildPaginationHTML(
      window._intPage,
      totalPages,
      "_intPage",
      "renderInterventionPage",
    );
}

// ── Pagination renderer (max 5 page buttons + ellipsis) ──────
function buildPaginationHTML(current, total, varName, renderFn) {
  if (total <= 1) return "";
  const pages = [];
  const push = (n) => pages.push(n);
  if (total <= 7) {
    for (let i = 1; i <= total; i++) push(i);
  } else {
    push(1);
    let start = Math.max(2, current - 1);
    let end = Math.min(total - 1, current + 1);
    if (current <= 3) {
      start = 2;
      end = 4;
    }
    if (current >= total - 2) {
      start = total - 3;
      end = total - 1;
    }
    if (start > 2) push("…");
    for (let i = start; i <= end; i++) push(i);
    if (end < total - 1) push("…");
    push(total);
  }
  const prev = `<button class="page-btn" ${current === 1 ? "disabled" : ""} onclick="window.${varName}=${current - 1};${renderFn}()">←</button>`;
  const next = `<button class="page-btn" ${current === total ? "disabled" : ""} onclick="window.${varName}=${current + 1};${renderFn}()">→</button>`;
  const mid = pages
    .map((p) =>
      p === "…"
        ? `<span class="page-ellipsis">…</span>`
        : `<button class="page-btn ${p === current ? "active" : ""}" onclick="window.${varName}=${p};${renderFn}()">${p}</button>`,
    )
    .join("");
  return prev + mid + next;
}

// ── Inject stat-card icons on load ───────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const slots = {
    "icon-total": ICON.chat,
    "icon-tox": ICON.shield,
    "icon-sent": ICON.pulse,
  };
  Object.entries(slots).forEach(([id, svg]) => {
    const el = document.getElementById(id);
    if (el) el.innerHTML = svg;
  });
  // Greeting photons
  spawnPhotons(document.getElementById("greeting-photons"));
  // Live clock
  startLiveClock();
  // Typing effect
  startTyping("typing-text", "ModBot is watching your server");
  // Particle burst
  attachParticleBurst();
});
