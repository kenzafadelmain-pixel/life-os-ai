"""
AIChatbot
=========

A single class with multiple back-ends:

* `DeepSeekBackend` — uses the DeepSeek chat-completions REST API
  (OpenAI-compatible). Preferred default when a key is configured.
* `OpenAIBackend`   — uses the OpenAI chat-completions REST API.
* `GeminiBackend`   — uses the Gemini `generateContent` REST API.
* `LocalIntelligenceEngine` — deterministic offline fallback so the demo
  always *works*, even with no API key configured.

The route layer only ever talks to `AIChatbot`; the backend is selected
at construction time based on which API key is available.
"""
from __future__ import annotations

import json
import os
import random
import re
import time
import urllib.error
import urllib.request
from abc import ABC, abstractmethod
from typing import Optional

SYSTEM_PROMPT = """\
You are Aurora, the AI core of LIFE OS — a futuristic operating system for
human life. You help the user with productivity, studies, mental wellbeing,
and clear thinking. Be concise, warm, and practical. Use Markdown for
structure. Address the user by their name when known. Never invent facts
about the user; only use what they have shared.
"""


# ---------------------------------------------------------------- backends
class _Backend(ABC):
    name: str = "base"

    @abstractmethod
    def chat(self, messages: list[dict], system: str) -> str: ...


class LocalIntelligenceEngine(_Backend):
    """
    Offline fallback. Uses simple templates + keyword routing.

    It's intentionally narrow: the demo works without a network, but the
    *real* magic kicks in as soon as an API key is configured.
    """

    name = "local"

    TEMPLATES = {
        "greeting": [
            "Hey {name} — Aurora here. What's the first thing on your mind today?",
            "Welcome back, {name}. Let's make the next hour count. What are we tackling?",
        ],
        "study": [
            "Let's break it into **three 50-minute Pomodoros** with 10-minute breaks. "
            "Open one tab, silence notifications, and start with the topic you're most avoiding.",
        ],
        "stress": [
            "Take 4 slow breaths — in for 4, hold for 4, out for 6. "
            "Then write down the *one* thing you can act on in the next 20 minutes. "
            "That's where momentum lives.",
        ],
        "task": [
            "Quick test: if you could only finish **one** thing today and the rest would auto-fail, "
            "which one would you pick? Start there. Everything else is noise.",
        ],
        "motivation": [
            "Discipline isn't a feeling — it's the *next* action. "
            "Pick the smallest possible step (open the file, write one sentence) and do only that.",
        ],
        "default": [
            "I'm with you. Tell me a bit more — what would 'progress' look like in the next hour?",
            "Got it. Let's narrow this down: what's the constraint that's slowing you the most right now?",
        ],
    }

    def chat(self, messages: list[dict], system: str) -> str:
        last_user = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        text = last_user.lower()
        name_match = re.search(r"name:\s*([A-Za-z ]+)", system)
        name = name_match.group(1).split()[0] if name_match else "friend"

        # crude keyword routing
        if any(w in text for w in ("hi", "hello", "hey", "yo ", "morning")):
            bucket = "greeting"
        elif any(w in text for w in ("study", "exam", "revise", "learn")):
            bucket = "study"
        elif any(w in text for w in ("stress", "anxious", "overwhelm", "panic", "burnout")):
            bucket = "stress"
        elif any(w in text for w in ("task", "todo", "deadline", "plan")):
            bucket = "task"
        elif any(w in text for w in ("motivat", "tired", "lazy", "procrast")):
            bucket = "motivation"
        else:
            bucket = "default"

        return random.choice(self.TEMPLATES[bucket]).format(name=name)


