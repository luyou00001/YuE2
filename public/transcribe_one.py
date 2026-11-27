"""Transcribe one local clip with the uploaded SheetSage2 and MERT snapshots."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

SHEET = "/cache/yue2_files/SheetSage2"
MERT = "/cache/yue2_files/MERT-v2-FullSong"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", type=Path, default=Path("/cache/yue2_outputs/vae_batch/000/mix.wav"))
    parser.add_argument("--output", type=Path, default=Path("/cache/yue2_outputs/vae_batch/000/score"))
    args = parser.parse_args()
    import torch
    from transformers import AutoModel

    if not args.audio.is_file():
        raise SystemExit(f"missing audio {args.audio}")
    args.output.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(4)
    model = AutoModel.from_pretrained(
        SHEET,
        trust_remote_code=True,
        local_files_only=True,
        base_model_path=MERT,
    ).eval().cuda()
    result = model.transcribe(str(args.audio), output_dir=str(args.output), dtype="fp32")
    score = args.output / "score.abc"
    print("score_exists", score.is_file())
    if score.is_file():
        text = score.read_text(encoding="utf-8")
        print("score_chars", len(text))
        print(text[:1200])
    print("abc_error", result.get("abc_error"))
    print("warnings", result.get("warnings"))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        raise
