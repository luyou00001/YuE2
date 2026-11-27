"""Match the 100 Suno songs to local audio and write one lyric/style pair.

Does not print lyrics or style text, and does not load a model.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import soundfile as sf

ROOT = Path("/cache/yue2_files/datasets/suno_100")
IDS = Path("public/suno_100/selected_song_ids.txt")
TAGS = {
    "intro": "Intro",
    "verse": "Verse",
    "pre chorus": "Pre-Chorus",
    "chorus": "Chorus",
    "bridge": "Bridge",
    "outro": "Outro",
    "interlude": "Interlude",
    "instrumental": "Instrumental",
    "hook": "Chorus",
    "refrain": "Chorus",
}


def section_tag(name):
    folded = name.lower()
    folded = re.sub(r"\([^)]*\)", " ", folded)
    folded = re.sub(r"[0-9]+", " ", folded)
    folded = folded.replace("_", " ").replace("-", " ")
    folded = " ".join(folded.split())
    return TAGS.get(folded, "Verse")


def lyrics_from_sections(sections):
    blocks = []
    for section in sections:
        tag = section_tag(str(section.get("section") or "Verse"))
        text = str(section.get("text") or "").strip()
        blocks.append(f"[{tag}]\n{text}" if text else f"[{tag}]")
    lyrics = "\n\n".join(blocks).strip()
    if not lyrics:
        raise ValueError("song has no lyric sections")
    return lyrics + "\n"


def style_text(value):
    style = str(value or "").strip()
    if not style:
        raise ValueError("song has no style")
    lowered = style.lower()
    if "mandarin" not in lowered and "chinese" not in lowered:
        style = "Mandarin, " + style
    return style


def jsonl_path(root, explicit):
    if explicit is not None:
        return explicit
    for candidate in (
        root / "train_cn.jsonl",
        root / "train_cn_partial.jsonl",
        Path("public/suno_100/train_cn.jsonl"),
        Path("public/suno_100/train_cn_partial.jsonl"),
    ):
        if candidate.is_file():
            return candidate
    raise SystemExit(f"no train_cn jsonl under {root} or public/suno_100")


def load_rows(path, wanted):
    chosen = {}
    rows = 0
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            rows += 1
            row = json.loads(line)
            song_id = str(row.get("song_id") or "")
            if song_id not in wanted:
                continue
            track = int(row.get("track_index", 0))
            current = chosen.get(song_id)
            if current is None or track < int(current.get("track_index", 99)):
                chosen[song_id] = row
    return rows, chosen


def index_mixes(root):
    found = {}
    if not root.is_dir():
        return found
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".mp3", ".wav", ".flac"}:
            continue
        parts = set(path.parts)
        if "suno_vocal" in parts or "suno_bgm" in parts:
            continue
        rank = 0 if "suno_wav" in parts else 1
        current = found.get(path.stem)
        if current is None or rank < current[0]:
            found[path.stem] = (rank, path)
    return {stem: path for stem, (rank, path) in found.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--ids", type=Path, default=IDS)
    parser.add_argument("--jsonl", type=Path)
    parser.add_argument("--write", type=int, default=1)
    parser.add_argument("--output", type=Path, default=Path("/cache/yue2_outputs/suno_prep"))
    args = parser.parse_args()
    ids = [line.strip() for line in args.ids.read_text(encoding="utf-8").splitlines() if line.strip()]
    source = jsonl_path(args.root, args.jsonl)
    row_count, chosen = load_rows(source, set(ids))
    mixes = index_mixes(args.root)
    missing_meta = []
    missing_audio = []
    ready = []
    for song_id in ids:
        row = chosen.get(song_id)
        if row is None:
            missing_meta.append(song_id)
            continue
        track = int(row.get("track_index", 0))
        audio = mixes.get(f"{song_id}_{track}")
        if audio is None:
            missing_audio.append(song_id)
            continue
        ready.append((song_id, track, audio, row))
    print(
        f"jsonl={source} jsonl_rows={row_count} selected={len(ids)} "
        f"matched={len(ready)} missing_meta={len(missing_meta)} missing_audio={len(missing_audio)} "
        f"mix_files={len(mixes)}"
    )
    if missing_audio[:5]:
        print("missing_audio_ids=" + ",".join(missing_audio[:5]))
    if missing_meta[:5]:
        print("missing_meta_ids=" + ",".join(missing_meta[:5]))
    args.output.mkdir(parents=True, exist_ok=True)
    for index, (song_id, track, audio, row) in enumerate(ready[:max(args.write, 0)]):
        folder = args.output / f"{index:03d}"
        folder.mkdir(parents=True, exist_ok=True)
        lyrics = lyrics_from_sections(row.get("sections") or [])
        style = style_text(row.get("style"))
        info = sf.info(audio)
        (folder / "lyric.txt").write_text(lyrics, encoding="utf-8")
        (folder / "style.txt").write_text(style, encoding="utf-8")
        (folder / "audio.path").write_text(str(audio), encoding="utf-8")
        meta = {
            "id": song_id,
            "track": track,
            "audio_sec": info.frames / info.samplerate,
            "lyric_chars": len(lyrics),
            "style_chars": len(style),
            "sections": len(row.get("sections") or []),
        }
        (folder / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        print(
            f"wrote={index:03d} id={song_id} track={track} audio_sec={meta['audio_sec']:.2f} "
            f"lyric_chars={meta['lyric_chars']} style_chars={meta['style_chars']} sections={meta['sections']}"
        )
    if not ready:
        raise SystemExit("no selected song has both metadata and a mix file")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        raise
