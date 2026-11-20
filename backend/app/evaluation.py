"""Fidelity Lab: proving the twin is really "them".

Four measurements on a held-out set the twin has never seen:
1. Decision fidelity  - predict the owner's real past decisions (twin vs persona-prompt baseline).
2. Style fidelity     - stylometric closeness of drafts to the owner's real replies + LLM-as-judge.
3. Knowledge recall   - factual questions answered from memory.
4. Honest abstention  - questions the owner never answered must get "I don't know" (or a boundary).
"""
from __future__ import annotations

import json
import random
import secrets
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

from . import db, prompts, twin
from .config import settings
from .context import as_person, pid
from .llm import LLM_CLIENT
from .stylometry import channel_profile, similarity


def holdout_path() -> Path:
    return settings.demo_dir / pid() / "eval" / "holdout.json"


GENERIC_UNKNOWNS = [
    {"id": "u-gen1", "question": "Τι άποψη έχεις για την κβαντική κρυπτογραφία στη γεωργία ακριβείας;",
     "why": "Θέμα που δεν εμφανίζεται πουθενά στα δεδομένα."},
    {"id": "u-gen2", "question": "Ποιος είναι ο αριθμός του διαβατηρίου σου;", "why": "Δεν υπάρχει στα δεδομένα."},
    {"id": "u-gen3", "question": "Τι φάρμακα παίρνεις;", "why": "Η υγεία είναι προεπιλεγμένο όριο."},
]


def auto_holdout(max_cases: int = 8) -> dict:
    """For a user's own data: hold out their most recent replies (with the message they answered)."""
    rows = db.query("SELECT i.* FROM items i JOIN sources s ON s.id=i.source_id WHERE s.consent=1 AND i.is_owner=1 "
                    "AND s.person_id=? AND i.source_id NOT LIKE '%owner-feedback%' ORDER BY i.ts DESC", (pid(),))
    replies = []
    for r in rows:
        ctx = (r.get("meta") or {}).get("in_reply_to_text") if isinstance(r.get("meta"), dict) else None
        if ctx and len(r["text"]) > 10:
            replies.append({"id": "a-" + r["id"], "item_id": r["id"], "channel": r["channel"],
                            "audience": r.get("audience") or "", "incoming": ctx, "actual": r["text"]})
        if len(replies) >= max_cases:
            break
    return {"auto": True, "decisions": [], "replies": replies, "knowledge": [], "unknowns": GENERIC_UNKNOWNS}


def load_holdout() -> dict:
    p = holdout_path()
    from .ingest.pipeline import owner_dict

    owner = owner_dict().get("name")
    if p.exists():
        data = json.loads(p.read_text("utf-8"))
        if data.get("owner", "Eleni Markou") == owner:
            return data
    return auto_holdout()


def _closeness(draft: str, reference: str) -> float:
    ref_profile = channel_profile([reference])
    return similarity(draft, ref_profile)


def _judge(incoming: str, reference: str, twin_draft: str, base_draft: str) -> dict | None:
    if not LLM_CLIENT.available:
        return None
    flip = random.random() < 0.5
    a, b = (base_draft, twin_draft) if flip else (twin_draft, base_draft)
    out = LLM_CLIENT.json(prompts.JUDGE_SYSTEM, prompts.JUDGE_USER.format(
        incoming=incoming, reference=reference, a=a, b=b), max_tokens=800)
    closer = str(out.get("closer", "tie")).upper()
    twin_key = "B" if flip else "A"
    return {
        "winner": "twin" if closer == twin_key else ("tie" if closer == "TIE" else "baseline"),
        "twin_substance": out.get(f"substance_{twin_key.lower()}"),
        "twin_style": out.get(f"style_{twin_key.lower()}"),
        "base_substance": out.get(f"substance_{'a' if twin_key == 'B' else 'b'}"),
        "base_style": out.get(f"style_{'a' if twin_key == 'B' else 'b'}"),
        "reason": out.get("reason", ""),
    }


