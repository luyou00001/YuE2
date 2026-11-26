"""Check that YuE2-3B can compute an AR loss and backward on one saved song.

This does not update or save weights. It uses the tokens already written by
inference, so it does not need the unreleased semantic tokenizer.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from yue2.protocol import CODEC_OFFSET, CODEC_SIZE, MUSIC_END


def load_ids(song, max_semantic):
    song = Path(song)
    prefix = np.load(song / "prefix.npy", allow_pickle=False).astype(np.int64).tolist()
    semantic = np.load(song / "semantic.npy", allow_pickle=False).astype(np.int64)
    if semantic.ndim != 1 or semantic.size < 1:
        raise SystemExit(f"{song} has no semantic tokens")
    if semantic.min() < 0 or semantic.max() >= CODEC_SIZE:
        raise SystemExit("semantic.npy is outside the 32768 codec range")
    semantic = semantic[:max_semantic]
    ids = prefix + [int(token) + CODEC_OFFSET for token in semantic] + [MUSIC_END]
    labels = [-100] * len(prefix) + ids[len(prefix):]
    return ids, labels, len(prefix)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--song", type=Path, required=True)
    parser.add_argument("--model", type=Path, default=Path("/cache/yue2_files/YuE2-3B"))
    parser.add_argument("--max-semantic", type=int, default=64)
    args = parser.parse_args()
    if not torch.cuda.is_available():
        raise SystemExit("CUDA is not available")
    ids, labels, prefix_len = load_ids(args.song, args.max_semantic)
    supervised = sum(label != -100 for label in labels[1:])
    print(f"tokens={len(ids)} prefix={prefix_len} supervised={supervised}")
    from yue2.modeling_yue2 import YuE2ForCausalLM
    model = YuE2ForCausalLM.from_pretrained(
        args.model, torch_dtype=torch.bfloat16, low_cpu_mem_usage=True).cuda()
    model.train()
    input_ids = torch.tensor([ids], device="cuda")
    label_ids = torch.tensor([labels], device="cuda")
    loss = model(input_ids, labels=label_ids, use_cache=False).loss
    loss.backward()
    grad = model.lm_head.weight.grad
    finite = bool(torch.isfinite(loss).item() and grad is not None and torch.isfinite(grad).all())
    print(f"ar_loss={float(loss.detach().float()):.4f} weighted_0.25={float(loss.detach().float()) * 0.25:.4f}")
    print(f"lm_head_grad_finite={finite} grad_norm={float(grad.float().norm()):.4f}")
    print("no weights were updated or saved")
    if not finite:
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()
    except torch.cuda.OutOfMemoryError:
        print("out of memory; rerun with a smaller --max-semantic", file=sys.stderr)
        raise SystemExit(1)
