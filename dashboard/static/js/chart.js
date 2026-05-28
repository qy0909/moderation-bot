// ── Chart defaults — ModBot deep space ───────────────────────
Chart.defaults.color = "#4a7050";
Chart.defaults.borderColor = "#1a3d1f";
Chart.defaults.font.family = "'DM Sans', sans-serif";

const ACCENT_GREEN = "#44ff88";
const ACCENT_RED = "#ff4f6b";
const ACCENT_YELLOW = "#f7c94f";
const GRID_COLOR = "#1a3d1f";

// ── Public init for analytics-style pages ────────────────────
async function loadCharts() {
  const feedData = await fetch(`/api/${serverId}/feed`).then(r => r.json());

  bindTimeframe("tf-tox",  (tf) => initToxicityScatter(tf, feedData));
  bindTimeframe("tf-sent", (tf) => initSentimentScatter(tf, feedData));
  bindTimeframe("tf-vol",  initVolumeBar);
  bindTimeframe("tf-pie",  initInterventionPie);
  bindTimeframe("tf-cloud", (tf) => loadEmotionCloud(tf, feedData));


  initToxicityScatter("24h", feedData);
  initSentimentScatter("24h", feedData);
  initVolumeBar("24h");
  initInterventionPie("24h");
  loadEmotionCloud("24h", feedData); 
}

// ── Helpers ──────────────────────────────────────────────────
function tfToMs(tf) {
  switch (tf) {
    case "1h":
      return 1 * 3600000;
    case "6h":
      return 6 * 3600000;
    case "12h":
      return 12 * 3600000;
    case "24h":
      return 24 * 3600000;
    case "all":
      return Infinity;
    default:
      return 24 * 3600000;
  }
}

function fmtTimeLabel(ts, includeDate = false) {
  const d = new Date(ts);
  let h = d.getHours();
  const m = String(d.getMinutes()).padStart(2, "0");
  const ap = h >= 12 ? "PM" : "AM";
  h = h % 12;
  if (h === 0) h = 12;

  // HH:MM AA part
  const timeStr = `${h}:${m}${ap}`;

  if (includeDate) {
    // DD/MM/YYYY part
    const day = String(d.getDate()).padStart(2, "0");
    const month = String(d.getMonth() + 1).padStart(2, "0"); // Months are 0-indexed
    const year = d.getFullYear();
    const dateStr = `${day}/${month}/${year}`;

    return `${dateStr}, \u00A0 ${timeStr}`;
  }

  return timeStr;
}
function pointColorTox(v) {
  if (v >= 0.85) return ACCENT_RED;
  if (v >= 0.6) return ACCENT_YELLOW;
  return ACCENT_GREEN;
}
function pointColorSent(v) {
  if (v > 0.2) return ACCENT_GREEN;
  if (v < -0.2) return ACCENT_RED;
  return ACCENT_YELLOW;
}

function chartScaleOptions(yLabel, yRange) {
  return {
    responsive: true,
    maintainAspectRatio: false,
    plugins: { legend: { display: false } },
    scales: {
      x: {
        type: "linear",
        grid: { color: GRID_COLOR },
        ticks: {
          font: { size: 10 },
          maxRotation: 0,
          autoSkip: false,
          callback: (value) => {
            // Check if the value looks like a timestamp (e.g., > 1 trillion)
            if (value > 1000000000000) {
              return fmtTimeLabel(value, false);
            }
            return value;
          },
        },
      },
      y: {
        grid: { color: GRID_COLOR },
        ticks: { font: { size: 11 } },
        title: { display: !!yLabel, text: yLabel, font: { size: 11 } },
        ...(yRange ? { min: yRange[0], max: yRange[1] } : {}),
      },
    },
  };
}

// ── Bind timeframe selector buttons ──────────────────────────
function bindTimeframe(groupId, onChange) {
  const group = document.getElementById(groupId);
  if (!group) return;
  group.querySelectorAll(".tf-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      group
        .querySelectorAll(".tf-btn")
        .forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      onChange(btn.dataset.tf);
    });
  });
}

