/* Chat page — message send, typing animation, voice in/out, markdown render. */
(function () {
  'use strict';

  const $messages = document.getElementById('messages');
  const $input    = document.getElementById('composer-input');
  const $send     = document.getElementById('send-btn');
  const $mic      = document.getElementById('mic-btn');
  if (!$messages || !$input || !$send) return;

  // ---- Render any server-rendered markdown bubbles ---------------------
  document.querySelectorAll('[data-md]').forEach((el) => {
    if (window.marked) el.innerHTML = window.marked.parse(el.textContent || '');
  });
  scrollToEnd();

  // ---- Send ------------------------------------------------------------
  $send.addEventListener('click', sendMessage);
  $input.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
  $input.addEventListener('input', () => {
    // autosize
    $input.style.height = 'auto';
    $input.style.height = Math.min(140, $input.scrollHeight) + 'px';
  });

  async function sendMessage() {
    const text = $input.value.trim();
    if (!text) return;

    appendMessage('user', text);
    $input.value = '';
    $input.style.height = 'auto';
    const typing = appendTyping();

    try {
      const resp = await fetch('/app/chat/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          session_id: $messages.dataset.sessionId || null,
        }),
      });
      const data = await resp.json();

      typing.remove();

      if (data.error) {
        appendMessage('assistant', `_Error: ${data.error}_`);
      } else {
        appendMessage('assistant', data.answer);
        $messages.dataset.sessionId = String(data.session_id);
        const pill = document.getElementById('provider-pill');
        if (pill && data.provider) pill.textContent = data.provider;
        // If we *just* created a session, refresh sidebar.
        if (!new URL(window.location.href).searchParams.get('session')) {
          // bump URL silently so future reloads land on the same chat
          const url = new URL(window.location.href);
          url.searchParams.set('session', data.session_id);
          window.history.replaceState({}, '', url);
        }
      }
    } catch (e) {
      typing.remove();
      appendMessage('assistant', '_Connection error. Try again._');
    }
  }

  function appendMessage(role, text) {
    const wrap = document.createElement('div');
    wrap.className = `message ${role}`;
    const who = document.createElement('div');
    who.className = 'who';
    who.textContent = role === 'assistant' ? 'A' : 'Y';
    const bubble = document.createElement('div');
    bubble.className = 'bubble';
    bubble.innerHTML = window.marked ? window.marked.parse(text) : escapeHtml(text);
    wrap.appendChild(who); wrap.appendChild(bubble);
    $messages.appendChild(wrap);
    scrollToEnd();
    return wrap;
  }

  function appendTyping() {
    const wrap = document.createElement('div');
    wrap.className = 'message assistant';
    wrap.innerHTML = `
      <div class="who">A</div>
      <div class="bubble">
        <span class="typing"><span></span><span></span><span></span></span>
      </div>
    `;
    $messages.appendChild(wrap);
    scrollToEnd();
    return wrap;
  }

  function scrollToEnd() {
    $messages.scrollTop = $messages.scrollHeight;
  }

  function escapeHtml(s) {
    return s.replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
  }

  // ---- Voice input (Web Speech API) ----------------------------------
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  let recognition = null;
  if (SR && $mic) {
    recognition = new SR();
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.lang = navigator.language || 'en-US';

    $mic.addEventListener('click', () => {
      if ($mic.classList.contains('recording')) {
        recognition.stop();
      } else {
        try { recognition.start(); $mic.classList.add('recording'); }
        catch (e) { console.warn(e); }
      }
    });

    recognition.addEventListener('result', (ev) => {
      const transcript = Array.from(ev.results)
        .map((r) => r[0].transcript)
        .join('');
      $input.value = transcript;
    });
    recognition.addEventListener('end', () => $mic.classList.remove('recording'));
    recognition.addEventListener('error', () => $mic.classList.remove('recording'));
  } else if ($mic) {
    $mic.title = 'Voice not supported in this browser';
    $mic.style.opacity = '0.5';
    $mic.disabled = true;
  }
})();
