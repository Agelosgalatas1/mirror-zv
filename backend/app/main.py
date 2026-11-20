"""MIRROR API + static frontend.

Organisation: a CEO and two managers (Sales, Finance) who report only to the CEO.
Each person has their own twin and their own memory. A manager's twin inherits the
CEO's company values and decision rules. Managers log in with email + password and can
talk to their own twin and consult the twin of the person they report to, but never
see the other manager's data.
"""
from __future__ import annotations

import logging
import secrets
import time
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import APIRouter, Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from starlette.exceptions import HTTPException as StarletteHTTPException
from pydantic import BaseModel, Field

from . import db, evaluation, jobs, mirror_api, profile, twin, voice
from .auth import COOKIE, SESSION_TTL, allowed_targets, check_target, current_user, public_person, session_token
from .config import settings
from .context import CURRENT_PERSON, as_person, pid
from .ingest import pipeline
from .ingest.parsers import SUPPORTED
from .llm import LLM_CLIENT, LLMError
from .privacy import DEFAULT_BOUNDARIES
from .retrieval import INDEX, index_for

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("mirror")

MAX_UPLOAD = 25 * 1024 * 1024


def _ensure_profile() -> None:
    """Make sure the current person has a persona model (shipped snapshot, or heuristic)."""
    latest = profile.latest()
    if latest and latest["meta"].get("method") in ("snapshot", "heuristic") \
            and latest["meta"].get("snapshot_hash") != profile.snapshot_hash():
        snap = profile.load_snapshot()  # the shipped snapshot changed (new version of the app)
        if snap:
            profile.save_version(snap, "snapshot", snap["meta"]["note"])
        return
    if not latest and db.one("SELECT i.id FROM items i JOIN sources s ON s.id=i.source_id WHERE s.person_id=? LIMIT 1",
                             (pid(),)):
        snap = profile.load_snapshot()
        prof = snap or profile.build_heuristic()
        profile.save_version(prof, prof["meta"]["method"], prof["meta"].get("note", ""))


def demo_fingerprint() -> str:
    """Changes whenever the shipped demo data changes (a new company, new files)."""
    import hashlib

    h = hashlib.sha256()
    for path in sorted(settings.demo_dir.rglob("*")):
        if path.is_file():
            h.update(path.relative_to(settings.demo_dir).as_posix().encode())
            h.update(hashlib.sha256(path.read_bytes()).digest())
    return h.hexdigest()[:16]


def bootstrap() -> None:
    db.connect()
    fingerprint = demo_fingerprint()
    seeded = db.one("SELECT id FROM persons LIMIT 1")
    if settings.auto_seed and seeded and db.get_setting("demo_fingerprint", None) != fingerprint:
        log.info("The shipped demo data changed: re-seeding")
        db.reset_all()
        db.execute("DELETE FROM sessions")
        db.execute("DELETE FROM persons")
        seeded = None
    if settings.auto_seed and not seeded:
        log.info("Seeding demo organisation from %s", settings.demo_dir)
        pipeline.ingest_demo(settings.demo_dir)
        db.set_setting("demo_fingerprint", fingerprint)
    else:
        for p in pipeline.load_org(settings.demo_dir).get("persons", []):
            pipeline.upsert_person(p)  # keep people / logins in sync with the shipped org file
    for row in db.query("SELECT id FROM persons"):
        with as_person(row["id"]):
            index_for(row["id"]).rebuild()
            _ensure_profile()
    log.info("MIRROR ready · LLM=%s:%s · %d people", LLM_CLIENT.provider, LLM_CLIENT.model,
             len(db.query("SELECT id FROM persons")))


@asynccontextmanager
async def lifespan(_: FastAPI):
    bootstrap()
    yield


app = FastAPI(title="MIRROR — your digital self", version="2.0.0", lifespan=lifespan)


@app.exception_handler(twin.TwinNotReady)
async def _not_ready(_: Request, exc: twin.TwinNotReady):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(StarletteHTTPException)
async def _http_error(_: Request, exc: StarletteHTTPException):
    """One error shape for both clients: `detail` (API) and `error` / `code` (web app)."""
    body = {"detail": exc.detail, "error": exc.detail}
    if isinstance(exc, mirror_api.MirrorAccess):
        body.update(code="mirror_access", mirror_id=exc.mirror_id)
    return JSONResponse(status_code=exc.status_code, content=body, headers=getattr(exc, "headers", None))


