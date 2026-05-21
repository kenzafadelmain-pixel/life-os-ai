/* LIFE OS AI — shared app-shell JS
   Loaded on every page. Keep this lean — feature pages have their own bundles. */

(function () {
  'use strict';

  // ---- Aurora launcher — go to chat (or open mini-composer if already on it)
  const launcher = document.getElementById('aurora-launcher-btn');
  if (launcher) {
    launcher.addEventListener('click', () => {
      window.location.href = '/app/chat/';
    });
  }

  // ---- ⌘K / Ctrl+K — quick jump to chat
  document.addEventListener('keydown', (e) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      window.location.href = '/app/chat/';
    }
  });

  // ---- Auto-dismiss flashes after 5s
  document.querySelectorAll('.flash').forEach((el) => {
    setTimeout(() => {
      el.style.transition = 'opacity 0.4s, transform 0.4s';
      el.style.opacity = '0';
      el.style.transform = 'translateY(-6px)';
      setTimeout(() => el.remove(), 400);
    }, 5000);
  });

  // ---- Soft page-fade on internal nav clicks
  document.querySelectorAll('a[href^="/"]').forEach((a) => {
    a.addEventListener('click', (e) => {
      // Skip modifier-clicks, new-tab clicks, anchors, downloads.
      if (e.metaKey || e.ctrlKey || e.shiftKey || a.target === '_blank') return;
      if (a.getAttribute('href').startsWith('#')) return;
      const main = document.querySelector('.main');
      if (main) main.style.opacity = '0.7';
    });
  });
})();
