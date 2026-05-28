// ── Animated network of glowing green nodes + floating particles ───────────────────────────

(function initNetwork() {
  const canvas = document.getElementById('network-canvas');
  if (!canvas) return;
  const ctx = canvas.getContext('2d');

  let W = 0, H = 0, dpr = window.devicePixelRatio || 1;
  const NODE_COUNT = 26;
  const PARTICLE_COUNT = 55;
  const LINK_DIST = 180;
  const GREEN = '34, 224, 122';

  const nodes = [];
  const particles = [];

  function resize() {
    const rect = canvas.getBoundingClientRect();
    W = rect.width; H = rect.height;
    canvas.width = W * dpr;
    canvas.height = H * dpr;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function rand(a, b) { return a + Math.random() * (b - a); }

  function seed() {
    nodes.length = 0;
    particles.length = 0;
    for (let i = 0; i < NODE_COUNT; i++) {
      nodes.push({
        x: rand(0, W), y: rand(0, H),
        vx: rand(-0.18, 0.18), vy: rand(-0.18, 0.18),
        r: rand(2.2, 3.8),
        pulse: Math.random() * Math.PI * 2,
      });
    }
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      particles.push({
        x: rand(0, W), y: rand(0, H),
        vx: rand(-0.05, 0.05), vy: rand(-0.15, -0.04),
        r: rand(0.6, 1.6),
        a: rand(0.2, 0.7),
        life: rand(0, 1),
      });
    }
  }

  function step(t) {
    ctx.clearRect(0, 0, W, H);

    // links
    for (let i = 0; i < nodes.length; i++) {
      for (let j = i + 1; j < nodes.length; j++) {
        const a = nodes[i], b = nodes[j];
        const dx = a.x - b.x, dy = a.y - b.y;
        const d = Math.hypot(dx, dy);
        if (d < LINK_DIST) {
          const alpha = (1 - d / LINK_DIST) * 0.35;
          ctx.strokeStyle = `rgba(${GREEN}, ${alpha})`;
          ctx.lineWidth = 0.8;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }
    }

    // nodes (glow + core)
    for (const n of nodes) {
      n.x += n.vx; n.y += n.vy;
      n.pulse += 0.03;
      if (n.x < 0 || n.x > W) n.vx *= -1;
      if (n.y < 0 || n.y > H) n.vy *= -1;

      const glow = 14 + Math.sin(n.pulse) * 6;
      const grad = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, glow);
      grad.addColorStop(0, `rgba(${GREEN}, 0.9)`);
      grad.addColorStop(0.4, `rgba(${GREEN}, 0.35)`);
      grad.addColorStop(1, `rgba(${GREEN}, 0)`);
      ctx.fillStyle = grad;
      ctx.beginPath();
      ctx.arc(n.x, n.y, glow, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = `rgba(180, 255, 210, 0.95)`;
      ctx.beginPath();
      ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2);
      ctx.fill();
    }

    // floating particles
    for (const p of particles) {
      p.x += p.vx; p.y += p.vy;
      p.life += 0.005;
      if (p.y < -10 || p.x < -10 || p.x > W + 10) {
        p.x = rand(0, W); p.y = H + 5;
        p.vx = rand(-0.05, 0.05); p.vy = rand(-0.15, -0.04);
        p.a = rand(0.2, 0.7);
      }
      const tw = 0.6 + Math.sin(p.life * 6) * 0.4;
      ctx.fillStyle = `rgba(${GREEN}, ${p.a * tw})`;
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fill();
    }

    requestAnimationFrame(step);
  }

  window.addEventListener('resize', () => { resize(); seed(); });
  resize(); seed(); requestAnimationFrame(step);
})();


// ── Auth ─────────────────────────── 

const VALID = { username: 'admin', password: 'modbot2026' };

document.getElementById('login-form').addEventListener('submit', (e) => {
  e.preventDefault();
  const serverId = document.getElementById('serverId').value.trim();
  const username = document.getElementById('username').value.trim();
  const password = document.getElementById('password').value;
  const err = document.getElementById('login-error');
  err.textContent = '';

  if (!/^\d{6,32}$/.test(serverId)) {
    err.textContent = 'Discord Server ID must be a numeric ID (6-32 digits).';
    return;
  }
  if (username !== VALID.username || password !== VALID.password) {
    err.textContent = 'Invalid username or password.';
    return;
  }

  sessionStorage.setItem('modbot_auth', JSON.stringify({
    serverId, username, at: Date.now(),
  }));
  window.location.href = '/';
});
