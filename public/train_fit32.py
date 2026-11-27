"""One AdamW step per packed song on the last decoder layer.

The base YuE2-3B directory is only read. The new weights go to
/cache/yue2_ckpts/fit32-suno8.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "public"))

from train_abc_loss import abc_labels

SOURCE = Path("/cache/yue2_files/YuE2-3B")
PACKED = Path("/cache/yue2_outputs/suno_packed")
OUTPUT = Path("/cache/yue2_ckpts/fit32-suno8")


def main():
    if not torch.cuda.is_available():
        raise SystemExit("CUDA is not available")
    source = SOURCE.resolve()
    destination = OUTPUT.resolve()
    if destination == source or source in destination.parents:
        raise SystemExit(f"refusing to write inside the base checkpoint: {source}")
    if destination.exists() and any(destination.iterdir()):
        raise SystemExit(f"output is not empty: {destination}")
    from yue2.modeling_yue2 import YuE2ForCausalLM
    model = YuE2ForCausalLM.from_pretrained(
        source, torch_dtype=torch.bfloat16, low_cpu_mem_usage=True).cuda()
    for parameter in model.parameters():
        parameter.requires_grad = False
    trainable = list(model.model.layers[-1].parameters())
    for parameter in trainable:
        parameter.requires_grad = True
    count = sum(parameter.numel() for parameter in trainable)
    print(f"trainable_params={count} layer=last songs=8")
    optimizer = torch.optim.AdamW(trainable, lr=1e-5, weight_decay=0.0)
    model.train()
    torch.cuda.reset_peak_memory_stats()
    for index in range(8):
        prefix_path = PACKED / f"{index:03d}" / "prefix.npy"
        prefix = np.load(prefix_path, allow_pickle=False).astype(np.int64).tolist()
        labels = abc_labels(prefix)
        input_ids = torch.tensor([prefix], device="cuda")
        label_ids = torch.tensor([labels], device="cuda")
        optimizer.zero_grad(set_to_none=True)
        loss = model(input_ids, labels=label_ids, use_cache=False).loss
        loss.backward()
        optimizer.step()
        print(
            f"song={index:03d} tokens={len(prefix)} "
            f"abc_loss={float(loss.detach().float()):.4f}"
        )
    peak = torch.cuda.max_memory_allocated() / (1024 ** 3)
    print(f"peak_gib={peak:.2f}")
    destination.mkdir(parents=True)
    model.save_pretrained(destination, safe_serialization=True)
    token_file = source / "qwen.tiktoken"
    if token_file.is_file():
        shutil.copyfile(token_file, destination / "qwen.tiktoken")
    print(f"saved={destination}")
    print(f"base_unchanged={source}")
    print("fit32_done=8")


if __name__ == "__main__":
    try:
        main()
    except torch.cuda.OutOfMemoryError:
        print("out of memory during the last-layer update; nothing was saved", file=sys.stderr)
        raise SystemExit(1)