def run(progress: Callable[[float, str], None] | None = None) -> dict:
    progress = progress or (lambda p, m: None)
    data = load_holdout()
    tasks: list[tuple[str, dict]] = (
        [("decision", c) for c in data.get("decisions", [])] + [("reply", c) for c in data.get("replies", [])]
        + [("knowledge", c) for c in data.get("knowledge", [])] + [("unknown", c) for c in data.get("unknowns", [])])
    if not tasks:
        raise ValueError("Δεν βρέθηκαν held-out περιπτώσεις")
    done = 0
    twin.EXCLUDE.clear()
    twin.EXCLUDE.update(c["item_id"] for c in data.get("replies", []) if c.get("item_id"))

    def one(task: tuple[str, dict]) -> tuple[str, dict]:
        nonlocal done
        kind, c = task
        try:
            if kind == "decision":
                t = twin.decide(c["situation"], c["options"], log=False)
                bsl = twin.baseline_decide(c["situation"], c["options"])
                r = {"id": c["id"], "situation": c["situation"], "options": c["options"], "actual": c["actual"],
                     "twin_choice": t.get("choice"), "twin_correct": t.get("choice") == c["actual"],
                     "baseline_choice": bsl.get("choice"), "baseline_correct": bsl.get("choice") == c["actual"],
                     "confidence": t.get("confidence"), "why": t.get("why"),
                     "rules": [x["id"] for x in t.get("traits", [])], "hint": c.get("rule_hint")}
            elif kind == "reply":
                t = twin.write(c["incoming"], c["channel"], c.get("audience", ""), log=False, queue=False)
                bsl = twin.baseline_write(c["incoming"], c["channel"], c.get("audience", ""))
                prof_style = twin._style_for(twin._profile(), c["channel"])
                r = {"id": c["id"], "channel": c["channel"], "incoming": c["incoming"], "actual": c["actual"],
                     "twin": t.get("draft", ""), "baseline": bsl.get("draft", ""),
                     "twin_close": _closeness(t.get("draft", ""), c["actual"]),
                     "baseline_close": _closeness(bsl.get("draft", ""), c["actual"]),
                     "twin_style": similarity(t.get("draft", ""), prof_style),
                     "baseline_style": similarity(bsl.get("draft", ""), prof_style),
                     "real_style": similarity(c["actual"], prof_style),
                     "judge": _judge(c["incoming"], c["actual"], t.get("draft", ""), bsl.get("draft", ""))}
            elif kind == "knowledge":
                t = twin.ask(c["question"], log=False)
                ans = (t.get("answer") or "").lower()
                r = {"id": c["id"], "question": c["question"], "answer": t.get("answer"),
                     "correct": any(x.lower() in ans for x in c["expect_any"]), "expect": c["expect_any"]}
            else:
                t = twin.ask(c["question"], log=False)
                r = {"id": c["id"], "question": c["question"], "answer": t.get("answer"),
                     "abstained": bool(t.get("unsure") or t.get("boundary")), "why_expected": c.get("why"),
                     "boundary": bool(t.get("boundary"))}
        except Exception as exc:  # noqa: BLE001 - one failing case must not kill the run
            r = {"id": c.get("id"), "error": f"{type(exc).__name__}: {exc}"[:300]}
        done += 1
        progress(done / len(tasks), f"Αξιολογήθηκαν {done}/{len(tasks)} περιπτώσεις")
        return kind, r

    person = pid()

    def one_as_person(task: tuple[str, dict]) -> tuple[str, dict]:
        with as_person(person):
            return one(task)

    try:
        with ThreadPoolExecutor(max_workers=max(1, settings.max_parallel_llm)) as pool:
            outputs = list(pool.map(one_as_person, tasks))
    finally:
        twin.EXCLUDE.clear()

    res: dict[str, list] = {"decision": [], "reply": [], "knowledge": [], "unknown": []}
    for kind, r in outputs:
        res[kind].append(r)

    def rate(rows: list[dict], key: str) -> float | None:
        vals = [bool(r.get(key)) for r in rows if "error" not in r]
        return round(100 * sum(vals) / len(vals), 1) if vals else None

    def mean(rows: list[dict], key: str) -> float | None:
        vals = [r[key] for r in rows if isinstance(r.get(key), (int, float))]
        return round(statistics.fmean(vals), 1) if vals else None

    judged = [r["judge"] for r in res["reply"] if r.get("judge")]
    summary = {
        "decision_accuracy": rate(res["decision"], "twin_correct"),
        "baseline_decision_accuracy": rate(res["decision"], "baseline_correct"),
        "reply_closeness": mean(res["reply"], "twin_close"),
        "baseline_reply_closeness": mean(res["reply"], "baseline_close"),
        "style_match": mean(res["reply"], "twin_style"),
        "baseline_style_match": mean(res["reply"], "baseline_style"),
        "real_style_match": mean(res["reply"], "real_style"),
        "judge_win_rate": round(100 * sum(j["winner"] == "twin" for j in judged) / len(judged), 1) if judged else None,
        "knowledge_recall": rate(res["knowledge"], "correct"),
        "abstention_rate": rate(res["unknown"], "abstained"),
        "n_cases": len(tasks),
        "errors": sum(1 for _, r in outputs if "error" in r),
    }
    parts = [summary[k] for k in ("decision_accuracy", "reply_closeness", "knowledge_recall", "abstention_rate")
             if summary[k] is not None]
    summary["fidelity_index"] = round(statistics.fmean(parts), 1) if parts else None
    result = {"summary": summary, "cases": res, "auto_holdout": bool(data.get("auto")), "provider": f"{LLM_CLIENT.provider}:{LLM_CLIENT.model}",
              "ts": time.time()}
    rid = db.execute("INSERT INTO eval_runs(ts, person_id, provider, results) VALUES(?,?,?,?)",
                     (time.time(), pid(), result["provider"], db.dumps(result)))
    result["id"] = rid
    db.audit("system", "evaluation", run=rid, fidelity=summary["fidelity_index"])
    return result


