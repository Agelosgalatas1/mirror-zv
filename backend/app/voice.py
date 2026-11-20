"""Optional premium voice and avatar.

* ElevenLabs: text-to-speech (each person has their own voice) and speech-to-text (Scribe).
* Simli: a live talking face, driven by the same ElevenLabs audio.

Both are opt-in per answer (the user picks "Φωνή" or "Avatar"), keys stay on the
server, and only the twin's final answer text is sent to ElevenLabs. Simli gets
a short-lived session token; the browser never sees the Simli key.
"""
from __future__ import annotations

import hashlib
import io
import json
import logging
import os
import threading
import time
import uuid
import wave
from collections import OrderedDict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from . import db

log = logging.getLogger("mirror.voice")

RATE = 16000  # PCM 16-bit mono 16 kHz: playable as WAV and exactly what Simli expects
MAX_TEXT = 1200
MAX_AUDIO_BYTES = 8 * 1024 * 1024

# Per person: the three voices auditioned in the team's ZV build (Sophia, Eric, Zenia).
DEFAULT_VOICES = {"ceo": "7smwXrU3C1PfaspIIUZB", "sales": "cjVigY5qzO86Huf0OWal", "finance": "qq6iLYCLMNznH8v9gGx5"}
VOICE_NAMES = {"ceo": "Sophia", "sales": "Eric", "finance": "Zenia"}
DEFAULT_MODELS = {"sales": "eleven_flash_v2_5"}
FALLBACK_VOICE = "EXAVITQu4vr4xnSDxMaL"  # stock voice available to every ElevenLabs account
DEFAULT_MODEL = "eleven_multilingual_v2"  # best Greek pronunciation
# Simli stock faces (docs.simli.com/api-reference/preset-faces): Kate, Hank, Zahra (portraits in frontend/simli-faces).
DEFAULT_FACES = {"ceo": "c060fe44-9b14-43e8-b92c-83a0e230db11", "sales": "9fcd5739-bf66-49a5-b525-d02d7f0bc2fc",
                 "finance": "a6d08e06-038a-4b32-84ae-b02e0f0f1140"}
FACE_NAMES = {"ceo": "Kate", "sales": "Hank", "finance": "Zahra"}


class VoiceError(RuntimeError):
    pass


def _key(name: str) -> str:
    return os.getenv(name, "").strip().strip('"').strip("'")


def elevenlabs_enabled() -> bool:
    return bool(_key("ELEVENLABS_API_KEY"))


def simli_enabled() -> bool:
    flag = os.getenv("SIMLI_ENABLED", "auto").strip().lower()
    return flag in ("", "auto", "true", "1", "yes") and bool(_key("SIMLI_API_KEY"))


def capabilities() -> dict:
    return {"tts": "elevenlabs" if elevenlabs_enabled() else "browser",
            "stt": "elevenlabs" if elevenlabs_enabled() else "browser",
            "avatar": simli_enabled()}


def voice_for(person: str) -> str:
    return _key(f"ELEVENLABS_VOICE_{person.upper()}") or DEFAULT_VOICES.get(person, FALLBACK_VOICE)


def face_for(person: str) -> str:
    return _key(f"SIMLI_FACE_{person.upper()}") or DEFAULT_FACES.get(person, DEFAULT_FACES["ceo"])


def _wav(pcm: bytes) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(pcm)
    return buf.getvalue()


# ------------------------------------------------------------------ text to speech

_CACHE: "OrderedDict[str, bytes]" = OrderedDict()
_CACHE_LOCK = threading.Lock()
_BAD_VOICES: set[str] = set()


def _explain_http(code: int, what: str) -> str:
    if code in (401, 403):
        return f"Το ElevenLabs αρνήθηκε το αίτημα ({what}, HTTP {code}). Έλεγξε το κλειδί και τις άδειές του."
    if code == 429:
        return f"Το ElevenLabs περιόρισε το αίτημα ({what}, 429). Έλεγξε τα credits και τα όρια χρήσης."
    return f"Το ElevenLabs δεν ολοκλήρωσε το αίτημα ({what}, HTTP {code})."


def _tts_call(text: str, voice: str, model: str, person: str) -> bytes:
    body = {"text": text, "model_id": model,
            "voice_settings": {"stability": 0.5 if person == "sales" else 0.45, "similarity_boost": 0.75,
                               "use_speaker_boost": True}}
    req = Request(f"https://api.elevenlabs.io/v1/text-to-speech/{voice}?output_format=pcm_{RATE}",
                  data=json.dumps(body).encode(),
                  headers={"xi-api-key": _key("ELEVENLABS_API_KEY"), "Content-Type": "application/json",
                           "Accept": "audio/pcm"})
    with urlopen(req, timeout=60) as resp:
        raw = resp.read(MAX_AUDIO_BYTES + 1)
    if len(raw) > MAX_AUDIO_BYTES or not raw:
        raise VoiceError("Μη έγκυρος ήχος από το ElevenLabs.")
    return raw[: len(raw) - (len(raw) % 2)]


