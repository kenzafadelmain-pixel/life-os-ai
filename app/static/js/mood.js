/* Mood page — live sentiment analysis preview + 14-day chart. */
(function () {
  'use strict';

  // ---- Live preview --------------------------------------------------
  const $textarea = document.getElementById('journal');
  const $box      = document.getElementById('live-analysis');
  const $emo      = document.getElementById('la-emotion');
  const $sent     = document.getElementById('la-sentiment');
  const $stress   = document.getElementById('la-stress');
  const $mot      = document.getElementById('la-motivation');
  const $summary  = document.getElementById('la-summary');

  let debounce = null;
  if ($textarea) {
    $textarea.addEventListener('input', () => {
      clearTimeout(debounce);
      const text = $textarea.value.trim();
      if (text.length < 12) { $box.style.display = 'none'; return; }
      debounce = setTimeout(async () => {
        try {
          const resp = await fetch('/app/mood/analyse', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ journal: text }),
          });
          const data = await resp.json();
          $emo.textContent = data.emotion;
          $emo.className = `emotion-pill emo-${data.emotion}`;
          $sent.textContent   = `sentiment ${data.sentiment}`;
          $stress.textContent = `stress ${data.stress}`;
          $mot.textContent    = `motivation ${data.motivation}`;
          $summary.textContent = data.summary;
          $box.style.display = 'block';
        } catch (e) { /* silent */ }
      }, 320);
    });
  }

  // ---- Trend chart ---------------------------------------------------
  const canvas = document.getElementById('moodChart');
  if (!canvas || !window.Chart) return;
  const trend = JSON.parse(canvas.dataset.trend || '[]');

  new Chart(canvas.getContext('2d'), {
    type: 'line',
    data: {
      labels: trend.map((p) => p.date.slice(5)),
      datasets: [
        { label: 'Sentiment',  data: trend.map((p) => p.sentiment * 10 + 5),
          borderColor: '#22d3ee', backgroundColor: 'rgba(34,211,238,0.18)',
          fill: true, tension: 0.35, borderWidth: 2.4 },
        { label: 'Motivation', data: trend.map((p) => p.motivation),
          borderColor: '#a855f7', tension: 0.35, borderWidth: 2 },
        { label: 'Stress',     data: trend.map((p) => p.stress),
          borderColor: '#facc15', tension: 0.35, borderWidth: 2 },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { position: 'bottom', labels: { boxWidth: 10, padding: 12 } },
        tooltip: { backgroundColor: 'rgba(12,13,24,0.95)' },
      },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,0.04)' } },
        y: { min: 0, max: 10, grid: { color: 'rgba(255,255,255,0.04)' } },
      },
    },
  });
})();
