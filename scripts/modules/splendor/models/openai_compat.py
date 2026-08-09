# SPDX-License-Identifier: GPL-2.0-or-later
"""OpenAI-compatible backend — the local-model lingua franca.

One adapter covers **llama.cpp server, Ollama (`/v1`), LM Studio, vLLM, and
OpenAI itself** (D-2.2, D-7.3): they all speak ``POST /v1/chat/completions`` and
``GET /v1/models``. Set ``is_local`` so the Router can honour local-first. Uses
stdlib ``urllib`` — no ``openai``/``requests`` dependency.
"""
from __future__ import annotations

import json
import urllib.error
import urllib.request

from .base import (
    Backend, BackendUnavailable, Capability, CompletionRequest, CompletionResult, Modality,
)


class OpenAICompatBackend(Backend):
    def __init__(self, name, base_url, model, *, is_local=True, api_key=None,
                 modalities=(Modality.TEXT,), context_tokens=None, supports_tools=False):
        self.name = name
        self.base_url = base_url.rstrip("/")   # e.g. http://127.0.0.1:11434/v1
        self.model = model
        self.api_key = api_key
        self.capability = Capability(
            frozenset(modalities), bool(is_local), context_tokens, supports_tools)

    def _request(self, path, data=None, timeout=30.0):
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        body = json.dumps(data).encode() if data is not None else None
        req = urllib.request.Request(
            self.base_url + path, data=body, headers=headers,
            method="POST" if data is not None else "GET")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode())

    def reachable(self, timeout: float = 1.5) -> bool:
        try:
            self._request("/models", data=None, timeout=timeout)
            return True
        except Exception:
            return False

    def complete(self, req: CompletionRequest, timeout: float = 30.0) -> CompletionResult:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in req.messages],
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
        }
        try:
            data = self._request("/chat/completions", data=payload, timeout=timeout)
        except (urllib.error.URLError, OSError) as exc:
            # Honest failure — never a fabricated completion (framework §2).
            raise BackendUnavailable(f"{self.name} unavailable: {exc}") from exc
        try:
            text = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise BackendUnavailable(f"{self.name} returned an unexpected shape: {exc}") from exc
        return CompletionResult(text=text, backend=self.name, model=self.model, raw=data)
