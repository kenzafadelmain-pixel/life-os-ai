/* Pomodoro timer for the Study page. Logs sessions on completion. */
(function () {
  'use strict';

  const $time   = document.getElementById('pom-time');
  const $start  = document.getElementById('pom-start');
  const $pause  = document.getElementById('pom-pause');
  const $reset  = document.getElementById('pom-reset');
  const $length = document.getElementById('pom-length');
  const $subj   = document.getElementById('pom-subject');
  const $fg     = document.getElementById('pom-fg-circle');
  if (!$time || !$start) return;

  const RING_CIRCUMFERENCE = 666;

  let totalSec = parseInt($length.value, 10) * 60;
  let remaining = totalSec;
  let interval = null;
  let running = false;

  render();

  $length.addEventListener('change', () => {
    if (running) return;
    totalSec = parseInt($length.value, 10) * 60;
    remaining = totalSec;
    render();
  });

  $start.addEventListener('click', start);
  $pause.addEventListener('click', pause);
  $reset.addEventListener('click', reset);

  function start() {
    if (running) return;
    running = true;
    $start.disabled = true;
    $pause.disabled = false;
    interval = setInterval(tick, 1000);
  }

  function pause() {
    running = false;
    $start.disabled = false;
    $pause.disabled = true;
    clearInterval(interval);
  }

  function reset() {
    pause();
    totalSec = parseInt($length.value, 10) * 60;
    remaining = totalSec;
    render();
  }

  function tick() {
    remaining -= 1;
    if (remaining <= 0) {
      remaining = 0;
      render();
      complete();
      return;
    }
    render();
  }

  function render() {
    const m = String(Math.floor(remaining / 60)).padStart(2, '0');
    const s = String(remaining % 60).padStart(2, '0');
    $time.textContent = `${m}:${s}`;
    const ratio = remaining / totalSec;
    $fg.style.strokeDashoffset = (RING_CIRCUMFERENCE * (1 - ratio)).toFixed(1);
  }

  async function complete() {
    pause();
    // friendly notification
    if ('Notification' in window && Notification.permission === 'granted') {
      new Notification('Pomodoro complete — take a break.');
    }
    // Log the session
    try {
      await fetch('/app/study/session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          subject_id: $subj.value || null,
          duration_min: Math.round(totalSec / 60),
          focus_score: 8,
          notes: 'Pomodoro completed',
        }),
      });
      // Flash visual feedback
      const card = $time.closest('.pomodoro');
      card.style.boxShadow = '0 0 80px rgba(168,85,247,0.5)';
      setTimeout(() => (card.style.boxShadow = ''), 1800);
    } catch (e) { console.warn(e); }
    reset();
  }

  // Ask for notification permission early.
  if ('Notification' in window && Notification.permission === 'default') {
    Notification.requestPermission();
  }
})();
