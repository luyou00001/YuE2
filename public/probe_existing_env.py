"""Load YuE2 on the already installed torch and print the first real error.

Does not install or upgrade packages. Run with the existing interpreter:

    CUDA_VISIBLE_DEVICES=0 python public/probe_existing_env.py
"""
from __future__ import annotations

import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
MODEL = Path("/cache/yue2_files/YuE2-3B")


def report(name):
    try:
        module = __import__(name)
    except Exception as exc:
        print(f"{name}: MISSING {type(exc).__name__}: {exc}")
        return False
    print(f"{name}: {getattr(module, '__version__', 'present')}")
    return True


def main():
    print("python:", sys.version.replace("\n", " "))
    import torch
    print("torch:", torch.__version__, "cuda:", torch.version.cuda, "available:", torch.cuda.is_available())
    if not torch.cuda.is_available():
        raise SystemExit("CUDA is not available in this environment")
    print("gpu:", torch.cuda.get_device_name(0), torch.cuda.get_device_capability(0))
    print("mem_gib:", round(torch.cuda.get_device_properties(0).total_memory / 2**30, 1))
    ready = all(report(name) for name in ("transformers", "safetensors", "numpy"))
    if not ready:
        raise SystemExit("missing import above; do not pip install torch or pip install .")
    if not (MODEL / "model.safetensors").is_file():
        raise SystemExit(f"weights not found: {MODEL}")
    print("loading", MODEL)
    from yue2.modeling_yue2 import YuE2ForCausalLM
    model = YuE2ForCausalLM.from_pretrained(MODEL, torch_dtype=torch.bfloat16, low_cpu_mem_usage=True)
    model.eval().to("cuda")
    ids = torch.tensor([[1, 2]], device="cuda")
    with torch.inference_mode():
        logits = model(ids).logits
    print("forward_ok", tuple(logits.shape), logits.dtype, bool(torch.isfinite(logits).all()))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        raise SystemExit(1)