@app.exception_handler(LLMError)
async def _llm_error(_: Request, exc: LLMError):
    msg = f"Σφάλμα μοντέλου AI: {exc}"
    return JSONResponse(status_code=502, content={"detail": msg, "error": msg, "code": "provider"})


# ------------------------------------------------------------------ authentication

_public_person = public_person
_check_target = check_target


class LoginIn(BaseModel):
    username: str | None = Field(default=None, max_length=200)
    email: str | None = Field(default=None, max_length=200)
    password: str = Field(min_length=1, max_length=200)


def find_login(name: str) -> dict | None:
    name = name.strip().lower()
    if not name:
        return None
    for row in db.query("SELECT * FROM persons WHERE pw_hash IS NOT NULL"):
        if name in {(row.get("email") or "").lower(), ((row.get("meta") or {}).get("username") or "").lower()}:
            return row
    return None


@app.post("/api/login")
def login(body: LoginIn, response: Response):
    row = find_login(body.username or body.email or "")
    if not row or not pipeline.check_password(body.password, row.get("pw_hash")):
        time.sleep(0.4)  # slow down guessing
        raise HTTPException(401, "Λάθος στοιχεία σύνδεσης")
    token = secrets.token_urlsafe(32)
    db.execute("INSERT INTO sessions(token, person_id, created_at) VALUES(?,?,?)", (token, row["id"], time.time()))
    with as_person(row["id"]):
        db.audit("owner", "login")
    response.set_cookie(COOKIE, token, max_age=SESSION_TTL, httponly=True, samesite="strict", path="/")
    return {"token": token, "person": _public_person(row), **mirror_api.session_payload(row)}


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/org")
def org_public():
    """Who is in the organisation (names and roles only), for the login page."""
    return {"company": db.get_setting("company", ""), "persons": [_public_person(r) for r in db.query("SELECT * FROM persons")]}


api = APIRouter(prefix="/api", dependencies=[Depends(current_user)])


@app.post("/api/logout")
def logout(request: Request, response: Response):
    token, _ = session_token(request)
    if token:
        db.execute("DELETE FROM sessions WHERE token=?", (token,))
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


# ------------------------------------------------------------------ status / settings

@api.get("/status")
def status(user: dict = Depends(current_user)):
    prof = profile.latest()
    me = pid()
    counts = db.one(
        "SELECT (SELECT count(*) FROM sources WHERE person_id=?) s, "
        "(SELECT count(*) FROM items i JOIN sources s ON s.id=i.source_id WHERE s.person_id=?) i, "
        "(SELECT count(*) FROM items i JOIN sources s ON s.id=i.source_id WHERE s.person_id=? AND i.is_owner=1) o, "
        "(SELECT count(*) FROM chunks c JOIN sources s ON s.id=c.source_id WHERE s.person_id=?) c",
        (me, me, me, me))
    persons = [_public_person(r) for r in db.query("SELECT * FROM persons")]
    return {
        "owner": pipeline.owner_dict(),
        "me": _public_person(user),
        "org": {"company": db.get_setting("company", ""), "persons": persons},
        "targets": [_public_person(pipeline.person_row(t)) for t in allowed_targets(me)],
        "llm": LLM_CLIENT.info(),
        "voice": voice.capabilities(),
        "retrieval": {"chunks": INDEX.size, "hybrid": INDEX.has_embeddings},
        "counts": {"sources": counts["s"], "items": counts["i"], "owner_items": counts["o"], "chunks": counts["c"],
                   "pending_drafts": 0},
        "profile": {"version": prof.get("version"), "method": prof["meta"]["method"],
                    "built_at": prof["meta"]["built_at"]} if prof else None,
        "jobs": {k: jobs.running(k) for k in ("profile", "eval")},
        "supported_files": SUPPORTED,
    }


