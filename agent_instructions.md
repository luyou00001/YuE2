# V100 上的小步前向已經成功

`public/probe_existing_env.py` 的結果是 `forward_ok (1, 2, 184704) torch.bfloat16 True`。

這表示在現有的 `PyTorch-2.0.0` 環境裡，Python 3.9.11 和 `torch 2.3.1+cu121` 已經能把 YuE2-3B 載入這張 31.7 GiB 的 V100，並用 BF16 算出有限的 logits。詞表寬度 184704 和模型一致。`torch_dtype is deprecated` 仍然只是警告。不要在這個環境執行 `pip install .` 或 `pip install torch`。

下一步用同一環境生成第一首歌。使用 eager 路徑，避開 CUDA graph。權重用已經放好的本地目錄：

```bash
conda activate PyTorch-2.0.0
cd /home/ma-user/work/YuE2
CUDA_VISIBLE_DEVICES=0 PYTHONPATH=src python -m yue2.cli generate \
  --request examples/song.json \
  --model /cache/yue2_files/YuE2-3B \
  --vae /cache/yue2_files/YuE2-Vae \
  --offline --device cuda --backend torch-eager --budget 30 \
  --output outputs/first-song
```

V100 沒有原生 BF16，矩陣運算會用 FP32 模擬，整首歌會比 A100 慢很多。開始後如果幾分鐘內就報錯，把完整輸出貼回來。如果它一直在印進度，就讓它跑完，最後聽 `outputs/first-song/audio.flac`。若一開始就說缺少 `tiktoken` 或 `soundfile`，先停下來，不要升級 torch。

本次沒有更新任何文件。
