"""One backward through the last decoder layer. Does not save or change the base.

This checks that a 32GB V100 can take a gradient on one layer for song 000.
The base directory is only read. No optimizer step runs.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "public"))

from train_abc_loss import abc_labels


def main():
    if not torch.cuda.is_available():
        raise SystemExit("CUDA is not available")
    source = Path("/cache/yue2_files/YuE2-3B")
    packed = Path("/cache/yue2_outputs/suno_packed/000/prefix.npy")
    prefix = np.load(packed, allow_pickle=False).astype(np.int64).tolist()
    labels = abc_labels(prefix)
    print(f"tokens={len(prefix)} supervised_abc={sum(label != -100 for label in labels[1:])}")
    from yue2.modeling_yue2 import YuE2ForCausalLM
    model = YuE2ForCausalLM.from_pretrained(
        source, torch_dtype=torch.bfloat16, low_cpu_mem_usage=True).cuda()
    for parameter in model.parameters():
        parameter.requires_grad = False
    trainable = list(model.model.layers[-1].parameters())
    for parameter in trainable:
        parameter.requires_grad = True
    count = sum(parameter.numel() for parameter in trainable)
    print(f"trainable_params={count} layer=last")
    model.train()
    input_ids = torch.tensor([prefix], device="cuda")
    label_ids = torch.tensor([labels], device="cuda")
    torch.cuda.reset_peak_memory_stats()
    loss = model(input_ids, labels=label_ids, use_cache=False).loss
    loss.backward()
    peak = torch.cuda.max_memory_allocated() / (1024 ** 3)
    print(f"abc_loss={float(loss.detach().float()):.4f}")
    print(f"peak_gib={peak:.2f}")
    print("no weights were updated or saved")
    print(f"base_unchanged={source}")


if __name__ == "__main__":
    try:
        main()
    except torch.cuda.OutOfMemoryError:
        print("out of memory on one last-layer backward", file=sys.stderr)
        raise SystemExit(1)
