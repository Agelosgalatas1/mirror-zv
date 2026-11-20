# Επεξήγηση: Παράγει απαντήσεις, προσχέδια και προτάσεις αποφάσεων με το επιτρεπόμενο προφίλ και τα σχετικά τεκμήρια.
"""The twin itself: Ask, Write and Decide, each returning an explanation.

Every answer comes back with the traits and memories it relied on, a
confidence, a measured style-match score and an "unsure" flag, so the owner
can see *why* the twin said what it said.
"""
from __future__ import annotations

import math
import re
import time
from typing import Any

from . import db, prompts, sharing, verified_chat
from .ingest.pipeline import get_owner
from .llm import LLM_CLIENT, LLMUnavailable
from .context import pid
from .privacy import DEFAULT_BOUNDARIES, check_boundaries
from .profile import for_twin as current_profile
from .profile import trait_index
from .retrieval import INDEX, Hit, tokenize
from .stylometry import CHANNEL_LABELS, describe_rules, similarity

CHANNELS = list(CHANNEL_LABELS)
# Item ids hidden from the twin while an evaluation runs on them (auto hold-out for own data).
EXCLUDE: set[str] = set()


class TwinNotReady(RuntimeError):
    pass


# ------------------------------------------------------------------ context building

def _profile() -> dict:
    prof = current_profile()
    if not prof:
        raise TwinNotReady("Το twin δεν έχει ακόμα persona model. Πρόσθεσε δεδομένα και χτίσε πρώτα το προφίλ.")
    return prof


def persona_digest(prof: dict) -> str:
    def lines(sec: str, key: str = "text", limit: int = 30) -> str:
        out = []
        for t in prof.get(sec, [])[:limit]:
            extra = ""
            if sec == "decision_rules" and t.get("when"):
                extra = f"  [applies when: {t['when']}]"
            if sec == "relationships":
                out.append(f"- {t['id']}: {t.get('name')} ({t.get('role', '')}) — {t.get('relation', '')}")
                continue
            src = t.get("inherited_from")
            tag = f" [INHERITED from {src['name']}, {src['role']}: company rule, overrides personal rules]" if src else ""
            out.append(f"- {t['id']}{tag}: {t.get(key) or t.get('text')}{extra} (confidence {t.get('confidence', 0):.2f})")
        return "\n".join(out) or "- (none)"

    return "\n".join([
        f"Summary: {prof.get('summary', '')}",
        "\nVALUES\n" + lines("values", limit=40),
        "\nDECISION RULES\n" + lines("decision_rules", "rule", limit=40),
        "\nPREFERENCES\n" + lines("preferences"),
        "\nKNOWLEDGE\n" + lines("knowledge", limit=30),
        "\nRELATIONSHIPS\n" + lines("relationships"),
        "\nVOICE NOTES\n" + "\n".join(f"- {v}" for v in prof.get("voice_notes", [])),
        "\nKNOWN UNKNOWNS (topics with no opinion yet)\n" + "\n".join(f"- {u}" for u in prof.get("unknowns", [])),
    ])


def _query_vec(text: str):
    if not INDEX.has_embeddings:
        return None
    v = LLM_CLIENT.embed([text])
    return v[0] if v else None


# Επεξήγηση: Η πρόσβαση σε ιδιωτικές μνήμες μπλοκάρεται για ξένο χρήστη.
def memories(query: str, k: int = 8) -> list[Hit]:
    if sharing.restricted():
        return []
    where = (lambda it: it.get("id") not in EXCLUDE) if EXCLUDE else None
    return INDEX.search(query, k=k, query_vec=_query_vec(query), where=where)


def format_memories(hits: list[Hit]) -> str:
    out = []
    for n, h in enumerate(hits, 1):
        it = h.item
        who = "me" if it.get("is_owner") else (it.get("author") or "someone")
        meta = f"{it.get('channel', '')}, {(it.get('ts') or '')[:10]}, written by {who}"
        if it.get("subject"):
            meta += f', "{it["subject"]}"'
        out.append(f"M{n} ({meta}):\n{h.text[:1100]}")
    return "\n\n".join(out) or "(no relevant memories found)"


def format_profile_facts(prof: dict, question: str, k: int = 6) -> str:
    """Put the strongest matching, evidence-backed profile traits next to the retrieved memories."""
    lines = []
    for score, trait in _score_traits(prof, question)[:k]:
        text = _say(trait)
        trigger = trait.get("when")
        if trigger and trigger not in text:
            text += f" [applies when: {trigger}]"
        lines.append(f"- [{trait['id']} · {trait['section']} · relevance {score:.2f}] {text}")
    return "\n".join(lines) or "(no profile traits matched this question)"


def exemplars(channel: str, query: str, n: int = 4) -> list[dict]:
    if sharing.restricted():
        return []
    hits = INDEX.search(query, k=n, where=lambda it: bool(it.get("is_owner")) and it.get("channel") == channel
                        and it.get("id") not in EXCLUDE)
    seen = {h.item_id for h in hits}
    picked = [h.item for h in hits]
    if len(picked) < n:
        rows = db.query(
            "SELECT i.* FROM items i JOIN sources s ON s.id=i.source_id WHERE s.consent=1 AND i.is_owner=1 "
            "AND s.person_id=? AND i.channel=? ORDER BY length(i.text) DESC LIMIT ?", (pid(), channel, n * 3))
        for r in rows:
            if r["id"] not in seen and r["id"] not in EXCLUDE and len(picked) < n:
                picked.append(r)
                seen.add(r["id"])
    return picked


def format_exemplars(items: list[dict], name: str) -> str:
    out = []
    for i, it in enumerate(items, 1):
        ctx = (it.get("meta") or {}).get("in_reply_to_text") if isinstance(it.get("meta"), dict) else None
        block = f"Example {i}:"
        if ctx:
            block += f"\n[they wrote] {ctx[:400]}"
        block += f"\n[{name} replied]\n{it['text'][:1200]}"
        out.append(block)
    return "\n\n".join(out) or "(no examples in this channel yet)"


def _boundaries() -> list[dict]:
    return db.get_setting("boundaries", DEFAULT_BOUNDARIES)


# Επεξήγηση: Μετατρέπει τις αναφορές του AI σε πραγματικά διαθέσιμα τεκμήρια.
def _resolve_refs(out: dict, prof: dict, hits: list[Hit]) -> dict:
    tindex = trait_index(prof)
    traits = []
    for ref in out.get("trait_refs", []) or []:
        t = tindex.get(str(ref).strip())
        if t:
            traits.append({"id": t["id"], "section": t["section"],
                           "text": t.get("rule") or t.get("text") or f"{t.get('name')}: {t.get('relation')}",
                           "confidence": t.get("confidence"), "evidence": t.get("evidence", []),
                           "inherited_from": t.get("inherited_from")})
    mems = []
    for ref in out.get("memory_refs", []) or []:
        m = re.match(r"M?(\d+)", str(ref).strip())
        if m and 1 <= int(m.group(1)) <= len(hits):
            h = hits[int(m.group(1)) - 1]
            mems.append(_hit_view(h, f"M{m.group(1)}"))
    return {"traits": traits, "memories": mems}


