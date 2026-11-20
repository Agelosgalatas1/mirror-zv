"""The API of the MIRROR web app (the team's ZV frontend), on top of the MIRROR twin engine.

The browser only ever sees conversations: knowledge, inheritance and access rules stay on the
server. Access is upward only: a person chats with the AI of everyone they report to, and tests
their own AI in the self-test. Spoken answers ("voice turns") keep the ElevenLabs audio on the
server; the Simli avatar gets a short-lived token for one checked answer at a time.
"""
from __future__ import annotations

import random
import re
import secrets
import time
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from . import db, profile, twin, voice
from .auth import allowed_targets, current_user
from .context import as_person
from .ingest import pipeline
from .llm import LLM_CLIENT

router = APIRouter(prefix="/api", dependencies=[Depends(current_user)])
VOICE_TTL = 24 * 3600


class MirrorAccess(HTTPException):
    def __init__(self, mirror_id: str):
        super().__init__(403, "Δεν έχεις πρόσβαση σε αυτό το Mirror.")
        self.mirror_id = mirror_id


def iso(ts: float | None) -> str | None:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat() if ts else None


# ------------------------------------------------------------------ people and access

def _meta(row: dict) -> dict:
    return row.get("meta") or {}


def user_view(row: dict) -> dict:
    o = pipeline.owner_dict(row["id"])
    meta = _meta(row)
    return {"username": meta.get("username") or row["id"], "employee_id": row["id"], "name": o["name"],
            "role_name": meta.get("username") or row["id"], "job_title": (o.get("role") or "").split(",")[0].strip(),
            "department": meta.get("department", ""), "manager_id": row.get("reports_to")}


def chat_mirrors(user: dict) -> list[dict]:
    """The Mirrors this user may chat with: everyone they report to (never their own, never sideways)."""
    return [{"id": t, "title": pipeline.owner_dict(t)["name"]} for t in allowed_targets(user["id"])[1:]]


def session_payload(user: dict) -> dict:
    return {"user": user_view(user), "mirrors": chat_mirrors(user),
            "ai": {"online": LLM_CLIENT.available, "provider": LLM_CLIENT.provider, "model": LLM_CLIENT.model}}


SECTION_LABELS = {"values": "Αξία", "knowledge": "Γνώση", "preferences": "Προτίμηση", "decision_rules": "Κανόνας απόφασης",
                  "relationships": "Συνεργασία"}


def explain(res: dict) -> dict:
    """What the browser may show under an answer: why, which traits, which of the person's own messages."""
    traits = []
    for t in (res.get("traits") or [])[:4]:
        src = t.get("inherited_from") or {}
        traits.append({"kind": SECTION_LABELS.get(t.get("section"), "Χαρακτηριστικό"), "text": t.get("text") or "",
                       "inherited_from": src.get("display_name") or src.get("name")})
    sources = []
    for m in (res.get("memories") or [])[:3]:
        where = twin.CHANNEL_LABELS.get(m.get("channel") or "", m.get("channel") or "")
        sources.append({"label": " · ".join(x for x in (m.get("subject"), where, m.get("date")) if x),
                        "quote": " ".join(str(m.get("snippet") or "").split())[:260],
                        "own": m.get("author") == "me"})
    return {"why": res.get("why") or "", "confidence": res.get("confidence"), "unsure": bool(res.get("unsure")),
            "boundary": bool(res.get("boundary")), "mode": res.get("mode") or ("llm" if LLM_CLIENT.available else "offline"),
            "traits": traits, "sources": sources}


def guard(user: dict, mid: str) -> str:
    if mid not in {m["id"] for m in chat_mirrors(user)}:
        raise MirrorAccess(mid)
    return mid


@router.get("/session")
def session(user: dict = Depends(current_user)):
    return session_payload(user)


@router.get("/hierarchy")
def hierarchy(user: dict = Depends(current_user)):
    """The company directory (safe fields), with whether and why this user may chat with each AI."""
    rows = db.query("SELECT * FROM persons ORDER BY rowid")  # the order of org.json
    mine = pipeline.ancestors(user["id"])
    allowed = {m["id"] for m in chat_mirrors(user)}
    out = []
    for r in rows:
        if r["id"] == user["id"]:
            rel = "self"
        elif mine and r["id"] == mine[0]:
            rel = "manager"
        elif r["id"] in mine:
            rel = "above"
        elif user["id"] in pipeline.ancestors(r["id"]):
            rel = "below"
        else:
            rel = "other_line"
        can = r["id"] in allowed
        reason = None if can else "self" if rel == "self" else rel if rel in ("below", "other_line") else "not_permitted"
        v = user_view(r)
        out.append({"id": r["id"], "name": v["name"], "job_title": v["job_title"], "role_name": v["role_name"],
                    "department": v["department"], "manager_id": r.get("reports_to"), "mirror_id": r["id"],
                    "can_chat": can, "is_me": rel == "self", "relation": rel, "reason": reason})
    return out


