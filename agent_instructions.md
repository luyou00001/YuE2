# V100 推理與權重下載

現有代碼不能當作已經跑通的 V100 推理。模型在 CUDA 上固定用 BF16 載入，`pipeline.py` 會檢查 `torch.cuda.is_bf16_supported()`。V100 是計算能力 7.0，沒有 BF16 Tensor Core。PyTorch 這個檢查默認包含軟件模擬，所以在 V100 上可能返回 True，進程不一定立刻退出；真正的矩陣運算會落到 FP32 模擬，速度接近 FP32，而且和官方 BF16 路徑不是同一條。

同時被卡住的路徑：

- FP8 AR 要求計算能力至少 8.9，V100 會直接報錯。
- vLLM 後端把 `dtype` 寫成 `bfloat16`，vLLM 自己會拒絕計算能力 7.0。
- CUDA graph、FlashAttention 的官方路徑也是按 Ampere 及更新的卡來寫的。
- 文檔裡的整首歌驗收沒有 V100。最低建議仍是支援 BF16 的 NVIDIA、24 GB 顯存。

顯存：`YuE2-3B` 的 `model.safetensors` 是 7.26 GB。VAE 解碼是 FP32，權重文件約 531 MB。32 GB 的 V100 才有餘地試單卡短歌；16 GB 在權重、KV cache 和 VAE 疊在一起時很緊。`low_vram=True` 只是把暫時不用的 AR 或 NAR 專家放回 CPU，沒有把數值格式改成 FP16。

64 張 V100：當前推理是單卡、一次一首歌，沒有張量並行。64 張卡不會自動切同一個模型。要先讓一張卡出聲，之後才談多進程吞吐。

權重可以公開下載，推理不需要 MERT2 或 SheetSage2。

- 歌曲模型：https://huggingface.co/m-a-p/YuE2-3B
- 默認聽歌解碼器：https://huggingface.co/m-a-p/YuE2-Vae
- 論文表格用的解碼器：https://huggingface.co/m-a-p/YuE2-Vae-legacy

```bash
pip install -U "huggingface_hub==0.36.2"
hf download m-a-p/YuE2-3B --local-dir /data/models/YuE2-3B
hf download m-a-p/YuE2-Vae --local-dir /data/models/YuE2-Vae
```

在一張 V100 上先看硬件判斷，不要直接開整首歌：

```bash
python - << 'PY'
import torch
print("capability", torch.cuda.get_device_capability())
print("bf16_check_default", torch.cuda.is_bf16_supported())
print("bf16_native", torch.cuda.is_bf16_supported(including_emulation=False))
print("name", torch.cuda.get_device_name())
print("mem_gib", torch.cuda.get_device_properties(0).total_memory / 2**30)
PY
```

`bf16_native` 在 V100 上應為 False。權重是 CC BY-NC 4.0，公司商用需要另談授權。

本次沒有更新任何文件。