def speak(text: str, person: str) -> bytes:
    """WAV (16 kHz mono PCM) of the person's voice reading the text. Cached to save credits."""
    if not elevenlabs_enabled():
        raise VoiceError("Δεν έχει ρυθμιστεί κλειδί ElevenLabs.")
    text = " ".join(text.split())[:MAX_TEXT]
    if not text:
        raise VoiceError("Δεν υπάρχει κείμενο για εκφώνηση.")
    voice = voice_for(person)
    if voice in _BAD_VOICES:
        voice = FALLBACK_VOICE
    model = _key(f"ELEVENLABS_MODEL_{person.upper()}") or DEFAULT_MODELS.get(person) or _key("ELEVENLABS_MODEL") \
        or DEFAULT_MODEL
    cache_key = hashlib.sha256(f"{voice}|{model}|{text}".encode()).hexdigest()
    with _CACHE_LOCK:
        if cache_key in _CACHE:
            _CACHE.move_to_end(cache_key)
            return _CACHE[cache_key]
    try:
        pcm = _tts_call(text, voice, model, person)
    except HTTPError as exc:
        if exc.code in (400, 404) and voice != FALLBACK_VOICE:
            # the chosen voice is not in this ElevenLabs account: use a stock voice instead
            log.warning("ElevenLabs voice %s unavailable (HTTP %s); falling back to a stock voice", voice, exc.code)
            _BAD_VOICES.add(voice)
            try:
                pcm = _tts_call(text, FALLBACK_VOICE, model, person)
            except HTTPError as exc2:
                raise VoiceError(_explain_http(exc2.code, "φωνή")) from None
        else:
            raise VoiceError(_explain_http(exc.code, "φωνή")) from None
    except (URLError, TimeoutError, OSError):
        raise VoiceError("Δεν έγινε σύνδεση με το ElevenLabs.") from None
    wav = _wav(pcm)
    with _CACHE_LOCK:
        _CACHE[cache_key] = wav
        while len(_CACHE) > 60:
            _CACHE.popitem(last=False)
    return wav


# ------------------------------------------------------------------ speech to text

def transcribe(audio: bytes, content_type: str = "audio/webm") -> str:
    if not elevenlabs_enabled():
        raise VoiceError("Δεν έχει ρυθμιστεί κλειδί ElevenLabs.")
    if not audio or len(audio) > 12 * 1024 * 1024:
        raise VoiceError("Η ηχογράφηση είναι κενή ή πολύ μεγάλη.")
    models = [_key("ELEVENLABS_STT_MODEL") or "scribe_v2", "scribe_v1"]
    last = None
    for model in dict.fromkeys(models):
        boundary = "mirror-" + uuid.uuid4().hex
        fields = {"model_id": model, "language_code": "ell", "tag_audio_events": "false", "diarize": "false"}
        body = b"".join(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
                        for k, v in fields.items())
        ext = "webm" if "webm" in content_type else "ogg" if "ogg" in content_type else "mp4" if "mp4" in content_type \
            else "wav"
        body += (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="speech.{ext}"\r\n'
                 f"Content-Type: {content_type or 'application/octet-stream'}\r\n\r\n").encode() + audio
        body += f"\r\n--{boundary}--\r\n".encode()
        req = Request("https://api.elevenlabs.io/v1/speech-to-text", data=body,
                      headers={"xi-api-key": _key("ELEVENLABS_API_KEY"),
                               "Content-Type": "multipart/form-data; boundary=" + boundary})
        try:
            with urlopen(req, timeout=60) as resp:
                return str(json.loads(resp.read(2_000_000)).get("text", "")).strip()
        except HTTPError as exc:
            last = exc
            if exc.code in (400, 422) and model != "scribe_v1":
                continue  # unknown model name: retry with the stable one
            if exc.code in (401, 403):
                raise VoiceError("Το ElevenLabs αρνήθηκε τη μεταγραφή. Ενεργοποίησε «Speech to Text» στις άδειες "
                                 f"του κλειδιού (HTTP {exc.code}).") from None
            raise VoiceError(_explain_http(exc.code, "μεταγραφή")) from None
        except (URLError, TimeoutError, OSError):
            raise VoiceError("Δεν έγινε σύνδεση με το ElevenLabs.") from None
    raise VoiceError(_explain_http(getattr(last, "code", 0), "μεταγραφή"))


# ------------------------------------------------------------------ Simli avatar sessions

def _limit(name: str, default: int) -> int:
    try:
        return max(0, int(os.getenv(name, str(default))))
    except ValueError:
        return default


def simli_session(person: str, audio_seconds: float, user_id: str) -> dict:
    """Mint a short-lived Simli session token for one spoken answer, within a local daily budget."""
    if not simli_enabled():
        raise VoiceError("Το Simli δεν έχει ρυθμιστεί.")
    seconds = max(10, min(120, int(audio_seconds) + 15))
    today = time.strftime("%Y-%m-%d")
    used = (db.one("SELECT COALESCE(SUM(seconds),0) s FROM simli_usage WHERE day=?", (today,)) or {}).get("s", 0)
    daily = _limit("SIMLI_DAILY_SECONDS", 600)
    if used + seconds > daily:
        raise VoiceError(f"Συμπληρώθηκε το ημερήσιο όριο avatar ({daily // 60} λεπτά). Συνεχίζεις με φωνή.")
    body = {"faceId": face_for(person), "handleSilence": True, "maxSessionLength": seconds, "maxIdleTime": 15,
            "audioInputFormat": "pcm16", "streaming_width": 768, "streaming_height": 768}
    req = Request("https://api.simli.ai/compose/token", data=json.dumps(body).encode(),
                  headers={"x-simli-api-key": _key("SIMLI_API_KEY"), "Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=20) as resp:
            token = json.loads(resp.read(65536))["session_token"]
    except HTTPError as exc:
        raise VoiceError(f"Το Simli δεν ξεκίνησε (HTTP {exc.code}). Έλεγξε το κλειδί και το υπόλοιπο.") from None
    except (URLError, TimeoutError, OSError, ValueError, KeyError):
        raise VoiceError("Το Simli δεν είναι διαθέσιμο αυτή τη στιγμή.") from None
    db.execute("INSERT INTO simli_usage(ts, day, user_id, person, seconds) VALUES(?,?,?,?,?)",
               (time.time(), today, user_id, person, seconds))
    return {"session_token": token, "max_seconds": seconds, "face": FACE_NAMES.get(person, "")}
