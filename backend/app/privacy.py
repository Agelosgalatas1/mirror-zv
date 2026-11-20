# Επεξήγηση: Εντοπίζει υποστηριζόμενα προσωπικά στοιχεία και εφαρμόζει τα όρια θεμάτων του κατόχου.
"""Privacy layer: PII redaction at ingestion and owner-defined boundaries.

Redaction runs *before* anything is stored or sent to an LLM. Detectors are
pattern + checksum based (IBAN mod-97, Greek AFM checksum, AMKA/cards Luhn),
so they are fast, deterministic and explainable, and they cover Greek
identifiers that generic PII tools miss.
"""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
IBAN_RE = re.compile(r"\b[A-Z]{2}\d{2}(?:[ ]?[A-Z0-9]{4}){2,7}(?:[ ]?[A-Z0-9]{1,4})?\b")
PHONE_GR_RE = re.compile(r"(?<![\w+])(?:\+30[\s-]?)?(?:2\d{2}|69\d)[\s-]?\d{3}[\s-]?\d{4}(?!\w)")
PHONE_INTL_RE = re.compile(r"(?<![\w])\+\d{1,3}(?:[\s-]?\d{2,4}){2,4}(?!\w)")
DIGITS9_RE = re.compile(r"(?<!\d)\d{9}(?!\d)")
DIGITS11_RE = re.compile(r"(?<!\d)\d{11}(?!\d)")
CARD_RE = re.compile(r"(?<!\d)(?:\d[ -]?){13,19}(?!\d)")


def _iban_ok(raw: str) -> bool:
    s = raw.replace(" ", "")
    if len(s) < 15 or len(s) > 34:
        return False
    s = s[4:] + s[:4]
    try:
        return int("".join(str(int(c, 36)) for c in s)) % 97 == 1
    except ValueError:
        return False


def _afm_ok(s: str) -> bool:
    d = [int(c) for c in s]
    if len(d) != 9 or sum(d) == 0:
        return False
    total = sum(d[i] * (2 ** (8 - i)) for i in range(8))
    return total % 11 % 10 == d[8]


def _luhn_ok(s: str) -> bool:
    digits = [int(c) for c in s if c.isdigit()]
    if len(digits) < 11:
        return False
    total = 0
    for i, d in enumerate(reversed(digits)):
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def _amka_ok(s: str) -> bool:
    day, month = int(s[0:2]), int(s[2:4])
    return 1 <= day <= 31 and 1 <= month <= 12 and _luhn_ok(s)


@dataclass
class Redaction:
    text: str
    counts: Counter


# Επεξήγηση: Αντικαθιστά τα αναγνωρισμένα ευαίσθητα μοτίβα πριν από αποθήκευση και χρήση από AI.
def redact(text: str) -> Redaction:
    counts: Counter = Counter()

    def sub(pattern: re.Pattern, label: str, check=None):
        nonlocal text

        def repl(m: re.Match) -> str:
            val = m.group(0)
            if check and not check(val):
                return val
            counts[label] += 1
            return f"[{label}]"

        text = pattern.sub(repl, text)

    sub(EMAIL_RE, "EMAIL")
    sub(IBAN_RE, "IBAN", _iban_ok)
    sub(CARD_RE, "CARD", lambda v: _luhn_ok(v) and len(re.sub(r"\D", "", v)) >= 13)
    sub(DIGITS11_RE, "AMKA", _amka_ok)
    sub(DIGITS9_RE, "AFM", _afm_ok)
    sub(PHONE_INTL_RE, "PHONE")
    sub(PHONE_GR_RE, "PHONE")
    return Redaction(text=text, counts=counts)


# --------------------------------------------------------------------------
# Boundaries: topics the owner never lets the twin speak about.
# --------------------------------------------------------------------------

DEFAULT_BOUNDARIES = [
    {
        "id": "health",
        "label": "Υγεία & ιατρικά",
        "enabled": True,
        "keywords": ["health", "medical", "medication", "medicine", "diagnosis", "doctor", "therapy", "illness",
                     "pregnan", "blood type", "υγεία", "φάρμακ", "γιατρ", "διάγνωσ", "θεραπεί", "ασθέν", "εγκυμοσ"],
    },
    {
        "id": "finance",
        "label": "Προσωπικά οικονομικά & κωδικοί",
        "enabled": True,
        "keywords": ["salary", "my bank", "your password", "my password", "pin code", "credit card", "your iban",
                     "net worth", "μισθ", "τον κωδικό σου", "τράπεζ", "πιστωτικ"],
    },
    {
        "id": "beliefs",
        "label": "Πολιτική & θρησκεία",
        "enabled": True,
        "keywords": ["vote for", "political party", "religion", "religious", "ψηφίσ", "κόμμα", "θρησκ"],
    },
    {
        "id": "relationships",
        "label": "Ερωτικές σχέσεις",
        "enabled": True,
        "keywords": ["boyfriend", "girlfriend", "dating", "partner at home", "σχέση σου", "γκόμεν", "ραντεβού με"],
    },
]


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFD", s.lower())
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


GREEK_CREDIT_CARD = re.compile(r"\bπιστωτικ(?:η|ης|ες|ων)\s+(?:(?:σου|μου|του|της|μας|σας|τους)\s+)?καρτ")


# Επεξήγηση: Εντοπίζει ερωτήσεις που εμπίπτουν στα προστατευμένα θέματα.
def check_boundaries(text: str, boundaries: list[dict]) -> dict | None:
    folded = _fold(text)
    for b in boundaries:
        if not b.get("enabled", True):
            continue
        for kw in b.get("keywords", []):
            term = _fold(kw)
            # The legacy Greek finance stem also matches ordinary business credit policy.
            if b["id"] == "finance" and term == "πιστωτικ":
                matched = bool(GREEK_CREDIT_CARD.search(folded))
            else:
                matched = term in folded
            if matched:
                return {"id": b["id"], "label": b["label"], "matched": kw}
    return None
