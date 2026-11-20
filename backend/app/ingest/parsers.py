# Επεξήγηση: Μετατρέπει διαφορετικούς τύπους αρχείων σε κοινή μορφή μηνυμάτων και εγγράφων.
"""Parsers that turn a raw digital footprint into normalised items.

Supported: .mbox / .eml (email), Slack-style .json, WhatsApp .txt exports,
generic JSON message lists, Markdown / text notes and documents, PDF, and
.zip archives containing any of these.
"""
from __future__ import annotations

import email
import email.policy
import io
import json
import mailbox
import re
import tempfile
import zipfile
from dataclasses import dataclass, field
from datetime import datetime
from email.utils import getaddresses, parsedate_to_datetime
from pathlib import Path
from typing import Iterable


@dataclass
class Owner:
    name: str
    aliases: list[str]
    emails: list[str]
    org_domain: str = ""
    display_name: str = ""
    role: str = ""

    def is_me(self, author: str | None, address: str | None = None) -> bool:
        if address and address.lower() in {e.lower() for e in self.emails}:
            return True
        if not author:
            return False
        a = author.strip().lower()
        return any(a == x.lower() for x in self.aliases)

    @classmethod
    def from_dict(cls, d: dict) -> "Owner":
        return cls(
            name=d.get("name", "Owner"),
            aliases=d.get("aliases") or [d.get("name", "Owner")],
            emails=d.get("emails") or [],
            org_domain=d.get("org_domain", ""),
            display_name=d.get("display_name") or d.get("name", "Owner").split()[0],
            role=d.get("role", ""),
        )


@dataclass
class RawItem:
    kind: str  # email | chat | note | doc
    channel: str  # email_external | email_internal | chat_team | chat_personal | note | doc
    text: str
    author: str | None = None
    is_owner: bool = False
    audience: str | None = None
    counterpart: str | None = None
    subject: str | None = None
    ts: str | None = None
    ext_id: str | None = None
    reply_to_ext: str | None = None
    meta: dict = field(default_factory=dict)


# ----------------------------------------------------------------- helpers

def _audience_for_domain(domain: str, owner: Owner) -> tuple[str, str]:
    d = domain.lower()
    if owner.org_domain and d.endswith(owner.org_domain.lower()):
        return "email_internal", "Colleague"
    if any(k in d for k in ("gov", "cityof", "municipal", "dimos", "δήμος")):
        return "email_external", "Public sector"
    if any(k in d for k in ("ventures", "capital", "invest")):
        return "email_external", "Investor"
    if any(k in d for k in ("recruit", "talent", "hr")):
        return "email_external", "Recruiter"
    return "email_external", "External partner"


def _clean_email_body(body: str) -> str:
    lines = []
    for line in body.replace("\r\n", "\n").split("\n"):
        if line.strip() in ("--", "-- "):
            break  # signature block
        if line.startswith(">"):
            continue  # quoted reply
        if re.match(r"^On .+wrote:$", line.strip()):
            break
        lines.append(line)
    return "\n".join(lines).strip()


def _email_body(msg: email.message.Message) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True) or b""
                return payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        return ""
    payload = msg.get_payload(decode=True)
    if payload is None:
        return str(msg.get_payload())
    return payload.decode(msg.get_content_charset() or "utf-8", errors="replace")


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


# ----------------------------------------------------------------- email

# Επεξήγηση: Αναγνωρίζει αποστολέα, κανάλι και περιεχόμενο κάθε email.
def parse_email_message(msg: email.message.Message, owner: Owner) -> RawItem | None:
    from_list = getaddresses([str(msg.get("From", ""))])
    to_list = getaddresses([str(msg.get("To", "")), str(msg.get("Cc", ""))])
    from_name, from_addr = from_list[0] if from_list else ("", "")
    is_owner = owner.is_me(from_name, from_addr)
    counterpart_name, counterpart_addr = (to_list[0] if (is_owner and to_list) else (from_name, from_addr))
    domain = counterpart_addr.split("@")[-1] if "@" in counterpart_addr else ""
    channel, audience = _audience_for_domain(domain, owner)
    body = _clean_email_body(_email_body(msg))
    if not body:
        return None
    try:
        ts = _iso(parsedate_to_datetime(str(msg.get("Date")))) if msg.get("Date") else None
    except (TypeError, ValueError):
        ts = None
    return RawItem(
        kind="email",
        channel=channel,
        text=body,
        author=from_name or from_addr,
        is_owner=is_owner,
        audience=audience,
        counterpart=counterpart_name or counterpart_addr,
        subject=str(msg.get("Subject", "")) or None,
        ts=ts,
        ext_id=str(msg.get("Message-ID", "")) or None,
        reply_to_ext=str(msg.get("In-Reply-To", "")) or None,
    )


def parse_mbox(data: bytes, owner: Owner) -> list[RawItem]:
    with tempfile.NamedTemporaryFile(suffix=".mbox", delete=True) as tmp:
        tmp.write(data)
        tmp.flush()
        box = mailbox.mbox(tmp.name, create=False)
        items = [parse_email_message(m, owner) for m in box]
        box.close()
    return [i for i in items if i]


def parse_eml(data: bytes, owner: Owner) -> list[RawItem]:
    msg = email.message_from_bytes(data, policy=email.policy.compat32)
    item = parse_email_message(msg, owner)
    return [item] if item else []


