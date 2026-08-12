#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Reference diffusion-LoRA trainer for Splendor — a real DDPM + peft LoRA finetune.

Speaks the JSON line protocol of ``splendor.train.trainer.SubprocessTrainer``. Trains a
*style* LoRA on the look of your renders: a small DDPM denoiser learns to predict the
noise added to your images; only the peft LoRA adapters train (the base is frozen). No
`diffusers` dependency (torch + peft only), and fully offline — the "images" are flat
pixel vectors you pass in (e.g. downsampled renders), so nothing is downloaded.

    capabilities : {"op":"capabilities"} → {"ok":true,"torch":..,"peft":..}
    train        : {"op":"train","images":[[...floats...], ...],"steps":..,"rank":..}
                   → {"ok":true,"adapter_path":..,"adapter_digest":..,
                      "initial_loss":..,"final_loss":..,"trainable_params":..}

Any failure → {"ok":false,"error":..}; the adapter is never fabricated.
"""
import hashlib
import json
import os
import sys
import tempfile


def _fail(msg):
    print(json.dumps({"ok": False, "error": str(msg)}))
    sys.exit(0)


def _capabilities():
    import torch
    import peft
    return {"ok": True, "backends": ["ddpm+peft"], "torch": torch.__version__,
            "peft": peft.__version__, "cuda": bool(torch.cuda.is_available())}


def _train(intent):
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from peft import LoraConfig, get_peft_model

    images = intent.get("images") or []
    if not images:
        raise ValueError("no images to train a style LoRA on")
    dim = len(images[0])
    if any(len(im) != dim for im in images):
        raise ValueError("all images must be the same length (flatten to a fixed size)")
    rank = int(intent.get("rank", 8))
    steps = int(intent.get("steps", 120))
    lr = float(intent.get("lr", 5e-3))
    seed = int(intent.get("seed", 0))
    torch.manual_seed(seed)
    data = torch.tensor(images, dtype=torch.float32)

    class TinyDenoiser(nn.Module):
        def __init__(self, d, h=96):
            super().__init__()
            self.inp = nn.Linear(d + 1, h)
            self.mid = nn.Linear(h, h)
            self.out = nn.Linear(h, d)

        def forward(self, x, t):
            h = torch.cat([x, t], dim=-1)
            h = F.silu(self.inp(h))
            h = F.silu(self.mid(h))
            return self.out(h)

    model = get_peft_model(
        TinyDenoiser(dim),
        LoraConfig(r=rank, lora_alpha=2 * rank, target_modules=["inp", "mid", "out"], lora_dropout=0.0))
    model.train()
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())

    steps_t = 50
    betas = torch.linspace(1e-4, 0.02, steps_t)
    acp = torch.cumprod(1.0 - betas, dim=0)
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=lr)
    initial_loss = final_loss = None
    for step in range(steps):
        opt.zero_grad()
        total_loss = 0.0
        for x0 in data:
            x0 = x0.unsqueeze(0)
            t = torch.randint(0, steps_t, (1,))
            a = acp[t].unsqueeze(-1)
            eps = torch.randn_like(x0)
            xt = a.sqrt() * x0 + (1.0 - a).sqrt() * eps
            pred = model(xt, t.float().unsqueeze(-1) / steps_t)
            loss = F.mse_loss(pred, eps)
            loss.backward()
            total_loss += float(loss.item())
        opt.step()
        avg = total_loss / len(data)
        if step == 0:
            initial_loss = avg
        final_loss = avg

    out_dir = intent.get("output_dir") or tempfile.mkdtemp(prefix="splendor_diffusion_lora_")
    os.makedirs(out_dir, exist_ok=True)
    model.save_pretrained(out_dir)
    adapter_file = os.path.join(out_dir, "adapter_model.safetensors")
    if not os.path.exists(adapter_file):
        alt = os.path.join(out_dir, "adapter_model.bin")
        adapter_file = alt if os.path.exists(alt) else adapter_file
    digest = "sha256:" + hashlib.sha256(open(adapter_file, "rb").read()).hexdigest()
    return {"ok": True, "adapter_path": adapter_file, "adapter_digest": digest,
            "initial_loss": initial_loss, "final_loss": final_loss, "steps": steps,
            "trainable_params": trainable, "total_params": total, "dim": dim, "base": "tiny-ddpm(offline)"}


def main():
    try:
        intent = json.loads(sys.stdin.read() or "{}")
    except ValueError as exc:
        _fail(f"invalid intent JSON: {exc}")
    op = intent.get("op", "train")
    try:
        if op == "capabilities":
            print(json.dumps(_capabilities()))
        elif op == "train":
            print(json.dumps(_train(intent)))
        else:
            _fail(f"unknown op: {op!r}")
    except ImportError as exc:
        _fail(f"trainer dependency missing ({exc}); run under a Python with torch/peft")
    except Exception as exc:
        _fail(f"{type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
