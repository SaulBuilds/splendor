#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Reference LLM-LoRA trainer for Splendor — a real peft LoRA finetune.

Speaks the JSON line protocol of ``splendor.train.trainer.SubprocessTrainer``: one
intent on stdin, one JSON result on stdout.

    capabilities : {"op":"capabilities"} → {"ok":true,"torch":..,"peft":..,...}
    train        : {"op":"train","dataset":[{"prompt":..,"completion":..}],...}
                   → {"ok":true,"adapter_path":..,"adapter_digest":..,
                      "initial_loss":..,"final_loss":..,"trainable_params":..}

To stay fully offline (no model/tokenizer downloads) the base is a small
randomly-initialised GPT-2 with a byte-level tokenizer (vocab 256). Pass a HF id as
``base`` to adapt a real pretrained model instead (may download). The LoRA is genuine
— only the adapter matrices train (peft), the base is frozen — and a real
``adapter_model.safetensors`` is written. Any failure is reported as ``{"ok":false,
"error":..}``; the adapter is never fabricated.

Run under a Python with torch/transformers/peft (the system Python, not Blender's).
"""
import hashlib
import json
import os
import sys
import tempfile


def _fail(msg):
    print(json.dumps({"ok": False, "error": str(msg)}))
    sys.exit(0)


def _encode(text, maxlen=63):
    return list(text.encode("utf-8", "ignore")[:maxlen]) or [0]


def _capabilities():
    import torch
    import peft
    import transformers
    return {"ok": True, "backends": ["peft"], "torch": torch.__version__,
            "transformers": transformers.__version__, "peft": peft.__version__,
            "cuda": bool(torch.cuda.is_available())}


def _train(intent):
    import torch
    from peft import LoraConfig, get_peft_model
    from transformers import GPT2Config, GPT2LMHeadModel, AutoModelForCausalLM, AutoTokenizer

    dataset = intent.get("dataset") or []
    if not dataset:
        raise ValueError("empty dataset")
    rank = int(intent.get("rank", 8))
    steps = int(intent.get("steps", 60))
    lr = float(intent.get("lr", 5e-3))
    seed = int(intent.get("seed", 0))
    base = (intent.get("base") or "").strip()
    torch.manual_seed(seed)

    if base:
        tok = AutoTokenizer.from_pretrained(base)
        if tok.pad_token is None:
            tok.pad_token = tok.eos_token
        model = AutoModelForCausalLM.from_pretrained(base)
        target = ["q_proj", "v_proj"]

        def encode(text):
            return tok(text, truncation=True, max_length=64, return_tensors="pt").input_ids
    else:
        # Fully-offline tiny GPT-2 + byte tokenizer (vocab 256).
        cfg = GPT2Config(vocab_size=256, n_embd=32, n_layer=1, n_head=2, n_positions=64)
        model = GPT2LMHeadModel(cfg)
        target = ["c_attn"]

        def encode(text):
            return torch.tensor([_encode(text)])

    lcfg = LoraConfig(r=rank, lora_alpha=2 * rank, target_modules=target,
                      lora_dropout=0.0, task_type="CAUSAL_LM")
    model = get_peft_model(model, lcfg)
    model.train()
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())

    examples = [encode(f"{d.get('prompt','')} -> {d.get('completion','')}") for d in dataset]
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=lr)
    initial_loss = final_loss = None
    for step in range(steps):
        opt.zero_grad()
        total_loss = 0.0
        for ids in examples:
            out = model(ids, labels=ids)
            out.loss.backward()
            total_loss += float(out.loss.item())
        opt.step()
        avg = total_loss / len(examples)
        if step == 0:
            initial_loss = avg
        final_loss = avg

    out_dir = intent.get("output_dir") or tempfile.mkdtemp(prefix="splendor_lora_")
    os.makedirs(out_dir, exist_ok=True)
    model.save_pretrained(out_dir)
    adapter_file = os.path.join(out_dir, "adapter_model.safetensors")
    if not os.path.exists(adapter_file):  # older peft may write a .bin
        alt = os.path.join(out_dir, "adapter_model.bin")
        adapter_file = alt if os.path.exists(alt) else adapter_file
    digest = "sha256:" + hashlib.sha256(open(adapter_file, "rb").read()).hexdigest()
    return {
        "ok": True, "adapter_path": adapter_file, "adapter_digest": digest,
        "initial_loss": initial_loss, "final_loss": final_loss, "steps": steps,
        "trainable_params": trainable, "total_params": total,
        "base": base or "tiny-gpt2(byte,offline)",
    }


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
        _fail(f"trainer dependency missing ({exc}); run under a Python with torch/transformers/peft")
    except Exception as exc:  # honest: any failure is a protocol error, never a fake adapter
        _fail(f"{type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
