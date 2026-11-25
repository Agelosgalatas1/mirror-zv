# Επεξήγηση: Μάθηση από κάθε συνομιλία, χωρίς τα λόγια των άλλων να γίνονται «ο άνθρωπος».
"""Learning from every conversation.

1. Every 👍 / 👎 on an answer strengthens or weakens the person's own traits that answer relied on.
   The adjusted confidence is applied whenever the Mirror reasons (``profile.for_twin``), so the next
   answers change at once. A rated inherited rule counts for the person who owns that rule.
2. Every question the Mirror could not answer is queued in its owner's self-test. When the owner
   answers it, the answer becomes owner-verified knowledge and the question leaves the queue.

What is never learned: the wording of other people's questions as the person's opinions, and any
chat text as a persona trait or a source. Only the owner can turn a question into knowledge.
"""
from __future__ import annotations

import re
import time
import unicodedata

from . import db

STEP = 0.05          # confidence change per net 👍 / 👎
MAX_SHIFT = 0.25     # ratings move a trait at most this far from what the evidence says
FLOOR, CEILING = 0.2, 0.99


def _key(question: str) -> str:
    q = unicodedata.normalize("NFD", question.lower())
    q = "".join(c for c in q if unicodedata.category(c) != "Mn")
    return " ".join(re.findall(r"\w+", q))[:300]


# ------------------------------------------------------------------ 1. ratings → trait weights

def rate(user_id: str, target: str, message_id: int | None, rating: str) -> dict:
    """Store a rating for one answer the user received from ``target`` (one vote per user and answer)."""
    traits: list[str] = []
    if message_id:
        row = db.one("SELECT m.payload FROM messages m JOIN conversations c ON c.id=m.conversation_id "
                     "WHERE m.id=? AND m.role='twin' AND c.user_id=? AND c.target=?", (message_id, user_id, target))
        if not row:
            raise LookupError("Η απάντηση δεν βρέθηκε σε δική σου συζήτηση.")
        traits = [t["id"] for t in (row["payload"] or {}).get("traits", []) if t.get("id")]
    db.execute("INSERT INTO answer_ratings(user_id, target, message_id, rating, traits, ts) VALUES(?,?,?,?,?,?) "
               "ON CONFLICT(user_id, target, message_id) DO UPDATE SET rating=excluded.rating, traits=excluded.traits, "
               "ts=excluded.ts", (user_id, target, message_id or 0, rating, db.dumps(traits), time.time()))
    return {"traits": len(traits)}


def signals() -> dict[tuple[str, str], tuple[int, int]]:
    """(owner, trait id) → (👍, 👎). Inherited ids ("ceo.r1") count for the person who owns the rule."""
    out: dict[tuple[str, str], list[int]] = {}
    for r in db.query("SELECT target, rating, traits FROM answer_ratings"):
        for tid in r["traits"] or []:
            owner, _, own_id = tid.partition(".") if "." in tid else (r["target"], "", tid)
            cell = out.setdefault((owner, own_id), [0, 0])
            cell[0 if r["rating"] == "faithful" else 1] += 1
    return {k: (v[0], v[1]) for k, v in out.items()}


def apply(prof: dict, person: str, sections: tuple[str, ...]) -> dict:
    """The profile with every rated trait's confidence moved by its colleagues' ratings."""
    sig = signals()
    if not sig:
        return prof
    prof = dict(prof)
    for sec in sections:
        adjusted = []
        for t in prof.get(sec, []):
            src = (t.get("inherited_from") or {}).get("id")
            key = (src, t["id"].split(".", 1)[1]) if src and "." in t["id"] else (person, t["id"])
            up, down = sig.get(key, (0, 0))
            if up or down:
                base = float(t.get("confidence") or 0.6)
                shift = max(-MAX_SHIFT, min(MAX_SHIFT, STEP * (up - down)))
                t = {**t, "confidence": round(max(FLOOR, min(CEILING, base + shift)), 2), "chat_signal": {"up": up, "down": down}}
            adjusted.append(t)
        prof[sec] = adjusted
    return prof


# ------------------------------------------------------------------ 2. unanswered questions → owner's self-test

def record_turn(asker: str, target: str, question: str, res: dict) -> None:
    """Queue a question the Mirror could not answer, for its owner (never the owner's own questions)."""
    q = " ".join(question.split())
    if asker == target or res.get("boundary") or not res.get("unsure") or len(q) < 8 or len(q.split()) < 2:
        return
    now = time.time()
    db.execute("INSERT INTO chat_gaps(person_id, qkey, question, asked, first_at, last_at) VALUES(?,?,?,?,?,?) "
               "ON CONFLICT(person_id, qkey) DO UPDATE SET asked=chat_gaps.asked+1, last_at=excluded.last_at, "
               "resolved_at=NULL WHERE chat_gaps.resolved_at IS NULL",
               (target, _key(q), q[:500], 1, now, now))


def gaps(person: str, limit: int = 8) -> list[dict]:
    rows = db.query("SELECT question, asked, last_at FROM chat_gaps WHERE person_id=? AND resolved_at IS NULL "
                    "ORDER BY asked DESC, last_at DESC LIMIT ?", (person, limit))
    return [{"question": r["question"], "asked": r["asked"]} for r in rows]


def resolve(person: str, question: str) -> None:
    db.execute("UPDATE chat_gaps SET resolved_at=? WHERE person_id=? AND qkey=? AND resolved_at IS NULL",
               (time.time(), person, _key(question)))


def reopen(person: str, question: str) -> None:
    db.execute("UPDATE chat_gaps SET resolved_at=NULL WHERE person_id=? AND qkey=?", (person, _key(question)))


def stats(person: str) -> dict:
    """What colleagues' conversations have taught this person's Mirror so far."""
    rated = db.one("SELECT count(*) n, sum(rating='faithful') up FROM answer_ratings WHERE target=?", (person,)) or {}
    traits = sum(1 for (owner, _), (u, d) in signals().items() if owner == person and u != d)
    learned = db.one("SELECT count(*) n FROM chat_gaps WHERE person_id=? AND resolved_at IS NOT NULL", (person,)) or {}
    return {"rated_answers": rated.get("n") or 0, "faithful": rated.get("up") or 0,
            "traits_adjusted": traits, "questions_learned": learned.get("n") or 0,
            "questions_waiting": len(gaps(person, 100))}
