# Επεξήγηση: Κοινός χειρισμός παρόχων AI, δομημένων απαντήσεων και προαιρετικών embeddings.
"""Provider-agnostic LLM access: Anthropic Claude, OpenAI, Ollama or offline.

Every call asks for a JSON object back. The rest of the system works on
structured outputs only, which makes the twin's answers inspectable.
"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
from dataclasses import dataclass, field
from typing import Any

import numpy as np

from .config import settings

log = logging.getLogger("mirror.llm")

# Models that accept Anthropic's server-side refusal fallback.
_FALLBACK_MODELS = ("claude-opus-5-5", "claude-opus-5", "claude-fable-5-2", "claude-fable-5-1", "claude-sonnet-5-5")


DEFAULT_OPENAI_URL = "https://api.openai.com/v1"
DEFAULT_ANTHROPIC_URL = "https://api.anthropic.com"


class LLMError(RuntimeError):
    pass


class LLMUnavailable(LLMError):
    pass


def parse_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError as exc:
            raise LLMError(f"Model did not return valid JSON: {exc}") from exc
    raise LLMError("Model did not return JSON")


@dataclass
class Stats:
    calls: int = 0
    errors: int = 0
    total_latency: float = 0.0
    last_error: str | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)

    def record(self, latency: float, error: str | None = None) -> None:
        with self.lock:
            self.calls += 1
            self.total_latency += latency
            if error:
                self.errors += 1
                self.last_error = error


class LLM:
    def __init__(self) -> None:
        self.stats = Stats()
        # Keys can be overridden at runtime from the UI (kept in memory only, never persisted).
        self.keys = {"anthropic": settings.anthropic_api_key, "openai": settings.openai_api_key}
        self.models = {"anthropic": settings.anthropic_model, "openai": settings.openai_model,
                       "ollama": settings.ollama_model}
        self.wanted = settings.llm_provider
        self.provider, self.model = self._resolve()
        self._client: Any = None
        self._embed_client: Any = None
        self._sem = threading.Semaphore(max(1, settings.max_parallel_llm))

    # ------------------------------------------------------------ setup
    def _resolve(self) -> tuple[str, str]:
        p = self.wanted
        if p == "auto":
            if self.keys["anthropic"]:
                p = "anthropic"
            elif self.keys["openai"]:
                p = "openai"
            elif settings.ollama_base_url:
                p = "ollama"
            else:
                p = "offline"
        if p in ("anthropic", "openai") and not self.keys[p]:
            p = "offline"
        if p == "ollama" and not settings.ollama_base_url:
            p = "offline"
        return p, self.models.get(p, "rule-based")

    @staticmethod
    def clean_key(raw: str) -> str:
        """Keys are often pasted with quotes, a 'Bearer ' prefix, spaces or line breaks."""
        key = raw.strip().strip('"').strip("'").strip()
        if key.lower().startswith("bearer "):
            key = key[7:]
        key = re.sub(r"\s+", "", key)
        if not key.isascii() or any(c in key for c in "*•"):
            raise ValueError("Το key περιέχει μη έγκυρους χαρακτήρες (π.χ. «…» ή ελληνικά γράμματα). "
                             "Αντέγραψέ το ολόκληρο από τη σελίδα των API keys.")
        if len(key) < 20:
            raise ValueError("Το key φαίνεται κομμένο. Αντέγραψέ το ολόκληρο.")
        return key

    def explain(self, exc: Exception) -> str:
        """A short Greek explanation of a provider error, for the UI."""
        name = type(exc).__name__
        if name == "AuthenticationError":
            return f"Ο πάροχος ({self.provider}) απέρριψε το key (401). Έλεγξε ότι το αντέγραψες ολόκληρο και ότι είναι ενεργό."
        if name == "NotFoundError":
            return f"Το μοντέλο «{self.model}» δεν είναι διαθέσιμο με αυτό το key. Δοκίμασε άλλο μοντέλο (π.χ. gpt-4o-mini)."
        if name == "PermissionDeniedError":
            return "Το key δεν έχει δικαίωμα σε αυτό το μοντέλο ή το project (403)."
        if name == "RateLimitError":
            return "Όριο χρήσης ή χωρίς υπόλοιπο (429). Έλεγξε το billing του λογαριασμού σου."
        if name in ("APIConnectionError", "APITimeoutError"):
            return "Δεν έγινε σύνδεση με τον πάροχο. Συνήθως φταίει μη έγκυρος χαρακτήρας στο key ή το δίκτυο."
        return f"{name}: {str(exc)[:200]}"

    def check(self) -> tuple[bool, str]:
        """Cheap live check that the key and the model work (no tokens spent)."""
        if not self.available:
            return True, "offline"
        try:
            client = self._get_client()
            client.models.retrieve(self.model)
            return True, "ok"
        except Exception as exc:  # noqa: BLE001 - reported to the user in Greek
            return False, self.explain(exc)

    def configure(self, provider: str, api_key: str | None = None, model: str | None = None) -> dict:
        provider = provider.strip().lower()
        if provider not in ("auto", "anthropic", "openai", "ollama", "offline"):
            raise ValueError("Άγνωστος πάροχος")
        before = (dict(self.keys), dict(self.models), self.wanted)
        if api_key and provider in ("anthropic", "openai"):
            self.keys[provider] = self.clean_key(api_key)
        if model and provider in self.models:
            self.models[provider] = model.strip()
        self.wanted = provider
        self.provider, self.model = self._resolve()
        self._client = None
        self._embed_client = None
        if provider in ("anthropic", "openai"):
            if self.provider == "offline":
                self.keys, self.models, self.wanted = before
                self.provider, self.model = self._resolve()
                raise ValueError("Δεν δόθηκε key για αυτόν τον πάροχο.")
            ok, msg = self.check()
            if not ok:
                self.keys, self.models, self.wanted = before
                self.provider, self.model = self._resolve()
                self._client = None
                self._embed_client = None
                raise ValueError(msg)
        self.stats.last_error = None
        return self.info()

    @property
    def available(self) -> bool:
        return self.provider != "offline"

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        if self.provider == "anthropic":
            import anthropic

            self._client = anthropic.Anthropic(api_key=self.keys["anthropic"], base_url=DEFAULT_ANTHROPIC_URL,
                                               timeout=settings.llm_timeout,
                                               max_retries=2)
        elif self.provider in ("openai", "ollama"):
            from openai import OpenAI

            if self.provider == "openai":
                kwargs: dict[str, Any] = {"api_key": self.keys["openai"]}
                # always explicit: an empty OPENAI_BASE_URL env var would otherwise break the SDK
                kwargs["base_url"] = settings.openai_base_url or DEFAULT_OPENAI_URL
            else:
                kwargs = {"api_key": "ollama", "base_url": settings.ollama_base_url.rstrip("/") + "/v1"}
            self._client = OpenAI(timeout=settings.llm_timeout, max_retries=2, **kwargs)
        else:
            raise LLMUnavailable("No LLM provider configured (offline mode)")
        return self._client

    def info(self) -> dict:
        return {
            "provider": self.provider,
            "model": self.model,
            "available": self.available,
            "embeddings": self.embeddings_available,
            "calls": self.stats.calls,
            "errors": self.stats.errors,
            "avg_latency_s": round(self.stats.total_latency / self.stats.calls, 2) if self.stats.calls else None,
            "last_error": self.stats.last_error,
        }

    # ------------------------------------------------------------ completion
    # Επεξήγηση: Ζητά δομημένη απάντηση ώστε τα υπόλοιπα μέρη να επεξεργάζονται κοινή μορφή.
    def json(self, system: str, user: str, *, max_tokens: int = 4000, effort: str = "low") -> dict:
        if not self.available:
            raise LLMUnavailable("offline")
        t0 = time.time()
        with self._sem:
            try:
                text = self._complete(system, user, max_tokens=max_tokens, effort=effort)
                try:
                    out = parse_json(text)
                except LLMError:
                    # one repair attempt
                    text = self._complete(
                        system,
                        user + "\n\nIMPORTANT: your previous answer was not valid JSON. Reply with ONE valid JSON object only.",
                        max_tokens=max_tokens, effort=effort,
                    )
                    out = parse_json(text)
                self.stats.record(time.time() - t0)
                return out
            except Exception as exc:  # noqa: BLE001 - surfaced to the caller and the UI
                self.stats.record(time.time() - t0, f"{type(exc).__name__}: {exc}"[:300])
                raise

    def _complete(self, system: str, user: str, *, max_tokens: int, effort: str) -> str:
        client = self._get_client()
        if self.provider == "anthropic":
            return self._anthropic(client, system, user, max_tokens, effort)
        return self._openai(client, system, user, max_tokens, effort)

    def _anthropic(self, client: Any, system: str, user: str, max_tokens: int, effort: str) -> str:
        import anthropic

        params: dict[str, Any] = {
            "model": self.model,
            "max_tokens": max_tokens,
            "system": system,
            "messages": [{"role": "user", "content": user}],
        }
        use_effort = not self.model.startswith(("claude-3", "claude-haiku-4", "claude-sonnet-4-5"))
        if use_effort:
            params["output_config"] = {"effort": "low" if effort == "minimal" else effort}
        try:
            if self.model.startswith(_FALLBACK_MODELS):
                resp = client.beta.messages.create(
                    betas=["server-side-fallback-2026-07-01"], fallbacks="default", **params
                )
            else:
                resp = client.messages.create(**params)
        except (TypeError, anthropic.BadRequestError) as exc:
            # Older SDK or a model that rejects the optional parameters: retry plainly.
            log.warning("Retrying Anthropic call without optional params: %s", exc)
            params.pop("output_config", None)
            resp = client.messages.create(**params)
        if resp.stop_reason == "refusal":
            raise LLMError("The model declined this request (refusal).")
        return "".join(getattr(b, "text", "") for b in resp.content if getattr(b, "type", "") == "text")

    def _openai(self, client: Any, system: str, user: str, max_tokens: int, effort: str) -> str:
        params: dict[str, Any] = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "response_format": {"type": "json_object"},
        }
        reasoning = self.provider == "openai" and self.model.startswith(("gpt-5", "o1", "o3", "o4"))
        if reasoning:
            params["reasoning_effort"] = {"minimal": "minimal", "low": "low", "medium": "medium",
                                          "high": "high"}.get(effort, "low")
            params["max_completion_tokens"] = max_tokens + 4000
        else:
            params["temperature"] = 0.4
            params["max_tokens"] = max_tokens
        try:
            resp = client.chat.completions.create(**params)
        except Exception as exc:  # noqa: BLE001
            if "response_format" in str(exc) or "reasoning_effort" in str(exc):
                params.pop("response_format", None)
                params.pop("reasoning_effort", None)
                resp = client.chat.completions.create(**params)
            else:
                raise
        return resp.choices[0].message.content or ""

    # ------------------------------------------------------------ embeddings
    @property
    def embeddings_available(self) -> bool:
        return bool(settings.use_embeddings and self.keys["openai"])

    # Επεξήγηση: Αν τα embeddings αποτύχουν, η αναζήτηση συνεχίζει με BM25.
    def embed(self, texts: list[str]) -> list[np.ndarray] | None:
        if not self.embeddings_available or not texts:
            return None
        try:
            if self._embed_client is None:
                from openai import OpenAI

                kwargs: dict[str, Any] = {"api_key": self.keys["openai"]}
                # always explicit: an empty OPENAI_BASE_URL env var would otherwise break the SDK
                kwargs["base_url"] = settings.openai_base_url or DEFAULT_OPENAI_URL
                self._embed_client = OpenAI(timeout=60, max_retries=2, **kwargs)
            out: list[np.ndarray] = []
            for i in range(0, len(texts), 96):
                resp = self._embed_client.embeddings.create(model=settings.openai_embedding_model,
                                                            input=[t[:6000] for t in texts[i:i + 96]])
                out.extend(np.asarray(d.embedding, dtype=np.float32) for d in resp.data)
            return out
        except Exception as exc:  # noqa: BLE001 - embeddings are optional, BM25 still works
            log.warning("Embeddings unavailable, falling back to BM25 only: %s", exc)
            self.stats.last_error = f"embeddings: {exc}"[:300]
            return None


LLM_CLIENT = LLM()
