# Επεξήγηση: Ροή εισαγωγής: ανάγνωση, απόκρυψη προσωπικών στοιχείων, τεμαχισμός, αποθήκευση και ευρετήριο.
"""Ingestion pipeline: parse -> redact -> chunk -> (embed) -> store -> index."""
from __future__ import annotations

import hashlib
import secrets
import json
import re
import time
from collections import Counter
from pathlib import Path

import numpy as np

from .. import db
from ..context import as_person, pid
from ..llm import LLM_CLIENT
from ..privacy import redact
from ..retrieval import INDEX
from .parsers import Owner, RawItem, iter_demo_files, parse_file

KIND_OF_FILE = {".mbox": "email", ".eml": "email", ".json": "chat", ".pdf": "document", ".zip": "archive"}


def person_row(person_id: str | None = None) -> dict | None:
    return db.one("SELECT * FROM persons WHERE id=?", (person_id or pid(),))


def owner_dict(person_id: str | None = None) -> dict:
    row = person_row(person_id)
    if not row:
        return {"name": "Owner", "aliases": ["Owner"], "emails": []}
    meta = row.get("meta") or {}
    return {"id": row["id"], "name": row["name"], "display_name": row.get("display_name"), "role": row.get("role") or "",
            "reports_to": row.get("reports_to"), "aliases": meta.get("aliases", [row["name"]]),
            "emails": meta.get("emails", []), "org_domain": meta.get("org_domain", "")}


def get_owner() -> Owner:
    return Owner.from_dict(owner_dict())


# Επεξήγηση: Αποθηκεύουμε παράγωγο του κωδικού με salt, όχι τον ίδιο τον κωδικό.
def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(8)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 120_000).hex()
    return f"{salt}${digest}"


def check_password(password: str, stored: str | None) -> bool:
    if not stored or "$" not in stored:
        return False
    salt, _ = stored.split("$", 1)
    return secrets.compare_digest(hash_password(password, salt), stored)


def upsert_person(p: dict) -> None:
    login = p.get("login") or {}
    db.execute(
        "INSERT INTO persons(id, name, display_name, role, reports_to, email, pw_hash, meta) VALUES(?,?,?,?,?,?,?,?) "
        "ON CONFLICT(id) DO UPDATE SET name=excluded.name, display_name=excluded.display_name, role=excluded.role, "
        "reports_to=excluded.reports_to, email=excluded.email, "
        "pw_hash=COALESCE(excluded.pw_hash, persons.pw_hash), meta=excluded.meta",
        (p["id"], p["name"], p.get("display_name"), p.get("role", ""), p.get("reports_to"),
         (login.get("email") or "").lower() or None,
         hash_password(login["password"]) if login.get("password") else None,
         json.dumps({"aliases": p.get("aliases", []), "emails": p.get("emails", []),
                     "org_domain": p.get("org_domain", ""), "department": p.get("department", ""),
                     "username": (login.get("username") or "").lower(),
                     "has_ai": p.get("has_ai", True)}, ensure_ascii=False)))


# Επεξήγηση: Ακολουθεί την αλυσίδα προϊσταμένων, αποφεύγοντας κύκλους.
def ancestors(person_id: str) -> list[str]:
    """The reporting chain above a person (manager, manager's manager, ...)."""
    chain, seen = [], set()
    cur = person_row(person_id)
    while cur and cur.get("reports_to") and cur["reports_to"] not in seen:
        seen.add(cur["reports_to"])
        chain.append(cur["reports_to"])
        cur = person_row(cur["reports_to"])
    return chain


def _source_id(filename: str, data: bytes) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", Path(filename).stem.lower()).strip("-")[:24] or "source"
    return f"{pid()}-{slug}-{hashlib.sha1(data).hexdigest()[:6]}"


def chunk_text(text: str, max_chars: int = 900) -> list[str]:
    """Split by markdown headings, then paragraphs, keeping chunks <= max_chars."""
    sections = re.split(r"\n(?=#{1,3} )", text)
    chunks: list[str] = []
    for sec in sections:
        sec = sec.strip()
        if not sec:
            continue
        if len(sec) <= max_chars:
            chunks.append(sec)
            continue
        buf = ""
        for para in re.split(r"\n\s*\n|\n(?=[-*] |\*\*)", sec):
            para = para.strip()
            if not para:
                continue
            if len(buf) + len(para) + 2 > max_chars and buf:
                chunks.append(buf)
                buf = ""
            buf = f"{buf}\n\n{para}" if buf else para
        if buf:
            chunks.append(buf)
    return chunks or [text[:max_chars]]


def _source_kind(filename: str, items: list[RawItem]) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".txt" and items and items[0].kind == "chat":
        return "chat"
    if ext in (".md", ".txt", ".markdown"):
        return items[0].kind if items else "note"
    return KIND_OF_FILE.get(ext, "file")