// ── Toxicity Scatter ─────────────────────────────────────────
let _toxChart = null;
async function initToxicityScatter(tf, data) {
  
  try {
    const cutoff = Date.now() - tfToMs(tf);
    const filtered = data
      .filter(
        (r) =>
          r.message_timestamp &&
          new Date(r.message_timestamp).getTime() >= cutoff,
      )
      .filter(
        (r) => r.toxicity_score !== null && r.toxicity_score !== undefined,
      );
    const points = filtered.map((r) => ({
      x: new Date(r.message_timestamp).getTime(), // Keep the full timestamp
      y: parseFloat(r.toxicity_score),
    }));
    const colors = points.map((p) => pointColorTox(p.y));
    const ctx = document.getElementById("toxicityChart");
    if (!ctx) return;
    if (_toxChart) _toxChart.destroy();
    _toxChart = new Chart(ctx, {
      type: "scatter",
      data: {
        datasets: [
          {
            data: points,
            backgroundColor: colors,
            borderColor: colors,
            pointRadius: 4,
            pointHoverRadius: 6,
          },
        ],
      },
      options: {
        ...chartScaleOptions("Toxicity Score", [0, 1]),
        plugins: {
          legend: { display: false },
          tooltip: {
            padding: 12,
            caretPadding: 10,
            callbacks: {
              title: () => "",
              label: (c) => {
                const timeAndDate = fmtTimeLabel(c.raw.x, true);
                return `\u00A0 ${timeAndDate} \u00A0 | \u00A0 Toxicity: ${c.raw.y.toFixed(2)}`;
              },
            },
          },
        },
      },
    });
  } catch (e) {
    console.error("Toxicity scatter error:", e);
  }
}

// ── Sentiment Scatter ────────────────────────────────────────
let _sentChart = null;
async function initSentimentScatter(tf, data) {
  
  try {
    const cutoff = Date.now() - tfToMs(tf);
    const filtered = data
      .filter(
        (r) =>
          r.message_timestamp &&
          new Date(r.message_timestamp).getTime() >= cutoff,
      )
      .filter(
        (r) => r.sentiment_score !== null && r.sentiment_score !== undefined,
      );
    const points = filtered.map((r) => ({
      x: new Date(r.message_timestamp).getTime(), // Keep the full timestamp
      y: parseFloat(r.sentiment_score),
    }));
    const colors = points.map((p) => pointColorSent(p.y));
    const ctx = document.getElementById("sentimentChart");
    if (!ctx) return;
    if (_sentChart) _sentChart.destroy();
    _sentChart = new Chart(ctx, {
      type: "scatter",
      data: {
        datasets: [
          {
            data: points,
            backgroundColor: colors,
            borderColor: colors,
            pointRadius: 4,
            pointHoverRadius: 6,
          },
        ],
      },
      options: {
        ...chartScaleOptions("Sentiment Score", [-1, 1]),
        plugins: {
          legend: { display: false },
          tooltip: {
            padding: 12,
            caretPadding: 10,
            callbacks: {
              title: () => "",
              label: (c) => {
                const timeAndDate = fmtTimeLabel(c.raw.x, true);
                return `\u00A0 ${timeAndDate} \u00A0 | \u00A0 Sentiment: ${c.raw.y.toFixed(2)}`;
              },
            },
          },
        },
      },
    });
  } catch (e) {
    console.error("Sentiment scatter error:", e);
  }
}

// ── Volume Bar (gap-filled hourly buckets) ───────────────────
let _volChart = null;
async function initVolumeBar(tf) {
  
  try {
    const res = await fetch(`/api/${serverId}/volume`);
    const all = await res.json();

    // Index API rows by the start-of-hour timestamp
    const byHour = {};
    all.forEach((r) => {
      const ts = new Date(r.hour);
      ts.setMinutes(0, 0, 0);
      byHour[ts.getTime()] = parseInt(r.message_count) || 0;
    });

    // Determine the hour range to render
    const now = new Date();
    now.setMinutes(0, 0, 0);
    const endMs = now.getTime();

    let hours;
    if (tf === "all") {
      const keys = Object.keys(byHour).map(Number);
      if (keys.length) {
        const minKey = Math.min(...keys);
        hours = Math.max(1, Math.round((endMs - minKey) / 3600000) + 1);
      } else {
        hours = 24;
      }
    } else {
      hours = tf === "1h" ? 1 : tf === "6h" ? 6 : tf === "12h" ? 12 : 24;
    }

    const labels = [];
    const volume = [];
    for (let i = hours - 1; i >= 0; i--) {
      const t = endMs - i * 3600000;
      const d = new Date(t);
      labels.push(String(d.getHours()).padStart(2, "0") + ":00");
      volume.push(byHour[t] || 0);
    }

    const ctx = document.getElementById("volumeChart");
    if (!ctx) return;
    if (_volChart) _volChart.destroy();
    _volChart = new Chart(ctx, {
      type: "bar",
      data: {
        labels,
        datasets: [
          {
            label: "Messages",
            data: volume,
            backgroundColor: "rgba(68,255,136,0.3)",
            borderColor: ACCENT_GREEN,
            borderWidth: 1,
            borderRadius: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            padding: 12,
            caretPadding: 10,
            callbacks: {
              title: () => "",
              label: (c) => {
                const label = c.label;
                const [hours, minutes] = label.split(":");
                const d = new Date();
                d.setHours(parseInt(hours), parseInt(minutes), 0, 0);
                const datePart = fmtTimeLabel(d.getTime(), true).split(" ")[0];
                const timePart = fmtTimeLabel(d.getTime(), false);

                return `\u00A0 ${datePart} \u00A0 ${timePart} \u00A0 | \u00A0 Messages: ${c.parsed.y}`;
              },
            },
          },
        },
        scales: {
          x: {
            grid: { color: GRID_COLOR },
            ticks: {
              font: { size: 11 },
              maxTicksLimit: 12,
              autoSkip: true,
              callback: function (val, index) {
                const label = this.getLabelForValue(val);
                const [hours, minutes] = label.split(":");
                const d = new Date();
                d.setHours(parseInt(hours), parseInt(minutes), 0, 0);

                return fmtTimeLabel(d.getTime(), false); 
              },
            },
          },
          y: {
            grid: { color: GRID_COLOR },
            ticks: { font: { size: 11 }, precision: 0 },
            beginAtZero: true,
          },
        },
      },
    });
  } catch (e) {
    console.error("Volume chart error:", e);
  }
}

