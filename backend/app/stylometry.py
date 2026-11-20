"""Deterministic stylometry: a measurable writing fingerprint per channel.

The LLM never decides what "sounds like Eleni". These numbers do: they are
computed from what the owner actually wrote, shown in the persona dashboard,
fed to the generator as hard style rules, and reused as a fidelity metric.
"""
from __future__ import annotations

import math
import re
import statistics
import unicodedata
from collections import Counter
from typing import Iterable

EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF\U0001F900-\U0001F9FF⭐✅]"
)
WORD_RE = re.compile(r"[\wάέήίόύώϊϋΐΰ']+", re.UNICODE)
SENT_SPLIT = re.compile(r"(?<=[.!?;…])\s+|\n+")
GREEK_RE = re.compile(r"[Ͱ-Ͽἀ-῿]")
LATIN_RE = re.compile(r"[A-Za-z]")

FEATURES = [
    ("words", "Λέξεις ανά μήνυμα"),
    ("sent_len", "Λέξεις ανά πρόταση"),
    ("greek_ratio", "Ελληνικά έναντι αγγλικών"),
    ("emoji_rate", "Emoji ανά 100 λέξεις"),
    ("exclaim_rate", "Θαυμαστικά ανά πρόταση"),
    ("question_rate", "Ερωτήσεις ανά πρόταση"),
    ("bullet_ratio", "Γραμμές σε λίστα"),
    ("lower_start", "Ξεκινά με μικρά"),
    ("word_len", "Μέσο μήκος λέξης"),
]

# Typical spread used when a channel has too few samples to estimate one.
DEFAULT_SPREAD = {
    "words": 25.0, "sent_len": 4.0, "greek_ratio": 0.25, "emoji_rate": 1.5, "exclaim_rate": 0.2,
    "question_rate": 0.2, "bullet_ratio": 0.15, "lower_start": 0.35, "word_len": 0.6,
}

STOP = set(
    "the a an and or but to of in on for with is are be it this that we i you my our your at as by from "
    "so if not no yes do just can will was have has had me us they them he she its it's i'm".split()
) | set("και να το τα η ο οι την της του των σε με για που δεν θα από στο στη στην είναι ένα μια αν πιο".split())

# Informal markers that count as signature words on their own.
MARKERS = {"tbh", "πλιζ", "παμε", "οκ", "ok", "lol", "btw", "imo", "fyi", "deal", "τελειο", "ναιιι", "sorry"}

CHANNEL_LABELS = {
    "email_external": "Email προς τα έξω",
    "email_internal": "Email σε συναδέλφους",
    "chat_team": "Chat ομάδας",
    "chat_personal": "Προσωπικό chat",
    "note": "Προσωπικές σημειώσεις",
    "doc": "Έγγραφα",
}


def features(text: str) -> dict[str, float]:
    words = WORD_RE.findall(text)
    n_words = max(len(words), 1)
    sentences = [s for s in SENT_SPLIT.split(text) if WORD_RE.search(s)]
    n_sent = max(len(sentences), 1)
    lines = [ln for ln in text.splitlines() if ln.strip()]
    greek = len(GREEK_RE.findall(text))
    latin = len(LATIN_RE.findall(text))
    first_alpha = next((c for c in text if c.isalpha()), "")
    bullets = sum(1 for ln in lines if re.match(r"^\s*(?:[-*•]|\d+[.)])\s+", ln))
    return {
        "words": float(len(words)),
        "sent_len": len(words) / n_sent,
        "greek_ratio": greek / max(greek + latin, 1),
        "emoji_rate": 100.0 * len(EMOJI_RE.findall(text)) / n_words,
        "exclaim_rate": text.count("!") / n_sent,
        "question_rate": (text.count("?") + text.count(";") * (1 if greek > latin else 0)) / n_sent,
        "bullet_ratio": bullets / max(len(lines), 1),
        "lower_start": 1.0 if first_alpha and first_alpha.islower() else 0.0,
        "word_len": sum(len(w) for w in words) / n_words,
    }