# Επεξήγηση: Η πηγή και τα αποσπάσματα αποθηκεύονται για το τρέχον πρόσωπο.
def ingest_bytes(filename: str, data: bytes, *, consent: bool = True, actor: str = "owner") -> dict:
    owner = get_owner()
    raw_items = parse_file(filename, data, owner)
    if not raw_items:
        raise ValueError(f"Δεν βρέθηκε αναγνώσιμο περιεχόμενο στο {filename}")
    sid = _source_id(filename, data)
    if db.one("SELECT id FROM sources WHERE id=?", (sid,)):
        raise ValueError(f"Το {filename} έχει ήδη εισαχθεί")

    # link owner email replies to the message they answer (used for style exemplars)
    by_ext = {it.ext_id: it for it in raw_items if it.ext_id}
    for it in raw_items:
        if it.is_owner and it.reply_to_ext and it.reply_to_ext in by_ext:
            it.meta["in_reply_to_text"] = by_ext[it.reply_to_ext].text

    pii = Counter()
    rows_items, rows_chunks = [], []
    ext_to_id: dict[str, str] = {}
    for n, it in enumerate(raw_items):
        iid = f"{sid}-{n:03d}"
        if it.ext_id:
            ext_to_id[it.ext_id] = iid
        r = redact(it.text)
        pii.update(r.counts)
        meta = dict(it.meta)
        if "in_reply_to_text" in meta:
            rr = redact(meta["in_reply_to_text"])
            meta["in_reply_to_text"] = rr.text
        rows_items.append([iid, sid, it.kind, it.channel, it.author, int(it.is_owner), it.audience,
                           it.counterpart, it.subject, it.ts, r.text, it.reply_to_ext, meta])
        for c, ch in enumerate(chunk_text(r.text)):
            rows_chunks.append([f"{iid}.{c}", iid, sid, ch])

    for row in rows_items:
        row[11] = ext_to_id.get(row[11]) if row[11] else None
        row[12] = json.dumps(row[12], ensure_ascii=False)

    vectors = LLM_CLIENT.embed([c[3] for c in rows_chunks])
    for i, c in enumerate(rows_chunks):
        c.append(vectors[i].astype(np.float32).tobytes() if vectors else None)

    kind = _source_kind(filename, raw_items)
    with db.tx() as conn:
        conn.execute(
            "INSERT INTO sources(id, person_id, name, kind, added_at, consent, n_items, pii, meta) "
            "VALUES(?,?,?,?,?,?,?,?,?)",
            (sid, pid(), Path(filename).name, kind, time.time(), int(consent), len(rows_items), json.dumps(dict(pii)),
             json.dumps({"owner_items": sum(1 for r in rows_items if r[5]), "chunks": len(rows_chunks),
                         "embedded": bool(vectors)})),
        )
        conn.executemany(
            "INSERT INTO items(id, source_id, kind, channel, author, is_owner, audience, counterpart, subject, ts, "
            "text, reply_to, meta) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", rows_items)
        conn.executemany("INSERT INTO chunks(id, item_id, source_id, text, embedding) VALUES(?,?,?,?,?)", rows_chunks)
    db.audit(actor, "ingest", source=sid, file=Path(filename).name, items=len(rows_items), pii=dict(pii))
    INDEX.rebuild()
    return {"source_id": sid, "items": len(rows_items), "chunks": len(rows_chunks), "pii_redacted": dict(pii),
            "kind": kind}


def load_org(demo_dir: Path) -> dict:
    org_file = demo_dir / "org.json"
    return json.loads(org_file.read_text("utf-8")) if org_file.exists() else {"persons": []}


# Επεξήγηση: Κάθε φάκελος demo εισάγεται στη χωριστή μνήμη του αντίστοιχου προσώπου.
def ingest_demo(demo_dir: Path) -> list[dict]:
    """Create the demo organisation and ingest each person's own footprint into their own memory."""
    org = load_org(demo_dir)
    db.set_setting("company", org.get("company", ""))
    results = []
    for p in org.get("persons", []):
        upsert_person(p)
    for p in org.get("persons", []):
        folder = demo_dir / p["id"]
        if not folder.exists():
            continue
        with as_person(p["id"]):
            for path in iter_demo_files(folder):
                try:
                    rel = path.relative_to(folder).as_posix()
                    results.append(ingest_bytes(rel, path.read_bytes(), actor="system"))
                except ValueError as exc:
                    results.append({"file": path.name, "error": str(exc)})
    return results


# Επεξήγηση: Ακυρώνει σχετικές δημοσιεύσεις πριν αφαιρέσει την πηγή και ενημερώσει το ευρετήριο.
def delete_source(source_id: str) -> dict:
    src = db.one("SELECT * FROM sources WHERE id=? AND person_id=?", (source_id, pid()))
    if not src:
        raise KeyError(source_id)
    item_ids = [r["id"] for r in db.query("SELECT id FROM items WHERE source_id=?", (source_id,))]
    from .. import sharing
    sharing.invalidate_source(pid(), source_id)
    with db.tx() as conn:
        conn.execute("DELETE FROM chunks WHERE source_id=?", (source_id,))
        conn.execute("DELETE FROM items WHERE source_id=?", (source_id,))
        conn.execute("DELETE FROM sources WHERE id=?", (source_id,))
    db.audit("owner", "forget_source", source=source_id, name=src["name"], items=len(item_ids))
    INDEX.rebuild()
    return {"deleted_items": item_ids, "name": src["name"]}


# Επεξήγηση: Η ανάκληση συγκατάθεσης αποκλείει την πηγή από τη χρήση της.
def set_consent(source_id: str, consent: bool) -> None:
    if not consent:
        from .. import sharing
        sharing.invalidate_source(pid(), source_id)
    db.execute("UPDATE sources SET consent=? WHERE id=? AND person_id=?", (int(consent), source_id, pid()))
    db.audit("owner", "consent", source=source_id, consent=consent)
    INDEX.rebuild()
