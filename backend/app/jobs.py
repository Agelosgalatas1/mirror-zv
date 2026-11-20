# Επεξήγηση: Εκτελεί αργές εργασίες στο παρασκήνιο και επιστρέφει την πρόοδό τους.
"""Tiny background-job runner for long operations (profile build, evaluation)."""
from __future__ import annotations

import threading
import time
import traceback
import uuid
from typing import Any, Callable

from .context import CURRENT_VIEWER, as_person, pid

_JOBS: dict[str, dict[str, Any]] = {}
_LOCK = threading.Lock()


# Επεξήγηση: Μεταφέρει και το πλαίσιο χρήστη στην εργασία ώστε να διατηρούνται οι ίδιοι έλεγχοι.
def start(kind: str, fn: Callable[[Callable[[float, str], None]], Any]) -> dict:
    with _LOCK:
        for j in _JOBS.values():
            if j["kind"] == kind and j["status"] == "running" and j.get("person") == pid():
                return j
        jid = uuid.uuid4().hex[:10]
        job = {"id": jid, "kind": kind, "status": "running", "progress": 0.0, "message": "Starting…",
               "started": time.time(), "result": None, "error": None}
        _JOBS[jid] = job

    def progress(p: float, msg: str) -> None:
        job["progress"] = round(max(0.0, min(1.0, p)), 3)
        job["message"] = msg

    person = pid()
    viewer = CURRENT_VIEWER.get()
    job["person"] = person

    def runner() -> None:
        token = CURRENT_VIEWER.set(viewer)
        try:
            with as_person(person):
                job["result"] = fn(progress)
            job["status"] = "done"
            job["progress"] = 1.0
            job["message"] = "Done"
        except Exception as exc:  # noqa: BLE001
            job["status"] = "error"
            job["error"] = f"{type(exc).__name__}: {exc}"
            job["trace"] = traceback.format_exc()[-2000:]
        finally:
            CURRENT_VIEWER.reset(token)
        job["finished"] = time.time()

    threading.Thread(target=runner, daemon=True, name=f"job-{kind}").start()
    return job


def get(jid: str) -> dict | None:
    j = _JOBS.get(jid)
    if not j:
        return None
    return {k: v for k, v in j.items() if k not in ("trace",)}


def running(kind: str) -> dict | None:
    for j in _JOBS.values():
        if j["kind"] == kind and j["status"] == "running" and j.get("person") == pid():
            return get(j["id"])
    return None
