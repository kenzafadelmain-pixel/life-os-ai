/* Landing-page interactions:
   - reveal-on-scroll for sections
   - subtle parallax on the orbital visual
*/
(function () {
  'use strict';

  // Reveal-on-scroll
  const candidates = document.querySelectorAll(
    '.hero-left, .hero-right, .feature, .voice, .metric-card, .cta-card, .section-head'
  );
  candidates.forEach((el) => el.classList.add('reveal'));

  const io = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add('in');
          io.unobserve(e.target);
        }
      });
    },
    { threshold: 0.12 }
  );
  candidates.forEach((el) => io.observe(el));

  // Parallax orbital (very subtle)
  const orbital = document.querySelector('.orbital');
  if (orbital && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    window.addEventListener('mousemove', (e) => {
      const x = (e.clientX / window.innerWidth - 0.5) * 16;
      const y = (e.clientY / window.innerHeight - 0.5) * 16;
      orbital.style.transform = `translate(${x}px, ${y}px)`;
    });
  }
})();