# ----------------------------------------------------------------- chats

WA_LINE = re.compile(
    r"^\[?(\d{1,2}/\d{1,2}/\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?(?:\s?[APap][Mm])?)\]?\s*(?:-\s*)?([^:]{1,60}):\s(.*)$"
)


def _wa_ts(d: str, t: str) -> str | None:
    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%y %H:%M", "%d/%m/%Y %H:%M:%S", "%m/%d/%y %I:%M %p"):
        try:
            return datetime.strptime(f"{d} {t.upper()}", fmt).isoformat()
        except ValueError:
            continue
    return None


def parse_whatsapp(text: str, owner: Owner) -> list[RawItem]:
    items: list[RawItem] = []
    for line in text.splitlines():
        m = WA_LINE.match(line.strip())
        if m:
            d, t, author, msg = m.groups()
            author = author.strip()
            items.append(
                RawItem(kind="chat", channel="chat_personal", text=msg.strip(), author=author,
                        is_owner=owner.is_me(author), audience="Friend", ts=_wa_ts(d, t))
            )
        elif items and line.strip():
            items[-1].text += "\n" + line.strip()
    _attach_chat_context(items)
    return items


def _attach_chat_context(items: list[RawItem]) -> None:
    """For owner messages, remember the message they replied to (for style exemplars)."""
    for i, it in enumerate(items):
        if it.is_owner and i > 0 and not items[i - 1].is_owner:
            it.meta["in_reply_to_text"] = items[i - 1].text
            it.counterpart = items[i - 1].author
        elif not it.is_owner:
            it.counterpart = owner_placeholder()


def owner_placeholder() -> str:
    return "owner"


# Επεξήγηση: Κανονικοποιεί εξαγωγές chat και συνδέει τα διαθέσιμα συμφραζόμενα.
def parse_chat_json(data: bytes, owner: Owner) -> list[RawItem]:
    obj = json.loads(data.decode("utf-8"))
    msgs = obj.get("messages", obj) if isinstance(obj, dict) else obj
    items: list[RawItem] = []
    for m in msgs:
        if not isinstance(m, dict):
            continue
        author = m.get("user_name") or m.get("author") or m.get("user") or m.get("from")
        text = m.get("text") or m.get("content") or ""
        if not text.strip():
            continue
        channel_name = str(m.get("channel", ""))
        items.append(
            RawItem(kind="chat", channel="chat_team", text=text.strip(), author=author,
                    is_owner=owner.is_me(author), audience="Team", ts=m.get("ts") or m.get("date"),
                    meta={"chat_channel": channel_name} if channel_name else {})
        )
    _attach_chat_context(items)
    return items


# ----------------------------------------------------------------- notes / docs

def parse_text_doc(text: str, filename: str, owner: Owner) -> list[RawItem]:
    lower = filename.lower()
    is_note = any(k in lower for k in ("note", "journal", "log", "diary", "1on1", "one_on"))
    title = Path(filename).stem.replace("_", " ").strip()
    first_heading = re.search(r"^#\s+(.+)$", text, re.M)
    if first_heading:
        title = first_heading.group(1).strip()
    return [
        RawItem(kind="note" if is_note else "doc", channel="note" if is_note else "doc", text=text.strip(),
                author=owner.name, is_owner=True, audience="Self" if is_note else "Readers", subject=title)
    ]


def parse_pdf(data: bytes, filename: str, owner: Owner) -> list[RawItem]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    text = "\n\n".join((p.extract_text() or "") for p in reader.pages)
    return parse_text_doc(text, filename, owner) if text.strip() else []


# ----------------------------------------------------------------- dispatcher

# Επεξήγηση: Επιλέγει αναγνώστη ανάλογα με τον τύπο αρχείου.
def parse_file(filename: str, data: bytes, owner: Owner) -> list[RawItem]:
    name = filename.lower()
    if name.endswith(".zip"):
        out: list[RawItem] = []
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for info in zf.infolist():
                if info.is_dir() or info.file_size > 20_000_000 or "__MACOSX" in info.filename:
                    continue
                out.extend(parse_file(info.filename, zf.read(info), owner))
        return out
    if name.endswith(".mbox"):
        return parse_mbox(data, owner)
    if name.endswith(".eml"):
        return parse_eml(data, owner)
    if name.endswith(".pdf"):
        return parse_pdf(data, filename, owner)
    if name.endswith(".json"):
        return parse_chat_json(data, owner)
    text = data.decode("utf-8", errors="replace")
    if name.endswith(".txt") and sum(1 for line in text.splitlines()[:30] if WA_LINE.match(line.strip())) >= 3:
        return parse_whatsapp(text, owner)
    if name.endswith((".md", ".txt", ".markdown")):
        return parse_text_doc(text, filename, owner)
    raise ValueError(f"Μη υποστηριζόμενος τύπος αρχείου: {filename}")


SUPPORTED = ".mbox, .eml, .json (Slack/chat), .txt (εξαγωγή WhatsApp ή σημειώσεις), .md, .pdf, .zip"


# Επεξήγηση: Εντοπίζει τα υποστηριζόμενα αρχεία για την αρχική εισαγωγή.
def iter_demo_files(demo_dir: Path) -> Iterable[Path]:
    for p in sorted(demo_dir.rglob("*")):
        if p.is_file() and p.parent.name != "eval" and p.name != "owner.json":
            yield p
