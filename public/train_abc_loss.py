"""Measure YuE2's ABC loss on one packed song. Does not update weights.

Labels cover the ABC tokens and the ABC end marker. Lyrics, style, and the
music-start marker stay ignored. This is not audio-token training.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from yue2.protocol import ABC_END, ABC_START, MUSIC_START


def abc_labels(prefix):
    prefix = [int(token) for token in prefix]
    if prefix.count(ABC_START) != 1 or prefix.count(ABC_END) != 1:
        raise SystemExit("prefix must contain one ABC span")
    start = prefix.index(ABC_START)
    end = prefix.index(ABC_END)
    if not start < end < len(prefix) or MUSIC_START in prefix[start:end]:
        raise SystemExit("ABC span is out of order")
    labels = [-100] * len(prefix)
    for index in range(start + 1, end + 1):
        labels[index] = prefix[index]
    return labels


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packed", type=Path, required=True)
    parser.add_argument("--model", type=Path, default=Path("/cache/yue2_files/YuE2-3B"))
    args = parser.parse_args()
    if not torch.cuda.is_available():
        raise SystemExit("CUDA is not available")
    prefix = np.load(args.packed / "prefix.npy", allow_pickle=False).astype(np.int64).tolist()
    labels = abc_labels(prefix)
    supervised = sum(label != -100 for label in labels[1:])
    print(f"tokens={len(prefix)} supervised_abc={supervised}")
    from yue2.modeling_yue2 import YuE2ForCausalLM
    model = YuE2ForCausalLM.from_pretrained(
        args.model, torch_dtype=torch.bfloat16, low_cpu_mem_usage=True).cuda().eval()
    input_ids = torch.tensor([prefix], device="cuda")
    label_ids = torch.tensor([labels], device="cuda")
    with torch.no_grad():
        loss = model(input_ids, labels=label_ids, use_cache=False).loss
    print(f"abc_loss={float(loss.detach().float()):.4f}")
    print("no weights were updated or saved")


if __name__ == "__main__":
    try:
        main()
    except torch.cuda.OutOfMemoryError:
        print("out of memory on this ABC sequence", file=sys.stderr)
        raise SystemExit(1)