def _hit_view(h: Hit, label: str) -> dict:
    it = h.item
    return {"ref": label, "item_id": h.item_id, "source_id": h.source_id, "snippet": h.text[:500],
            "channel": it.get("channel"), "date": (it.get("ts") or "")[:10], "subject": it.get("subject"),
            "author": "me" if it.get("is_owner") else it.get("author")}


def _style_for(prof: dict, channel: str) -> dict:
    return prof.get("style", {}).get("channels", {}).get(channel, {})


def _calibrate(llm_conf: Any, n_traits: int, n_mems: int, unsure: bool) -> float:
    try:
        c = float(llm_conf)
    except (TypeError, ValueError):
        c = 0.5
    grounding = min(1.0, 0.35 + 0.15 * n_traits + 0.1 * n_mems)
    conf = 0.65 * c + 0.35 * grounding
    if unsure:
        conf = min(conf, 0.45)
    return round(max(0.05, min(conf, 0.98)), 2)


def _boundary_reply(b: dict, name: str) -> dict:
    return {
        "answer": f"Αυτό προτιμώ να το απαντήσω εγώ προσωπικά. (Όριο: {b['label']})",
        "draft": None, "boundary": b, "unsure": True, "confidence": 1.0,
        "why": f"Ο/Η {name} έχει ορίσει το «{b['label']}» ως θέμα για το οποίο το twin δεν μιλά ποτέ.",
        "traits": [], "memories": [], "mode": "boundary",
    }


# ------------------------------------------------------------------ offline (rule-based) engine

