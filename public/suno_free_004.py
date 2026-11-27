"""Generate Suno song 004 from its lyrics and style, without the ABC score."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PREP = Path("/cache/yue2_outputs/suno_prep/004")
OUTPUT = Path("/cache/yue2_outputs/suno_free")


def main():
    style_path = PREP / "style.txt"
    lyrics_path = PREP / "lyric.txt"
    if not style_path.is_file() or not lyrics_path.is_file():
        raise SystemExit("missing prepared style or lyrics for 004")
    style = style_path.read_text(encoding="utf-8").strip()
    if not style:
        raise SystemExit("style is empty")
    print("free004_start id=suno_cn_011286", flush=True)
    completed = subprocess.run(
        [
            sys.executable, "-m", "yue2.cli", "generate",
            "--model", "/cache/yue2_files/YuE2-3B",
            "--vae", "/cache/yue2_files/YuE2-Vae",
            "--backend", "torch-eager",
            "--budget", "30",
            "--offline",
            "--cot", "full",
            "--seed", "831001",
            "--id", "suno_004_free",
            "--lyrics-file", str(lyrics_path),
            "--style", style,
            "--output", str(OUTPUT),
        ],
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)
    print("free004_done", flush=True)


if __name__ == "__main__":
    main()