def _first_line(text: str) -> str | None:
    line = text.strip().splitlines()[0].strip() if text.strip() else ""
    if 0 < len(line.split()) <= 4 and line.endswith((",", "!")):
        return re.sub(r"\s+", " ", line)
    return None


def _signoff(text: str) -> str | None:
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if len(lines) < 3:
        return None
    last = lines[-1]
    if len(last.split()) <= 2 and len(last) <= 20:
        prev = lines[-2]
        if len(prev.split()) <= 3 and prev.endswith((",", "!")):
            return f"{prev} / {last}"
        return last
    return None


def _generalise_greeting(g: str) -> str:
    # "Hi Peter," -> "Hi <name>,"
    parts = g.split()
    if len(parts) >= 2 and parts[1][0].isupper():
        return parts[0] + " <name>" + ("," if g.endswith(",") else "!")
    return g


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _grams(text: str) -> set[str]:
    toks = [w.lower() for w in WORD_RE.findall(text)]
    out = set()
    for n in (1, 2, 3):
        for i in range(len(toks) - n + 1):
            gram = toks[i:i + n]
            if gram[0] in STOP or gram[-1] in STOP or any(len(g) < 2 or g.isdigit() for g in gram):
                continue
            if n == 1 and _fold(gram[0]) not in MARKERS:
                continue
            out.add(" ".join(gram))
    return out


def signature_phrases(texts: list[str], top: int = 10, background: list[str] | None = None) -> list[dict]:
    """Expressions the owner uses across several messages, and much more often than other people do."""
    own: Counter = Counter()
    for t in texts:
        own.update(_grams(t))
    bg: Counter = Counter()
    for t in background or []:
        bg.update(_grams(t))
    n_own, n_bg = max(len(texts), 1), max(len(background or []), 1)
    scored = []
    for g, c in own.items():
        if c < 2:
            continue
        ratio = (c / n_own) / ((bg.get(g, 0) + 0.5) / n_bg)
        if background and ratio < 2.5:
            continue
        length_bonus = 1 + 0.5 * (len(g.split()) - 1)
        scored.append((c * length_bonus * min(ratio, 8) ** 0.5, g, c))
    scored.sort(key=lambda x: (-x[0], x[1]))
    kept: list[tuple[str, int]] = []
    for _, g, c in scored:
        if any(g in k or k in g for k, _ in kept):
            continue
        kept.append((g, c))
        if len(kept) >= top:
            break
    return [{"phrase": g, "messages": c} for g, c in kept]


def channel_profile(texts: list[str], background: list[str] | None = None) -> dict:
    feats = [features(t) for t in texts if t.strip()]
    if not feats:
        return {}
    mean = {k: statistics.fmean(f[k] for f in feats) for k, _ in FEATURES}
    spread = {}
    for k, _ in FEATURES:
        vals = [f[k] for f in feats]
        sd = statistics.pstdev(vals) if len(vals) > 1 else 0.0
        spread[k] = max(sd, DEFAULT_SPREAD[k] * 0.5)
    greetings = Counter(_generalise_greeting(g) for g in (_first_line(t) for t in texts) if g)
    signoffs = Counter(s for s in (_signoff(t) for t in texts) if s)
    emojis = Counter(e for t in texts for e in EMOJI_RE.findall(t))
    return {
        "samples": len(feats),
        "mean": {k: round(v, 3) for k, v in mean.items()},
        "spread": {k: round(v, 3) for k, v in spread.items()},
        "greetings": [g for g, _ in greetings.most_common(4)],
        "signoffs": [s for s, _ in signoffs.most_common(4)],
        "emojis": [e for e, _ in emojis.most_common(6)],
        "phrases": signature_phrases(texts, top=8, background=background),
    }