// ── Intervention Pie (doughnut) ──────────────────────────────
let _pieChart = null;
async function initInterventionPie(tf) {
  
  try {
    const res = await fetch(`/api/${serverId}/breakdown`);
    const data = await res.json();
    const counts = { ignore: 0, soft_reminder: 0, warning: 0, escalate: 0 };
    data.forEach((r) => {
      if (counts[r.action_type] !== undefined)
        counts[r.action_type] = parseInt(r.count) || 0;
    });

    const ctx = document.getElementById("interventionPieChart");
    if (!ctx) return;
    if (_pieChart) _pieChart.destroy();

    const hasData = Object.values(counts).some((v) => v > 0);

    // Gradient factory — called after chart mounts so we have canvas dimensions
    function makeGradients(chartCtx, chartArea) {
      const { left, right, top, bottom } = chartArea;
      const cx = (left + right) / 2;
      const cy = (top + bottom) / 2;
      const r  = Math.min(right - left, bottom - top) / 2;

      // Each segment gets a radial gradient from bright centre-edge → darker outer-edge
      const defs = [
        ["#9ca3af", "#374151"],   // ignore   — gray
        ["#6effaa", "#0f6e56"],   // soft     — green
        ["#fde68a", "#b45309"],   // warning  — amber
        ["#ff6b8a", "#7f1d1d"],   // escalate — red
      ];

      return defs.map(([inner, outer]) => {
        const g = chartCtx.createRadialGradient(cx, cy, r * 0.45, cx, cy, r);
        g.addColorStop(0, inner);
        g.addColorStop(1, outer);
        return g;
      });
    }

    // Plugin that rebuilds gradients on every resize / first draw
    const gradientPlugin = {
      id: "gradientFill",
      beforeDatasetsUpdate(chart) {
        if (!hasData) return;
        if (!chart.chartArea) return;
        const grads = makeGradients(chart.ctx, chart.chartArea);
        chart.data.datasets[0].backgroundColor = grads;
      },
    };

    _pieChart = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: ["Ignore", "Soft Reminder", "Warning", "Escalate"],
        datasets: [
          {
            data: hasData
              ? [counts.ignore, counts.soft_reminder, counts.warning, counts.escalate]
              : [1, 1, 1, 1],
            backgroundColor: hasData
              ? ["#9ca3af", "#44ff88", "#f7c94f", "#ff4f6b"]  // overwritten by plugin
              : [
                  "rgba(107,114,128,0.07)",
                  "rgba(68,255,136,0.07)",
                  "rgba(247,201,79,0.07)",
                  "rgba(255,79,107,0.07)",
                ],
            borderColor: hasData
              ? ["rgba(255,255,255,0.12)", "rgba(255,255,255,0.12)",
                 "rgba(255,255,255,0.12)", "rgba(255,255,255,0.12)"]
              : ["rgba(107,114,128,0.2)", "rgba(68,255,136,0.2)",
                 "rgba(247,201,79,0.2)",  "rgba(255,79,107,0.2)"],
            borderWidth: hasData ? 1.5 : 1,
            hoverOffset: 8,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "62%",
        animation: {
          animateRotate: true,
          duration: 700,
          easing: "easeInOutQuart",
        },
        plugins: {
          legend: {
  position: "bottom",
  labels: {
    padding: 20,
    font: { size: 12, family: "DM Sans, sans-serif" },
    color: "#ffffff",
    boxWidth: 12,
    boxHeight: 12,
    borderRadius: 6,   // makes the box a circle pill
    useBorderRadius: true,
    generateLabels(chart) {
      const solidColors = ["#9ca3af", "#44ff88", "#f7c94f", "#ff4f6b"];
      const emptyColor  = "rgba(255,255,255,0.2)";
      return chart.data.labels.map((label, i) => ({
        text: label,
        fillStyle:   hasData ? solidColors[i] : emptyColor,
        strokeStyle: hasData ? solidColors[i] : emptyColor,
        lineWidth:   0,
        hidden:      false,
        index:       i,
        fontColor:   "#ffffff",
      }));
    },
  },
},
          tooltip: {
            enabled: hasData,
            backgroundColor: "rgba(10,20,15,0.85)",
            titleColor: "#e8f5ea",
            bodyColor: "#9fddbb",
            borderColor: "rgba(68,255,136,0.2)",
            borderWidth: 1,
            padding: 10,
            callbacks: {
              label(item) {
                const total = item.dataset.data.reduce((a, b) => a + b, 0);
                const pct   = total ? ((item.parsed / total) * 100).toFixed(1) : 0;
                return `  ${item.parsed.toLocaleString()}  (${pct}%)`;
              },
            },
          },
        },
      },
      plugins: [
        gradientPlugin,
        {
          id: "noDataLabel",
          beforeDraw(chart) {
            if (hasData) return;
            const { width, height, ctx: c } = chart;
            c.save();
            c.font = "13px DM Sans, sans-serif";
            c.fillStyle = "rgba(232,245,234,0.35)";
            c.textAlign = "center";
            c.textBaseline = "middle";
            c.fillText("No data", width / 2, height / 2);
            c.restore();
          },
        },
        {
          // draws a soft inner shadow ring at the cutout edge
          id: "innerRing",
          afterDatasetsDraw(chart) {
            if (!hasData) return;
            const { ctx: c, chartArea: a } = chart;
            const cx = (a.left + a.right) / 2;
            const cy = (a.top + a.bottom) / 2;
            const cutR = (Math.min(a.right - a.left, a.bottom - a.top) / 2) * 0.62;
            c.save();
            c.beginPath();
            c.arc(cx, cy, cutR, 0, Math.PI * 2);
            c.strokeStyle = "rgba(255,255,255,0.06)";
            c.lineWidth = 2;
            c.stroke();
            c.restore();
          },
        },
      ],
    });
  } catch (e) {
    console.error("Intervention pie error:", e);
  }
}

