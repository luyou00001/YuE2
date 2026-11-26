"""Print field types for the first 180w record. Does not print lyrics or paths."""
import json
import sys
from pathlib import Path


def main():
    record = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8").splitlines()[0])
    inner = record.get("v", record)
    if isinstance(inner, str):
        inner = json.loads(inner)
    print("song_key_chars", len(str(record.get("k", ""))))
    if not isinstance(inner, dict):
        print("record_type", type(inner).__name__)
        return
    for key, value in inner.items():
        if not isinstance(value, str):
            print(f"{key}: {type(value).__name__}")
            continue
        if key.endswith("path"):
            path = Path(value)
            suffix = path.suffix if path.suffix else "none"
            print(f"{key}: suffix={suffix} exists={path.is_file()}")
        else:
            print(f"{key}: chars={len(value)}")


if __name__ == "__main__":
    main()
