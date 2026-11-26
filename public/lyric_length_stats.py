"""Count lyric lengths in the 180w index. Does not print lyric text."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

CFG = Path("/cache/yue2_files/datasets/acctask-180w-acc-caption-cfgs")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-scan", type=int, default=5000)
    args = parser.parse_args()
    buckets = {"0": 0, "1-7": 0, "8-19": 0, "20-49": 0, "50+": 0}
    scanned = 0
    longest = 0
    for path in sorted(CFG.glob("200w*.txt")):
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                raw = json.loads(line)
                inner = raw.get("v", raw)
                if isinstance(inner, str):
                    inner = json.loads(inner)
                lyric = str(inner.get("lyric") or "") if isinstance(inner, dict) else ""
                n = len(lyric)
                longest = max(longest, n)
                if n == 0:
                    buckets["0"] += 1
                elif n <= 7:
                    buckets["1-7"] += 1
                elif n <= 19:
                    buckets["8-19"] += 1
                elif n <= 49:
                    buckets["20-49"] += 1
                else:
                    buckets["50+"] += 1
                scanned += 1
                if scanned >= args.max_scan:
                    break
        if scanned >= args.max_scan:
            break
    print(f"scanned={scanned} longest={longest}")
    for name, count in buckets.items():
        print(f"{name}: {count}")


if __name__ == "__main__":
    main()