class LLMConfig(BaseModel):
    provider: Literal["auto", "anthropic", "openai", "ollama", "offline"]
    api_key: str | None = Field(default=None, max_length=400)
    model: str | None = Field(default=None, max_length=100)


@api.post("/llm")
def configure_llm(cfg: LLMConfig):
    try:
        info = LLM_CLIENT.configure(cfg.provider, cfg.api_key, cfg.model)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    db.audit("owner", "llm_config", provider=info["provider"], model=info["model"])  # key is never logged
    return info


# ------------------------------------------------------------------ sources / ingestion (own data only)

@api.get("/sources")
def list_sources():
    return {"sources": db.query("SELECT * FROM sources WHERE person_id=? ORDER BY added_at", (pid(),))}


@api.post("/sources")
async def upload(file: UploadFile = File(...)):
    data = await file.read()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "Πολύ μεγάλο αρχείο (έως 25 MB)")
    try:
        return pipeline.ingest_bytes(file.filename or "upload.txt", data)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


class ConsentIn(BaseModel):
    consent: bool


@api.patch("/sources/{sid}")
def consent(sid: str, body: ConsentIn):
    if not db.one("SELECT id FROM sources WHERE id=? AND person_id=?", (sid, pid())):
        raise HTTPException(404, "Άγνωστη πηγή")
    pipeline.set_consent(sid, body.consent)
    return {"ok": True}


@api.delete("/sources/{sid}")
def forget(sid: str):
    before = profile.current()
    try:
        res = pipeline.delete_source(sid)
    except KeyError as exc:
        raise HTTPException(404, "Άγνωστη πηγή") from exc
    after = profile.current()
    res["traits_forgotten"] = (after or {}).get("forgotten_traits", 0) - (before or {}).get("forgotten_traits", 0)
    return res


@api.get("/items/{iid}")
def get_item(iid: str, user: dict = Depends(current_user)):
    it = db.one("SELECT i.*, s.name AS source_name, s.person_id AS person_id FROM items i "
                "JOIN sources s ON s.id=i.source_id WHERE i.id=?", (iid,))
    # evidence is visible for your own data and for the people above you (inherited rules cite their data)
    if not it or it["person_id"] not in allowed_targets(user["id"]):
        raise HTTPException(404, "Δεν βρέθηκε (ίσως έχει διαγραφεί)")
    return it


@api.post("/reset-demo")
def reset_demo():
    db.reset_all()
    pipeline.ingest_demo(settings.demo_dir)
    for row in db.query("SELECT id FROM persons"):
        with as_person(row["id"]):
            index_for(row["id"]).rebuild()
            _ensure_profile()
    db.audit("owner", "reset_demo")
    return {"ok": True}


# ------------------------------------------------------------------ persona model

@api.get("/profile")
def get_profile(target: str | None = None, user: dict = Depends(current_user)):
    with as_person(_check_target(user, target)):
        prof = profile.current()
        if not prof:
            raise HTTPException(404, "Δεν υπάρχει ακόμα προφίλ")
        prof = profile.with_inheritance(prof)
        prof["read_only"] = pid() != user["id"]
        return prof


@api.get("/profile/versions")
def versions():
    rows = db.query("SELECT id, created_at, method, note FROM profile_versions WHERE person_id=? ORDER BY id DESC "
                    "LIMIT 30", (pid(),))
    return {"versions": rows}


@api.get("/profile/diff")
def profile_diff(a: int, b: int):
    va = db.one("SELECT profile FROM profile_versions WHERE id=? AND person_id=?", (a, pid()))
    vb = db.one("SELECT profile FROM profile_versions WHERE id=? AND person_id=?", (b, pid()))
    if not va or not vb:
        raise HTTPException(404, "Άγνωστη έκδοση")
    return profile.diff(va["profile"], vb["profile"])


@api.post("/profile/build")
def build_profile():
    def work(progress):
        before = profile.current()
        if LLM_CLIENT.available:
            prof = profile.build_with_llm(progress)
            method = "llm"
        else:
            progress(0.5, "Χωρίς μοντέλο AI: εξαγωγή βάσει μοτίβων")
            prof = profile.build_heuristic()
            method = "heuristic"
        vid = profile.save_version(prof, method, prof["meta"].get("note", ""))
        return {"version": vid, "diff": profile.diff(before, prof)}

    return jobs.start("profile", work)


