/* Dashboard + productivity page — Chart.js setup + heatmap rendering. */
(function () {
  'use strict';

  // Defensive default styles so the global Chart instance matches our theme.
  if (window.Chart) {
    Chart.defaults.color = '#b8bad0';
    Chart.defaults.font.family = 'Inter, system-ui, sans-serif';
    Chart.defaults.borderColor = 'rgba(255,255,255,0.06)';
  }

  /** Build the chart on either canvas#trendChart or canvas#forecastChart. */
  function buildForecast(canvas) {
    if (!canvas || !window.Chart) return;
    const history = JSON.parse(canvas.dataset.history || '[]');
    const forecast = JSON.parse(canvas.dataset.forecast || '[]');

    const labels = [
      ...history.map((p) => p.date),
      ...forecast.map((p) => p.date),
    ];
    const historyValues = history.map((p) => p.value);
    const forecastValues = [
      ...Array(history.length).fill(null),
      ...(history.length ? [history[history.length - 1].value] : []),
      ...forecast.map((p) => p.value),
    ].slice(0, labels.length);

    const ctx = canvas.getContext('2d');

    // Aurora gradient stroke
    const grad = ctx.createLinearGradient(0, 0, canvas.width, 0);
    grad.addColorStop(0, '#22d3ee');
    grad.addColorStop(1, '#a855f7');

    const fillGrad = ctx.createLinearGradient(0, 0, 0, 240);
    fillGrad.addColorStop(0, 'rgba(34,211,238,0.32)');
    fillGrad.addColorStop(1, 'rgba(34,211,238,0)');

    new Chart(ctx, {
      type: 'line',
      data: {
        labels,
        datasets: [
          {
            label: 'Past 14 days',
            data: historyValues,
            borderColor: grad,
            backgroundColor: fillGrad,
            borderWidth: 2.4,
            tension: 0.4,
            fill: true,
            pointRadius: 3,
            pointBackgroundColor: '#22d3ee',
          },
          {
            label: 'Forecast',
            data: forecastValues,
            borderColor: '#a855f7',
            borderDash: [6, 4],
            borderWidth: 2,
            tension: 0.4,
            fill: false,
            pointRadius: 3,
            pointBackgroundColor: '#a855f7',
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { boxWidth: 10, boxHeight: 10, padding: 14 },
          },
          tooltip: {
            backgroundColor: 'rgba(12,13,24,0.95)',
            borderColor: 'rgba(34,211,238,0.4)',
            borderWidth: 1,
            padding: 10,
            titleFont: { family: 'JetBrains Mono', size: 11 },
            bodyFont: { family: 'Inter', size: 12 },
          },
        },
        scales: {
          x: {
            grid: { color: 'rgba(255,255,255,0.04)' },
            ticks: { font: { size: 10 }, maxRotation: 0, autoSkip: true, maxTicksLimit: 7 },
          },
          y: {
            beginAtZero: true,
            max: 100,
            grid: { color: 'rgba(255,255,255,0.04)' },
            ticks: { font: { size: 10 } },
          },
        },
      },
    });
  }

  buildForecast(document.getElementById('trendChart'));
  buildForecast(document.getElementById('forecastChart'));

  // ---- Heatmap rendering -----------------------------------------------
  const heat = document.getElementById('heatmap');
  if (heat) {
    let cells = [];
    try { cells = JSON.parse(heat.dataset.cells || '[]'); } catch (e) {}
    const byDate = new Map(cells.map((c) => [c.date, c.value]));

    const today = new Date();
    const days = 35;
    // Render oldest-first so today is in the bottom-right.
    for (let i = days - 1; i >= 0; i--) {
      const d = new Date(today);
      d.setDate(d.getDate() - i);
      const iso = d.toISOString().slice(0, 10);
      const v = byDate.get(iso) || 0;
      let level = 0;
      if (v >= 80) level = 4;
      else if (v >= 60) level = 3;
      else if (v >= 35) level = 2;
      else if (v > 0)   level = 1;
      const cell = document.createElement('div');
      cell.className = 'heatmap-cell';
      cell.dataset.v = String(level);
      cell.title = `${iso} · ${v}`;
      heat.appendChild(cell);
    }
  }
})();
