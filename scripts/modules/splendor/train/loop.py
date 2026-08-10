# SPDX-License-Identifier: GPL-2.0-or-later
"""The workflow-LoRA training loop — capture → featurize → train → eval, closed.

A **Workflow LoRA** is a low-rank adapter that learns your *prompt → intent-parameter*
preferences from eval-scored runs: given the prompts of high-scoring captured
workflows and the parameters they used, it learns to predict good parameters for a
new prompt. The loop is honest and measured against reality — success is defined by
the **Eval SDK** re-scoring held-out prompts, not by the training loss alone.

Pure (numpy + the Eval SDK), deterministic, bpy-free. The trained adapter is
content-addressed (:meth:`LoRAAdapter.digest`) so it can be pinned + attested like any
other Splendor artifact.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .featurize import featurize_batch
from .lora import train_lora


@dataclass
class Sample:
    """One captured run: the prompt, the palette it used, and the eval palette limit
    that defined 'good' for that prompt."""
    prompt: str
    palette: int
    limit: int


def _targets(samples):
    return np.array([[s.palette / 256.0] for s in samples], dtype=np.float64)


def _eval_pass_rate(samples, palettes):
    """Fraction of `samples` whose predicted palette passes the Eval SDK's
    PaletteAdherence at that sample's limit — the reality check."""
    import splendor_eval as ev
    passed = 0
    for s, p in zip(samples, palettes):
        harness = ev.EvalHarness([ev.PaletteAdherence(s.limit)])
        rec = harness.evaluate({"palette_colors": int(round(p)), "tri_count": 0}, s.prompt, seed=0)
        passed += 1 if rec.passed_all else 0
    return passed / len(samples) if samples else 0.0


def _predict_palettes(adapter, prompts, dim):
    x = featurize_batch(prompts, dim)
    return np.clip(adapter.predict(x)[:, 0] * 256.0, 1.0, 256.0)


def run_training_loop(train_samples, holdout_samples, dim: int = 32, rank: int = 2,
                      epochs: int = 400, lr: float = 0.3, seed: int = 0) -> dict:
    """Train a Workflow LoRA on `train_samples`, evaluate on `holdout_samples`.

    Returns metrics: the loss history, the Eval-SDK pass rates for the LoRA vs. a
    constant baseline (mean training palette), the improvement, and the adapter (with
    its content digest).
    """
    if not train_samples:
        raise ValueError("no captured runs to train on")
    x = featurize_batch([s.prompt for s in train_samples], dim)
    y = _targets(train_samples)
    adapter, history = train_lora(x, y, rank=rank, epochs=epochs, lr=lr, seed=seed)

    baseline_palette = float(np.mean([s.palette for s in train_samples]))
    lora_pred = _predict_palettes(adapter, [s.prompt for s in holdout_samples], dim)
    lora_pass = _eval_pass_rate(holdout_samples, lora_pred)
    base_pass = _eval_pass_rate(holdout_samples, [baseline_palette] * len(holdout_samples))
    return {
        "epochs": len(history) - 1,
        "final_loss": history[-1],
        "loss_history": history,
        "adapter": adapter,
        "adapter_digest": adapter.digest(),
        "baseline_palette": baseline_palette,
        "eval_pass_lora": lora_pass,
        "eval_pass_baseline": base_pass,
        "improvement": lora_pass - base_pass,
    }
