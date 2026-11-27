"""Transcribe, pack, and score one prepared Suno song. Does not update weights."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PREP = Path("/cache/yue2_outputs/suno_prep/000")
PACKED = Path("/cache/yue2_outputs/suno_packed/000")


def run(args):
    print("stage", args[1], flush=True)
    completed = subprocess.run(args, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main():
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    audio_path = PREP / "audio.path"
    meta_path = PREP / "meta.json"
    if not audio_path.is_file() or not meta_path.is_file():
        raise SystemExit("run public/suno_prepare.py first")
    audio = audio_path.read_text(encoding="utf-8").strip()
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    score = PREP / "score" / "score.abc"
    python = sys.executable
    if not score.is_file():
        run([python, "public/transcribe_one.py", "--audio", audio, "--output", str(PREP / "score")])
    if not (PACKED / "prefix.npy").is_file():
        run([
            python, "public/pack_suno_one.py",
            "--audio", audio,
            "--lyrics-file", str(PREP / "lyric.txt"),
            "--score", str(score),
            "--style-file", str(PREP / "style.txt"),
            "--id", meta["id"],
            "--output", str(PACKED),
        ])
    run([python, "public/train_abc_loss.py", "--packed", str(PACKED)])


if __name__ == "__main__":
    main()
