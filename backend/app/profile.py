# Επεξήγηση: Χτίζει την περσόνα από τεκμήρια και προσθέτει μόνο τους εγκεκριμένους κληρονομούμενους κανόνες.
"""The persona model: an inspectable, evidence-backed profile of the owner.

Pipeline (LLM mode):  map (extract candidate traits per batch, with item ids
as citations) -> reduce (merge, dedupe, rank) -> deterministic post-processing
(confidence from evidence, stylometry, knowledge graph).

Every trait carries the ids of the items that support it. Deleting a source
removes its evidence, and traits left without evidence disappear: forgetting
data really changes the twin.
"""
from __future__ import annotations

import json
from pathlib import Path
import re
import time
import unicodedata
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable

from . import db, prompts, sharing
from .config import settings
from .context import as_person, pid
from .ingest.pipeline import ancestors, get_owner, owner_dict
from .llm import LLM_CLIENT
from .stylometry import build_style

SECTIONS = ("values", "knowledge", "preferences", "decision_rules", "relationships")
PREFIX = {"values": "v", "knowledge": "k", "preferences": "p", "decision_rules": "r", "relationships": "h"}


# ------------------------------------------------------------------ helpers

def _fold(s: str) -> str:
    s = unicodedata.normalize("NFD", (s or "").lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def owner_items() -> list[dict]:
    return db.query(
        "SELECT i.* FROM items i JOIN sources s ON s.id=i.source_id WHERE s.consent=1 AND i.is_owner=1 "
        "AND s.person_id=? ORDER BY ts", (pid(),))


def all_items() -> list[dict]:
    return db.query("SELECT i.* FROM items i JOIN sources s ON s.id=i.source_id WHERE s.consent=1 "
                    "AND s.person_id=? ORDER BY ts", (pid(),))


def format_item(it: dict, max_chars: int = 1500) -> str:
    who = "OWNER" if it["is_owner"] else (it.get("author") or "?")
    to = f" -> {it['counterpart']}" if it.get("counterpart") and it["is_owner"] else ""
    subj = f' | "{it["subject"]}"' if it.get("subject") else ""
    date = (it.get("ts") or "")[:10]
    text = it["text"] if len(it["text"]) <= max_chars else it["text"][:max_chars] + " …"
    return f"[{it['id']}] ({it['channel']}, {date}, {who}{to}{subj})\n{text}"


def _resolve_evidence(ev: list, items: dict[str, dict], folded: dict[str, str]) -> list[str]:
    out = []
    for e in ev or []:
        if isinstance(e, str) and e in items:
            out.append(e)
        elif isinstance(e, str):
            m = re.search(r"[\w.-]+-\d{3}", e)
            if m and m.group(0) in items:
                out.append(m.group(0))
        elif isinstance(e, dict) and e.get("quote"):
            q = _fold(e["quote"])
            for iid, t in folded.items():
                if q in t:
                    out.append(iid)
                    break
    return list(dict.fromkeys(out))


def _confidence(n_evidence: int, llm_conf: float | None) -> float:
    base = min(0.95, 0.4 + 0.15 * n_evidence)
    if llm_conf is not None:
        try:
            base = 0.6 * base + 0.4 * float(llm_conf)
        except (TypeError, ValueError):
            pass
    return round(min(base, 0.97), 2)


# Επεξήγηση: Συνδέει χαρακτηριστικά με τεκμήρια και υπολογίζει τα συμπληρωματικά στοιχεία του προφίλ.
def finalise(raw: dict, method: str, note: str = "") -> dict:
    """Attach ids, resolve evidence, compute confidence, add stylometry + graph."""
    items = {it["id"]: it for it in all_items()}
    folded = {iid: _fold(it["text"]) for iid, it in items.items()}
    owner = get_owner()
    prof: dict[str, Any] = {
        "owner": {"name": owner.name, "display_name": owner.display_name, "role": owner.role},
        "summary": raw.get("summary", ""),
        "voice_notes": raw.get("voice_notes", [])[:10],
        "unknowns": raw.get("unknowns", [])[:10],
        "persona_greeting": raw.get("persona_greeting", {}),
    }
    for sec in SECTIONS:
        out = []
        for n, t in enumerate(raw.get(sec, []) or []):
            if not isinstance(t, dict):
                continue
            ev = _resolve_evidence(t.get("evidence", []), items, folded)
            verified = bool(t.get("owner_verified"))
            if not ev and not verified:
                continue
            t = dict(t)
            t["id"] = t.get("id") or f"{PREFIX[sec]}{n + 1}"
            t["evidence"] = ev
            t["confidence"] = 1.0 if verified else _confidence(len(ev), t.get("confidence"))
            if sec == "decision_rules":
                t["prefers"] = [str(x) for x in t.get("prefers", [])][:12]
                t["avoids"] = [str(x) for x in t.get("avoids", [])][:12]
            out.append(t)
        prof[sec] = out
    prof["style"] = build_style(owner_items(), [i for i in items.values() if not i["is_owner"]])
    prof["graph"] = build_graph(list(items.values()), owner.aliases)
    prof["meta"] = {
        "method": method,
        "note": note,
        "built_at": time.time(),
        "items_used": len(items),
        "owner_items": sum(1 for it in items.values() if it["is_owner"]),
        "llm": f"{LLM_CLIENT.provider}:{LLM_CLIENT.model}" if method == "llm" else None,
    }
    return prof


# ------------------------------------------------------------------ graph

ENTITY_RE = re.compile(r"\b([A-ZΑ-ΩΆ-Ώ][\wά-ώ]+(?:\s+[A-ZΑ-ΩΆ-Ώ][\wά-ώ]+){0,2})")
ENTITY_STOP = {
    "Hi", "Hey", "Dear", "Thanks", "Best", "The", "This", "That", "What", "Why", "When", "We", "I", "If", "It",
    "Our", "My", "Yes", "No", "One", "Two", "Let's", "Happy", "Honest", "Short", "Proposal", "Option", "Options",
    "Decision", "Review", "Result", "Huge", "Only", "Since", "Between", "Things", "Still", "First", "Read", "Note",
    "Mission", "Principles", "Owner", "Contact", "Process", "Moved", "Hottest", "Proud", "Worried", "Αγαπητή",
    "Καλημέρα", "Σας", "Θα", "Με", "Για", "Δεν", "Μπορούμε", "Προτείνω", "Ο", "Η", "Το", "Sept", "Oct", "Aug",
    "July", "June", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday", "Πάμε", "Stack",
    "Board", "Most", "Full", "Good", "Great", "Way", "Changing", "Running", "Talk", "Write", "Accessibility",
    "Expanding", "Selling", "Car", "Bet", "Kind", "Partnerships", "Regards", "Agenda", "Feedback", "Agreed",
    "Disagree", "Pushed", "Explained", "Wants", "Feels", "She", "He", "Not", "Q4", "Go", "Will",
}


def build_graph(items: list[dict], owner_aliases: list[str]) -> dict:
    alias_f = {_fold(a) for a in owner_aliases}
    people: Counter = Counter()
    ent_items: dict[str, set] = defaultdict(set)
    for it in items:
        for who in (it.get("author"), it.get("counterpart")):
            if who and who not in ("owner",) and _fold(who) not in alias_f and "@" not in who and len(who) > 2:
                people[who] += 1
                ent_items[who].add(it["id"])
        for m in ENTITY_RE.finditer(it["text"]):
            e = m.group(1).strip()
            first = e.split()[0]
            if first in ENTITY_STOP or e in ENTITY_STOP or _fold(e) in alias_f or len(e) < 3:
                continue
            ent_items[e].add(it["id"])
    # merge single first names into full names ("Maria" -> "Maria Alexiou")
    full = [p for p in people if " " in p]
    for e in list(ent_items):
        if " " not in e:
            match = [p for p in full if p.split()[0] == e]
            if len(match) == 1:
                ent_items[match[0]] |= ent_items.pop(e)
    nodes = []
    for e, ids in ent_items.items():
        if len(ids) < 2 and e not in people:
            continue
        nodes.append({"id": e, "type": "person" if e in people else "topic", "weight": len(ids)})
    nodes.sort(key=lambda n: -n["weight"])
    nodes = nodes[:36]
    keep = {n["id"] for n in nodes}
    edges = []
    names = sorted(keep)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            w = len(ent_items[a] & ent_items[b])
            if w >= 1 and (w >= 2 or a in people or b in people):
                edges.append({"source": a, "target": b, "weight": w})
    edges.sort(key=lambda e: -e["weight"])
    return {"nodes": nodes, "edges": edges[:90]}


# ------------------------------------------------------------------ builders

EXTRACT_CHARS = 6000


def _batches(items: list[dict], max_chars: int = 10000) -> list[list[dict]]:
    out, cur, size = [], [], 0
    for it in items:
        s = len(format_item(it, EXTRACT_CHARS))
        if cur and size + s > max_chars:
            out.append(cur)
            cur, size = [], 0
        cur.append(it)
        size += s
    if cur:
        out.append(cur)
    return out


def build_with_llm(progress: Callable[[float, str], None] | None = None) -> dict:
    return finalise(extract_with_llm(progress), "llm")


# Επεξήγηση: Αναλύει τα δεδομένα σε ομάδες και συγχωνεύει τα ευρήματα με τις παραπομπές τους.
def extract_with_llm(progress: Callable[[float, str], None] | None = None, cache: Path | None = None) -> dict:
    """The merged persona model as the model returned it (evidence still as item ids).

    `cache`: optional file that keeps the per-batch results, so a failed merge does not repeat the extraction."""
    owner = get_owner()
    items = all_items()
    if not items:
        raise ValueError("Δεν έχουν εισαχθεί ακόμα δεδομένα")
    batches = _batches(items)
    progress = progress or (lambda p, m: None)
    progress(0.05, f"Εξαγωγή χαρακτηριστικών από {len(items)} στοιχεία σε {len(batches)} ομάδες")
    done = 0

    def run(batch: list[dict]) -> dict:
        nonlocal done
        user = prompts.EXTRACT_USER.format(
            owner=owner.name, role=owner.role, items="\n\n".join(format_item(i, EXTRACT_CHARS) for i in batch))
        out = LLM_CLIENT.json(prompts.EXTRACT_SYSTEM.format(owner=owner.name), user, max_tokens=6000,
                              effort="medium")
        done += 1
        progress(0.05 + 0.65 * done / len(batches), f"Αναλύθηκε η ομάδα {done}/{len(batches)}")
        return out

    if cache and cache.exists():
        partials = json.loads(cache.read_text("utf-8"))
    else:
        with ThreadPoolExecutor(max_workers=settings.max_parallel_llm) as pool:
            partials = list(pool.map(run, batches))
        if cache:
            cache.write_text(json.dumps(partials, ensure_ascii=False), "utf-8")

    candidates: dict[str, list] = {sec: [] for sec in SECTIONS}
    extra = {"voice_notes": [], "unknowns": []}
    for p in partials:
        for sec in SECTIONS:
            candidates[sec].extend(x for x in p.get(sec, []) or [] if isinstance(x, dict))
        for k in extra:
            extra[k].extend(str(x) for x in p.get(k, []) or [])
    progress(0.75, "Συγχώνευση και αφαίρεση διπλότυπων")
    merged = LLM_CLIENT.json(
        prompts.MERGE_SYSTEM.format(owner=owner.name),
        prompts.MERGE_USER.format(owner=owner.name, role=owner.role,
                                  candidates=json.dumps({**candidates, **extra}, ensure_ascii=False)),
        max_tokens=12000, effort="low",
    )
    progress(0.95, "Υπολογισμός ύφους και γράφου γνώσης")
    return merged


SENT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
PREF_RE = re.compile(r"\b(prefer|rather|love|like|hate|don't like|never|always|no meetings|προτιμ|μου αρέσ|ποτέ|πάντα)",
                     re.I)
DEC_RE = re.compile(r"\b(decision|decided|decide|recommend|my vote|my call|why:|because|αποφασ|προτείνω|γιατί)", re.I)
KW_RE = re.compile(r"[\wά-ώ]{5,}", re.U)


def build_heuristic(note: str = "") -> dict:
    """Offline fallback: pattern-based extraction. Coarser, but fully explainable."""
    mine = owner_items()
    raw: dict[str, list] = {sec: [] for sec in SECTIONS}
    seen: set[str] = set()
    for it in mine:
        for s in SENT_RE.split(it["text"]):
            s = s.strip(" -*•\t")
            if not (25 <= len(s) <= 220) or _fold(s) in seen:
                continue
            seen.add(_fold(s))
            if DEC_RE.search(s):
                kws = [w.lower() for w in KW_RE.findall(s)][:8]
                raw["decision_rules"].append({"rule": s, "when": "similar situations", "prefers": kws, "avoids": [],
                                              "evidence": [it["id"]], "confidence": 0.5})
            elif PREF_RE.search(s):
                raw["preferences"].append({"text": s, "polarity": "like", "domain": it["channel"],
                                           "evidence": [it["id"]], "confidence": 0.5})
            elif re.search(r"\d", s) and it["channel"] in ("doc", "note"):
                raw["knowledge"].append({"text": s, "category": "work", "evidence": [it["id"]], "confidence": 0.5})
    for sec in raw:
        raw[sec] = raw[sec][:25]
    owner = get_owner()
    raw["summary"] = f"{owner.name} — {owner.role}. Το προφίλ φτιάχτηκε offline με εξαγωγή βάσει μοτίβων."
    return finalise(raw, "heuristic", note or "Φτιάχτηκε χωρίς LLM. Σύνδεσε ένα μοντέλο AI για πιο πλούσιο προφίλ.")


# Επεξήγηση: Φορτώνει το έτοιμο demo προφίλ του σωστού προσώπου.
def load_snapshot() -> dict | None:
    p = settings.snapshot_dir / f"{pid()}.json"
    if not p.exists():
        return None
    raw = p.read_bytes()
    snap = json.loads(raw.decode("utf-8"))
    if snap.get("owner_name") != get_owner().name:
        return None
    prof = finalise(snap, "snapshot", "Έτοιμο προφίλ που συνοδεύει τα demo δεδομένα. "
                                      "Πάτα «Ξαναχτίσε» για να παραχθεί ζωντανά από τα δεδομένα.")
    prof["meta"]["snapshot_hash"] = snapshot_hash(raw)
    return prof


def snapshot_hash(raw: bytes | None = None) -> str | None:
    import hashlib

    if raw is None:
        path = settings.snapshot_dir / f"{pid()}.json"
        if not path.exists():
            return None
        raw = path.read_bytes()
    return hashlib.sha1(raw).hexdigest()[:12]


# ------------------------------------------------------------------ versions

# Επεξήγηση: Νέα έκδοση που αλλάζει κανόνα ή τεκμήρια ακυρώνει την παλιά έγκρισή του.
def save_version(profile: dict, method: str, note: str = "") -> int:
    # Discard changed approvals, so reverting/reusing an ID cannot revive them.
    for record in db.query('SELECT * FROM trait_publications WHERE person_id=?', (pid(),)):
        trait = next((t for t in profile.get(record['section'], []) if t['id']==record['trait_id']), None)
        if (not trait or trait.get('scope') != 'company'
                or sharing.content_hash(record['section'], trait) != record['content_hash']):
            db.execute('DELETE FROM trait_publications WHERE person_id=? AND trait_id=?', (pid(), record['trait_id']))
    vid = db.execute("INSERT INTO profile_versions(created_at, person_id, method, note, profile) VALUES(?,?,?,?,?)",
                     (time.time(), pid(), method, note, db.dumps(profile)))
    db.audit("system" if method != "owner-edit" else "owner", "profile_version", version=vid, method=method)
    return vid


def latest() -> dict | None:
    row = db.one("SELECT * FROM profile_versions WHERE person_id=? ORDER BY id DESC LIMIT 1", (pid(),))
    if not row:
        return None
    prof = row["profile"]
    prof["version"] = row["id"]
    # Older owner edits copied the original snapshot metadata into the new version.
    prof.setdefault("meta", {})["method"] = row["method"]
    return prof


# Επεξήγηση: Φιλτράρει χαρακτηριστικά που δεν έχουν πλέον διαθέσιμα τεκμήρια ή επιβεβαίωση κατόχου.
def current() -> dict | None:
    """Latest profile, with evidence filtered to data that still exists and is consented."""
    prof = latest()
    if not prof:
        return None
    alive = {r["id"] for r in db.query(
        "SELECT i.id FROM items i JOIN sources s ON s.id=i.source_id WHERE s.consent=1 AND s.person_id=?", (pid(),))}
    dropped = 0
    for sec in SECTIONS:
        kept = []
        for t in prof.get(sec, []):
            ev = [e for e in t.get("evidence", []) if e in alive]
            if not ev and not t.get("owner_verified"):
                dropped += 1
                continue
            if len(ev) != len(t.get("evidence", [])):
                t["confidence"] = _confidence(len(ev), None)
            t["evidence"] = ev
            kept.append(t)
        prof[sec] = kept
    prof["forgotten_traits"] = dropped
    return prof


INHERITABLE = ("values", "decision_rules")


# Επεξήγηση: Κληρονομούνται μόνο δημοσιευμένοι εταιρικοί κανόνες των ανωτέρων.
def inherited_traits(person_id: str | None = None) -> list[dict]:
    """Company values and decision rules inherited from everyone above this person, closest manager first.

    Personal habits of a manager (scope == "personal") are not inherited. Inherited ids are prefixed with
    the owner's id (e.g. "ceo.r5") so it is always visible where a rule comes from."""
    out: list[dict] = []
    for level, anc in enumerate(ancestors(person_id or pid()), start=1):
        with as_person(anc):
            prof = current()
            who = owner_dict(anc)
        if not prof:
            continue
        for t in sharing.demo_rules(anc) + sharing.approved_traits(anc, prof):
            out.append({**t, "id": f"{anc}.{t['id']}",
                        "inherited_from": {"id": anc, "name": who.get("name"), "display_name": who.get("display_name"),
                                           "role": who.get("role"), "level": level}})
    return out


def with_inheritance(prof: dict) -> dict:
    """Profile as shown to the owner: own traits plus a separate, read-only inherited block."""
    inh = inherited_traits()
    prof = dict(prof)
    prof["inherited"] = {
        "from": [sharing.public_identity(a) for a in ancestors(pid())],
        "values": [t for t in inh if t["section"] == "values"],
        "decision_rules": [t for t in inh if t["section"] == "decision_rules"],
    }
    return prof


# Επεξήγηση: Συνθέτει το προφίλ που επιτρέπεται να δει ο συγκεκριμένος χρήστης.
def for_twin() -> dict | None:
    """Profile the twin reasons with: inherited company rules first (they win on conflict), then own traits."""
    prof = current()
    if not prof:
        return None
    if sharing.restricted():
        prof = sharing.public_profile(prof, pid())
    inh = inherited_traits()
    if inh:
        prof = dict(prof)
        for sec in INHERITABLE:
            prof[sec] = [t for t in inh if t["section"] == sec] + list(prof.get(sec, []))
        prof["inherited_from"] = [sharing.public_identity(a) for a in ancestors(pid())]
    from . import learning  # 👍 / 👎 from every conversation move the weight of the traits they rated
    return learning.apply(prof, pid(), SECTIONS)


def trait_index(prof: dict) -> dict[str, dict]:
    return {t["id"]: {**t, "section": sec} for sec in SECTIONS for t in prof.get(sec, [])}


def diff(old: dict | None, new: dict) -> dict:
    def keyset(p: dict | None, sec: str) -> dict[str, str]:
        if not p:
            return {}
        return {_fold(t.get("text") or t.get("rule") or t.get("name") or ""): (t.get("text") or t.get("rule")
                                                                             or t.get("name") or "")
                for t in p.get(sec, [])}

    out = {}
    for sec in SECTIONS:
        a, b = keyset(old, sec), keyset(new, sec)
        out[sec] = {"added": [b[k] for k in b if k not in a][:12], "removed": [a[k] for k in a if k not in b][:12]}
    return out


def owner_edit(trait_id: str, action: str, text: str | None = None) -> dict:
    prof = current()
    if not prof:
        raise ValueError("Δεν υπάρχει ακόμα προφίλ")
    for sec in SECTIONS:
        for i, t in enumerate(prof.get(sec, [])):
            if t["id"] != trait_id:
                continue
            if action == "delete":
                prof[sec].pop(i)
            elif action == "verify":
                t["owner_verified"] = True
                t["confidence"] = 1.0
            elif action == "edit" and text:
                key = "rule" if sec == "decision_rules" else ("relation" if sec == "relationships" else "text")
                t[key] = text
                t["owner_verified"] = True
                t["confidence"] = 1.0
            else:
                raise ValueError("unknown action")
            prof.pop("version", None)
            save_version(prof, "owner-edit", f"{action} {trait_id}")
            db.audit("owner", f"trait_{action}", trait=trait_id, text=text)
            return prof
    raise KeyError(trait_id)


def add_owner_trait(section: str, text: str, scope: str = "personal") -> dict:
    prof = current()
    if not prof or section not in SECTIONS:
        raise ValueError("Άγνωστη ενότητα")
    n = len(prof[section]) + 1
    tid = f"{PREFIX[section]}o{n}"
    key = "rule" if section == "decision_rules" else "text"
    trait = {"id": tid, key: text, "evidence": [], "owner_verified": True, "confidence": 1.0, "scope": scope}
    if section == "decision_rules":
        trait.update({"when": "ορίστηκε από τον κάτοχο", "prefers": [w.lower() for w in KW_RE.findall(text)][:8], "avoids": []})
    prof[section].append(trait)
    prof.pop("version", None)
    save_version(prof, "owner-edit", f"add {tid}")
    return prof