class OpenAIBackend(_Backend):
    name = "openai"
    URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def chat(self, messages: list[dict], system: str) -> str:
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}] + messages,
            "temperature": 0.7,
            "max_tokens": 600,
        }
        req = urllib.request.Request(
            self.URL,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            return payload["choices"][0]["message"]["content"].strip()
        except (urllib.error.URLError, KeyError, json.JSONDecodeError) as exc:
            return f"_[OpenAI request failed: {exc}. Falling back to local response.]_"


class DeepSeekBackend(_Backend):
    """
    DeepSeek chat backend.

    DeepSeek exposes an OpenAI-compatible REST API, so the request/response
    shape is identical to OpenAI's — only the base URL and model name change.
    See https://api-docs.deepseek.com for the latest reference.
    """

    name = "deepseek"
    URL = "https://api.deepseek.com/chat/completions"

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def chat(self, messages: list[dict], system: str) -> str:
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}] + messages,
            "temperature": 0.7,
            "max_tokens": 600,
            "stream": False,
        }
        req = urllib.request.Request(
            self.URL,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            return payload["choices"][0]["message"]["content"].strip()
        except urllib.error.HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", errors="ignore")[:240]
            except Exception:
                detail = ""
            return f"_[DeepSeek HTTP {exc.code}: {detail}. Falling back to local response.]_"
        except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError) as exc:
            return f"_[DeepSeek request failed: {exc}. Falling back to local response.]_"


class GeminiBackend(_Backend):
    name = "gemini"
    URL_TMPL = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        "{model}:generateContent?key={key}"
    )

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def chat(self, messages: list[dict], system: str) -> str:
        history = "\n".join(f"{m['role'].title()}: {m['content']}" for m in messages)
        prompt = f"{system}\n\nConversation so far:\n{history}\n\nAssistant:"
        body = {"contents": [{"parts": [{"text": prompt}]}]}
        url = self.URL_TMPL.format(model=self.model, key=self.api_key)
        req = urllib.request.Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            return payload["candidates"][0]["content"]["parts"][0]["text"].strip()
        except (urllib.error.URLError, KeyError, IndexError, json.JSONDecodeError) as exc:
            return f"_[Gemini request failed: {exc}. Falling back to local response.]_"


# ---------------------------------------------------------------- facade
class AIChatbot:
    """Public-facing chat service used by routes."""

    def __init__(self, openai_key: str = "", gemini_key: str = "",
                 deepseek_key: str = "",
                 openai_model: str = "gpt-4o-mini",
                 gemini_model: str = "gemini-1.5-flash",
                 deepseek_model: str = "deepseek-chat"):
        self.local = LocalIntelligenceEngine()
        # Selection priority: DeepSeek → OpenAI → Gemini → Local.
        if deepseek_key:
            self.backend: _Backend = DeepSeekBackend(deepseek_key, deepseek_model)
        elif openai_key:
            self.backend = OpenAIBackend(openai_key, openai_model)
        elif gemini_key:
            self.backend = GeminiBackend(gemini_key, gemini_model)
        else:
            self.backend = self.local

    @property
    def provider(self) -> str:
        return self.backend.name

    def reply(
        self,
        history: list[dict],
        user_profile: Optional[dict] = None,
        memory_context: str = "",
    ) -> str:
        """Generate a single assistant reply for the given chat history."""
        sys_prompt = SYSTEM_PROMPT
        if user_profile:
            sys_prompt += f"\n\nUser profile — name: {user_profile.get('name','friend')}."
        if memory_context:
            sys_prompt += f"\n\nLong-term memory:\n{memory_context}"

        try:
            answer = self.backend.chat(history, sys_prompt)
            if not answer or answer.startswith("_["):
                local = self.local.chat(history, sys_prompt)
                return f"{answer}\n\n{local}" if answer else local
            return answer
        except Exception as exc:
            return f"_[AI error: {exc}.]_ {self.local.chat(history, sys_prompt)}"

    def summarise_title(self, first_message: str) -> str:
        """Produce a short title for a new chat session."""
        text = first_message.strip().replace("\n", " ")
        return (text[:48] + "…") if len(text) > 48 else (text or "New conversation")
   
