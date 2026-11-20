"""Human publication is the only authority for sharing ancestor knowledge.

Model output and snapshot flags never grant access. Approval is a separate DB
record bound to the exact reviewed content and live evidence. Public views never
include source text, citations to private items, private summaries or stylometry.
"""
from __future__ import annotations

import hashlib
import time

from . import db
from .context import CURRENT_VIEWER, as_person, pid

SECTIONS = ('values', 'decision_rules')
PUBLIC_FIELDS = ('id', 'text', 'rule', 'first_person', 'when', 'prefers', 'avoids', 'scope', 'confidence')


def restricted(person: str | None = None) -> bool:
    viewer = CURRENT_VIEWER.get()
    return viewer is not None and viewer != (person or pid())


def content_hash(section: str, trait: dict) -> str:
    data = {k: trait[k] for k in PUBLIC_FIELDS if k in trait}
    # A changed/revoked evidence set also invalidates its publication.
    data['evidence'] = sorted(trait.get('evidence') or [])
    return hashlib.sha256(db.dumps([section, data]).encode()).hexdigest()


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


def public_profile(prof: dict, person: str) -> dict:
    traits = approved_traits(person, prof)
    return {'owner': prof.get('owner', {}), 'summary': '', 'voice_notes': [], 'unknowns': [],
            'persona_greeting': {}, 'style': {}, 'graph': {}, 'version': prof.get('version'),
            'meta': {'method': 'published-company-rules'},
            **{section: [t for t in traits if t['section'] == section]
               for section in ('values', 'decision_rules', 'knowledge', 'preferences', 'relationships')}}


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
    return 'shared-v1:' + hashlib.sha256(db.dumps([viewer, target, rows]).encode()).hexdigest()


def visible_messages(rows: list[dict], viewer: str, target: str) -> list[dict]:
    if viewer == target:
        return rows
    stamp = access_fingerprint(viewer, target)
    return [r for r in rows if (r.get('payload') or {}).get('access_fingerprint') == stamp]


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