# ------------------------------------------------------------------ conversations

def _conversation(user: dict, mid: str, cid: str) -> dict:
    try:
        n = int(cid)
    except ValueError:
        raise HTTPException(404, "Η συζήτηση δεν βρέθηκε.") from None
    conv = db.one("SELECT * FROM conversations WHERE id=? AND user_id=? AND target=?", (n, user["id"], mid))
    if not conv:
        raise HTTPException(404, "Η συζήτηση δεν βρέθηκε.")
    return conv


def _thread_view(c: dict) -> dict:
    last_q = db.one("SELECT text FROM messages WHERE conversation_id=? AND role='user' ORDER BY id DESC LIMIT 1", (c["id"],))
    last_a = db.one("SELECT text FROM messages WHERE conversation_id=? AND role='twin' ORDER BY id DESC LIMIT 1", (c["id"],))
    turns = db.one("SELECT count(*) n FROM messages WHERE conversation_id=? AND role='user'", (c["id"],))["n"]
    return {"conversation_id": str(c["id"]), "title": c["title"], "created_at": iso(c["created_at"]),
            "updated_at": iso(c["updated_at"]), "expires_at": None, "turns": turns,
            "last_question": (last_q or {}).get("text", ""), "last_answer": (last_a or {}).get("text", "")}


class TitleIn(BaseModel):
    title: str = Field(default="Νέα συζήτηση", max_length=200)


@router.get("/mirrors/{mid}/conversations")
def conversations(mid: str, user: dict = Depends(current_user)):
    guard(user, mid)
    rows = db.query("SELECT * FROM conversations WHERE user_id=? AND target=? ORDER BY updated_at DESC LIMIT 100",
                    (user["id"], mid))
    return [_thread_view(c) for c in rows]


@router.post("/mirrors/{mid}/conversations")
def new_conversation(mid: str, body: TitleIn, user: dict = Depends(current_user)):
    guard(user, mid)
    now = time.time()
    title = " ".join(body.title.split())[:120] or "Νέα συζήτηση"
    cid = db.execute("INSERT INTO conversations(user_id, target, title, created_at, updated_at) VALUES(?,?,?,?,?)",
                     (user["id"], mid, title, now, now))
    return _thread_view(db.one("SELECT * FROM conversations WHERE id=?", (cid,)))


@router.get("/mirrors/{mid}/conversations/{cid}")
def conversation(mid: str, cid: str, user: dict = Depends(current_user)):
    guard(user, mid)
    conv = _conversation(user, mid, cid)
    msgs = db.query("SELECT id, role, text, payload, created_at FROM messages WHERE conversation_id=? ORDER BY id",
                    (conv["id"],))
    voiced = {r["message_id"]: r["id"] for r in db.query(
        "SELECT id, message_id FROM voice_turns WHERE user_id=? AND conversation_id=? AND state='READY' "
        "AND audio IS NOT NULL AND created_at>?", (user["id"], conv["id"], time.time() - VOICE_TTL))}
    turns, question = [], None
    for m in msgs:
        if m["role"] == "user":
            question = m
        elif question is not None:
            turns.append({"turn_id": m["id"], "question": question["text"], "answer": m["text"],
                          "created_at": iso(m["created_at"]), "voice_turn_id": voiced.get(m["id"]),
                          "explain": explain(m["payload"] or {}) if m["payload"] else None})
            question = None
    return turns


@router.post("/mirrors/{mid}/conversations/{cid}/rename")
def rename(mid: str, cid: str, body: TitleIn, user: dict = Depends(current_user)):
    guard(user, mid)
    conv = _conversation(user, mid, cid)
    title = " ".join(body.title.split())[:120]
    if not title:
        raise HTTPException(400, "Ο τίτλος δεν μπορεί να είναι κενός.")
    db.execute("UPDATE conversations SET title=? WHERE id=?", (title, conv["id"]))
    return {"conversation_id": str(conv["id"]), "title": title}


