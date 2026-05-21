"""
EmotionDetector
===============

A lightweight, dependency-free sentiment + emotion classifier used by the
mood-journal feature. It deliberately avoids heavyweight NLP libraries so the
project runs anywhere Python runs — but the interface is identical to what
you'd swap in (VADER, transformers, etc.) later.

The detector returns:
    {
        "sentiment": float in [-1, 1],
        "emotion":   one of {"happy","calm","sad","anxious","angry","tired","motivated","neutral"},
        "stress":    int 1..10,
        "motivation":int 1..10,
        "summary":   str — short supportive reflection
    }
"""
from __future__ import annotations

import re
from collections import Counter

POSITIVE = {
    "great", "good", "happy", "awesome", "amazing", "love", "calm", "peaceful",
    "excited", "proud", "grateful", "confident", "energetic", "focused", "win",
    "accomplished", "ok", "okay", "joy", "joyful", "smile", "fun", "fine",
    "productive", "rested", "balanced", "hope", "hopeful", "inspired",
}
NEGATIVE = {
    "bad", "sad", "tired", "angry", "anxious", "worried", "stress", "stressed",
    "overwhelmed", "depressed", "lonely", "afraid", "scared", "fail", "failed",
    "hate", "panic", "burnt", "burnout", "hopeless", "exhausted", "down",
    "frustrat", "annoyed", "guilty", "ashamed", "cry", "crying", "hurt",
}
INTENSIFIERS = {"very", "really", "extremely", "so", "super", "deeply", "completely"}
NEGATIONS   = {"not", "no", "never", "without", "barely", "hardly"}

EMOTION_HINTS = {
    "happy":     {"happy", "joy", "joyful", "excited", "grateful", "smile", "fun"},
    "calm":      {"calm", "peaceful", "rested", "balanced", "ok", "okay", "fine"},
    "sad":       {"sad", "lonely", "down", "cry", "hurt", "depressed"},
    "anxious":   {"anxious", "worried", "panic", "scared", "afraid", "stress", "stressed"},
    "angry":     {"angry", "annoyed", "frustrat", "hate"},
    "tired":     {"tired", "exhausted", "burnt", "burnout", "sleepy"},
    "motivated": {"motivated", "inspired", "focused", "productive", "confident", "win"},
}

SUPPORTIVE_REPLIES = {
    "happy":     "Beautiful — name what specifically lit you up. Repeat the conditions tomorrow.",
    "calm":      "This is a great state to plan from. Pick one meaningful task while clarity is here.",
    "sad":       "What you're feeling is valid. Try one small, kind thing for yourself in the next hour.",
    "anxious":   "Breathe. 4-4-6. Write the worry down and the *next* tiny action you can control.",
    "angry":     "Step away from any decision for 20 minutes. Energy is real — channel it into a quick walk or workout.",
    "tired":     "Recovery isn't optional. Plan a real break or earlier sleep tonight — not 'maybe', but on the calendar.",
    "motivated": "Catch the wave. Pick the highest-leverage task and start before the feeling fades.",
    "neutral":   "Steady is good. Pick one tiny win for the next hour to build forward momentum.",
}


class EmotionDetector:
    """Stateless analyzer — instantiate once and reuse."""

    WORD_RE = re.compile(r"[A-Za-z']+")

    def analyse(self, text: str) -> dict:
        text = (text or "").strip()
        if not text:
            return {
                "sentiment": 0.0, "emotion": "neutral",
                "stress": 5, "motivation": 5,
                "summary": "Write a few sentences and I'll reflect them back to you.",
            }

        tokens = [t.lower() for t in self.WORD_RE.findall(text)]
        score = 0.0
        emotion_counts: Counter = Counter()

        for i, tok in enumerate(tokens):
            weight = 1.0
            prev = tokens[i - 1] if i > 0 else ""
            if prev in INTENSIFIERS:
                weight = 1.6
            negated = prev in NEGATIONS

            if tok in POSITIVE or any(tok.startswith(p) for p in POSITIVE):
                score += -weight if negated else weight
            elif tok in NEGATIVE or any(tok.startswith(n) for n in NEGATIVE):
                score += weight if negated else -weight

            for emo, words in EMOTION_HINTS.items():
                if tok in words or any(tok.startswith(w) for w in words):
                    emotion_counts[emo] += 1

        # Normalise sentiment to [-1, 1]
        n = max(len(tokens), 1)
        sentiment = max(-1.0, min(1.0, score / (n ** 0.5)))

        emotion = emotion_counts.most_common(1)[0][0] if emotion_counts else (
            "happy" if sentiment > 0.25 else
            "sad"   if sentiment < -0.25 else
            "neutral"
        )

        # Stress + motivation derived from sentiment + emotion
        stress_base = 5 - int(round(sentiment * 4))
        if emotion in ("anxious", "angry", "tired"):
            stress_base += 2
        stress = max(1, min(10, stress_base))

        motivation_base = 5 + int(round(sentiment * 4))
        if emotion == "motivated":
            motivation_base += 2
        if emotion in ("tired", "sad"):
            motivation_base -= 2
        motivation = max(1, min(10, motivation_base))

        return {
            "sentiment": round(sentiment, 2),
            "emotion": emotion,
            "stress": stress,
            "motivation": motivation,
            "summary": SUPPORTIVE_REPLIES.get(emotion, SUPPORTIVE_REPLIES["neutral"]),
        }
