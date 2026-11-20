"""Which person's twin a piece of code is working for.

Every request runs "as" one person of the organisation (set by the auth
dependency). All data access is scoped to that person, so one manager can
never read another manager's memory.
"""
from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar
from typing import Iterator

CURRENT_VIEWER: ContextVar[str | None] = ContextVar("current_viewer", default=None)

CURRENT_PERSON: ContextVar[str] = ContextVar("current_person", default="ceo")


def pid() -> str:
    return CURRENT_PERSON.get()


@contextmanager
def as_person(person_id: str) -> Iterator[str]:
    token = CURRENT_PERSON.set(person_id)
    try:
        yield person_id
    finally:
        CURRENT_PERSON.reset(token)
