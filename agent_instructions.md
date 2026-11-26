# 用 NAR 的 mox 抓一首，再抽 YuE2 VAE latent

不再檢查 `moxing` 能不能用。讀檔沿 NAR 的 `mox.file.copy`，把 `s3://` 抓到 `/cache/yue2_files/datasets/audio_cache/`。第一條記錄的伴奏取 `mix_path`，人聲用同一個 `k` 去 `vocal_wav_all.txt` 找。兩條對齊後相加，只取前 10 秒，用 `/cache/yue2_files/YuE2-Vae` 編成 latent。不使用 MuCodec，也不印歌詞和對象路徑。

```bash
CUDA_VISIBLE_DEVICES=0 PYTHONPATH=src python public/fetch_one_vae_latent.py
```

成功時會印 `latent_shape` 為 `(1, 64, T)`，以及 `finite=True`。文件在 `/cache/yue2_outputs/vae_one/latent.npy`。這只證明聲學目標可以從這 180 萬條裡抽出來。樂譜、風格句子和 32768 類語義 token 仍要後面逐項補。

本次更新的文件：`public/fetch_one_vae_latent.py`
