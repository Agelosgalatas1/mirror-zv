# Επεξήγηση: Εργαλείο παραγωγής έτοιμων προφίλ από τα demo δεδομένα· εκτελείται μόνο όταν ζητηθεί.
"""Rebuild the shipped persona snapshots (data/snapshot/<id>.json) from the demo data with an LLM.

    DATA_DIR=/tmp/mirror-build python -m tools.build_snapshots /out [ceo sales finance]

The snapshot is what the app loads when it starts without a model: the persona model the LLM
extracted, with every trait still pointing at the items that prove it (as ids and as short quotes,
so the evidence survives a re-ingestion). Greetings are written by hand in GREETINGS.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from app import db, profile
from app.config import settings
from app.context import as_person
from app.ingest import pipeline
from app.llm import LLM_CLIENT
from app.retrieval import index_for

GREETINGS = {
    "ceo": {"chat": "Καλημέρα. Δανάη εδώ — το AI αντίγραφό μου. Ρώτα με για προτεραιότητες, εγκρίσεις ή πώς θα το αποφάσιζα.",
            "thanks": "Τίποτα. Αν χρειαστεί κάτι πάνω από τα όριά σου, έλα με εισήγηση.",
            "how": "Καλά, Q4 με πολλή δουλειά: αξιόπιστη παράδοση και renewals πρώτα. Εσύ;"},
    "sales": {"chat": "Γεια! Αλέξανδρος εδώ (το AI αντίγραφό μου). Ρώτα με για προσφορές, εκπτώσεις και πελάτες.",
              "thanks": "Να 'σαι καλά! Ό,τι χρειαστείς για τον πελάτη, εδώ είμαι.",
              "how": "Όλα καλά, τρέχουμε τα renewals του Q4. Εσύ;"},
    "finance": {"chat": "Γεια σου. Μυρτώ εδώ — το AI αντίγραφό μου. Ρώτα με για όρους πληρωμής, πιστωτικά όρια και εγκρίσεις.",
                "thanks": "Τίποτα. Στείλε μου τα στοιχεία και το εξετάζω.",
                "how": "Καλά, κλείνουμε τις συμφωνίες του μήνα. Εσύ;"},
}


def _quote(text: str) -> str:
    """A distinctive 60-90 character fragment from the middle of an item (first full line that long)."""
    for line in text.splitlines():
        line = line.strip(" -*>#\t")
        if 40 <= len(line) <= 400 and not line.lower().startswith(("from:", "to:", "subject:", "date:")):
            return line[:90]
    return text.strip()[:90]


def main(out: Path, only: set[str] | None = None) -> None:
    db.connect()
    pipeline.ingest_demo(settings.demo_dir)
    if not LLM_CLIENT.available:
        sys.exit("Χρειάζεται ένα μοντέλο AI (OPENAI_API_KEY ή ANTHROPIC_API_KEY).")
    for row in db.query("SELECT id FROM persons ORDER BY id"):
        person = row["id"]
        if only and person not in only:
            continue
        with as_person(person):
            index_for(person).rebuild()
            items = {it["id"]: it for it in profile.all_items()}
            raw = profile.extract_with_llm(lambda p, m: print(f"  {person}: {m}", flush=True),
                                           cache=out / f".{person}.partials.json")
            for sec in profile.SECTIONS:
                for t in raw.get(sec, []) or []:
                    ev = []
                    for e in t.get("evidence", []) or []:
                        if isinstance(e, str) and e in items:
                            ev += [e, {"quote": _quote(items[e]["text"])}]
                    t["evidence"] = ev
            raw["owner_name"] = pipeline.owner_dict(person)["name"]
            raw["persona_greeting"] = GREETINGS.get(person, {})
            kept = profile.finalise(raw, "snapshot")
            print(f"{person}: " + ", ".join(f"{sec} {len(kept[sec])}" for sec in profile.SECTIONS))
        (out / f"{person}.json").write_text(json.dumps(raw, ensure_ascii=False, indent=1), "utf-8")


if __name__ == "__main__":
    main(Path(sys.argv[1] if len(sys.argv) > 1 else settings.snapshot_dir), set(sys.argv[2:]) or None)
