/* Task board — drag & drop between columns. */
(function () {
  'use strict';

  const board = document.getElementById('task-board');
  if (!board) return;

  let dragged = null;

  board.querySelectorAll('.task-card').forEach((card) => bindCard(card));
  board.querySelectorAll('.task-column').forEach((col) => bindColumn(col));

  function bindCard(card) {
    card.addEventListener('dragstart', () => {
      dragged = card;
      card.classList.add('dragging');
    });
    card.addEventListener('dragend', () => {
      card.classList.remove('dragging');
      dragged = null;
    });
  }

  function bindColumn(col) {
    col.addEventListener('dragover', (e) => {
      e.preventDefault();
      col.style.borderColor = 'rgba(34,211,238,0.4)';
    });
    col.addEventListener('dragleave', () => {
      col.style.borderColor = '';
    });
    col.addEventListener('drop', async (e) => {
      e.preventDefault();
      col.style.borderColor = '';
      if (!dragged) return;
      const taskId = dragged.dataset.taskId;
      const newStatus = col.dataset.status;
      if (dragged.dataset.status === newStatus) return;

      // Optimistic UI
      col.appendChild(dragged);
      dragged.dataset.status = newStatus;

      try {
        const resp = await fetch(`/app/tasks/${taskId}/status`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: newStatus }),
        });
        const data = await resp.json();
        if (data.stats) updateCounts(data.stats);
      } catch (err) {
        console.error(err);
      }
    });
  }

  function updateCounts(stats) {
    const map = {
      todo: stats.todo, doing: stats.doing, done: stats.done,
    };
    document.querySelectorAll('.task-column').forEach((col) => {
      const c = col.querySelector('.count');
      if (c) c.textContent = map[col.dataset.status] ?? c.textContent;
    });
  }
})();
