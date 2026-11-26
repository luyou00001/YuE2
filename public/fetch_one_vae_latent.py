"""Fetch one NAR vocal/acc pair with mox and encode a short YuE2 VAE latent.

Does not use MuCodec tokens and does not print lyrics or object keys.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

CFG = Path("/cache/yue2_files/datasets/acctask-180w-acc-caption-cfgs")
CACHE = Path("/cache/yue2_files/datasets/audio_cache")
SR = 48000


def first_record():
    lists = sorted(CFG.glob("200w*.txt"))
    if not lists:
        raise SystemExit(f"no 200w txt under {CFG}")
    raw = json.loads(lists[0].read_text(encoding="utf-8").splitlines()[0])
    inner = raw.get("v", raw)
    if isinstance(inner, str):
        inner = json.loads(inner)
    song_id = str(raw.get("k", ""))
    return song_id, inner


def lookup_vocal(song_id):
    wanted = {song_id, song_id.removeprefix("huawei_music-")}
    with (CFG / "vocal_wav_all.txt").open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            key, value = line.split(" ", 1)
            bare = key.removeprefix("huawei_music-")
            if key in wanted or bare in wanted:
                return value.strip()
    return None


def fetch(uri):
    import moxing as mox
    if not str(uri).startswith("s3://"):
        return Path(uri)
    local = CACHE / str(uri).removeprefix("s3://")
    local.parent.mkdir(parents=True, exist_ok=True)
    if not local.is_file():
        mox.file.copy(str(uri), str(local))
    return local


def load_stereo(path):
    audio, rate = sf.read(path, dtype="float32", always_2d=True)
    audio = torch.from_numpy(np.ascontiguousarray(audio.T))
    if audio.shape[0] == 1:
        audio = audio.repeat(2, 1)
    audio = audio[:2]
    if rate != SR:
        import torchaudio
        audio = torchaudio.functional.resample(audio, rate, SR)
    return audio


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vae", type=Path, default=Path("/cache/yue2_files/YuE2-Vae"))
    parser.add_argument("--seconds", type=float, default=10.0)
    parser.add_argument("--output", type=Path, default=Path("/cache/yue2_outputs/vae_one"))
    args = parser.parse_args()
    song_id, record = first_record()
    vocal_uri = lookup_vocal(song_id)
    acc_uri = record.get("mix_path")
    if not vocal_uri or not acc_uri:
        raise SystemExit("first record has no vocal path or mix_path")
    print(f"lyric_chars={len(str(record.get('lyric', '')))}")
    vocal = load_stereo(fetch(vocal_uri))
    acc = load_stereo(fetch(acc_uri))
    frames = min(vocal.shape[-1], acc.shape[-1], int(args.seconds * SR))
    if frames < 1920:
        raise SystemExit(f"crop too short: {frames} samples")
    mix = vocal[:, :frames] + acc[:, :frames]
    peak = mix.abs().max().clamp_min(1e-6)
    mix = (mix / peak * 0.9).unsqueeze(0)
    from yue2.modeling_vae import YuE2VAE
    vae = YuE2VAE.from_pretrained(args.vae, decoder_only=False, device="cuda")
    latent = vae.encode(mix).detach().float().cpu()
    args.output.mkdir(parents=True, exist_ok=True)
    np.save(args.output / "latent.npy", latent.numpy())
    print(f"latent_shape={tuple(latent.shape)} finite={bool(torch.isfinite(latent).all())}")
    print(f"saved={args.output / 'latent.npy'}")


if __name__ == "__main__":
    main()
