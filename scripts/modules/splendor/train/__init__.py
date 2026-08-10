# SPDX-License-Identifier: GPL-2.0-or-later
"""Training layer (P3-adjacent, SPL-S3) — honest by construction.

Four modalities (D-3.1): diffusion LoRAs, LLM LoRAs, **weightless workflow
capture**, and 3D/geometry models. Only workflow capture is real here — it saves a
successful workflow as a reusable, content-hashed library entry (learning by
example, no gradients). The weight-based modalities are *named honestly*: a job
reports "trainer not yet wired" rather than faking a trained model, and cloud /
Citrate-DePIN compute (D-3.2) reports availability truthfully. Pure Python.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass

from splendor.graph import dumps

MODALITIES = ("diffusion_lora", "llm_lora", "workflow_lora", "workflow_capture", "geometry_model")
COMPUTES = ("local", "cloud", "depin")

# The real, trainable modalities (deterministic loss + Eval-SDK-scored improvement).
TRAINABLE = ("workflow_capture", "workflow_lora")


@dataclass
class LibraryEntry:
    id: str
    digest: str
    artifact: str
    modality: str = "workflow_capture"


class WorkflowLibrary:
    """Captured, reusable workflows (D-7.2). In-memory now; later persisted + pinned."""

    def __init__(self):
        self._entries: list[LibraryEntry] = []

    def capture(self, workflow, name=None) -> LibraryEntry:
        artifact = dumps(workflow)
        digest = "sha256:" + hashlib.sha256(artifact.encode()).hexdigest()
        entry = LibraryEntry(id=name or f"wf-{len(self._entries) + 1}", digest=digest, artifact=artifact)
        self._entries.append(entry)
        return entry

    def all(self):
        return list(self._entries)

    def __len__(self):
        return len(self._entries)


def compute_available(kind: str, env) -> bool:
    """Is this compute source usable? Local is present; cloud/DePIN are config-gated."""
    if kind == "local":
        return True
    if kind == "cloud":
        return bool(env.get("SPLENDOR_CLOUD_TRAINING"))
    if kind == "depin":
        return bool(env.get("SPLENDOR_DEPIN_COMPUTE"))
    return False


def job_status(modality: str, compute: str, env) -> str:
    """The honest status for a job — capture + Workflow LoRA are real; weight LoRAs
    (LLM/diffusion adapting real model weights) still need a delegated trainer."""
    if modality == "workflow_capture":
        return "ready · weightless capture"
    if modality == "workflow_lora":
        return "ready · trains a low-rank adapter on captured runs"
    if not compute_available(compute, env):
        label = {"cloud": "cloud", "depin": "Citrate DePIN"}.get(compute, compute)
        return f"{label} compute unavailable — not configured"
    return f"queued · requires a {modality} weight trainer (not yet wired)"


# Re-export the training-loop API (lazy-friendly: these pull in numpy).
from .featurize import featurize, featurize_batch  # noqa: E402
from .lora import LoRAAdapter, mse, train_lora  # noqa: E402
from .loop import Sample, run_training_loop  # noqa: E402

__all__ = [
    "MODALITIES", "COMPUTES", "TRAINABLE", "LibraryEntry", "WorkflowLibrary",
    "compute_available", "job_status",
    "featurize", "featurize_batch", "LoRAAdapter", "mse", "train_lora",
    "Sample", "run_training_loop",
]
