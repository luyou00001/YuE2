"""Report SheetSage2 files and missing packages. Does not install anything."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SHEET = Path("/cache/yue2_files/SheetSage2")
MERT = Path("/cache/yue2_files/MERT-v2-FullSong")


def has_weights(path):
    if not path.is_dir():
        return False
    names = [item.name for item in path.iterdir()]
    return any(name.endswith(".safetensors") or name.endswith(".bin") for name in names)


def requirement_name(line):
    text = line.split("#", 1)[0].strip()
    if not text or text.startswith("-"):
        return None
    for mark in ("==", ">=", "<=", "~=", "!=", ">"):
        if mark in text:
            return text.split(mark, 1)[0].strip()
    return text


def main():
    print("python", sys.version.split()[0])
    for name in ("torch", "torchaudio", "transformers", "numpy"):
        spec = importlib.util.find_spec(name)
        if spec is None:
            print(f"{name}: MISSING")
            continue
        module = __import__(name)
        print(f"{name}: {getattr(module, '__version__', 'present')}")
    print(f"sheetsage_dir={SHEET.is_dir()} weights={has_weights(SHEET)} infer={(SHEET / 'infer.py').is_file()} requirements={(SHEET / 'requirements.txt').is_file()}")
    print(f"mert_dir={MERT.is_dir()} weights={has_weights(MERT)} config={(MERT / 'config.json').is_file()}")
    requirements = SHEET / "requirements.txt"
    if not requirements.is_file():
        raise SystemExit("missing SheetSage2 requirements.txt")
    for line in requirements.read_text(encoding="utf-8").splitlines():
        name = requirement_name(line)
        if name is None:
            continue
        module_name = name.replace("-", "_")
        spec = importlib.util.find_spec(module_name)
        if spec is None and module_name != name:
            spec = importlib.util.find_spec(name)
        print(f"requirement {line.strip()}: {'present' if spec else 'MISSING'}")


if __name__ == "__main__":
    main()