let _cloudAnimId = null;
// ── Emotion tag cloud (Overview page) ────────────────────────
async function loadEmotionCloud(tf, data) {
  const cloud = document.getElementById("emotion-cloud");
  if (!cloud) return;

  // cancel previous animation loop before starting new one
  if (_cloudAnimId) {
    cancelAnimationFrame(_cloudAnimId);
    _cloudAnimId = null;
  }

  try {
    // ── Apply timeframe filter ─────────────────────────────
    const cutoff = Date.now() - tfToMs(tf);
    const filtered = tf === "all"
      ? data
      : data.filter(r => r.message_timestamp &&
          new Date(r.message_timestamp).getTime() >= cutoff);

    // ── Build counts AND accumulate sentiment per emotion ──
    const counts = {};
    const sentimentSums = {};
    const sentimentCounts = {};

    filtered.forEach((r) => {
      const e = (r.emotion || "").trim();
      if (!e) return;
      counts[e] = (counts[e] || 0) + 1;
      const s = parseFloat(r.sentiment_score);
      if (!isNaN(s)) {
        sentimentSums[e] = (sentimentSums[e] || 0) + s;
        sentimentCounts[e] = (sentimentCounts[e] || 0) + 1;
      }
    });

    // ── Cap to top 18 emotions ─────────────────────────────
    const entries = Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 18);

    if (!entries.length) {
      cloud.innerHTML = '<div class="empty-state">No emotion data yet</div>';
      return;
    }

    // ── Canvas setup ───────────────────────────────────────
    cloud.innerHTML = '<canvas id="emotion-canvas"></canvas>';
    const canvas = document.getElementById("emotion-canvas");
    const dpr = window.devicePixelRatio || 1;
    const W = cloud.offsetWidth || 600;
    const H = 320;
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    canvas.style.width = W + "px";
    canvas.style.height = H + "px";
    const ctx = canvas.getContext("2d");
    ctx.scale(dpr, dpr);

    const cx = W / 2;
    const cy = H / 2;
    const max = entries[0][1];
    const min = entries[entries.length - 1][1];

    // ── Clamp orbit radius to canvas bounds ────────────────
    const maxOrbit = Math.min(W, H) / 2 - 30;

    const rings = [
      { r: 60,  speed: 0.006 },
      { r: 115, speed: 0.004 },
      { r: 165, speed: 0.0025 },
    ];

    const bubbles = entries.map(([emo, n], i) => {
      const ring = rings[i % rings.length];
      const t = max === min ? 1 : (n - min) / (max - min);
      const rawOrbit = ring.r + Math.floor(i / rings.length) * 52;
      return {
        emo, n,
        radius: 22 + Math.round(t * 14),
        fontSize: 10 + Math.round(t * 5),
        orbitR: Math.min(rawOrbit, maxOrbit),
        speed: ring.speed * (Math.random() > 0.5 ? 1 : -1),
        angle: (i / entries.length) * Math.PI * 2,
        alpha: 0,
      };
    });

    // ── Sentiment colour helper ────────────────────────────
    function sentimentColor(emo, alpha = 1) {
      const n = sentimentCounts[emo];
      if (!n) return `rgba(160,160,180,${alpha})`;
      const avg = sentimentSums[emo] / n;
      if (avg > 0.2)  return `rgba(68,255,136,${alpha})`;
      if (avg < -0.2) return `rgba(255,79,107,${alpha})`;
      return              `rgba(247,201,79,${alpha})`;
    }

    let pulse = 0;

    function draw() {
      ctx.clearRect(0, 0, W, H);

      // Orbit rings
      bubbles.forEach((b) => {
        ctx.beginPath();
        ctx.arc(cx, cy, b.orbitR, 0, Math.PI * 2);
        ctx.strokeStyle = "rgba(68,255,136,0.06)";
        ctx.lineWidth = 1;
        ctx.stroke();
      });

      // Center core
      pulse += 0.03;
      const glow = 18 + Math.sin(pulse) * 6;
      const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, glow);
      grad.addColorStop(0, "rgba(68,255,136,0.9)");
      grad.addColorStop(1, "rgba(68,255,136,0)");
      ctx.beginPath();
      ctx.arc(cx, cy, glow, 0, Math.PI * 2);
      ctx.fillStyle = grad;
      ctx.fill();

      // Bubbles
      bubbles.forEach((b) => {
        b.angle += b.speed;
        b.alpha = Math.min(1, b.alpha + 0.02);
        const x = cx + Math.cos(b.angle) * b.orbitR;
        const y = cy + Math.sin(b.angle) * b.orbitR;

        // Connector line
        ctx.beginPath();
        ctx.moveTo(cx, cy);
        ctx.lineTo(x, y);
        ctx.strokeStyle = sentimentColor(b.emo, 0.08 * b.alpha);
        ctx.lineWidth = 1;
        ctx.stroke();

        // Bubble fill
        const bg = ctx.createRadialGradient(x, y, 0, x, y, b.radius);
        bg.addColorStop(0, sentimentColor(b.emo, 0.28 * b.alpha));
        bg.addColorStop(1, sentimentColor(b.emo, 0.05 * b.alpha));
        ctx.beginPath();
        ctx.arc(x, y, b.radius, 0, Math.PI * 2);
        ctx.fillStyle = bg;
        ctx.fill();
        ctx.strokeStyle = sentimentColor(b.emo, 0.4 * b.alpha);
        ctx.lineWidth = 1;
        ctx.stroke();

        // Label
        ctx.fillStyle = `rgba(232,245,234,${b.alpha})`;
        ctx.font = `600 ${b.fontSize}px DM Sans, sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(b.emo, x, y - 4);

        // Count
        ctx.fillStyle = sentimentColor(b.emo, 0.75 * b.alpha);
        ctx.font = `500 ${Math.max(9, b.fontSize - 3)}px DM Sans, sans-serif`;
        ctx.fillText(b.n, x, y + b.fontSize - 2);
      });

      _cloudAnimId = requestAnimationFrame(draw); 
    }

    draw();
  } catch (e) {
    console.error("Emotion cloud error:", e);
  }
}