class TraitEdit(BaseModel):
    action: Literal["delete", "verify", "edit"]
    text: str | None = None


@api.patch("/profile/traits/{tid}")
def edit_trait(tid: str, body: TraitEdit):
    if "." in tid:
        raise HTTPException(403, "Οι κανόνες που κληρονομούνται αλλάζουν μόνο από τον προϊστάμενο")
    try:
        return profile.with_inheritance(profile.owner_edit(tid, body.action, body.text))
    except KeyError as exc:
        raise HTTPException(404, "Άγνωστο χαρακτηριστικό") from exc


class TraitAdd(BaseModel):
    section: Literal["values", "knowledge", "preferences", "decision_rules"]
    text: str = Field(min_length=3, max_length=500)


@api.post("/profile/traits")
def add_trait(body: TraitAdd):
    return profile.with_inheritance(profile.add_owner_trait(body.section, body.text))


# ------------------------------------------------------------------ twin (own, or someone you report to)

class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    channel: str = "chat_team"
    history: list[dict] = Field(default_factory=list, max_length=20)
    target: str | None = None
    conversation_id: int | None = None


class WriteIn(BaseModel):
    incoming: str = Field(min_length=2, max_length=6000)
    channel: str = "email_external"
    audience: str = ""
    instructions: str = Field(default="", max_length=1000)
    critique: bool = True
    target: str | None = None


class DecideIn(BaseModel):
    situation: str = Field(min_length=5, max_length=4000)
    options: list[str] = Field(min_length=2, max_length=6)
    target: str | None = None


def _own_conversation(cid: int, user: dict) -> dict:
    conv = db.one("SELECT * FROM conversations WHERE id=? AND user_id=?", (cid, user["id"]))
    if not conv:
        raise HTTPException(404, "Η συνομιλία δεν βρέθηκε")
    return conv


@api.post("/twin/ask")
def ask(body: AskIn, user: dict = Depends(current_user)):
    target = _check_target(user, body.target)
    history = body.history
    conv = None
    if body.conversation_id:
        conv = _own_conversation(body.conversation_id, user)
        if conv["target"] != target:
            raise HTTPException(400, "Η συνομιλία ανήκει σε άλλο twin")
        rows = db.query("SELECT role, text, payload FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT 8",
                        (conv["id"],))
        history = [{"role": r["role"], "text": r["text"],
                    "traits": [t["id"] for t in (r["payload"] or {}).get("traits", [])]} for r in reversed(rows)]
    with as_person(target):
        res = twin.ask(body.question, body.channel, history=history)
    if conv:
        now = time.time()
        db.execute("INSERT INTO messages(conversation_id, role, text, payload, created_at) VALUES(?,?,?,?,?)",
                   (conv["id"], "user", body.question, "{}", now))
        res["message_id"] = db.execute(
            "INSERT INTO messages(conversation_id, role, text, payload, created_at) VALUES(?,?,?,?,?)",
            (conv["id"], "twin", res.get("answer", ""), db.dumps(res), now + 0.001))
        db.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now, conv["id"]))
    return res


# ------------------------------------------------------------------ conversations (saved chats, per user and twin)

class ConversationIn(BaseModel):
    target: str | None = None
    title: str = Field(default="Νέα συνομιλία", max_length=120)


@api.get("/conversations")
def list_conversations(target: str | None = None, user: dict = Depends(current_user)):
    t = _check_target(user, target)
    rows = db.query("SELECT c.*, (SELECT count(*) FROM messages m WHERE m.conversation_id=c.id) AS n FROM conversations c "
                    "WHERE c.user_id=? AND c.target=? ORDER BY c.updated_at DESC LIMIT 100", (user["id"], t))
    return {"conversations": rows}


