# Επεξήγηση: Η δημοσίευση εταιρικού κανόνα απαιτεί ρητή έγκριση για το ακριβές περιεχόμενό του.
"""Access to published traits and explicitly selected synthetic demo sources.

Model output and snapshot flags never grant access. User publications are bound
to reviewed content and live evidence. The shipped demo manifest names the
synthetic sources and official policies available along the demo reporting line.
"""
from __future__ import annotations

import hashlib
import json
import time

from . import db
from .config import BASE_DIR
from .context import CURRENT_VIEWER, as_person, pid

SECTIONS = ('values', 'decision_rules')
PUBLIC_FIELDS = ('id', 'text', 'rule', 'first_person', 'when', 'prefers', 'avoids', 'scope', 'confidence')
DEMO_ACCESS = json.loads((BASE_DIR / "data" / "demo_access.json").read_text("utf-8"))


def restricted(person: str | None = None) -> bool:
    viewer = CURRENT_VIEWER.get()
    return viewer is not None and viewer != (person or pid())


def demo_source_ids(person: str, kind: str, viewer: str | None = None) -> frozenset[str]:
    """Resolve the checked-in source IDs against the consented sources in this installation."""
    from .ingest.pipeline import ancestors

    viewer = viewer if viewer is not None else CURRENT_VIEWER.get()
    if viewer is not None and viewer != person and person not in ancestors(viewer):
        return frozenset()
    expected = DEMO_ACCESS.get(person, {}).get(kind, [])
    if not expected or db.get_setting("company") != "NexaTech Solutions":
        return frozenset()
    placeholders = ", ".join("?" for _ in expected)
    rows = db.query(f"SELECT id FROM sources WHERE person_id=? AND consent=1 AND id IN ({placeholders})",
                    (person, *expected))
    return frozenset(row["id"] for row in rows)


def demo_style_examples(person: str) -> list[dict]:
    ids = sorted(demo_source_ids(person, "style"))
    if not ids:
        return []
    placeholders = ", ".join("?" for _ in ids)
    return db.query(f"SELECT i.* FROM items i JOIN sources s ON s.id=i.source_id "
                    f"WHERE s.person_id=? AND s.consent=1 AND i.is_owner=1 "
                    f"AND i.source_id IN ({placeholders}) ORDER BY i.id", (person, *ids))


def demo_rules(person: str, viewer: str | None = None) -> list[dict]:
    entry = DEMO_ACCESS.get(person, {})
    if not entry.get("rules") or entry["policy_source"] not in demo_source_ids(person, "business", viewer):
        return []
    return [{"section": "decision_rules", "scope": "company", "evidence": [], "confidence": 0.95,
             "demo_policy": "DOC02", **rule} for rule in entry["rules"]]


def demo_work_topics(person: str) -> list[dict]:
    sources = demo_source_ids(person, "business")
    topics = []
    for topic in DEMO_ACCESS.get(person, {}).get("topics", []):
        if topic["source"] not in sources:
            continue
        chunk = db.one("SELECT text FROM chunks WHERE source_id=? AND instr(text, ?) = 1",
                       (topic["source"], topic["heading"] + "\n"))
        if chunk:
            body = chunk["text"].split("\n", 1)[1].replace("**", "").strip()
            topics.append({"id": topic["id"], "category": "εργασία", "confidence": 0.9, "evidence": [],
                           "text": f"{topic['title']}\n{body}"})
    return topics


# Επεξήγηση: Δένει την έγκριση με το περιεχόμενο και τα τεκμήρια που εξετάστηκαν.
def content_hash(section: str, trait: dict) -> str:
    data = {k: trait[k] for k in PUBLIC_FIELDS if k in trait}
    # A changed/revoked evidence set also invalidates its publication.
    data['evidence'] = sorted(trait.get('evidence') or [])
    return hashlib.sha256(db.dumps([section, data]).encode()).hexdigest()


# Επεξήγηση: Χαρακτηριστικό χωρίς ταιριαστή ανθρώπινη έγκριση δεν μοιράζεται.
def approved_traits(person: str, prof: dict) -> list[dict]:
    records = {r['trait_id']: r for r in db.query('SELECT * FROM trait_publications WHERE person_id=?', (person,))}
    out = []
    for section in SECTIONS:
        for trait in prof.get(section, []):
            record = records.get(trait['id'])
            if (trait.get('scope') != 'company' or not record or record['section'] != section
                    or record['content_hash'] != content_hash(section, trait)):
                continue
            public = {k: trait[k] for k in PUBLIC_FIELDS if k in trait}
            public.update(section=section, evidence=[], publication={
                'approved_by': record['approved_by'], 'approved_at': record['approved_at'],
                'content_hash': record['content_hash']})
            out.append(public)
    return out


def public_identity(person: str) -> dict:
    from .ingest.pipeline import owner_dict
    owner = owner_dict(person)
    return {k: owner.get(k) for k in ('id', 'name', 'display_name', 'role', 'reports_to')}


