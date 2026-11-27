"""Pack one audio, lyric file, and ABC score into a YuE2 prefix.

Does not load the 3B model, does not transcribe, and does not print lyrics.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from yue2.protocol import make_request, token_prefixes
from yue2.tokenization_yue2 import YuE2TextTokenizer


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", type=Path, required=True)
    parser.add_argument("--lyrics-file", type=Path, required=True)
    parser.add_argument("--score", type=Path, required=True)
    parser.add_argument("--style")
    parser.add_argument("--style-file", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", type=Path, default=Path("/cache/yue2_files/YuE2-3B"))
    parser.add_argument("--id", default="song")
    args = parser.parse_args()
    for path in (args.audio, args.lyrics_file, args.score, args.model / "qwen.tiktoken"):
        if not path.is_file():
            raise SystemExit(f"missing {path}")
    lyrics = args.lyrics_file.read_text(encoding="utf-8")
    abc = args.score.read_text(encoding="utf-8")
    style = args.style_file.read_text(encoding="utf-8") if args.style_file else (args.style or "")
    style = style.strip()
    if not lyrics.strip() or not abc.strip() or not style:
        raise SystemExit("style, lyrics, and score must be nonempty")
    info = sf.info(args.audio)
    request = make_request(style=style, lyrics=lyrics, cot="full", abc=abc, id=args.id)
    tokenizer = YuE2TextTokenizer.from_pretrained(args.model)
    prefix = token_prefixes(request, tokenizer)
    args.output.mkdir(parents=True, exist_ok=True)
    np.save(args.output / "prefix.npy", np.asarray(prefix, dtype=np.int32))
    (args.output / "score.abc").write_text(abc, encoding="utf-8")
    (args.output / "lyric.txt").write_text(lyrics, encoding="utf-8")
    meta = {
        "id": args.id,
        "audio_sec": info.frames / info.samplerate,
        "lyric_chars": len(lyrics),
        "abc_chars": len(abc),
        "prefix_len": len(prefix),
        "style_chars": len(style),
    }
    (args.output / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"audio_sec={meta['audio_sec']:.2f} lyric_chars={meta['lyric_chars']} "
        f"abc_chars={meta['abc_chars']} prefix_len={meta['prefix_len']} saved={args.output}"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        raise
