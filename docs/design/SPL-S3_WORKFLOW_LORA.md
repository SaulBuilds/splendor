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

## Still open (honest)
- **LLM / diffusion weight LoRAs** (adapting real model weights) still report "needs a weight
  trainer (not yet wired)" — a delegated trainer (llama.cpp / peft), like the signer, is the next
  step. The Workflow LoRA is the real, self-contained one.