def _overlap(a: str, b: str) -> float:
    ta, tb = set(tokenize(a)), set(tokenize(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / math.sqrt(len(ta) * len(tb))


def _best_traits(prof: dict, text: str, sections: tuple[str, ...], k: int = 3) -> list[dict]:
    scored = []
    for sec in sections:
        for t in prof.get(sec, []):
            body = " ".join(str(x) for x in [t.get("rule"), t.get("text"), t.get("when"), " ".join(t.get("prefers", []))]
                            if x)
            s = _overlap(text, body)
            if s > 0:
                scored.append((s, {**t, "section": sec}))
    scored.sort(key=lambda x: -x[0])
    return [dict(t, _score=round(s, 3)) for s, t in scored[:k]]


QSTOP = {"ποια", "ποιο", "ποιος", "ποιες", "ποιοι", "πως", "πώς", "τι", "που", "πού", "γιατι", "γιατί", "πόσο", "ποσο",
         "εισαι", "είσαι", "εχεις", "έχεις", "κανεις", "κάνεις", "την", "τον", "της", "του", "στο", "στη", "στην",
         "για", "και", "με", "να", "θα", "μας", "σου", "μου", "what", "which", "how", "why", "do", "does", "you", "your",
         "the", "is", "are", "our", "for", "to", "of", "in", "on", "we", "και", "ειναι", "είναι", "σε", "μια", "ένα",
         "ενα", "από", "απο", "τα", "το", "η", "ο", "οι", "τη", "των", "δεν", "αν", "κανουμε", "κάνουμε", "κανω", "κάνω",
         "κανει", "κάνει", "αγαπημενος", "αγαπημένος", "αγαπημενη", "αγαπημένη", "αγαπημενο", "αγαπημένο",
         "θελεις", "θέλεις", "πιστευεις", "πιστεύεις", "νομιζεις", "νομίζεις", "πες", "μου", "λιγο", "λίγο"}


def _words(text: str) -> list[str]:
    from .retrieval import _fold
    return [w for w in re.findall(r"\w+", _fold(text)) if len(w) >= 2 and w not in {_fold(x) for x in QSTOP}]


SUFFIXES = sorted(["ιες", "ιας", "οι", "ες", "ης", "ας", "ος", "ου", "ων", "εις", "ει", "ω", "α", "η", "ο", "ε", "ι", "ια", "ιο", "ιων",
                   "ους", "εσ", "ουμε", "ετε", "ουν", "ματα", "μα", "s", "es", "ing", "ed"], key=len, reverse=True)


def _stem(w: str) -> str:
    for suf in SUFFIXES:
        if w.endswith(suf) and len(w) - len(suf) >= 3:
            return w[: -len(suf)]
    return w


def _coverage(question: str, text: str) -> float:
    """Share of the question's content words found in text (exact = 1, same stem = 0.8, same prefix = 0.5)."""
    q = _words(question)
    if not q:
        return 0.0
    tw = set(_words(text))
    stems = {_stem(w) for w in tw}
    prefixes6 = {w[:6] for w in tw if len(w) >= 6}
    score = 0.0
    for w in q:
        if w in tw:
            score += 1
        elif _stem(w) in stems:
            score += 0.8
        elif len(w) >= 6 and w[:6] in prefixes6:
            score += 0.4
    return score / len(q)


def _specific_words(text: str) -> list[str]:
    """Content words used to tell a real topical match from one shared name."""
    return list(dict.fromkeys(w for w in _words(text) if len(w) >= 3))


def _supported_word_count(question: str, text: str) -> int:
    """Count distinct question terms supported by a candidate, including Greek stems."""
    target = _specific_words(question)
    words = set(_words(text))
    stems = {_stem(w) for w in words}
    prefixes = {w[:6] for w in words if len(w) >= 6}
    return sum(1 for w in target if w in words or _stem(w) in stems or (len(w) >= 6 and w[:6] in prefixes))


INTENTS = [
    ("greeting", re.compile(r"^(γεια|γειά|καλημερα|καλησπερα|χαιρετε|ελα|hey|hi|hello|yo)\b")),
    ("thanks", re.compile(r"\b(ευχαριστω|ευχαριστουμε|thanks|thank you|thx|merci)\b")),
    ("how", re.compile(r"(τι κανεις|πως εισαι|πως παει|how are you|τι γινεται)")),
    ("identity", re.compile(r"(ποια εισαι|ποιος εισαι|ποιο εισαι|who are you|τι εισαι|συστησου|πες μου για σενα)")),
    ("help", re.compile(r"(τι μπορεις να κανεις|τι ξερεις να κανεις|βοηθεια|^help$|τι να σε ρωτησω)")),
]
WHY_RE = re.compile(r"^(γιατι|why|πως ετσι|δηλαδη|σιγουρα|απο που το ξερεις|πως το ξερεις)\b")
MORE_RE = re.compile(r"^(και τι αλλο|τι αλλο|κατι αλλο|πες μου περισσοτερα|περισσοτερα|more|anything else|αλλο|και αλλο)$")


def _fold(text: str) -> str:
    from .retrieval import _fold as f
    return re.sub(r"\s+", " ", f(text)).strip(" ;?!.")


def _say(t: dict) -> str:
    """How the owner would say a trait (first person when available).

    Inherited company rules are someone else's words, so they are quoted with their source."""
    src = t.get("inherited_from")
    if src:
        return f"Κανόνας της εταιρείας από {src.get('display_name') or src.get('name')}: {t.get('rule') or t.get('text')}"
    return t.get("first_person") or t.get("rule") or t.get("text") or ""


def _trait_view(t: dict) -> dict:
    return {"id": t["id"], "section": t["section"], "text": t.get("rule") or t.get("text"),
            "confidence": t.get("confidence"), "evidence": t.get("evidence", []),
            "inherited_from": t.get("inherited_from")}


def _score_traits(prof: dict, question: str) -> list[tuple[float, dict]]:
    weights = {"knowledge": 1.15, "preferences": 1.1, "values": 0.9, "decision_rules": 0.9, "relationships": 1.0}
    # "θα έκανες / would you" questions are about decisions
    hypothetical = bool(re.match(r"^\s*(θα |would |what would|τι θα |αν )", _fold(question)))
    boost = {"decision_rules": 1.35, "values": 1.2} if hypothetical else {}
    # second-person questions ("πού μένεις;", "τι πίνεις;") are about the person, not the company
    personal = any(w.endswith(("εις", "εσαι", "ας")) and len(w) > 4 for w in _words(question))
    requested_versions = set(re.findall(r"(?<![a-z0-9])v\s*([1-9]\d*)\b", _fold(question)))
    asks_about_draft = bool(re.search(r"\bdraft\b|προσχεδι", _fold(question)))
    scored = []
    for sec, w in weights.items():
        for t in prof.get(sec, []):
            if sec == "relationships":
                t = {**t, "text": f"{t.get('name')} ({t.get('role', '')}): {t.get('relation', '')}"}
            body = " ".join(str(x) for x in (t.get("rule"), t.get("text"), t.get("when"), t.get("first_person")) if x)
            cov = _coverage(question, body)
            if cov <= 0:
                continue  # at least one content word must match
            if len(_specific_words(question)) >= 3 and _supported_word_count(question, body) < 2:
                continue  # a shared name or generic word alone is not evidence for a different topic
            sc = (0.75 * cov + 0.25 * _overlap(question, body)) * w * boost.get(sec, 1.0)
            if requested_versions:
                versions = set(re.findall(r"(?<![a-z0-9])v\s*([1-9]\d*)\b", _fold(body)))
                if requested_versions & versions:
                    sc *= 1.8
                elif versions:
                    sc *= 0.25
                else:
                    sc *= 0.55
            if asks_about_draft:
                sc *= 1.2 if re.search(r"\bdraft\b|προσχεδι", _fold(body)) else 0.8
            if personal and (sec == "preferences" or str(t.get("category", "")).startswith(("προσωπ", "personal"))):
                sc *= 1.25
            if sc > 0:
                scored.append((sc, {**t, "section": sec}))
    scored.sort(key=lambda x: -x[0])
    return scored


def _evidence_quote(t: dict, question: str) -> tuple[str, dict] | None:
    """The sentence from the trait's evidence that best supports it, with its source item."""
    if sharing.restricted() or t.get('inherited_from'):
        return None
    best = None
    for iid in t.get("evidence", [])[:4]:
        it = db.one("SELECT * FROM items WHERE id=?", (iid,))
        if not it:
            continue
        for sent in re.split(r"(?<=[.!?;])\s+|\n+", it["text"]):
            sent = sent.strip(" -*#")
            if not (15 <= len(sent) <= 240):
                continue
            sc = _coverage(_say(t) + " " + (t.get("text") or ""), sent) + 0.3 * _coverage(question, sent)
            if not best or sc > best[0]:
                best = (sc, sent, it)
    return (best[1], best[2]) if best else None


def _source_label(it: dict) -> str:
    where = CHANNEL_LABELS.get(it.get("channel", ""), it.get("channel", ""))
    to = f" προς {it['counterpart']}" if it.get("counterpart") and it.get("is_owner") and it["counterpart"] != "owner" else ""
    date = (it.get("ts") or "")[:10]
    return f"{where}{to}{', ' + date if date else ''}"


def _fact_from_memory(question: str, hits: list[Hit]) -> tuple[str, Hit] | None:
    """A sentence or adjacent heading/body window from the owner's texts that covers the question."""
    qw = _words(question)
    if len(qw) < 2:
        return None
    asks_for_amount = bool(re.search(r"\b(ποσο|ποση|ποσοι|amount|how much|budget|τιμη|ποσο)\b", _fold(question)))
    best, best_cov = None, 0.0
    for h in hits[:6]:
        if not h.item.get("is_owner"):
            continue
        sentences = [s.strip(" -*#|>\t") for s in re.split(r"(?<=[.!;])\s+|\n+", h.text)]
        # Headers often carry the period or subject while the next line carries the amount.
        # Score short adjacent windows together so exact facts such as "Q4 / €34k" stay linked.
        for start in range(len(sentences)):
            for width in (1, 2):
                sent = " ".join(s for s in sentences[start:start + width] if s)
                if not (20 <= len(sent) <= 360):
                    continue
                if asks_for_amount and not re.search(r"\d", sent):
                    continue
                if _supported_word_count(question, sent) < 2:
                    continue
                cov = _coverage(question, sent)
                if cov > best_cov:
                    best, best_cov = (sent, h), cov
    threshold = 0.45 if asks_for_amount else 0.6
    return best if best and best_cov >= threshold else None


def _offline_ask(prof: dict, question: str, hits: list[Hit], channel: str, history: list[dict] | None = None) -> dict:
    history = history or []
    q = _fold(question)
    last_user = next((h["text"] for h in reversed(history) if h.get("role") == "user"), "")
    last_twin = next((h for h in reversed(history) if h.get("role") == "twin"), None)
    tindex = trait_index(prof)
    last_traits = [tindex[i] for i in (last_twin or {}).get("traits", []) if i in tindex]
    greet = prof.get("persona_greeting") or {}
    name = prof.get("owner", {}).get("display_name", "")
    why_offline = ("Offline λειτουργία: βρήκα τα πιο σχετικά σημεία του προφίλ μου και τα μηνύματα που τα "
                   "αποδεικνύουν, χωρίς παραγωγή νέου κειμένου.")

    def reply(answer: str, used: list[dict], conf: float, unsure: bool = False, why: str = why_offline,
              mems: list[dict] | None = None) -> dict:
        return {"answer": answer, "unsure": unsure, "confidence": conf, "why": why,
                "traits": [_trait_view(t) for t in used],
                "memories": mems if mems is not None else [_hit_view(h, f"M{i + 1}") for i, h in enumerate(hits[:3])]}

    # 1. small talk
    n_raw = len(q.split())
    for intent, rx in INTENTS:
        limit = 6 if intent in ("identity", "help", "thanks") else 3
        if rx.search(q) and n_raw <= limit:
            text = {
                "greeting": greet.get("chat") or f"γεια! εδώ το AI αντίγραφο {('του προσώπου «' + name + '»') if name else ''}. ρώτα με ό,τι θες",
                "thanks": greet.get("thanks") or "τίποτα! 🙏",
                "how": greet.get("how") or "καλά, πολλή δουλειά! εσύ;",
                "identity": (prof.get("summary") or "") + " Είμαι το AI αντίγραφο αυτού του προσώπου: απαντώ μόνο από όσα έχει γράψει και αποφασίσει.",
                "help": ("Μπορείς να με ρωτήσεις τι ξέρω, τι προτιμώ ή πώς αποφασίζω, να μου ζητήσεις να απαντήσω σε "
                         "ένα μήνυμα ή να πάρω μια απόφαση. Δοκίμασε: «Τι κάνεις όταν η ομάδα διαφωνεί;»"),
            }[intent]
            return reply(text, [], 0.9, why="Κουβέντα, όχι ερώτηση για το προφίλ.", mems=[])

    # 2. follow-up: "why?" -> show the evidence behind the previous answer
    if WHY_RE.search(q) and n_raw <= 3 and last_traits:
        t = last_traits[0]
        ev = _evidence_quote(t, last_user)
        if ev:
            sent, it = ev
            ans = f"Γιατί έτσι το έχω κάνει στην πράξη. Είχα γράψει: «{sent}» ({_source_label(it)})."
            mem = [_hit_view(Hit(it["id"] + ".0", it["id"], it["source_id"], it["text"], 1.0, it), "M1")]
            return reply(ans, [t], round(min(0.9, t.get("confidence") or 0.7), 2),
                         why="Ζήτησες το γιατί: σου δείχνω το δικό μου μήνυμα που το αποδεικνύει.", mems=mem)

        if sharing.restricted() or t.get('inherited_from'):
            return reply('Γιατί αυτός είναι ο δημοσιευμένος εταιρικός κανόνας: ' + _say(t), [t],
                         min(0.9, t.get('confidence') or 0.7),
                         why='Παραπέμπω στον εγκεκριμένο κανόνα, χωρίς τις ιδιωτικές πηγές του κατόχου.', mems=[])

    # 3. follow-up: "and what else?" -> next best trait for the previous question
    if MORE_RE.search(q) and n_raw <= 4 and last_user:
        used_ids = {t["id"] for t in last_traits}
        more = [(sc, t) for sc, t in _score_traits(prof, last_user) if t["id"] not in used_ids and sc >= 0.2]
        if more:
            t = more[0][1]
            return reply("Και κάτι ακόμα: " + _say(t), [t], round(min(0.8, 0.3 + more[0][0] / 2), 2))
        return reply("Νομίζω αυτά είναι τα βασικά που ξέρω γι' αυτό.", [], 0.5)

    # 4. short follow-ups borrow the topic of the previous question ("και για το Κουκάκι;")
    effective = question
    scored = _score_traits(prof, question)
    top_score, top_trait = (scored[0] if scored else (0.0, None))
    if last_user and len(_words(question)) <= 2 and top_score < 0.3:
        effective = question + " " + last_user
        scored = _score_traits(prof, effective)
        top_score, top_trait = (scored[0] if scored else (0.0, None))
    unknown_raw = max((_coverage(effective, u) for u in prof.get("unknowns", [])), default=0.0)
    unknown_hit = 1.3 * unknown_raw if unknown_raw * len(_words(effective)) >= 1.6 else 0.0
    near, near_score = _nearest_reply(question, channel)
    near_cov = _coverage(question, (near or {}).get("meta", {}).get("in_reply_to_text", "")) if near else 0.0

    if unknown_hit >= 0.45 and unknown_hit >= top_score * 0.8:
        known = max(prof.get("unknowns", []), key=lambda u: _coverage(effective, u))
        return reply(f"Ειλικρινά, δεν το ξέρω ακόμα. {known}", [], 0.3, unsure=True)
    if near and near_cov >= 0.6 and near_cov > top_score and len(near["text"]) >= 60 and top_score < 0.45:
        mem = [_hit_view(Hit(near["id"] + ".0", near["id"], near["source_id"], near["text"], near_score, near), "M1")]
        return reply(f"Σε κάτι παρόμοιο είχα απαντήσει: «{near['text']}»", [], round(min(0.8, 0.35 + near_cov / 2), 2),
                     mems=mem)
    years = set(re.findall(r"\b20\d\d\b", question))
    if years and top_trait and not years & set(re.findall(r"\b20\d\d\b", _say(top_trait))):
        top_trait = None  # a fact about another year is not an answer: say "I don't know" instead of guessing
    if top_trait and top_score >= 0.27:
        answer = _say(top_trait)
        used = [top_trait]
        second = next(((sc, t) for sc, t in scored[1:4] if sc >= max(0.4, top_score * 0.9)
                       and t["section"] != top_trait["section"] and _overlap(_say(t), answer) < 0.5), None)
        if second:
            answer += " " + _say(second[1])
            used.append(second[1])
        return reply(answer, used, round(min(0.85, 0.3 + top_score / 2), 2))
    fact = _fact_from_memory(effective, hits)
    if fact and years and not years & set(re.findall(r"\b20\d\d\b", fact[0])):
        fact = None
    if fact:
        sent, h = fact
        mem = [_hit_view(h, "M1")]
        return reply(f"Από όσα έχω γράψει: «{sent}» ({_source_label(h.item)}).", [], 0.55, mems=mem,
                     why="Δεν υπάρχει γενικός κανόνας γι' αυτό στο προφίλ μου· σου δείχνω την πρόταση από τα δικά μου κείμενα "
                         "που απαντά ακριβώς στην ερώτηση.")
    return reply("Ειλικρινά, δεν το ξέρω. Δεν έχω γράψει τίποτα γι' αυτό, οπότε προτιμώ να μη μαντέψω. "
                 "Ρώτα με κάτι για τη δουλειά μου, τις αποφάσεις μου ή τις συνήθειές μου.", [], 0.3, unsure=True)


AMOUNT_RE = re.compile(r"(?:EUR|€)\s?(\d[\d.,]*)\s?(k)?|(\d[\d.,]*)\s?(k)?\s?(?:EUR|€|euro)", re.I)


def _amount(text: str) -> float | None:
    m = AMOUNT_RE.search(text)
    if not m:
        return None
    num, k = (m.group(1), m.group(2)) if m.group(1) else (m.group(3), m.group(4))
    num = num.rstrip(".,")
    if re.fullmatch(r"\d{1,3}([.,]\d{3})+", num):
        num = re.sub(r"[.,]", "", num)
    try:
        val = float(num.replace(",", "."))
    except ValueError:
        return None
    return val * 1000 if k else val


def _percent_value(text: str) -> float | None:
    match = re.search(r"(\d{1,3}(?:[.,]\d+)?)\s*%", text)
    if not match:
        return None
    return float(match.group(1).replace(",", "."))


def _percent_rule_applies(value: float, text: str) -> bool:
    """Check explicit percentage bands before letting a nearby policy rule score an option."""
    folded = _fold(text)
    ranges = [
        (float(a.replace(",", ".")), float(b.replace(",", ".")))
        for a, b in re.findall(r"(\d+(?:[.,]\d+)?)\s*%?\s*(?:-|–|—|to|εως)\s*(\d+(?:[.,]\d+)?)\s*%", folded)
    ]
    if any(low <= value <= high for low, high in ranges):
        return True
    thresholds = re.findall(r"(>=|≥|<=|≤|>|<|above|over|below|under|πανω απο|κατω απο|εως)\s*(\d+(?:[.,]\d+)?)\s*%", folded)
    if any((op in (">", "above", "over", "πανω απο") and value > float(n.replace(",", ".")))
           or (op in (">=", "≥") and value >= float(n.replace(",", ".")))
           or (op in ("<", "below", "under", "κατω απο") and value < float(n.replace(",", ".")))
           or (op in ("<=", "≤", "εως") and value <= float(n.replace(",", ".")))
           for op, n in thresholds):
        return True
    return False


def _kw_in(kw: str, option_tokens: set[str]) -> bool:
    """A multi-word keyword matches only if all its (non-prefix) tokens are in the option."""
    toks = [t for t in tokenize(kw) if not t.endswith("~")]
    return bool(toks) and all(t in option_tokens for t in toks)


def _decision_pattern_signals(situation: str, options: list[str]) -> tuple[list[float], dict[int, list[str]]]:
    """Apply a few evidence-neutral safeguards when options expose a common decision trap."""
    q = _fold(situation)
    scores = [0.0] * len(options)
    reasons: dict[int, list[str]] = {}

    def reward_options(query_re: str, option_re: str, penalty_re: str, weight: float,
                       reason: str, per_match: bool = False) -> None:
        if not re.search(query_re, q):
            return
        for i, option in enumerate(options):
            text = _fold(option)
            if per_match:
                good = len(re.findall(option_re, text))
                bad = len(re.findall(penalty_re, text))
                delta = min(3, good) * weight - min(3, bad) * weight * 1.5
            else:
                good = bool(re.search(option_re, text))
                bad = bool(re.search(penalty_re, text))
                delta = (weight if good else 0) - (weight * 1.5 if bad else 0)
            if delta:
                scores[i] += delta
                if delta > 0:
                    reasons.setdefault(i, []).append(reason)

    # Unknown cost, margin, or missing facts: ask for them before approval.
    reward_options(
        r"(?:δεν.{0,35}(?:γνωστ|επιβεβαι|στοιχει|δεδομ)|χωρις.{0,25}(?:στοιχει|δεδομ)|"
        r"αβεβαι|awaiting|unknown|not enough data|lack of data)",
        r"ζητ|request|confirm|verif|check|cost|margin|history|exposure|detail|στοιχει|επιβεβαι|περιθωρι|κοστο|δεδομ",
        r"approve|accept|commit|εγκριν|δεσμευ|συμφων|προχωρ",
        1.0,
        "Δεν έχουν επιβεβαιωθεί τα βασικά στοιχεία, οπότε προτιμώ να τα ζητήσω πριν από έγκριση.",
        per_match=True,
    )

    # Several new orders against an open balance must be considered together.
    reward_options(
        r"(?:ανεξοφλητ|ληξιπροθεσμ|open balance).{0,90}(?:παραγγελ|order)|"
        r"(?:παραγγελ|order).{0,90}(?:ανεξοφλητ|ληξιπροθεσμ|υπολοιπ|balance)",
        r"συνολικ|total|combined|overall|same picture|ιδια εικονα|ολη την εικονα|αθροισ|exposure|εκθεση",
        r"ξεχωριστ|separately|καθεμια|καθε μια|each order",
        2.2,
        "Εξετάζω τη συνολική έκθεση μαζί με το ανοιχτό υπόλοιπο.",
    )

    # Budget exceptions should stay scoped, owned, and reviewable.
    reward_options(
        r"εξαιρεσ.{0,80}(?:δαπαν|budget|προυπολογ|εκδηλω)|(?:δαπαν|expense).{0,80}(?:εκτο|outside).{0,30}(?:budget|προυπολογ)",
        r"συγκεκριμενη περιπτωση|one.?time|owner|υπευθυν|οφελ|benefit|ημερομη|review|ελεγχ|αποτελεσμα",
        r"μονιμ|permanent|ως κανονα για ολες|for all|γενικο κανονα",
        0.75,
        "Κρατώ την εξαίρεση συγκεκριμένη και ορίζω υπεύθυνο και ημερομηνία επανελέγχου.",
        per_match=True,
    )

    # A long exception with insufficient evidence is better tested as a pilot.
    reward_options(
        r"(?:exception|εξαιρεσ|συνεργατ).{0,100}(?:year|12 month|χρον|δεδομεν|στοιχει|partner)|"
        r"(?:δεν εχουμε αρκετα δεδομενα|not enough data).{0,100}(?:year|12 month|χρον|partner|συνεργατ)",
        r"pilot|πιλοτ|δοκιμ|review|εξοδο|stop.?loss|κριτηρι|owner|υπευθυν|ημερομη",
        r"12 μην|12 month|ολη τη χρονια|ολοκληρη χρονια|permanent|μονιμ|εγκριν|approve",
        1.6,
        "Προτιμώ πιλοτική συνεργασία με μετρήσιμα κριτήρια αντί για μακρά δέσμευση χωρίς δεδομένα.",
    )

    # When delivery is uncertain, communicate what is known and when the next update comes.
    reward_options(
        r"(?:παραδοσ|delivery).{0,90}(?:κινδυν|risk|περιμεν|await|επιβεβαιω|confirm)|"
        r"περιμεν.{0,50}(?:επιβεβαιω|supplier|προμηθευτ)",
        r"ενημερ|inform|notify|tell the customer|πελατ|today|σημερα|επανελθ|ωρα|υπευθυν|contact",
        r"περιμεν|wait|πριν.{0,20}πουμε|before.{0,20}say anything",
        2.5,
        "Ενημερώνω τον πελάτη για όσα γνωρίζω και ορίζω πότε θα επανέλθουμε.",
    )

    # Sales cannot commit to extended payment terms before Finance approves them.
    reward_options(
        r"net\s?(?:45|60|90)|παρατεταμενη εξοφληση|οροι πληρωμης|payment terms",
        r"finance|approvalflow|review|εγκρισ|ελεγχο|κλιμακ|περιμεν.{0,30}αξιολογ",
        r"δεσμευτικ|binding|commit|promise|βαζουμε net|υποσχε",
        2.6,
        "Δεν δεσμεύομαι για εκτεταμένους όρους πληρωμής πριν από έγκριση του Finance.",
    )
    return scores, reasons


def _option_scores(prof: dict, situation: str, options: list[str]) -> tuple[list[float], list[dict]]:
    rules = prof.get("decision_rules", []) + [
        {**v, "rule": v.get("text"), "prefers": v.get("prefers", []), "avoids": v.get("avoids", [])}
        for v in prof.get("values", [])]
    raw = [0.0] * len(options)
    applied: dict[str, dict] = {}
    contrib: list[dict[str, float]] = [{} for _ in options]
    amount = _amount(situation)
    percent = _percent_value(situation) if re.search(r"εκπτωσ|discount|concession", _fold(situation)) else None
    for r in rules:
        prefers = list(r.get("prefers", []))
        th = r.get("threshold")
        if th and amount is not None:
            prefers += th.get("above_prefers" if amount > th.get("amount", 0) else "below_prefers", [])
        trigger = r.get("when") or r.get("rule", "") or r.get("text", "")
        rule_text = f"{trigger} {r.get('rule', '')} {r.get('text', '')}"
        if percent is not None and re.search(r"\d+(?:[.,]\d+)?\s*%", _fold(rule_text)) \
                and not _percent_rule_applies(percent, rule_text):
            continue
        # Candidate options must not make an otherwise unrelated rule look applicable.
        rel = max(_overlap(situation, trigger), 0.65 * _overlap(situation, rule_text))
        support = _supported_word_count(situation, trigger)
        if support == 0:
            continue
        if len(_specific_words(situation)) >= 4 and support == 1:
            rel *= 0.65
        if rel <= 0.02:
            continue
        # soft signal: how much each option reads like what the person says they do (or avoid)
        said = f"{r.get('first_person', '')} {r.get('rule', '')} " + " ".join(prefers)
        avoided = " ".join(r.get("avoids", []))
        soft = [_coverage(opt, said) - 1.2 * _coverage(opt, avoided) if avoided else _coverage(opt, said)
                for opt in options]
        mean_soft = sum(soft) / len(soft)
        for i, opt in enumerate(options):
            ot = set(tokenize(opt))
            pro = sum(1 for kw in prefers if _kw_in(kw, ot))
            con = sum(1 for kw in r.get("avoids", []) if _kw_in(kw, ot))
            lean = 1.5 * (soft[i] - mean_soft)
            if pro or con or abs(lean) > 0.05:
                delta = rel * (pro - 1.2 * con + lean) * (r.get("confidence") or 0.6)
                if r.get("inherited_from"):
                    delta *= 1.25  # company rules from above win when they conflict
                raw[i] += delta
                contrib[i][r["id"]] = contrib[i].get(r["id"], 0.0) + delta
                applied[r["id"]] = r
    pattern_scores, _ = _decision_pattern_signals(situation, options)
    raw = [score + pattern for score, pattern in zip(raw, pattern_scores)]
    exps = [math.exp(4 * x) for x in raw]
    total = sum(exps)
    scores = [round(100 * e / total, 1) for e in exps]
    best = max(range(len(options)), key=lambda i: scores[i])
    # explain with the rules that pushed towards the chosen option (or against the others)
    weight = {rid: contrib[best].get(rid, 0.0) - max((contrib[j].get(rid, 0.0) for j in range(len(options)) if j != best),
                                                    default=0.0) for rid in applied}
    ranked = [applied[rid] for rid, w in sorted(weight.items(), key=lambda x: -x[1]) if w > 0]
    return scores, ranked


def _offline_decide(prof: dict, situation: str, options: list[str], hits: list[Hit]) -> dict:
    scores, applied = _option_scores(prof, situation, options)
    choice = max(range(len(options)), key=lambda i: scores[i])
    spread = max(scores) - min(scores)
    _, pattern_reasons = _decision_pattern_signals(situation, options)
    if not applied and not pattern_reasons:
        choice = None
    unsure = choice is None or spread < 8
    traits = [{"id": r["id"], "section": "decision_rules", "text": r.get("rule") or r.get("text"),
               "confidence": r.get("confidence"), "evidence": r.get("evidence", []),
               "inherited_from": r.get("inherited_from")} for r in applied[:4]]
    if choice is None:
        why = "Δεν βρήκα κανόνα που να ταιριάζει αρκετά σε αυτή την απόφαση, οπότε δεν θα μαντέψω."
    else:
        why = ("Θα πήγαινα με αυτό. " + " ".join(_say(r) for r in applied[:2])) if applied \
            else "Τίποτα στο ιστορικό μου δεν ταιριάζει ξεκάθαρα εδώ."
        if pattern_reasons.get(choice):
            why += " " + pattern_reasons[choice][0]
    confidence = min(0.3, 0.35 + spread / 120) if choice is None else min(0.9, 0.35 + spread / 120)
    return {"choice": choice, "scores": scores, "unsure": unsure, "confidence": round(confidence, 2),
            "why": why, "would_change_my_mind": "Δεδομένα που δείχνουν ότι η άλλη επιλογή δουλεύει καλύτερα για τους χρήστες μας.",
            "traits": traits, "memories": [_hit_view(h, f"M{i + 1}") for i, h in enumerate(hits[:3])]}


SENDER_PREFIX = re.compile(r"^\s*([A-ZΑ-ΩΆ-Ώ][\wά-ώ]+)\s*:")
SENDER_SIGNOFF = re.compile(r"(?:Best|Thanks|Regards|Cheers|Ευχαριστώ|Με εκτίμηση|Φιλικά)[,!]?\s+([A-ZΑ-ΩΆ-Ώ][\wά-ώ.]*(?:\s[A-ZΑ-ΩΆ-Ώ][\wά-ώ]+)?)\s*$")
GREETING_RE = re.compile(r"^(Hi|Hey|Dear|Hello|Καλημέρα|Γεια σου|Γεια σας)\s+([A-ZΑ-ΩΆ-Ώ][\wά-ώ]+)")


def _sender(incoming: str) -> str | None:
    m = SENDER_PREFIX.match(incoming) or SENDER_SIGNOFF.search(incoming.strip())
    return m.group(1).split()[0].rstrip(".") if m else None


def _readdress(text: str, old: str | None, incoming: str) -> str:
    """Point a reused reply at the new sender (offline nearest-neighbour replies)."""
    new = _sender(incoming)
    if not new or len(new) < 2:
        return text
    m = GREETING_RE.match(text)
    if m:
        return text[:m.start(2)] + new + text[m.end(2):]
    first = (old or "").split()[0] if old else ""
    if first and text.startswith(first):
        return new + text[len(first):]
    return text


def _nearest_reply(incoming: str, channel: str) -> tuple[dict | None, float]:
    """The owner's own past reply to the most similar incoming message (nearest-neighbour)."""
    if sharing.restricted():
        return None, 0.0
    rows = db.query("SELECT i.* FROM items i JOIN sources s ON s.id=i.source_id WHERE s.consent=1 AND i.is_owner=1 "
                    "AND s.person_id=?", (pid(),))
    best, best_score = None, 0.0
    for r in rows:
        ctx = (r.get("meta") or {}).get("in_reply_to_text") if isinstance(r.get("meta"), dict) else None
        if not ctx or r["id"] in EXCLUDE:
            continue
        score = _overlap(incoming, ctx) + 0.4 * _overlap(incoming, r["text"])
        if r["channel"] == channel:
            score *= 1.25
        elif r["channel"].split("_")[0] != channel.split("_")[0]:
            score *= 0.6
        if score > best_score:
            best, best_score = r, score
    return best, best_score


def _offline_write(prof: dict, incoming: str, channel: str, hits: list[Hit]) -> dict:
    style = _style_for(prof, channel)
    rules = _best_traits(prof, incoming, ("decision_rules", "values"), k=2)
    traits = [{"id": t["id"], "section": t["section"], "text": t.get("rule") or t.get("text"),
               "confidence": t.get("confidence"), "evidence": t.get("evidence", [])} for t in rules]
    near, score = _nearest_reply(incoming, channel)
    if near and score >= 0.18:
        return {"draft": _readdress(near["text"], near.get("counterpart"), incoming), "unsure": score < 0.3,
                "confidence": round(min(0.75, 0.3 + score), 2),
                "why": "Offline λειτουργία: χρησιμοποίησα τη δική μου απάντηση στο πιο παρόμοιο μήνυμα που έχω λάβει "
                       f"({CHANNEL_LABELS.get(near['channel'], near['channel'])}, {(near.get('ts') or '')[:10]}), "
                       "χωρίς παραγωγή κειμένου. Σύνδεσε ένα μοντέλο AI για να προσαρμοστεί ακριβώς σε αυτό το μήνυμα.",
                "style_choices": describe_rules(style)[:3], "traits": traits,
                "memories": [_hit_view(Hit(near["id"] + ".0", near["id"], near["source_id"], near["text"], score, near),
                                       "M1")]}
    greeting = (style.get("greetings") or [""])[0].replace("<name>", "").replace(" ,", ",").strip()
    signoff = (style.get("signoffs") or [""])[0].replace(" / ", "\n")
    body = "Ευχαριστώ για το μήνυμα."
    if rules:
        body += " Η θέση μου, σύντομα: " + (rules[0].get("rule") or rules[0].get("text") or "")
    body += "\n\nΘα επανέλθω με λεπτομέρειες."
    draft = "\n\n".join(p for p in (greeting, body, signoff) if p)
    return {"draft": draft, "unsure": True, "confidence": 0.3,
            "why": "Offline πρότυπο: ο συνηθισμένος μου χαιρετισμός και υπογραφή για αυτό το κανάλι, μαζί με τον πιο "
                   "σχετικό κανόνα απόφασης. Σύνδεσε ένα μοντέλο AI για πραγματικό draft.",
            "style_choices": describe_rules(style)[:3], "traits": traits,
            "memories": [_hit_view(h, f"M{i + 1}") for i, h in enumerate(hits[:3])]}


# ------------------------------------------------------------------ public API

def log_llm_error(exc: Exception) -> None:
    import logging

    logging.getLogger("mirror.twin").warning("AI call failed, answering offline: %s", LLM_CLIENT.explain(exc))
    LLM_CLIENT.stats.last_error = LLM_CLIENT.explain(exc)


def _format_history(history: list[dict] | None) -> str:
    lines = []
    for h in (history or [])[-8:]:
        who = "User" if h.get("role") == "user" else "You (twin)"
        lines.append(f"{who}: {str(h.get('text', ''))[:600]}")
    return "\n".join(lines) or "(new conversation)"


def suggested_questions() -> list[str]:
    prof = current_profile()
    return verified_chat.suggestions(prof, _boundaries()) if prof else []


def _reviewed_answer(prof: dict, question: str, history: list[dict] | None) -> dict | None:
    if WHY_RE.fullmatch(_fold(question)) and history and len(history) >= 2:
        previous_question, previous_answer = history[-2:]
        text = previous_question.get("text")
        if (previous_question.get("role") == "user" and previous_answer.get("mode") == "verified"
                and isinstance(text, str) and not check_boundaries(text, _boundaries())):
            previous = verified_chat.answer(prof, text, EXCLUDE)
            if previous:
                return {**previous, "answer": previous["why"]}
    return verified_chat.answer(prof, question, EXCLUDE)


# Επεξήγηση: Απαντά με προφίλ, σχετικά αποσπάσματα και ιστορικό· διαθέτει και offline διαδρομή.
def ask(question: str, channel: str = "chat_team", *, log: bool = True, history: list[dict] | None = None) -> dict:
    prof = _profile()
    owner = get_owner()
    t0 = time.time()
    b = check_boundaries(question, _boundaries())
    if b:
        res = _boundary_reply(b, owner.display_name)
    elif verified := _reviewed_answer(prof, question, history):
        res = verified
    else:
        last_user = next((h.get("text", "") for h in reversed(history or []) if h.get("role") == "user"), "")
        hits = memories(question + (" " + last_user if len(_words(question)) <= 3 else ""), k=8)
        res = None
        if LLM_CLIENT.available:
            try:
                style = _style_for(prof, channel)
                out = LLM_CLIENT.json(
                    prompts.TWIN_SYSTEM.format(owner=owner.name, role=owner.role, name=owner.display_name,
                                               persona=persona_digest(prof)),
                    prompts.ASK_USER.format(name=owner.display_name, memories=format_memories(hits),
                                            profile_facts=format_profile_facts(prof, question),
                                            channel_label=CHANNEL_LABELS.get(channel, channel),
                                            style_rules="\n".join(describe_rules(style)) or "-",
                                            exemplars=format_exemplars(exemplars(channel, question, 3),
                                                                       owner.display_name),
                                            history=_format_history(history), question=question),
                    max_tokens=1500, effort="minimal")
                refs = _resolve_refs(out, prof, hits)
                if bool(out.get("unsure")) and not refs["traits"] and not refs["memories"]:
                    # Do not let an LLM's generic abstention hide a strong, citable match in the local profile.
                    grounded = _offline_ask(prof, question, hits, channel, history)
                    if not grounded["unsure"] and (grounded["traits"] or grounded["memories"]):
                        res = {**grounded, "mode": "grounded-profile"}
                    else:
                        res = {"answer": str(out.get("answer", "")).strip(), "unsure": True,
                               "why": out.get("why", ""), **refs,
                               "confidence": _calibrate(out.get("confidence"), 0, 0, True), "mode": "llm"}
                else:
                    res = {"answer": str(out.get("answer", "")).strip(), "unsure": bool(out.get("unsure")),
                           "why": out.get("why", ""), **refs,
                           "confidence": _calibrate(out.get("confidence"), len(refs["traits"]), len(refs["memories"]),
                                                    bool(out.get("unsure"))), "mode": "llm"}
            except LLMUnavailable:
                res = None
            except Exception as exc:  # noqa: BLE001 - AI down: answer offline and say why
                log_llm_error(exc)
                res = {**_offline_ask(prof, question, hits, channel, history), "mode": "offline", "llm_error": LLM_CLIENT.explain(exc)}
        if res is None:
            res = {**_offline_ask(prof, question, hits, channel, history), "mode": "offline"}
        res["style_match"] = similarity(res["answer"], _style_for(prof, channel)) if res.get("answer") else None
    res["latency_s"] = round(time.time() - t0, 2)
    if log:
        db.audit("twin", "ask", question=question[:200], unsure=res.get("unsure"), mode=res.get("mode"))
    return res


# Επεξήγηση: Προτείνει επιλογή και αιτιολόγηση· δεν εκτελεί επιχειρηματική έγκριση.
def decide(situation: str, options: list[str], *, log: bool = True) -> dict:
    prof = _profile()
    owner = get_owner()
    options = [o.strip() for o in options if o and o.strip()]
    if len(options) < 2:
        raise ValueError("Δώσε τουλάχιστον δύο επιλογές")
    t0 = time.time()
    b = check_boundaries(situation, _boundaries())
    if b:
        res = _boundary_reply(b, owner.display_name)
        res.update({"choice": None, "scores": []})
        return res
    hits = memories(situation + " " + " ".join(options), k=8)
    res = None
    if LLM_CLIENT.available:
        try:
            out = LLM_CLIENT.json(
                prompts.TWIN_SYSTEM.format(owner=owner.name, role=owner.role, name=owner.display_name,
                                           persona=persona_digest(prof)),
                prompts.DECIDE_USER.format(name=owner.display_name, memories=format_memories(hits), situation=situation,
                                           options="\n".join(f"{i}. {o}" for i, o in enumerate(options))),
                max_tokens=2500)
            refs = _resolve_refs(out, prof, hits)
            try:
                choice = int(out.get("choice", 0))
            except (TypeError, ValueError):
                choice = 0
            choice = max(0, min(choice, len(options) - 1))
            scores = out.get("scores") or []
            if len(scores) != len(options):
                scores = [100.0 if i == choice else 0.0 for i in range(len(options))]
            res = {"choice": choice, "scores": [float(s) for s in scores], "unsure": bool(out.get("unsure")),
                   "why": out.get("why", ""), "would_change_my_mind": out.get("would_change_my_mind", ""), **refs,
                   "confidence": _calibrate(out.get("confidence"), len(refs["traits"]), len(refs["memories"]),
                                            bool(out.get("unsure"))), "mode": "llm"}
        except LLMUnavailable:
            res = None
        except Exception as exc:  # noqa: BLE001 - AI down: answer offline and say why
            log_llm_error(exc)
            res = {**_offline_decide(prof, situation, options, hits), "mode": "offline", "llm_error": LLM_CLIENT.explain(exc)}
    if res is None:
        res = {**_offline_decide(prof, situation, options, hits), "mode": "offline"}
    res["options"] = options
    res["latency_s"] = round(time.time() - t0, 2)
    if log:
        db.audit("twin", "decide", situation=situation[:200], choice=res.get("choice"), mode=res.get("mode"))
    return res


# Επεξήγηση: Συντάσσει προσχέδιο με το ύφος του προσώπου και ελεγχόμενες αναφορές.
def write(incoming: str, channel: str = "email_external", audience: str = "", instructions: str = "",
          *, critique: bool = True, log: bool = True, queue: bool = True) -> dict:
    prof = _profile()
    owner = get_owner()
    channel = channel if channel in CHANNEL_LABELS else "email_external"
    t0 = time.time()
    b = check_boundaries(incoming + " " + instructions, _boundaries())
    if b:
        return _boundary_reply(b, owner.display_name)
    hits = memories(incoming, k=7)
    style = _style_for(prof, channel)
    ex = exemplars(channel, incoming, 4)
    res = None
    if LLM_CLIENT.available:
        try:
            system = prompts.TWIN_SYSTEM.format(owner=owner.name, role=owner.role, name=owner.display_name,
                                                persona=persona_digest(prof))
            out = LLM_CLIENT.json(system, prompts.WRITE_USER.format(
                name=owner.display_name, memories=format_memories(hits), channel_label=CHANNEL_LABELS[channel],
                style_rules="\n".join(describe_rules(style)) or "-", exemplars=format_exemplars(ex, owner.display_name),
                audience=audience or "someone", incoming=incoming,
                instructions=f"Extra instruction from {owner.display_name} (follow it): {instructions}" if instructions else ""),
                max_tokens=3000)
            draft = str(out.get("draft", "")).strip()
            refs = _resolve_refs(out, prof, hits)
            critic = None
            before = similarity(draft, style)
            if critique and draft:
                try:
                    c = LLM_CLIENT.json(prompts.CRITIC_SYSTEM, prompts.CRITIC_USER.format(
                        name=owner.display_name, style_rules="\n".join(describe_rules(style)) or "-",
                        exemplars=format_exemplars(ex, owner.display_name), draft=draft), max_tokens=2500)
                    revised = str(c.get("revised") or "").strip()
                    after = similarity(revised, style) if revised else 0
                    critic = {"score": c.get("score"), "issues": c.get("issues", [])[:5], "style_before": before,
                              "style_after": after, "applied": bool(revised) and after >= before - 2}
                    if critic["applied"]:
                        draft = revised
                except Exception as exc:  # noqa: BLE001 - critique is best-effort
                    critic = {"error": str(exc)[:200]}
            res = {"draft": draft, "unsure": bool(out.get("unsure")), "why": out.get("why", ""),
                   "style_choices": out.get("style_choices", [])[:6], "critic": critic, **refs,
                   "confidence": _calibrate(out.get("confidence"), len(refs["traits"]), len(refs["memories"]),
                                            bool(out.get("unsure"))), "mode": "llm"}
        except LLMUnavailable:
            res = None
        except Exception as exc:  # noqa: BLE001 - AI down: answer offline and say why
            log_llm_error(exc)
            res = {**_offline_write(prof, incoming, channel, hits), "mode": "offline", "llm_error": LLM_CLIENT.explain(exc)}
    if res is None:
        res = {**_offline_write(prof, incoming, channel, hits), "mode": "offline"}
    res["style_match"] = similarity(res["draft"], style) if res.get("draft") else None
    res["style_rules"] = describe_rules(style)
    res["exemplars"] = [{"item_id": e["id"], "text": e["text"][:400]} for e in ex[:3]]
    res["channel"] = channel
    res["latency_s"] = round(time.time() - t0, 2)
    settings_disclosure = db.get_setting("disclosure", True)
    res["disclosure"] = f"Γράφτηκε από το ψηφιακό δίδυμο ({owner.display_name})" \
        if settings_disclosure else None
    if queue and res.get("draft"):
        res["draft_id"] = db.execute(
            "INSERT INTO drafts(created_at, person_id, kind, request, response, status) VALUES(?,?,?,?,?, 'pending')",
            (time.time(), pid(), "write", db.dumps({"incoming": incoming, "channel": channel, "audience": audience,
                                             "instructions": instructions}), db.dumps(res)))
    if log:
        db.audit("twin", "write", channel=channel, draft_id=res.get("draft_id"), mode=res.get("mode"))
    return res


# ------------------------------------------------------------------ baseline ("persona prompt" chatbot)

def baseline_decide(situation: str, options: list[str]) -> dict:
    owner = get_owner()
    if not LLM_CLIENT.available:
        return {"choice": 0, "why": "Offline baseline: διαλέγει πάντα την πρώτη επιλογή.", "mode": "offline"}
    out = LLM_CLIENT.json(prompts.BASELINE_SYSTEM.format(owner=owner.name, role=owner.role),
                          prompts.BASELINE_DECIDE.format(situation=situation, options="\n".join(
                              f"{i}. {o}" for i, o in enumerate(options))), max_tokens=1200)
    try:
        choice = max(0, min(int(out.get("choice", 0)), len(options) - 1))
    except (TypeError, ValueError):
        choice = 0
    return {"choice": choice, "why": out.get("why", ""), "mode": "llm"}


def baseline_write(incoming: str, channel: str, audience: str = "") -> dict:
    """Use the Twin's full response path for Studio's general-chat comparison.

    This keeps answers grounded in the same profile, memories, boundaries and
    writing style while avoiding draft persistence and duplicate audit events.
    """
    return write(incoming, channel, audience, critique=True, log=False, queue=False)


def compare(kind: str, payload: dict) -> dict:
    try:
        return _compare(kind, payload)
    except Exception as exc:  # noqa: BLE001 - the baseline is optional, never crash the page
        log_llm_error(exc)
        msg = LLM_CLIENT.explain(exc)
        return {"answer": "Το AI δεν απάντησε: " + msg, "draft": "Το AI δεν απάντησε: " + msg, "choice": 0,
                "why": msg, "mode": "offline", "llm_error": msg, "style_match": None}


def _compare(kind: str, payload: dict) -> dict:
    if kind == "decide":
        return baseline_decide(payload["situation"], payload["options"])
    if kind == "write":
        res = baseline_write(payload["incoming"], payload.get("channel", "email_external"), payload.get("audience", ""))
        prof = _profile()
        res["style_match"] = similarity(res["draft"], _style_for(prof, payload.get("channel", "email_external")))
        return res
    if kind == "ask":
        owner = get_owner()
        if not LLM_CLIENT.available:
            return {"answer": "Ως γενικός βοηθός δεν έχω πληροφορίες γι' αυτό.", "mode": "offline"}
        out = LLM_CLIENT.json(prompts.BASELINE_SYSTEM.format(owner=owner.name, role=owner.role),
                              f"{payload['question']}\nReturn JSON: {{\"answer\": \"...\"}}", max_tokens=1200)
        return {"answer": out.get("answer", ""), "mode": "llm"}
    raise ValueError(kind)


__all__ = ["ask", "decide", "write", "compare", "TwinNotReady", "LLMUnavailable", "CHANNELS"]