@api.post("/conversations")
def create_conversation(body: ConversationIn, user: dict = Depends(current_user)):
    t = _check_target(user, body.target)
    now = time.time()
    title = body.title.strip()[:120] or "Νέα συνομιλία"
    cid = db.execute("INSERT INTO conversations(user_id, target, title, created_at, updated_at) VALUES(?,?,?,?,?)",
                     (user["id"], t, title, now, now))
    return db.one("SELECT * FROM conversations WHERE id=?", (cid,))


@api.get("/conversations/{cid}")
def get_conversation(cid: int, user: dict = Depends(current_user)):
    conv = _own_conversation(cid, user)
    conv["messages"] = db.query("SELECT id, role, text, payload, created_at FROM messages WHERE conversation_id=? "
                                "ORDER BY id", (cid,))
    return conv


class RenameIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)


@api.patch("/conversations/{cid}")
def rename_conversation(cid: int, body: RenameIn, user: dict = Depends(current_user)):
    _own_conversation(cid, user)
    db.execute("UPDATE conversations SET title=? WHERE id=?", (body.title.strip(), cid))
    return {"ok": True}


@api.delete("/conversations/{cid}")
def delete_conversation(cid: int, user: dict = Depends(current_user)):
    _own_conversation(cid, user)
    db.execute("DELETE FROM messages WHERE conversation_id=?", (cid,))
    db.execute("DELETE FROM conversations WHERE id=?", (cid,))
    return {"ok": True}


class FeedbackIn(BaseModel):
    target: str | None = None
    message_id: int | None = None
    rating: Literal["faithful", "uncharacteristic"]


@api.post("/feedback")
def persona_feedback(body: FeedbackIn, user: dict = Depends(current_user)):
    """👍 «μοιάζει με το πρόσωπο» / 👎 «δεν μοιάζει»: a human fidelity signal shown in the fidelity test."""
    t = _check_target(user, body.target)
    db.execute("INSERT INTO persona_feedback(ts, user_id, target, message_id, rating) VALUES(?,?,?,?,?)",
               (time.time(), user["id"], t, body.message_id, body.rating))
    return feedback_stats(t, user)


@api.get("/feedback/stats")
def feedback_stats(target: str | None = None, user: dict = Depends(current_user)):
    t = _check_target(user, target)
    rows = db.query("SELECT rating, count(*) n FROM persona_feedback WHERE target=? GROUP BY rating", (t,))
    counts = {r["rating"]: r["n"] for r in rows}
    total = sum(counts.values())
    return {"faithful": counts.get("faithful", 0), "uncharacteristic": counts.get("uncharacteristic", 0),
            "total": total, "faithful_rate": round(100 * counts.get("faithful", 0) / total, 1) if total else None}


@api.post("/twin/write")
def write(body: WriteIn, user: dict = Depends(current_user)):
    with as_person(_check_target(user, body.target)):
        return twin.write(body.incoming, body.channel, body.audience, body.instructions, critique=body.critique,
                          queue=False)


@api.post("/twin/decide")
def decide(body: DecideIn, user: dict = Depends(current_user)):
    with as_person(_check_target(user, body.target)):
        try:
            return twin.decide(body.situation, body.options)
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc


class CompareIn(BaseModel):
    kind: Literal["ask", "write", "decide"]
    payload: dict
    target: str | None = None


@api.post("/twin/baseline")
def baseline(body: CompareIn, user: dict = Depends(current_user)):
    with as_person(_check_target(user, body.target)):
        return twin.compare(body.kind, body.payload)


# ------------------------------------------------------------------ voice (ElevenLabs) and avatar (Simli)

class SpeakIn(BaseModel):
    text: str = Field(min_length=1, max_length=4000)
    target: str | None = None


@api.post("/voice/speak")
def voice_speak(body: SpeakIn, user: dict = Depends(current_user)):
    """The answer read aloud in the voice of the person whose twin answered (WAV, 16 kHz)."""
    t = _check_target(user, body.target)
    try:
        wav = voice.speak(body.text, t)
    except voice.VoiceError as exc:
        raise HTTPException(502, str(exc)) from exc
    return Response(content=wav, media_type="audio/wav", headers={"Cache-Control": "no-store"})


