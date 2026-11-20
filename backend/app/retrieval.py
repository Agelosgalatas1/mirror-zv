# Επεξήγηση: Βρίσκει σχετικά αποσπάσματα με BM25 και, όταν υπάρχουν, διανύσματα σημασιολογικής αναζήτησης.
"""Hybrid retrieval over personal memory: BM25 (always) + dense embeddings
(when an embedding provider is configured), fused with Reciprocal Rank Fusion.

BM25 uses accent-folded tokens plus 5-char prefixes so Greek inflections
("απόφαση" / "αποφάσεις") and English plurals still match without a stemmer.
"""
from __future__ import annotations

import itertools
import math
import re
import threading
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Callable

import numpy as np

from . import db, sharing
from .context import pid

TOKEN_RE = re.compile(r"[\w]+", re.UNICODE)


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


# Επεξήγηση: Αφαιρεί τόνους και προσθέτει προθέματα για καλύτερη αντιστοίχιση ελληνικών λέξεων.
def tokenize(text: str) -> list[str]:
    toks = []
    for w in TOKEN_RE.findall(_fold(text)):
        if len(w) < 2:
            continue
        toks.append(w)
        if len(w) > 3 and w.endswith("s") and w.isascii():
            toks.append(w[:-1])
        if len(w) >= 5:
            toks.append(w[:5] + "~")
    return toks


@dataclass
class Hit:
    chunk_id: str
    item_id: str
    source_id: str
    text: str
    score: float
    item: dict


class MemoryIndex:
    def __init__(self, person: str) -> None:
        self.person = person
        self._lock = threading.RLock()
        self.chunks: list[dict] = []
        self.items: dict[str, dict] = {}
        self.doc_tokens: list[Counter] = []
        self.df: Counter = Counter()
        self.avgdl = 1.0
        self.emb: np.ndarray | None = None
        self.emb_rows: list[int] = []

    # Επεξήγηση: Ευρετηριάζει μόνο πηγές με συγκατάθεση του αντίστοιχου προσώπου.
    def rebuild(self) -> None:
        rows = db.query(
            "SELECT c.id, c.item_id, c.source_id, c.text, c.embedding FROM chunks c "
            "JOIN sources s ON s.id = c.source_id WHERE s.consent = 1 AND s.person_id = ?", (self.person,)
        )
        items = {r["id"]: r for r in db.query(
            "SELECT i.* FROM items i JOIN sources s ON s.id=i.source_id WHERE s.consent=1 AND s.person_id=?",
            (self.person,))}
        with self._lock:
            self.chunks = rows
            self.items = items
            self.doc_tokens = []
            self.df = Counter()
            for r in rows:
                item = items.get(r["item_id"], {})
                prefix = f"{item.get('subject') or ''} {item.get('counterpart') or ''} "
                c = Counter(tokenize(prefix + r["text"]))
                self.doc_tokens.append(c)
                self.df.update(c.keys())
            self.avgdl = (sum(sum(c.values()) for c in self.doc_tokens) / len(self.doc_tokens)) if rows else 1.0
            vecs, idx = [], []
            for i, r in enumerate(rows):
                if r.get("embedding"):
                    vecs.append(np.frombuffer(r["embedding"], dtype=np.float32))
                    idx.append(i)
            if vecs and len({v.shape[0] for v in vecs}) == 1:
                m = np.vstack(vecs)
                m /= np.linalg.norm(m, axis=1, keepdims=True) + 1e-9
                self.emb, self.emb_rows = m, idx
            else:
                self.emb, self.emb_rows = None, []

    @property
    def size(self) -> int:
        return len(self.chunks)

    @property
    def has_embeddings(self) -> bool:
        return self.emb is not None

    def _bm25(self, query: str, k1: float = 1.4, b: float = 0.75) -> list[tuple[int, float]]:
        q = tokenize(query)
        n = len(self.chunks)
        scores: dict[int, float] = defaultdict(float)
        for term in set(q):
            df = self.df.get(term, 0)
            if not df:
                continue
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            for i, c in enumerate(self.doc_tokens):
                tf = c.get(term, 0)
                if tf:
                    dl = sum(c.values())
                    scores[i] += idf * tf * (k1 + 1) / (tf + k1 * (1 - b + b * dl / self.avgdl))
        return sorted(scores.items(), key=lambda x: -x[1])

    def _dense(self, qvec: np.ndarray) -> list[tuple[int, float]]:
        if self.emb is None:
            return []
        q = qvec / (np.linalg.norm(qvec) + 1e-9)
        sims = self.emb @ q
        order = np.argsort(-sims)[:50]
        return [(self.emb_rows[j], float(sims[j])) for j in order]

    # Επεξήγηση: Συνδυάζει τις διαθέσιμες κατατάξεις και επιστρέφει περιορισμένα σχετικά αποσπάσματα.
    def search(
        self,
        query: str,
        k: int = 8,
        where: Callable[[dict], bool] | None = None,
        query_vec: np.ndarray | None = None,
    ) -> list[Hit]:
        shared_ids = sharing.demo_source_ids(self.person, "business") if sharing.restricted(self.person) else None
        if shared_ids == frozenset():
            return []
        with self._lock:
            if not self.chunks:
                return []
            rankings = [self._bm25(query)]
            if query_vec is not None and self.emb is not None:
                rankings.append(self._dense(query_vec))
            fused: dict[int, float] = defaultdict(float)
            for ranking in rankings:
                eligible = (i for i, _ in ranking
                            if (shared_ids is None or self.chunks[i]["source_id"] in shared_ids)
                            and (where is None or where(self.items.get(self.chunks[i]["item_id"], {}))))
                for rank, i in enumerate(itertools.islice(eligible, 60)):
                    fused[i] += 1.0 / (60 + rank)
            out: list[Hit] = []
            seen_items: set[str] = set()
            for i, s in sorted(fused.items(), key=lambda x: -x[1]):
                ch = self.chunks[i]
                item = self.items.get(ch["item_id"], {})
                if ch["item_id"] in seen_items and len(out) >= k // 2:
                    continue
                seen_items.add(ch["item_id"])
                out.append(Hit(ch["id"], ch["item_id"], ch["source_id"], ch["text"], round(s * 1000, 2), item))
                if len(out) >= k:
                    break
            return out


_INDEXES: dict[str, MemoryIndex] = {}
_INDEX_LOCK = threading.Lock()


def index_for(person: str) -> MemoryIndex:
    with _INDEX_LOCK:
        if person not in _INDEXES:
            idx = MemoryIndex(person)
            _INDEXES[person] = idx
            idx.rebuild()
        return _INDEXES[person]


class _CurrentIndex:
    """`INDEX` always refers to the memory of the person the request runs as."""

    def __getattr__(self, name: str):
        return getattr(index_for(pid()), name)


INDEX = _CurrentIndex()