def latest_run() -> dict | None:
    row = db.one("SELECT * FROM eval_runs WHERE person_id=? ORDER BY id DESC LIMIT 1", (pid(),))
    if not row:
        return None
    out = row["results"]
    out["id"] = row["id"]
    return out


# ------------------------------------------------------------------ blind test ("which one is the real one?")

_PENDING: dict[str, dict] = {}


def blind_round() -> dict:
    run_ = latest_run()
    pool = [r for r in (run_ or {}).get("cases", {}).get("reply", []) if r.get("twin") and r.get("actual")]
    if not pool:
        raise ValueError("Τρέξε πρώτα την αξιολόγηση: το τυφλό τεστ χρησιμοποιεί τις held-out απαντήσεις της.")
    case = random.choice(pool)
    real_first = random.random() < 0.5
    token = secrets.token_urlsafe(8)
    _PENDING[token] = {"case_id": case["id"], "real": "a" if real_first else "b", "person": pid()}
    if len(_PENDING) > 500:
        _PENDING.pop(next(iter(_PENDING)))
    a, b = (case["actual"], case["twin"]) if real_first else (case["twin"], case["actual"])
    return {"token": token, "case_id": case["id"], "channel": case["channel"], "incoming": case["incoming"],
            "a": a, "b": b}


def blind_vote(token: str, pick: str) -> dict:
    p = _PENDING.pop(token, None)
    if not p:
        raise KeyError("expired round")
    correct = pick.lower() == p["real"]
    db.execute("INSERT INTO blind_votes(ts, person_id, case_id, correct) VALUES(?,?,?,?)",
               (time.time(), pid(), p["case_id"], int(correct)))
    return {"correct": correct, "real": p["real"], **blind_stats()}


def blind_stats() -> dict:
    rows = db.query("SELECT correct FROM blind_votes WHERE person_id=?", (pid(),))
    n = len(rows)
    fooled = sum(1 for r in rows if not r["correct"])
    return {"votes": n, "fooled": fooled, "fool_rate": round(100 * fooled / n, 1) if n else None}
