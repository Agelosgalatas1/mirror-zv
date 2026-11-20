# Επεξήγηση: Μετατρέπει τα συνθετικά δεδομένα του παλιού έργου στη μορφή εισαγωγής του MIRROR.
"""Import the NexaTech Solutions datasets (team's ZV repo, folder `sources/`) as MIRROR demo data.

    python scripts/import_zv.py /path/to/ZV/sources

Writes backend/data/demo/{ceo,sales,finance}/ in formats the MIRROR pipeline ingests:
emails (.eml) and notes/documents/transcripts (.md/.txt) are copied as they are; Teams exports
become chat JSON; decision logs, workflow logs and draft/final pairs become readable Markdown.
The 12 November 2026 "examples" files are NOT ingested: they are the held-out evaluation set
(backend/data/demo/<id>/eval/holdout.json), so the twin never sees the answers it is tested on.
All data is synthetic.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "backend" / "data" / "demo"
PEOPLE = ("ceo", "sales", "finance")
HELD_OUT = {"M03_2026-11-12_decision_examples.md", "N06_2026-11-12_customer_conversation_examples.md",
            "N06_2026-11-12_risk_review_examples.md"}
LABELS = {
    "decision_id": "Απόφαση", "date": "Ημερομηνία", "event_time": "Χρόνος", "decider": "Αποφασίζει",
    "decision_owner": "Αποφασίζει", "decider_role": "Ρόλος", "title": "Τίτλος", "case": "Υπόθεση",
    "circumstances": "Συνθήκες", "options_considered": "Επιλογές", "choice": "Επιλογή", "decision": "Απόφαση",
    "rejected_alternative": "Απορρίφθηκε", "stated_reason": "Αιτιολόγηση", "rationale": "Αιτιολόγηση",
    "authority_limit": "Όριο εξουσιοδότησης", "policy_refs": "Πολιτικές", "human_final_action": "Τελική ανθρώπινη ενέργεια",
    "counterparty": "Αντισυμβαλλόμενος", "participants": "Συμμετέχοντες", "context": "Πλαίσιο", "draft": "Πρόχειρο",
    "final": "Τελικό κείμενο", "edit_notes": "Σημειώσεις επιμέλειας", "draft_author": "Πρόχειρο από",
    "editor": "Επιμέλεια από", "steps": "Βήματα", "actor": "Ποιος", "owner": "Υπεύθυνος",
}
SKIP_KEYS = {"synthetic", "related_source_ids", "message_id", "export_version", "seq"}


def _render(value, depth: int = 0) -> str:
    pad = "  " * depth
    if isinstance(value, dict):
        lines = []
        for k, v in value.items():
            if k in SKIP_KEYS or v in (None, "", [], {}):
                continue
            label = LABELS.get(k, k.replace("_", " "))
            if isinstance(v, (dict, list)):
                lines.append(f"{pad}- **{label}:**\n{_render(v, depth + 1)}")
            else:
                text = str(v).strip()
                lines.append(f"{pad}- **{label}:** " + (text if "\n" not in text else "\n\n" + text + "\n"))
        return "\n".join(lines)
    if isinstance(value, list):
        out = []
        for v in value:
            if isinstance(v, dict):
                out.append(_render(v, depth))
                out.append("")
            else:
                out.append(f"{pad}- {v}")
        return "\n".join(out).rstrip()
    return f"{pad}{value}"


def records_to_md(title: str, records: list[dict], heading_keys: tuple[str, ...]) -> str:
    parts = [f"# {title}", "", "Συνθετικά δεδομένα NexaTech Solutions.", ""]
    for r in records:
        head = " · ".join(str(r[k]) for k in heading_keys if r.get(k))
        parts += [f"## {head or 'Εγγραφή'}", "", _render(r), ""]
    return "\n".join(parts)


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text("utf-8").splitlines() if line.strip()]


def chat_to_json(path: Path) -> dict:
    """Any Teams-style export (flat or grouped in conversations) -> {"messages": [{author, text, ts, channel}]}."""
    data = json.loads(path.read_text("utf-8"))
    names = {p.get("email", "").lower(): p.get("name") for p in data.get("participants", []) if isinstance(p, dict)}
    default_channel = data.get("chat_name") or data.get("channel") or path.stem
    out: list[dict] = []

    def walk(node, channel: str) -> None:
        if isinstance(node, list):
            for x in node:
                walk(x, channel)
        elif isinstance(node, dict):
            if isinstance(node.get("text"), str) and any(k in node for k in ("from_name", "sender", "from", "author")):
                who = node.get("from_name") or node.get("sender") or node.get("author") or node.get("from")
                who = names.get(str(who).lower(), who)
                out.append({"author": who, "text": node["text"], "ts": node.get("timestamp") or node.get("ts"),
                            "channel": channel})
                return
            sub = node.get("topic") or node.get("title") or channel
            for k, v in node.items():
                if k in ("messages", "conversations", "threads", "replies"):
                    walk(v, sub if k == "messages" else channel)

    walk(data.get("conversations") or data.get("messages") or [], str(default_channel))
    return {"messages": out}


def import_person(src: Path, dst: Path) -> list[str]:
    written = []
    keep_eval = dst / "eval"
    saved_eval = None
    if keep_eval.exists():
        saved_eval = {p.name: p.read_bytes() for p in keep_eval.iterdir() if p.is_file()}
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for path in sorted(src.rglob("*")):
        if not path.is_file() or path.name.startswith(".") or path.name in HELD_OUT:
            continue
        rel = path.relative_to(src)
        folder = rel.parts[0] if len(rel.parts) > 1 else ""
        if path.suffix in (".eml", ".md", ".txt"):
            target = dst / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
        elif path.suffix == ".json" and folder in ("chats", "teams"):
            target = dst / "chats" / path.name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(chat_to_json(path), ensure_ascii=False, indent=1), "utf-8")
        elif path.name == "decisions.jsonl":
            target = dst / "docs" / "decision_log.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(records_to_md("Αρχείο αποφάσεων 2026", _read_jsonl(path),
                                            ("decision_id", "title", "case")), "utf-8")
        elif path.name == "workflow_events.jsonl":
            target = dst / "docs" / "workflow_log.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(records_to_md("Ροές εργασίας και εγκρίσεις 2026", _read_jsonl(path),
                                            ("workflow_id", "title")), "utf-8")
        elif path.name == "draft_final_pairs.json":
            target = dst / "docs" / "drafts_and_final_texts.md"
            target.parent.mkdir(parents=True, exist_ok=True)
            pairs = json.loads(path.read_text("utf-8")).get("pairs", [])
            target.write_text(records_to_md("Πρόχειρα και τελικά κείμενα", pairs, ("pair_id", "date")), "utf-8")
        else:
            continue
        written.append(str(target.relative_to(dst)))
    if saved_eval:
        keep_eval.mkdir(exist_ok=True)
        for name, data in saved_eval.items():
            (keep_eval / name).write_bytes(data)
    return written


def main() -> None:
    if len(sys.argv) > 1:
        src = Path(sys.argv[1]).expanduser().resolve()
    else:
        # Find a sibling ZV checkout even when MIRROR is nested one folder deeper (as on the team's desktop).
        src = next((parent / "ZV" / "sources" for parent in ROOT.parents
                    if (parent / "ZV" / "sources").is_dir()), ROOT.parent / "ZV" / "sources")
    for pid in PEOPLE:
        files = import_person(src / pid, OUT / pid)
        print(f"{pid}: {len(files)} αρχεία")


if __name__ == "__main__":
    main()
