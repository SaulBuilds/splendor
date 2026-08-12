---
created: 2026-08-10
branch: feat/spl-s3-lora
author: Claude Opus 4.8, directed by @SaulBuilds
status: active
---

# SPL-S3 — the Workflow LoRA training loop

A **Workflow LoRA** is a real low-rank adapter that learns your *prompt → intent-parameter*
preferences from eval-scored runs, closing the loop: **capture → featurize → train → eval**.
It is honest by construction — success is defined by the **Eval SDK** re-scoring held-out
prompts, not by the training loss.

## The pieces (`splendor.train`, numpy, deterministic)
- **`featurize`** — prompt → L2-normalised hashed bag-of-tokens (fixed seed → reproducible).
- **`lora`** — `LoRAAdapter` (`W = W0 + (α/r)·B·A`) + `train_lora`: real full-batch MSE gradient
  descent. Standard init (`A` small-random, `B` zero) ⇒ the untrained adapter is the base.
- **`loop`** — `run_training_loop(train, holdout)`: trains, then measures the Eval-SDK
  `PaletteAdherence` pass rate of the LoRA's held-out palette predictions vs. a constant
  baseline. The adapter is content-addressed (`digest()`) so it can be pinned + attested.

## Why it's real, not a stub (the old modality was "trainer not yet wired")
- **Loss actually falls** and a rank-r adapter **recovers a rank-r target** to ~0; an under-rank
  adapter provably can't (`test_spl_s3_lora.py [1]`).
- **It learns something useful**: on two prompt families with different palette limits, the LoRA
  passes the Eval SDK **1.00 vs the baseline's 0.50** — the constant baseline can't satisfy both
  limits; the LoRA learns them (`[3]`, +0.50 pass-rate).
- **Deterministic**: same seed/data → identical weights + digest.

## In the product
`SPLENDOR_OT_train_lora` (Training panel) trains on the captured-workflow LIBRARY: it extracts
`(prompt, palette)` samples, refuses honestly with < 4 runs (no fake adapter), trains, and
reports the Eval-SDK result + the content digest (`test_spl_s3_lora_ui.py`). On a small/degenerate
capture the reported gain may be modest — that honesty is the point; the numeric proof of learning
is the pure test.

## LLM-LoRA (real model weights) — DONE, delegated

Training an *LLM* LoRA needs torch/transformers/peft, which Blender's bundled Python doesn't have —
the same wall the signer hit. So it's **delegated to a trainer process** (`splendor.train.trainer`)
over a JSON protocol, exactly like the signer:

- `scripts/trainers/llm_lora_trainer.py` — a **real peft finetune**. Only the LoRA matrices train
  (the base is frozen); a real `adapter_model.safetensors` + content digest come back. Fully offline
  by default (a tiny randomly-initialised GPT-2 + byte tokenizer, no downloads); pass a HF id as
  `base` to adapt a pretrained model. Point Splendor at any trainer via `SPLENDOR_LORA_TRAINER`.
- The `llm_lora` modality (Training panel) builds a *prompt → params* dataset from captured runs and
  delegates. Blender has no torch, yet the product trains a real LoRA via the subprocess.

Verified (`test_spl_s3_llm_lora.py`, `_ui.py`): capabilities report the real backend; only the
adapter trains; loss falls; a real adapter + digest are produced; determinism; and honest
`TrainerUnavailable` when the trainer/deps are absent — never a fabricated adapter.

## Diffusion LoRA + geometry model — DONE

- **Diffusion LoRA** (`diffusion_lora`) — delegated like the LLM trainer, but a real **DDPM
  denoiser + peft LoRA** style finetune over your renders (`scripts/trainers/diffusion_lora_trainer.py`,
  torch+peft, no `diffusers`, fully offline on flat pixel vectors). Only the LoRA trains; the
  denoising loss falls; a real adapter + digest come back. `resolve_trainer(kind="diffusion")`
  and `train_diffusion(images)`; the panel builds the image set from the gallery/last render.
- **Geometry model** (`geometry_model`) — self-contained (numpy), a **PCA morphable shape basis**
  over captured same-topology meshes (`splendor.train.geometry`): mean + top-k components,
  reconstruction error → 0 at intrinsic rank, deterministic + content-addressed. The panel
  captures the active mesh and refits.

Verified: `test_spl_s3_geometry.py`, `test_spl_s3_diffusion.py`, `test_spl_s3_diffgeo_ui.py`.
All five modalities are now real (capture · workflow-LoRA · LLM-LoRA · diffusion-LoRA · geometry).

## Still open (honest)
- A **llama.cpp `finetune`** backend for the LLM trainer (alongside peft) when the binary is present.
- Conditioning the diffusion LoRA on captions/style tags (today's DDPM is unconditional).
