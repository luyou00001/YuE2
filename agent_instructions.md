# V100 探測結果和下一步

完整步驟在這份文件裡，下面就是可以直接在 V100 上執行的全部內容。

這份記錄裡的 TypeError 不用改代碼。它是探測腳本用了 PyTorch 2.0.0 沒有的參數 `including_emulation`，程式在印出有用結果之後才停下來。

已經確認的是：這張卡計算能力 `(7, 0)`，就是 V100；`is_bf16_supported()` 在這個舊環境裡返回 `True`，所以推理程式那道檢查目前不會因為這個函數直接退出。權重也已經在伺服器上：

- `/cache/yue2_files/YuE2-3B`
- `/cache/yue2_files/YuE2-Vae`
- `/cache/yue2_files/YuE2-Vae-legacy`

目前的 shell 是 `(PyTorch-2.0.0)`。YuE2 固定要 `torch==2.10.0` 和 Python 3.12，這個 conda 環境不能用來裝包或出歌。

在伺服器上先退出 conda，看驅動和顯存，再建一個新環境：

```bash
conda deactivate
nvidia-smi
python3.12 -m venv ~/venvs/yue2
source ~/venvs/yue2/bin/activate
python -m pip install --upgrade pip
python -m pip install torch==2.10.0 --index-url https://download.pytorch.org/whl/cu128
```

然後只做一次 BF16 矩陣乘法，確認這張 V100 能被這個輪子用：

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

`bf16` 的第二個值在 V100 上會是 `False`，這表示沒有原生 BF16。只要矩陣乘法印出 `torch.bfloat16` 和一個有限數字，就可以繼續。如果 `arch` 裡沒有 `sm_70`，或這一步報 CUDA 內核不匹配，把 torch 換成 CUDA 12.6 輪子再跑同一段：

```bash
python -m pip install torch==2.10.0 --index-url https://download.pytorch.org/whl/cu126
```

矩陣乘法通過之後，在 `/home/ma-user/work/YuE2` 安裝專案，並指到已經放好的權重：

```bash
cd /home/ma-user/work/YuE2
python -m pip install .
yue2 doctor --model /cache/yue2_files/YuE2-3B --vae /cache/yue2_files/YuE2-Vae --offline --device cuda
```

`doctor` 裡的依賴都有版本號之後，再生成第一首歌。用 eager 路徑，避開 CUDA graph、vLLM 和 FP8。顯存如果是 16 GB，把 `--budget` 改成 `16`：

```bash
yue2 generate --request examples/song.json \
  --model /cache/yue2_files/YuE2-3B \
  --vae /cache/yue2_files/YuE2-Vae \
  --offline --device cuda --backend torch-eager --low-vram --budget 30 \
  --output outputs/first-song
```

成功的話，聽 `outputs/first-song/audio.flac`。這一步仍然是 BF16 在 V100 上的模擬計算，只用來確認整條推理能走完。把 `doctor` 的輸出和生成時的報錯或耗時貼回來，再決定要不要改成 FP16。

本次沒有更新任何文件。
