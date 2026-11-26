"""Update only the output layer for a few steps and save a separate checkpoint.

The base YuE2-3B directory is never modified. This memorizes one saved song's
tokens; it is a trainer check, not a music-quality run.
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from train_loss_check import load_ids


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--song", type=Path, required=True)
    parser.add_argument("--model", type=Path, default=Path("/cache/yue2_files/YuE2-3B"))
    parser.add_argument("--output", type=Path, default=Path("/cache/yue2_ckpts/lmhead-city-lights"))
    parser.add_argument("--max-semantic", type=int, default=64)
    parser.add_argument("--steps", type=int, default=5)
    parser.add_argument("--lr", type=float, default=1e-5)
    args = parser.parse_args()
    source = args.model.resolve()
    destination = args.output.resolve()
    if destination == source or source in destination.parents:
        raise SystemExit(f"refusing to write inside the base checkpoint: {source}")
    if destination.exists() and any(destination.iterdir()):
        raise SystemExit(f"output is not empty: {destination}")
    if not torch.cuda.is_available():
        raise SystemExit("CUDA is not available")
    ids, labels, prefix_len = load_ids(args.song, args.max_semantic)
    print(f"tokens={len(ids)} prefix={prefix_len} supervised={sum(label != -100 for label in labels[1:])}")
    from yue2.modeling_yue2 import YuE2ForCausalLM
    model = YuE2ForCausalLM.from_pretrained(
        source, torch_dtype=torch.bfloat16, low_cpu_mem_usage=True).cuda()
    model.train()
    for parameter in model.parameters():
        parameter.requires_grad = False
    model.lm_head.weight.requires_grad = True
    optimizer = torch.optim.AdamW([model.lm_head.weight], lr=args.lr, weight_decay=0.0)
    input_ids = torch.tensor([ids], device="cuda")
    label_ids = torch.tensor([labels], device="cuda")
    for step in range(1, args.steps + 1):
        optimizer.zero_grad(set_to_none=True)
        loss = model(input_ids, labels=label_ids, use_cache=False).loss
        loss.backward()
        optimizer.step()
        print(f"step={step} ar_loss={float(loss.detach().float()):.4f}")
    destination.mkdir(parents=True)
    model.save_pretrained(destination, safe_serialization=True)
    shutil.copyfile(source / "qwen.tiktoken", destination / "qwen.tiktoken")
    print(f"saved={destination}")
    print(f"base_unchanged={source}")


if __name__ == "__main__":
    main()
