"""Reviewed demo answers backed by available documents or published rules."""
from __future__ import annotations

import json

from . import db, sharing
from .config import BASE_DIR
from .context import pid
from .privacy import check_boundaries
from .retrieval import _fold

GUIDES = json.loads((BASE_DIR / "data" / "verified_questions.json").read_text("utf-8"))
HELP = (
    ("Ποια στοιχεία χρησιμοποιεί αυτή η συνομιλία;",
     "Σε συνομιλία με Mirror προϊσταμένου βλέπεις τις εταιρικές αξίες και τους κανόνες που έχουν δημοσιευτεί."),
    ("Πώς βλέπω από πού προήλθε μια απάντηση;",
     "Πάτησε τον κανόνα ή την παραπομπή κάτω από την απάντηση για να δεις τι τη στηρίζει."),
    ("Ποιος εγκρίνει τη δημοσίευση ενός εταιρικού κανόνα;",
     "Ο κάτοχος του Mirror ελέγχει τον κανόνα και τον εγκρίνει για δημοσίευση μέσα από το Self-test."),
)


def _key(text: str) -> str:
    return " ".join(_fold(text).strip(" ;?!.").split())


def _entries(prof: dict, excluded=frozenset()):
    if sharing.restricted():
        for trait in prof.get("decision_rules", []):
            trigger = (trait.get("when") or "").strip().rstrip("?.;")
            rule = (trait.get("rule") or "").strip()
            if trait.get("publication") and trigger and rule and len(trigger) <= 150:
                yield (f"Ποιος είναι ο δημοσιευμένος κανόνας για «{trigger}»;",), rule, [], [trait]
        for question, answer in HELP:
            yield (question,), answer, [], []
        return

    guides = GUIDES.get(pid(), [])
    if not guides:
        return
    source_ids = sorted({entry["source"] for entry in guides})
    placeholders = ", ".join("?" for _ in source_ids)
    items = db.query(
        f"SELECT i.* FROM items i JOIN sources s ON s.id=i.source_id "
        f"WHERE s.person_id=? AND s.consent=1 AND i.is_owner=1 AND i.id IN ({placeholders})",
        (pid(), *source_ids),
    )
    by_id = {item["id"]: item for item in items}
    for guide in guides:
        item = by_id.get(guide["source"])
        if not item or item["id"] in excluded or guide["quote"] not in item["text"]:
            continue
        memory = {"ref": "M1", "item_id": item["id"], "source_id": item["source_id"],
                  "subject": item["subject"], "channel": item["channel"], "date": (item["ts"] or "")[:10],
                  "author": "me", "snippet": guide["quote"]}
        yield guide["questions"], guide["answer"], [memory], []


def suggestions(prof: dict, boundaries: list[dict], limit: int = 4) -> list[str]:
    questions = dict.fromkeys(group[0] for group, _, _, _ in _entries(prof)
                              if not check_boundaries(group[0], boundaries))
    return list(questions)[:limit]


def answer(prof: dict, question: str, excluded: set[str]) -> dict | None:
    key = _key(question)
    for questions, text, sources, traits in _entries(prof, excluded):
        if not any(key == _key(candidate) for candidate in questions):
            continue
        if not sharing.restricted():
            # An explicit self-test correction takes precedence for the same question.
            for fact in reversed(prof.get("knowledge", [])):
                learned_question, separator, correction = (fact.get("text") or "").partition(" → ")
                if fact.get("owner_verified") and separator and _key(learned_question) == key:
                    return {"answer": correction, "why": "Επιβεβαιωμένη διόρθωση από το Self-test.",
                            "traits": [{**fact, "section": "knowledge"}], "memories": [],
                            "confidence": 1.0, "unsure": False, "mode": "verified"}
        why = ("Η απάντηση τεκμηριώνεται από την πηγή που εμφανίζεται παρακάτω." if sources
               else "Η απάντηση προέρχεται από τον δημοσιευμένο κανόνα." if traits
               else "Η απάντηση περιγράφει τη λειτουργία του MIRROR.")
        return {"answer": text, "confidence": 1.0, "unsure": False, "mode": "verified", "why": why,
                "memories": sources, "traits": [{**trait, "text": trait["rule"]} for trait in traits]}
    return None
