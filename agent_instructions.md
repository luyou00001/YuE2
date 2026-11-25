# 用 conda 和默認 pip 在 V100 上安裝並試推理

用 conda 新建環境，套件只用默認的 `pip install`，不要加 `--index-url`。Linux 上 `pip install torch==2.10.0` 拿到的就是 CUDA 12.8 輪子，編譯範圍包含 V100 的計算能力 7.0。權重已經在伺服器上，不用再下載。

先離開現在的 `(PyTorch-2.0.0)`，再建環境：

```bash
conda deactivate
nvidia-smi
conda create -n yue2 python=3.12 -y
conda activate yue2
cd /home/ma-user/work/YuE2
python -m pip install --upgrade pip
python -m pip install torch==2.10.0
python -m pip install .
```

安裝後先做一次 BF16 矩陣乘法。第二個 `bf16` 值在 V100 上會是 `False`，這表示沒有原生 BF16。只要最後印出 `torch.bfloat16` 和一個有限數字，就繼續。

```bash
python - << 'PY'
import torch
print(torch.__version__, torch.version.cuda)
print(torch.cuda.get_device_name(), torch.cuda.get_device_capability())
print("mem_gib", round(torch.cuda.get_device_properties(0).total_memory / 2**30, 1))
print("arch", torch.cuda.get_arch_list())
print("bf16", torch.cuda.is_bf16_supported(), torch.cuda.is_bf16_supported(including_emulation=False))
x = torch.randn(256, 256, device="cuda", dtype=torch.bfloat16)
y = x @ x
print(y.dtype, float(y.float().abs().mean()))
PY
```

矩陣乘法通過之後，檢查依賴並生成第一首歌。用 eager 路徑，避開 CUDA graph、vLLM 和 FP8。顯存如果是 16 GB，把 `--budget` 改成 `16`。

```bash
yue2 doctor --model /cache/yue2_files/YuE2-3B --vae /cache/yue2_files/YuE2-Vae --offline --device cuda
yue2 generate --request examples/song.json \
  --model /cache/yue2_files/YuE2-3B \
  --vae /cache/yue2_files/YuE2-Vae \
  --offline --device cuda --backend torch-eager --low-vram --budget 30 \
  --output outputs/first-song
```

成功的話，聽 `outputs/first-song/audio.flac`。這一步仍是 BF16 在 V100 上的模擬計算，用來確認整條推理能走完。把 `nvidia-smi`、矩陣乘法輸出、`doctor` 和生成時的報錯或耗時貼回來。

本次沒有更新任何文件。