def build_style(owner_items: Iterable[dict], other_items: Iterable[dict] = ()) -> dict:
    by_channel: dict[str, list[str]] = {}
    for it in owner_items:
        by_channel.setdefault(it["channel"], []).append(it["text"])
    background = [it["text"] for it in other_items]
    channels = {ch: channel_profile(txts, background) for ch, txts in by_channel.items() if txts}
    message_texts = [t for ch, txts in by_channel.items() if ch != "doc" for t in txts]
    return {
        "channels": {k: v for k, v in channels.items() if v},
        "channel_labels": CHANNEL_LABELS,
        "feature_labels": dict(FEATURES),
        "signature_phrases": signature_phrases(message_texts, top=14, background=background),
    }


def similarity(text: str, channel_style: dict) -> float:
    """0-100: how close a text's fingerprint is to the owner's channel fingerprint."""
    if not channel_style or not text.strip():
        return 0.0
    f = features(text)
    mean, spread = channel_style["mean"], channel_style["spread"]
    # 'words' depends a lot on the message, so it gets a lower weight.
    weights = {"words": 0.5, "greek_ratio": 1.6, "emoji_rate": 1.2, "lower_start": 1.0}
    total_w, total = 0.0, 0.0
    for k, _ in FEATURES:
        w = weights.get(k, 1.0)
        z = abs(f[k] - mean[k]) / (spread[k] or 1.0)
        total += w * math.exp(-0.5 * z * z)
        total_w += w
    score = total / total_w
    # greeting / sign-off conventions
    bonus_checks = 0
    bonus = 0.0
    g = _first_line(text)
    if channel_style.get("greetings"):
        bonus_checks += 1
        if g and _generalise_greeting(g) in channel_style["greetings"]:
            bonus += 1
    s = _signoff(text)
    if channel_style.get("signoffs"):
        bonus_checks += 1
        if s and any(_fold(s.split(" / ")[-1]) == _fold(x.split(" / ")[-1]) for x in channel_style["signoffs"]):
            bonus += 1
    if bonus_checks:
        score = 0.8 * score + 0.2 * (bonus / bonus_checks)
    return round(100 * score, 1)


def describe_rules(channel_style: dict, labels: dict | None = None) -> list[str]:
    """Human-readable style rules derived from the numbers (also sent to the LLM)."""
    if not channel_style:
        return []
    m = channel_style["mean"]
    rules = []
    words = m["words"]
    rules.append(f"Μήκος: περίπου {int(round(words, -1)) or int(words)} λέξεις· προτάσεις ~{m['sent_len']:.0f} λέξεων.")
    gr = m["greek_ratio"]
    if gr > 0.7:
        rules.append("Γλώσσα: γράφει κυρίως ελληνικά, κρατά τους αγγλικούς τεχνικούς όρους όπως είναι.")
    elif gr > 0.25:
        rules.append(f"Γλώσσα: ανακατεύει ελληνικά και αγγλικά (~{gr:.0%} ελληνικοί χαρακτήρες), π.χ. ελληνικός χαιρετισμός + αγγλικό κείμενο.")
    else:
        rules.append("Γλώσσα: γράφει στα αγγλικά.")
    if m["lower_start"] > 0.6:
        rules.append("Συχνά ξεκινά με μικρά, χαλαρή στίξη.")
    if m["emoji_rate"] > 0.8:
        emo = " ".join(channel_style.get("emojis", [])[:4])
        rules.append(f"Χρησιμοποιεί συχνά emoji (~{m['emoji_rate']:.1f} ανά 100 λέξεις): {emo}")
    elif m["emoji_rate"] < 0.2:
        rules.append("Χωρίς emoji.")
    if m["bullet_ratio"] > 0.15:
        rules.append("Οργανώνει τα επιχειρήματα σε σύντομες λίστες.")
    if m["question_rate"] > 0.15:
        rules.append("Συνήθως κλείνει με μία συγκεκριμένη ερώτηση για να προχωρήσει το θέμα.")
    if channel_style.get("greetings"):
        rules.append("Χαιρετισμός: " + " | ".join(channel_style["greetings"][:3]))
    if channel_style.get("signoffs"):
        rules.append("Υπογραφή: " + " | ".join(channel_style["signoffs"][:3]))
    return rules