def _delete(conv_id: int) -> None:
    db.execute("DELETE FROM voice_turns WHERE conversation_id=?", (conv_id,))
    db.execute("DELETE FROM messages WHERE conversation_id=?", (conv_id,))
    db.execute("DELETE FROM conversations WHERE id=?", (conv_id,))


@router.post("/mirrors/{mid}/conversations/{cid}/delete")
def delete(mid: str, cid: str, user: dict = Depends(current_user)):
    guard(user, mid)
    if cid == "all":
        rows = db.query("SELECT id FROM conversations WHERE user_id=? AND target=?", (user["id"], mid))
        for r in rows:
            _delete(r["id"])
        return {"deleted": len(rows)}
    _delete(_conversation(user, mid, cid)["id"])
    return {"deleted": 1}


# ------------------------------------------------------------------ asking

class AskIn(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = None


def answer_in_conversation(user: dict, mid: str, question: str, cid: str | None) -> dict:
    """Ask the twin inside a saved conversation (its history gives context to follow-ups) and store the turn."""
    conv = _conversation(user, mid, cid) if cid else None
    history: list[dict] = []
    if conv:
        rows = db.query("SELECT role, text, payload FROM messages WHERE conversation_id=? ORDER BY id DESC LIMIT 8",
                        (conv["id"],))
        history = [{"role": r["role"], "text": r["text"],
                    "traits": [t["id"] for t in (r["payload"] or {}).get("traits", [])]} for r in reversed(rows)]
    with as_person(mid):
        res = twin.ask(" ".join(question.split()), "chat_team", history=history)
    if conv:
        now = time.time()
        db.execute("INSERT INTO messages(conversation_id, role, text, payload, created_at) VALUES(?,?,?,?,?)",
                   (conv["id"], "user", question.strip(), "{}", now))
        res["message_id"] = db.execute(
            "INSERT INTO messages(conversation_id, role, text, payload, created_at) VALUES(?,?,?,?,?)",
            (conv["id"], "twin", res.get("answer", ""), db.dumps(res), now + 0.001))
        db.execute("UPDATE conversations SET updated_at=? WHERE id=?", (now, conv["id"]))
        res["conversation_id"] = str(conv["id"])
    return res


@router.post("/mirrors/{mid}/ask")
def ask(mid: str, body: AskIn, user: dict = Depends(current_user)):
    guard(user, mid)
    res = answer_in_conversation(user, mid, body.question, body.conversation_id)
    return {"answer": res["answer"], "conversation_id": res.get("conversation_id"), "explain": explain(res)}


def _speak_into(turn_id: str, answer: str, mid: str) -> bool:
    try:
        wav = voice.speak(answer, mid)
    except voice.VoiceError:
        db.execute("UPDATE voice_turns SET state='TEXT_ONLY', answer=? WHERE id=?", (answer, turn_id))
        return False
    db.execute("UPDATE voice_turns SET state='READY', answer=?, audio=? WHERE id=?", (answer, wav, turn_id))
    return True


@router.post("/mirrors/{mid}/spoken-ask")
def spoken_ask(mid: str, body: AskIn, user: dict = Depends(current_user)):
    guard(user, mid)
    res = answer_in_conversation(user, mid, body.question, body.conversation_id)
    turn_id = uuid.uuid4().hex
    db.execute("INSERT INTO voice_turns(id, user_id, target, conversation_id, message_id, transcript, state, created_at) "
               "VALUES(?,?,?,?,?,?,?,?)", (turn_id, user["id"], mid, int(res["conversation_id"]) if res.get(
                   "conversation_id") else None, res.get("message_id"), body.question, "PENDING", time.time()))
    has_audio = _speak_into(turn_id, res["answer"], mid)
    return {"answer": res["answer"], "turn_id": turn_id, "has_audio": has_audio,
            "conversation_id": res.get("conversation_id"), "explain": explain(res)}


@router.post("/mirrors/{mid}/persona-feedback")
def persona_feedback(mid: str, body: dict, user: dict = Depends(current_user)):
    guard(user, mid)
    rating = body.get("rating")
    if rating not in ("faithful", "uncharacteristic"):
        raise HTTPException(400, "Μη έγκυρη αξιολόγηση.")
    db.execute("INSERT INTO persona_feedback(ts, user_id, target, message_id, rating) VALUES(?,?,?,?,?)",
               (time.time(), user["id"], mid, None, rating))
    return {"ok": True}


# ------------------------------------------------------------------ voice and avatar

@router.get("/mirrors/{mid}/avatar")
def avatar(mid: str, user: dict = Depends(current_user)):
    guard(user, mid)
    caps = voice.capabilities()
    return {"available": caps["avatar"], "voice": caps["tts"] == "elevenlabs",
            "voice_name": voice.VOICE_NAMES.get(mid), "max_seconds": 30, "avatar_provider": "simli",
            "face_name": voice.FACE_NAMES.get(mid, "")}


def _turn(user: dict, tid: str) -> dict:
    if not re.fullmatch(r"[0-9a-f]{32}", tid or ""):
        raise HTTPException(404, "Η φωνητική απάντηση δεν βρέθηκε.")
    row = db.one("SELECT * FROM voice_turns WHERE id=? AND user_id=? AND created_at>?",
                 (tid, user["id"], time.time() - VOICE_TTL))
    if not row:
        raise HTTPException(404, "Η φωνητική απάντηση δεν βρέθηκε ή έληξε.")
    guard(user, row["target"])
    return row


@router.post("/mirrors/{mid}/voice")
async def transcribe(mid: str, request: Request, conversation_id: str | None = None,
                     user: dict = Depends(current_user)):
    guard(user, mid)
    conv = _conversation(user, mid, conversation_id) if conversation_id else None
    audio = await request.body()
    try:
        text = voice.transcribe(audio, request.headers.get("content-type", "audio/wav"))
    except voice.VoiceError as exc:
        raise HTTPException(502, str(exc)) from exc
    turn_id = uuid.uuid4().hex
    db.execute("INSERT INTO voice_turns(id, user_id, target, conversation_id, transcript, state, created_at) "
               "VALUES(?,?,?,?,?,?,?)", (turn_id, user["id"], mid, conv["id"] if conv else None, text,
                                         "TRANSCRIBED", time.time()))
    return {"turn_id": turn_id, "transcript": text}


@router.post("/voice/{tid}/confirm")
def confirm(tid: str, body: dict, user: dict = Depends(current_user)):
    row = _turn(user, tid)
    if row["state"] != "TRANSCRIBED":
        raise HTTPException(409, "Αυτή η φωνητική ερώτηση έχει ήδη σταλεί.")
    text = " ".join(str(body.get("text") or "").split())[:4000]
    if not text:
        raise HTTPException(400, "Το μήνυμα είναι κενό.")
    cid = str(row["conversation_id"]) if row["conversation_id"] else None
    res = answer_in_conversation(user, row["target"], text, cid)
    db.execute("UPDATE voice_turns SET transcript=?, message_id=?, state='PENDING' WHERE id=?",
               (text, res.get("message_id"), tid))
    has_audio = _speak_into(tid, res["answer"], row["target"])
    return {"turn_id": tid, "answer": res["answer"], "has_audio": has_audio, "conversation_id": res.get("conversation_id"),
            "explain": explain(res)}


@router.get("/voice/{tid}")
def voice_meta(tid: str, user: dict = Depends(current_user)):
    row = _turn(user, tid)
    return {"turn_id": tid, "mirror_id": row["target"],
            "conversation_id": str(row["conversation_id"]) if row["conversation_id"] else None,
            "has_audio": row["state"] == "READY" and bool(row["audio"]), "animation": {}}


@router.get("/voice/{tid}/audio")
def voice_audio(tid: str, user: dict = Depends(current_user)):
    row = _turn(user, tid)
    if row["state"] != "READY" or not row["audio"]:
        raise HTTPException(404, "Δεν υπάρχει ήχος για αυτή την απάντηση.")
    return Response(content=row["audio"], media_type="audio/wav", headers={"Cache-Control": "no-store"})


_LEASES: dict[str, dict] = {}


@router.post("/voice/{tid}/simli")
def simli_session(tid: str, body: dict, user: dict = Depends(current_user)):
    row = _turn(user, tid)
    if str(body.get("conversation_id")) != str(row["conversation_id"]):
        raise HTTPException(403, "Το avatar ανήκει σε άλλη συζήτηση.")
    if row["state"] != "READY" or not row["audio"]:
        raise HTTPException(400, "Χρειάζεται πρώτα έτοιμη φωνητική απάντηση.")
    seconds = max(0.5, (len(row["audio"]) - 44) / 32000)
    try:
        sess = voice.simli_session(row["target"], seconds, user["id"])
    except voice.VoiceError as exc:
        raise HTTPException(502, str(exc)) from exc
    lease = secrets.token_hex(12)
    _LEASES[lease] = {"user": user["id"], "turn": tid, "until": time.time() + sess["max_seconds"] + 30}
    return {"session_token": sess["session_token"], "lease_id": lease, "turn_id": tid,
            "conversation_id": str(row["conversation_id"]), "mirror_id": row["target"], "face_name": sess["face"],
            "max_seconds": sess["max_seconds"], "audio_seconds": round(seconds, 2)}


@router.get("/voice/{tid}/simli/{lease}")
def simli_check(tid: str, lease: str, user: dict = Depends(current_user)):
    _turn(user, tid)
    info = _LEASES.get(lease)
    if not info or info["user"] != user["id"] or info["turn"] != tid or info["until"] < time.time():
        raise HTTPException(403, "Η συνεδρία avatar έληξε.")
    return {"ok": True}


@router.post("/voice/{tid}/simli/{lease}/close")
def simli_close(tid: str, lease: str, user: dict = Depends(current_user)):
    info = _LEASES.get(lease)
    if info and info["user"] == user["id"]:
        _LEASES.pop(lease, None)
    return {"ok": True}


# ------------------------------------------------------------------ self-test (the owner checks their own AI)

TOPICS = {"decision_rules": "Αποφάσεις & εγκρίσεις", "knowledge": "Γνώση της δουλειάς", "values": "Αξίες & προτεραιότητες",
          "preferences": "Τρόπος δουλειάς", "relationships": "Συνεργασίες"}
SECTION_OF = {v: k for k, v in TOPICS.items()}


def _own_profile() -> dict:
    prof = profile.current()
    if not prof:
        raise HTTPException(409, "Το AI σου δεν έχει ακόμα προφίλ.")
    return prof


def self_test_state(user: dict) -> dict:
    with as_person(user["id"]):
        prof = _own_profile()
    events = db.query("SELECT * FROM self_test_events WHERE person_id=? ORDER BY id DESC LIMIT 60", (user["id"],))
    topics = []
    for sec, name in TOPICS.items():
        if not prof.get(sec):
            continue
        streak = 0
        for e in events:
            if e["topic"] != name or e["undone_at"] or not e["feedback"]:
                continue
            if e["feedback"] != "correct":
                break
            streak += 1
        topics.append({"topic": name, "streak": min(streak, 3), "verified": streak >= 3})
    pending = [t for t in topics if not t["verified"]]
    nxt = min(pending, key=lambda t: t["streak"])["topic"] if pending else (topics[0]["topic"] if topics else None)
    custom = list({e["question"]: {"question": e["question"], "topic": e["topic"]}
                   for e in reversed(events) if e["question_source"] == "custom"}.values())[-10:]
    me = pipeline.owner_dict(user["id"])
    return {"mirror": {"id": user["id"], "name": me["name"]}, "topics": topics, "next_topic": nxt,
            "custom_questions": custom,
            "events": [{"event_id": e["id"], "topic": e["topic"], "question": e["question"], "feedback": e["feedback"],
                        "correction": e["correction"], "undone_at": iso(e["undone_at"])} for e in events[:12]]}


def _question_for(trait: dict, sec: str) -> str:
    """A question whose answer is the trait, without giving the answer away."""
    text = trait.get("rule") or trait.get("text") or trait.get("relation") or ""
    if LLM_CLIENT.available:
        try:
            out = LLM_CLIENT.json(
                "Γράφεις ερωτήσεις αυτο-ελέγχου στα ελληνικά. Επιστρέφεις ΜΟΝΟ JSON {\"question\": \"...\"}.",
                f"Γράψε μία σύντομη, φυσική ερώτηση (σε δεύτερο πρόσωπο, προς το ίδιο το πρόσωπο) της οποίας η σωστή "
                f"απάντηση είναι το παρακάτω χαρακτηριστικό. Μην αποκαλύπτεις την απάντηση μέσα στην ερώτηση.\n\n"
                f"Χαρακτηριστικό: {text}", max_tokens=300, effort="minimal")
            q = str(out.get("question", "")).strip()
            if 8 < len(q) < 300:
                return q
        except Exception:  # noqa: BLE001 - any model problem: use the offline wording below
            pass
    if sec == "relationships":
        return f"Πώς συνεργάζεσαι με το πρόσωπο «{trait.get('name', '')}»;"
    if sec == "decision_rules":
        return f"Τι κάνεις σε αυτή την περίπτωση: {trait.get('when') or 'ένα αίτημα εκτός ορίων'};"
    words = [w for w in re.findall(r"[\wά-ώΆ-Ώ€%-]{4,}", text) if not w.isdigit()][:4]
    topic = " ".join(words) if words else TOPICS[sec].lower()
    if sec == "values":
        return f"Τι μετράει περισσότερο για σένα σε σχέση με «{topic}»;"
    if sec == "preferences":
        return f"Πώς προτιμάς να δουλεύεις όταν πρόκειται για «{topic}»;"
    return f"Τι ξέρεις για «{topic}»;"


class SelfQuestionIn(BaseModel):
    topic: str | None = None
    custom_question: str | None = Field(default=None, max_length=500)


@router.get("/self-test")
def self_test(user: dict = Depends(current_user)):
    return self_test_state(user)


@router.post("/self-test/question")
def self_test_question(body: SelfQuestionIn, user: dict = Depends(current_user)):
    topic = body.topic if body.topic in SECTION_OF else next(iter(TOPICS.values()))
    if body.custom_question and body.custom_question.strip():
        return {"topic": topic, "question": " ".join(body.custom_question.split()), "question_source": "custom"}
    sec = SECTION_OF[topic]
    with as_person(user["id"]):
        traits = _own_profile().get(sec, [])
    if not traits:
        raise HTTPException(400, "Δεν υπάρχουν ακόμα στοιχεία για αυτό το θέμα.")
    asked = {e["question_source"] for e in db.query(
        "SELECT question_source FROM self_test_events WHERE person_id=? AND topic=?", (user["id"], topic))}
    fresh = [t for t in traits if f"trait:{t['id']}" not in asked] or traits
    trait = random.choice(fresh[:6])
    return {"topic": topic, "question": _question_for(trait, sec), "question_source": f"trait:{trait['id']}"}


class SelfAnswerIn(BaseModel):
    topic: str
    question: str = Field(min_length=3, max_length=500)
    question_source: str = Field(default="custom", max_length=80)
    user_answer: str = Field(min_length=1, max_length=4000)


@router.post("/self-test/answer")
def self_test_answer(body: SelfAnswerIn, user: dict = Depends(current_user)):
    if body.topic not in SECTION_OF:
        raise HTTPException(400, "Άγνωστο θέμα.")
    with as_person(user["id"]):
        res = twin.ask(body.question, "chat_team")
    eid = db.execute("INSERT INTO self_test_events(person_id, topic, question, question_source, user_answer, twin_answer, "
                     "created_at) VALUES(?,?,?,?,?,?,?)", (user["id"], body.topic, body.question, body.question_source,
                                                          body.user_answer.strip(), res["answer"], time.time()))
    return {"event_id": eid, "topic": body.topic, "question": body.question, "question_source": body.question_source,
            "user_answer": body.user_answer.strip(), "twin_answer": res["answer"]}


def _event(user: dict, eid: int) -> dict:
    e = db.one("SELECT * FROM self_test_events WHERE id=? AND person_id=?", (eid, user["id"]))
    if not e:
        raise HTTPException(404, "Το τεστ δεν βρέθηκε.")
    return e


class FeedbackIn(BaseModel):
    feedback: str
    correction: str = Field(default="", max_length=2000)


@router.post("/self-test/events/{eid}/feedback")
def self_test_feedback(eid: int, body: FeedbackIn, user: dict = Depends(current_user)):
    e = _event(user, eid)
    if body.feedback not in ("correct", "wrong"):
        raise HTTPException(400, "Μη έγκυρη αξιολόγηση.")
    trait_id = None
    correction = " ".join(body.correction.split())
    if body.feedback == "wrong" and correction:
        # The owner's correction becomes an owner-verified fact: the AI uses it from now on, everywhere.
        with as_person(user["id"]):
            prof = profile.add_owner_trait("knowledge", f"{e['question']} → {correction}")
            trait_id = prof["knowledge"][-1]["id"]
    db.execute("UPDATE self_test_events SET feedback=?, correction=?, trait_id=?, undone_at=NULL WHERE id=?",
               (body.feedback, correction or None, trait_id, eid))
    return self_test_state(user)


@router.post("/self-test/events/{eid}/undo")
def self_test_undo(eid: int, user: dict = Depends(current_user)):
    e = _event(user, eid)
    if e["trait_id"]:
        with as_person(user["id"]):
            try:
                profile.owner_edit(e["trait_id"], "delete")
            except KeyError:
                pass
    db.execute("UPDATE self_test_events SET undone_at=? WHERE id=?", (time.time(), eid))
    return self_test_state(user)
