"""Transcribe one local clip with the uploaded SheetSage2 and MERT snapshots."""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

AUDIO = Path("/cache/yue2_outputs/vae_batch/000/mix.wav")
OUTPUT = Path("/cache/yue2_outputs/vae_batch/000/score")
SHEET = "/cache/yue2_files/SheetSage2"
MERT = "/cache/yue2_files/MERT-v2-FullSong"


def main():
    import torch
    from transformers import AutoModel

    if not AUDIO.is_file():
        raise SystemExit(f"missing audio {AUDIO}")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    torch.set_num_threads(4)
    model = AutoModel.from_pretrained(
        SHEET,
        trust_remote_code=True,
        local_files_only=True,
        base_model_path=MERT,
    ).eval().cuda()
    result = model.transcribe(str(AUDIO), output_dir=str(OUTPUT), dtype="fp32")
    score = OUTPUT / "score.abc"
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
