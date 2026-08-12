# SPDX-License-Identifier: GPL-2.0-or-later
"""Delegated LLM-LoRA training — the weight-adapter modality, done for real.

Training an *LLM* LoRA (adapting real transformer weights) needs torch/transformers/
peft, which Blender's bundled Python doesn't have — the same wall the signer hit. So,
like the signer, this delegates to a separate **trainer process** over a tiny JSON
line protocol:

    capabilities : {"op":"capabilities"}      → {"ok":true,"backends":[...],"torch":...}
    train        : {"op":"train","dataset":[{"prompt":..,"completion":..}, ...],
                    "rank":8,"steps":60,"lr":5e-3,"output_dir":..}
                                              → {"ok":true,"adapter_path":..,
                                                 "adapter_digest":"sha256:..",
                                                 "initial_loss":..,"final_loss":..,
                                                 "trainable_params":..,"total_params":..}

A reference trainer that actually trains a peft LoRA ships at
``scripts/trainers/llm_lora_trainer.py``. Point Splendor at any trainer via
``SPLENDOR_LORA_TRAINER`` (a command); otherwise the bundled reference trainer runs
under ``python3``. If the process/deps are missing, callers get TrainerUnavailable —
honest, never a fabricated adapter.
"""
from __future__ import annotations

import json
import os
import shlex
import subprocess


class TrainerUnavailable(Exception):
    """No LLM-LoRA trainer is reachable, or the trainer process failed — honest,
    never a faked adapter."""


def _repo_root() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.abspath(os.path.join(here, os.pardir, os.pardir, os.pardir, os.pardir))


def default_trainer_script(kind: str = "llm") -> str:
    name = {"llm": "llm_lora_trainer.py", "diffusion": "diffusion_lora_trainer.py"}.get(kind)
    if name is None:
        raise ValueError(f"unknown trainer kind: {kind!r}")
    return os.path.join(_repo_root(), "scripts", "trainers", name)


class SubprocessTrainer:
    """An LLM-LoRA trainer invoked as a subprocess, one JSON intent per call."""

    def __init__(self, command, timeout: float = 1800.0, env: dict | None = None):
        self.command = list(command)
        self.timeout = timeout
        self._env = dict(os.environ)
        if env:
            self._env.update(env)

    def _invoke(self, payload: dict) -> dict:
        try:
            proc = subprocess.run(
                self.command, input=json.dumps(payload), capture_output=True,
                text=True, timeout=self.timeout, env=self._env,
            )
        except FileNotFoundError as exc:
            raise TrainerUnavailable(f"trainer command not found: {self.command!r} ({exc})") from exc
        except subprocess.TimeoutExpired as exc:
            raise TrainerUnavailable(f"trainer timed out after {self.timeout}s") from exc
        if proc.returncode != 0 and not proc.stdout.strip():
            raise TrainerUnavailable(
                f"trainer exited {proc.returncode}: {proc.stderr.strip()[:300] or '(no output)'}")
        try:
            result = json.loads(proc.stdout.strip().splitlines()[-1])
        except (ValueError, IndexError) as exc:
            raise TrainerUnavailable(
                f"trainer produced no JSON result: {proc.stdout.strip()[:200]!r} "
                f"stderr={proc.stderr.strip()[:200]!r}") from exc
        if not result.get("ok"):
            raise TrainerUnavailable(f"trainer error: {result.get('error', result)}")
        return result

    def capabilities(self) -> dict:
        return self._invoke({"op": "capabilities"})

    def train(self, dataset, rank: int = 8, steps: int = 60, lr: float = 5e-3,
              output_dir: str = "", base: str = "", seed: int = 0) -> dict:
        return self._invoke({
            "op": "train", "dataset": list(dataset), "rank": rank, "steps": steps,
            "lr": lr, "output_dir": output_dir, "base": base, "seed": seed,
        })

    def train_diffusion(self, images, rank: int = 8, steps: int = 120, lr: float = 5e-3,
                        output_dir: str = "", seed: int = 0) -> dict:
        return self._invoke({
            "op": "train", "images": [list(im) for im in images], "rank": rank,
            "steps": steps, "lr": lr, "output_dir": output_dir, "seed": seed,
        })


_TRAINER_ENV = {"llm": "SPLENDOR_LORA_TRAINER", "diffusion": "SPLENDOR_DIFFUSION_TRAINER"}


def resolve_trainer(env: dict | None = None, kind: str = "llm"):
    """Return a configured trainer for `kind` ('llm' or 'diffusion'), or None.

    The per-kind env command wins (``SPLENDOR_LORA_TRAINER`` /
    ``SPLENDOR_DIFFUSION_TRAINER``); otherwise the bundled reference trainer under
    ``python3`` (which reports honestly if torch/peft are missing). None only when
    neither exists.
    """
    env = env if env is not None else os.environ
    command = env.get(_TRAINER_ENV.get(kind, ""), "").strip()
    if command:
        return SubprocessTrainer(shlex.split(command))
    script = default_trainer_script(kind)
    if os.path.exists(script):
        python = env.get("SPLENDOR_TRAINER_PYTHON", "python3")
        return SubprocessTrainer([python, script])
    return None