@api.post("/voice/transcribe")
async def voice_transcribe(request: Request):
    audio = await request.body()
    try:
        text = voice.transcribe(audio, request.headers.get("content-type", "audio/webm"))
    except voice.VoiceError as exc:
        raise HTTPException(502, str(exc)) from exc
    return {"text": text}


class AvatarIn(BaseModel):
    target: str | None = None
    audio_seconds: float = Field(ge=0.1, le=120)


@api.post("/avatar/session")
def avatar_session(body: AvatarIn, user: dict = Depends(current_user)):
    t = _check_target(user, body.target)
    try:
        return voice.simli_session(t, body.audio_seconds, user["id"])
    except voice.VoiceError as exc:
        raise HTTPException(502, str(exc)) from exc


# ------------------------------------------------------------------ privacy & audit (API only)

@api.get("/audit")
def audit_log(limit: int = 100):
    return {"events": db.query("SELECT * FROM audit WHERE person_id=? ORDER BY id DESC LIMIT ?", (pid(), limit))}


@api.get("/privacy")
def privacy_report():
    sources = db.query("SELECT id, name, kind, consent, n_items, pii FROM sources WHERE person_id=?", (pid(),))
    totals: dict[str, int] = {}
    for s in sources:
        for k, v in (s["pii"] or {}).items():
            totals[k] = totals.get(k, 0) + v
    return {
        "pii_redacted": totals,
        "sources": sources,
        "boundaries": db.get_setting("boundaries", DEFAULT_BOUNDARIES),
        "llm": {"provider": LLM_CLIENT.provider, "sends": "μόνο ανωνυμοποιημένο κείμενο" if LLM_CLIENT.available else "τίποτα"},
    }


# ------------------------------------------------------------------ evaluation

@api.post("/eval/run")
def run_eval(target: str | None = None, user: dict = Depends(current_user)):
    with as_person(_check_target(user, target)):
        return jobs.start("eval", evaluation.run)


@api.get("/eval/latest")
def latest_eval(target: str | None = None, user: dict = Depends(current_user)):
    with as_person(_check_target(user, target)):
        r = evaluation.latest_run()
    if not r:
        raise HTTPException(404, "Δεν έχει γίνει ακόμα αξιολόγηση")
    return r


@api.get("/jobs/{jid}")
def job(jid: str, user: dict = Depends(current_user)):
    j = jobs.get(jid)
    if not j or j.get("person") not in allowed_targets(user["id"]):
        raise HTTPException(404, "Άγνωστη εργασία")
    return j


@api.get("/blind")
def blind(target: str | None = None, user: dict = Depends(current_user)):
    with as_person(_check_target(user, target)):
        try:
            return evaluation.blind_round()
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc


class VoteIn(BaseModel):
    token: str
    pick: Literal["a", "b"]
    target: str | None = None


@api.post("/blind")
def blind_vote(body: VoteIn, user: dict = Depends(current_user)):
    with as_person(_check_target(user, body.target)):
        try:
            return evaluation.blind_vote(body.token, body.pick)
        except KeyError as exc:
            raise HTTPException(410, "Ο γύρος έληξε, φόρτωσε νέο") from exc


@api.get("/blind/stats")
def blind_stats(target: str | None = None, user: dict = Depends(current_user)):
    with as_person(_check_target(user, target)):
        return evaluation.blind_stats()


app.include_router(mirror_api.router)
app.include_router(api)

# ------------------------------------------------------------------ frontend

STATIC_TYPES = {".avif": "image/avif", ".js": "text/javascript", ".css": "text/css", ".svg": "image/svg+xml"}
SECURITY_HEADERS = {"X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer",
                    "Permissions-Policy": "camera=(), geolocation=(), microphone=(self)"}

if settings.static_dir.exists():
    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404, "Not found")
        root = settings.static_dir.resolve()
        target = (root / path).resolve()
        if path and target.is_file() and root in target.parents:
            return FileResponse(target, media_type=STATIC_TYPES.get(target.suffix),
                                headers={**SECURITY_HEADERS, "Cache-Control": "no-cache"})
        return FileResponse(root / "index.html", headers={**SECURITY_HEADERS, "Cache-Control": "no-cache"})
