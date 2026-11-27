"""Generate one Suno song from lyrics and style, without the transcribed score."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

PREP = Path("/cache/yue2_outputs/suno_prep/000")
OUTPUT = Path("/cache/yue2_outputs/suno_free")


def main():
    style_path = PREP / "style.txt"
    lyrics_path = PREP / "lyric.txt"
    if not style_path.is_file() or not lyrics_path.is_file():
        raise SystemExit("missing prepared style or lyrics")
    style = style_path.read_text(encoding="utf-8").strip()
    if not style:
        raise SystemExit("style is empty")
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
            "--id", "suno_013117_free",
            "--lyrics-file", str(lyrics_path),
            "--style", style,
            "--output", str(OUTPUT),
        ],
        check=False,
    )
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