# Επεξήγηση: Η κοινή προβολή συνδυάζει δημοσιευμένους κανόνες και επιλεγμένο συνθετικό υλικό.
def public_profile(prof: dict, person: str) -> dict:
    traits = demo_rules(person) + approved_traits(person, prof)
    voice_notes = DEMO_ACCESS.get(person, {}).get("voice_notes", []) if demo_source_ids(person, "style") else []
    public = {'owner': prof.get('owner', {}), 'summary': '', 'voice_notes': voice_notes, 'unknowns': [],
            'persona_greeting': {}, 'style': {}, 'graph': {}, 'version': prof.get('version'),
            'meta': {'method': 'shared-profile'},
            **{section: [t for t in traits if t['section'] == section]
               for section in ('values', 'decision_rules', 'preferences', 'relationships')}}
    public["knowledge"] = demo_work_topics(person)
    return public


# Επεξήγηση: Μόνο ο κάτοχος εγκρίνει ή ανακαλεί τη δημοσίευση δικού του εταιρικού κανόνα.
def set_publication(person: str, trait_id: str, published: bool, expected_hash: str | None = None) -> None:
    from . import profile
    # This is an owner operation, never a capability inherited from a superior.
    viewer = CURRENT_VIEWER.get()
    if viewer is not None and viewer != person:
        raise PermissionError('Only the owner may publish this rule')
    with as_person(person):
        prof = profile.current()
        match = next(((s, t) for s in SECTIONS for t in (prof or {}).get(s, []) if t['id'] == trait_id), None)
        if not match:
            raise KeyError(trait_id)
        if published:
            section, trait = match
            if expected_hash != content_hash(section, trait):
                raise ValueError('Ο κανόνας άλλαξε. Έλεγξε ξανά το περιεχόμενο πριν τη δημοσίευση.')
            if trait.get('scope') != 'company':
                raise ValueError('Δημοσιεύονται μόνο χαρακτηριστικά με ρητό εταιρικό πεδίο (company).')
            db.execute('INSERT INTO trait_publications(person_id,trait_id,section,content_hash,approved_by,approved_at) '
                       'VALUES(?,?,?,?,?,?) ON CONFLICT(person_id,trait_id) DO UPDATE SET '
                       'section=excluded.section,content_hash=excluded.content_hash,approved_by=excluded.approved_by,'
                       'approved_at=excluded.approved_at',
                       (person, trait_id, section, content_hash(section, trait), person, time.time()))
        else:
            db.execute('DELETE FROM trait_publications WHERE person_id=? AND trait_id=?', (person, trait_id))
        db.audit('owner', 'publish_rule' if published else 'revoke_rule', trait=trait_id)


def review_rules(person: str) -> list[dict]:
    from . import profile
    with as_person(person):
        prof = profile.current() or {}
    approved = {t['id'] for t in approved_traits(person, prof)}
    return [{'id': t['id'], 'section': section, 'text': t.get('rule') or t.get('text') or '',
             'published': t['id'] in approved, 'content_hash': content_hash(section, t),
             'content': {k: t[k] for k in PUBLIC_FIELDS if k in t}}
            for section in SECTIONS for t in prof.get(section, []) if t.get('scope') == 'company']


# Επεξήγηση: Αποτυπώνει το σύνολο εγκρίσεων για έλεγχο παλιού ιστορικού και ήχου.
def access_fingerprint(viewer: str, target: str) -> str:
    from . import profile
    if viewer == target:
        return 'owner-v1:' + viewer
    rows = []
    from .ingest.pipeline import ancestors
    for person in (target, *ancestors(target)):
        with as_person(person):
            prof = profile.current() or {}
        rows += [(person, t['id'], t['publication']) for t in approved_traits(person, prof)]
        rows.append((person, sorted(demo_source_ids(person, "business", viewer)),
                     sorted(demo_source_ids(person, "style", viewer)), demo_rules(person, viewer)))
    return 'shared-v2:' + hashlib.sha256(db.dumps([viewer, target, rows]).encode()).hexdigest()


# Επεξήγηση: Παλιό ιστορικό με διαφορετικά δικαιώματα δεν επαναχρησιμοποιείται.
def visible_messages(rows: list[dict], viewer: str, target: str) -> list[dict]:
    if viewer == target:
        return rows
    stamp = access_fingerprint(viewer, target)
    return [r for r in rows if (r.get('payload') or {}).get('access_fingerprint') == stamp]


# Επεξήγηση: Η επαναφορά συγκατάθεσης δεν ανασταίνει προηγούμενες ακυρωμένες εγκρίσεις.
def invalidate_source(person: str, source_id: str) -> None:
    """Restoring consent must not resurrect a publication invalidated by withdrawal."""
    from . import profile
    item_ids = {r['id'] for r in db.query('SELECT id FROM items WHERE source_id=?', (source_id,))}
    with as_person(person):
        prof = profile.latest() or {}
    for section in SECTIONS:
        for trait in prof.get(section, []):
            if item_ids.intersection(trait.get('evidence') or []):
                db.execute('DELETE FROM trait_publications WHERE person_id=? AND trait_id=?', (person, trait['id']))
