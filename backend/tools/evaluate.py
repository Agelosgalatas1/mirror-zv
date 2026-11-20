"""Run the fidelity evaluation for every person and print a short table.

    docker compose exec mirror python -m tools.evaluate            # with the configured model
    docker compose exec mirror python -m tools.evaluate --offline  # rule-based engine only
"""
from __future__ import annotations

import sys

from app import db, evaluation
from app.context import as_person
from app.llm import LLM_CLIENT
from app.main import bootstrap

ROWS = [("decision_accuracy", "Κρυφές αποφάσεις σωστά (%)"), ("baseline_decision_accuracy", "  απλό chatbot (%)"),
        ("reply_closeness", "Ομοιότητα απάντησης (%)"), ("baseline_reply_closeness", "  απλό chatbot (%)"),
        ("knowledge_recall", "Σωστές γνώσεις (%)"), ("abstention_rate", "Έντιμο «δεν ξέρω» (%)"),
        ("fidelity_index", "Δείκτης πιστότητας")]


def main() -> None:
    if "--offline" in sys.argv:
        LLM_CLIENT.configure("offline")
    bootstrap()
    people = [r["id"] for r in db.query("SELECT id FROM persons ORDER BY CASE WHEN reports_to IS NULL THEN 0 ELSE 1 END, id")]
    results = {}
    for p in people:
        with as_person(p):
            results[p] = evaluation.run()["summary"]
    print(f"{'':34}" + "".join(f"{p:>10}" for p in people))
    for key, label in ROWS:
        cells = "".join(f"{results[p].get(key) if results[p].get(key) is not None else '-':>10}" for p in people)
        print(f"{label:34}{cells}")
    print(f"πάροχος: {LLM_CLIENT.provider}:{LLM_CLIENT.model}")


if __name__ == "__main__":
    main()
