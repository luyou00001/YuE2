"""Measure ABC loss for packed songs 000-007. Loads the model once.

Does not update weights and does not print lyrics or score text.
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

PACKED = Path("/cache/yue2_outputs/suno_packed")
SUMMARY = Path("/cache/yue2_outputs/suno_loss8/summary.txt")
MODEL = Path("/cache/yue2_files/YuE2-3B")


def main():
    if not torch.cuda.is_available():
        raise SystemExit("CUDA is not available")
    from yue2.modeling_yue2 import YuE2ForCausalLM
    model = YuE2ForCausalLM.from_pretrained(
        MODEL, torch_dtype=torch.bfloat16, low_cpu_mem_usage=True).cuda().eval()
    losses = []
    lines = []
    for index in range(8):
        folder = PACKED / f"{index:03d}"
        prefix_path = folder / "prefix.npy"
        if not prefix_path.is_file():
            raise SystemExit(f"missing {prefix_path}")
        prefix = np.load(prefix_path, allow_pickle=False).astype(np.int64).tolist()
        labels = abc_labels(prefix)
        supervised = sum(label != -100 for label in labels[1:])
        input_ids = torch.tensor([prefix], device="cuda")
        label_ids = torch.tensor([labels], device="cuda")
        with torch.no_grad():
            loss = model(input_ids, labels=label_ids, use_cache=False).loss
        value = float(loss.detach().float())
        del input_ids, label_ids, loss
        line = f"{index:03d} abc_loss={value:.4f} tokens={len(prefix)} supervised_abc={supervised}"
        print(line, flush=True)
        lines.append(line)
        losses.append(value)
    mean = sum(losses) / len(losses)
    print(f"abc_loss8_done=8 mean={mean:.4f}", flush=True)
    print("no weights were updated or saved", flush=True)
    SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    SUMMARY.write_text("\n".join(lines + [f"mean={mean:.4f}", "abc_loss8_done=8"]) + "\n", encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except torch.cuda.OutOfMemoryError:
        print("out of memory on an ABC sequence", file=sys.stderr)
        raise SystemExit(1)
