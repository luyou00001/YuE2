"""Encode a small batch of mixed 180w clips with the YuE2 VAE.

Skips very short lyrics. Saves a latent, a wav, and an mp3 for listening.
Does not print lyric text or object keys.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

from fetch_one_vae_latent import CFG, SR, fetch, load_stereo


def iter_records():
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
                yield str(raw.get("k", "")), inner


def lookup_vocals(song_ids):
    wanted = set()
    for song_id in song_ids:
        wanted.add(song_id)
        wanted.add(song_id.removeprefix("huawei_music-"))
    found = {}
    with (CFG / "vocal_wav_all.txt").open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or " " not in line:
                continue
            key, value = line.split(" ", 1)
            bare = key.removeprefix("huawei_music-")
            if key in wanted or bare in wanted:
                found[key] = value.strip()
                found[bare] = value.strip()
            if len(found) >= len(wanted) * 2:
                break
    return found


def write_mp3(wav_path, mp3_path):
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg is None:
        return False
    completed = subprocess.run(
        [ffmpeg, "-y", "-i", str(wav_path), "-codec:a", "libmp3lame", "-q:a", "2", str(mp3_path)],
        stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=False)
    if completed.returncode != 0 or not mp3_path.is_file():
        mp3_path.unlink(missing_ok=True)
        return False
    return True


def mix_clip(vocal_uri, acc_uri, seconds):
    vocal = load_stereo(fetch(vocal_uri))
    acc = load_stereo(fetch(acc_uri))
    frames = min(vocal.shape[-1], acc.shape[-1], int(seconds * SR))
    if frames < 1920:
        raise RuntimeError(f"crop too short: {frames}")
    mix = vocal[:, :frames] + acc[:, :frames]
    peak = mix.abs().max().clamp_min(1e-6)
    return (mix / peak * 0.9).unsqueeze(0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vae", type=Path, default=Path("/cache/yue2_files/YuE2-Vae"))
    parser.add_argument("--output", type=Path, default=Path("/cache/yue2_outputs/vae_batch"))
    parser.add_argument("--count", type=int, default=8)
    parser.add_argument("--seconds", type=float, default=10.0)
    parser.add_argument("--min-lyric-chars", type=int, default=1)
    parser.add_argument("--max-scan", type=int, default=20000)
    args = parser.parse_args()
    chosen = []
    scanned = 0
    for song_id, record in iter_records():
        scanned += 1
        lyric = str(record.get("lyric") or "")
        if len(lyric) < args.min_lyric_chars or not record.get("mix_path"):
            if scanned >= args.max_scan:
                break
            continue
        chosen.append((song_id, record.get("mix_path"), lyric))
        if len(chosen) >= args.count or scanned >= args.max_scan:
            break
    if not chosen:
        raise SystemExit(f"no records with lyric_chars>={args.min_lyric_chars} in the first {scanned}")
    vocals = lookup_vocals([item[0] for item in chosen])
    from yue2.modeling_vae import YuE2VAE
    vae = YuE2VAE.from_pretrained(args.vae, decoder_only=False, device="cuda")
    args.output.mkdir(parents=True, exist_ok=True)
    saved = 0
    for index, (song_id, acc_uri, lyric) in enumerate(chosen):
        vocal_uri = vocals.get(song_id) or vocals.get(song_id.removeprefix("huawei_music-"))
        folder = args.output / f"{index:03d}"
        if not vocal_uri:
            print(f"{index:03d} skipped no_vocal lyric_chars={len(lyric)}")
            continue
        try:
            mix = mix_clip(vocal_uri, acc_uri, args.seconds)
            latent = vae.encode(mix).detach().float().cpu()
            wave = vae.decode(latent.to("cuda"))[0].float().cpu().clamp(-1, 1).T.numpy()
            folder.mkdir(parents=True, exist_ok=True)
            np.save(folder / "latent.npy", latent.numpy())
            sf.write(folder / "mix.wav", wave, SR)
            has_mp3 = write_mp3(folder / "mix.wav", folder / "mix.mp3")
            (folder / "lyric.txt").write_text(lyric, encoding="utf-8")
            print(f"{index:03d} latent={tuple(latent.shape)} lyric_chars={len(lyric)} mp3={has_mp3}")
            saved += 1
        except Exception as exc:
            print(f"{index:03d} failed {type(exc).__name__}")
    print(f"saved={saved} scanned={scanned} output={args.output}")


if __name__ == "__main__":
    main()
