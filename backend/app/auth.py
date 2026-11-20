"""Sessions and access rules shared by every API route.

A session is either an HttpOnly cookie (the web app) or a bearer token (API clients, tests).
Cookie-authenticated writes must carry the `X-Mirror-Request` header, which a cross-site form
cannot send: a simple CSRF guard on top of SameSite=Strict.
"""
from __future__ import annotations

import time

from fastapi import HTTPException, Request

from . import db
from .context import CURRENT_PERSON, CURRENT_VIEWER
from .ingest import pipeline

SESSION_TTL = 7 * 24 * 3600
COOKIE = "mirror_session"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def public_person(row: dict) -> dict:
    o = pipeline.owner_dict(row["id"])
    meta = row.get("meta") or {}
    return {"id": row["id"], "name": o["name"], "display_name": o.get("display_name"), "role": o.get("role"),
            "reports_to": o.get("reports_to"), "department": meta.get("department", ""),
            "username": meta.get("username", ""), "can_login": bool(row.get("pw_hash"))}


def session_token(request: Request) -> tuple[str, bool]:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip(), False
    return request.cookies.get(COOKIE, ""), True


async def current_user(request: Request) -> dict:
    """Resolve the session and set the person every following call runs as."""
    token, from_cookie = session_token(request)
    sess = db.one("SELECT * FROM sessions WHERE token=?", (token,)) if token else None
    if not sess or time.time() - sess["created_at"] > SESSION_TTL:
        raise HTTPException(401, "Χρειάζεται σύνδεση")
    if from_cookie and request.method not in SAFE_METHODS and request.headers.get("x-mirror-request") != "1":
        raise HTTPException(403, "Το αίτημα απορρίφθηκε.")
    row = pipeline.person_row(sess["person_id"])
    if not row:
        raise HTTPException(401, "Χρειάζεται σύνδεση")
    CURRENT_PERSON.set(row["id"])
    CURRENT_VIEWER.set(row["id"])
    return row


def has_ai(person_id: str) -> bool:
    """Employees in the demo company have no AI counterpart of their own (as in the team's ZV build)."""
    row = pipeline.person_row(person_id)
    return bool(row) and (row.get("meta") or {}).get("has_ai", True) is not False


def allowed_targets(person_id: str) -> list[str]:
    """A person can use their own twin and the twins of everyone they report to, nothing sideways."""
    return [p for p in (person_id, *pipeline.ancestors(person_id)) if has_ai(p)]


def check_target(user: dict, target: str | None) -> str:
    target = target or user["id"]
    if target not in allowed_targets(user["id"]):
        raise HTTPException(403, "Δεν έχεις πρόσβαση στο twin αυτού του προσώπου")
    return target
