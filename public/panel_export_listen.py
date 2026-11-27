"""Write the two listening paths and their sizes. Does not print lyrics."""
from __future__ import annotations

from pathlib import Path

PREP = Path("/cache/yue2_outputs/suno_prep/000")
FREE = Path("/cache/yue2_outputs/suno_free/suno_013117_free/audio.mp3")


def describe(label, path):
    if not path.is_file():
        print(f"{label} missing {path}")
        return
    print(f"{label} bytes={path.stat().st_size} path={path}")


def main():
    pointer = PREP / "audio.path"
    original = Path(pointer.read_text(encoding="utf-8").strip()) if pointer.is_file() else pointer
    describe("original", original)
    describe("generated", FREE)
    print("compare melody and sections only")


if __name__ == "__main__":
    main()
