# MIRROR — pitch & demo script (≈ 5 minutes)

## 0:00 – The problem (30 s)
"Every 'AI twin' you've seen is the same trick: a chatbot with *'You are Danai, CEO'* in the prompt. It sounds confident, it invents opinions, and nobody can tell you **why** it said what it said, or whether it's actually *her*.

We asked three questions: what would it take for a twin to **decide like her**, **write like her**, and **know when it doesn't know**? And how would you **prove** it?"

## 0:30 – The idea (30 s)
"MIRROR, a mirror of yourself, builds a twin from four measurable parts:
1. a **memory** of everything she wrote,
2. an **inspectable persona model**: values, knowledge, preferences and decision rules, each one linked to evidence,
3. a **stylometric fingerprint** of how she writes in each channel,
4. and **owner control**: she approves, corrects, forgets."

## 1:00 – Live demo (2 min 30 s)
Company: the fictional **NexaTech Solutions**, with our team's synthetic datasets (emails, Teams, decision log, policies, minutes).
1. **Log in as `sales_manager`** (20 s): "Alexandros, Sales Manager. Home is the company pyramid: he can talk to the CEO's AI. Myrto, in Finance, is locked: *another reporting line*. Access only goes upwards, enforced on the server."
2. **Chat with Danai's Mirror** (40 s): "A client asks for a two-year exclusivity deal. What do I do?" → "No exclusivity: a non-exclusive pilot with a volume cap and a review", exactly as she decided for AegeanWorks. Then "why?": it shows her own email. "Who approves 14%?" → "above 12% comes to me".
3. **"I don't know"** (10 s): "Who should we hire as CTO?" → "I don't know, I've never written about it." An AI that invents opinions is an impersonation risk.
4. **Voice & Avatar** (30 s): switch to **Avatar**: the same answer in her voice (ElevenLabs) with a live face (Simli). Then **Voice avatar**: hands-free conversation.
5. **Log in as `ceo` → self-test** (40 s): "Danai is at the top: she doesn't chat with anyone's AI, she checks her own. She answers first, then sees what the AI would say. If it's wrong, her correction becomes verified knowledge. Three right in a row and the topic is verified."
6. **Fidelity** (10 s): "The 12 November examples were never shown to the AI. We use them to measure whether it decides and answers like the person, against a plain chatbot."

## 3:30 – Why it matters (45 s)
- **Business value:** executives, doctors, lawyers and public servants answer the same questions all day. A twin drafts in their voice, applies their rules, and **escalates what it shouldn't decide**. For Netcompany's public-sector clients: knowledge continuity when experts retire or rotate.
- **Trust by design:** evidence on every claim, the twin never sends anything on its own, disclosure footers, boundaries, consent per source, real forgetting (delete a source → traits disappear), audit log. GDPR-aligned and EU-AI-Act-friendly.
- **Runs anywhere:** one `docker compose up`; Claude, OpenAI, local Ollama, or fully offline.

## 4:15 – Close (15 s)
"Not a chatbot that *pretends* to be you, but a twin that can **show its work**, **prove its fidelity**, and **stays yours**. Thank you."

---

## Likely Q&A

**How does the twin learn and stay current?**
Retrieval over a hybrid memory, plus LLM map-reduce profile extraction with citations. New data → rebuild → versioned diff ("what changed in me"). Owner edits to drafts become new writing samples immediately.

**Why not fine-tune?**
Fine-tuned weights can't forget, can't cite and need lots of data. RAG + profile is auditable and deletable, and works from day one with ~80 items. Fine-tuning a small model on approved drafts is a natural next step once the owner has hundreds of them.

**How did you measure fidelity?**
Temporal hold-out split off *before* ingestion: decision accuracy against a same-model persona-prompt baseline, stylometric closeness to real replies, blind LLM-as-judge with randomised order, knowledge recall, abstention rate, and a human blind test.

**Isn't the offline engine cheating?**
It runs on the same persona model and memory; it just matches instead of generating. That proves the value is in the **model of the person**, not in the LLM. With an LLM, drafts adapt to the exact message and the baseline becomes the same LLM.

**Privacy?**
Redaction (with checksums for IBAN, AFM and AMKA) before storage, only redacted text to the LLM, no raw files kept, consent per source, erasure, local SQLite, an Ollama profile for on-premise use, keys never persisted or logged.

**Misuse / impersonation?**
The twin is bound to its owner, never sends, discloses itself, refuses boundary topics, and abstains when unsure. Everything is audited.

**Scale?**
SQLite + in-process index handles a person's lifetime of email (100k chunks) on a laptop. The module boundaries (retrieval, profile, LLM) map 1:1 to pgvector, a queue and a model gateway for multi-tenant use.
