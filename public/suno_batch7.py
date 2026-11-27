"""Transcribe the next 7 prepared Suno songs and pack their prefixes.

Skips a song that already has score.abc or prefix.npy. Does not print lyrics.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

PREP = Path("/cache/yue2_outputs/suno_prep")
PACKED = Path("/cache/yue2_outputs/suno_packed")


def run(args):
    print("stage", Path(args[1]).name, flush=True)
    completed = subprocess.run(args, check=False)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main():
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    run([sys.executable, "public/suno_prepare.py", "--write", "8"])
    done = 0
    for index in range(1, 8):
        folder = PREP / f"{index:03d}"
        audio_path = folder / "audio.path"
        meta_path = folder / "meta.json"
        if not audio_path.is_file() or not meta_path.is_file():
            raise SystemExit(f"missing prepared song {index:03d}")
        audio = audio_path.read_text(encoding="utf-8").strip()
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        score = folder / "score" / "score.abc"
        if not score.is_file():
            run([sys.executable, "public/transcribe_one.py", "--audio", audio, "--output", str(folder / "score")])
        packed = PACKED / f"{index:03d}"
        if not (packed / "prefix.npy").is_file():
            run([
                sys.executable, "public/pack_suno_one.py",
                "--audio", audio,
                "--lyrics-file", str(folder / "lyric.txt"),
                "--score", str(score),
                "--style-file", str(folder / "style.txt"),
                "--id", meta["id"],
                "--output", str(packed),
            ])
        print(f"ready={index:03d} id={meta['id']}", flush=True)
        done += 1
    print(f"batch7_done={done}")


if __name__ == "__main__":
    main()
