"""Mix one full vocal and accompaniment recording. Does not run the VAE.

Does not print lyrics or object keys. --seconds 0 keeps the whole overlap.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

import soundfile as sf

from fetch_one_vae_latent import SR, fetch, first_record, load_stereo, lookup_vocal


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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=0.0)
    parser.add_argument("--output", type=Path, default=Path("/cache/yue2_outputs/full_mix/000"))
    args = parser.parse_args()
    song_id, record = first_record()
    vocal_uri = lookup_vocal(song_id)
    acc_uri = record.get("mix_path")
    if not vocal_uri or not acc_uri:
        raise SystemExit("first record has no vocal path or mix_path")
    vocal = load_stereo(fetch(vocal_uri))
    acc = load_stereo(fetch(acc_uri))
    frames = min(vocal.shape[-1], acc.shape[-1])
    if args.seconds > 0:
        frames = min(frames, int(args.seconds * SR))
    if frames < SR:
        raise SystemExit(f"mix too short: {frames} samples")
    mix = vocal[:, :frames] + acc[:, :frames]
    peak = mix.abs().max().clamp_min(1e-6)
    wave = (mix / peak * 0.9).T.contiguous().numpy()
    args.output.mkdir(parents=True, exist_ok=True)
    wav_path = args.output / "mix.wav"
    sf.write(wav_path, wave, SR)
    has_mp3 = write_mp3(wav_path, args.output / "mix.mp3")
    print(f"duration_sec={frames / SR:.2f} mp3={has_mp3} saved={wav_path}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        raise
