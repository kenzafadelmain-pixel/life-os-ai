/* Files page — fetch and display AI-generated flashcards in a modal. */
function loadFlashcards(fileId, name) {
  const modal = document.getElementById('flash-modal');
  const title = document.getElementById('flash-title');
  const cards = document.getElementById('flash-cards');

  title.textContent = name;
  cards.innerHTML = '<p class="muted">Generating flashcards…</p>';
  modal.classList.add('open');

  fetch(`/app/files/${fileId}/flashcards`)
    .then((r) => r.json())
    .then((data) => {
      if (!data.cards || !data.cards.length) {
        cards.innerHTML = '<p class="muted">Not enough text to extract flashcards. Try a richer PDF.</p>';
        return;
      }
      cards.innerHTML = '';
      data.cards.forEach((c, i) => {
        const el = document.createElement('div');
        el.className = 'card';
        el.style.padding = '1rem 1.2rem';
        el.style.cursor = 'pointer';
        el.innerHTML = `
          <div class="mono muted" style="font-size:0.7rem; letter-spacing:0.16em; text-transform:uppercase;">
            card ${i + 1} / ${data.cards.length}
          </div>
          <div class="front" style="font-family:var(--font-display); font-size:1.05rem; margin:0.4rem 0;">
            ${escapeHtml(c.front)}
          </div>
          <div class="back" style="display:none; color: var(--cyan); font-weight: 600;">
            ${escapeHtml(c.back)}
          </div>
          <div class="muted mono" style="font-size:0.72rem; margin-top:0.4rem;">click to flip</div>
        `;
        el.addEventListener('click', () => {
          const back = el.querySelector('.back');
          back.style.display = back.style.display === 'none' ? 'block' : 'none';
        });
        cards.appendChild(el);
      });
    })
    .catch(() => {
      cards.innerHTML = '<p class="muted" style="color: var(--coral);">Couldn\'t load flashcards.</p>';
    });
}

function escapeHtml(s) {
  return String(s).replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}
