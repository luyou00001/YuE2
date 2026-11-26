# 這台 V100 連得到 OBS，但看不到桶 ttsingnorth

`moxing` 已載入，OBS SDK 也發出了請求。服務回的是 `404 NoSuchBucket`：`The specified bucket does not exist`。失敗發生在第一首人聲，對象在桶 `ttsingnorth` 裡。所以不是網路完全不通，也不是索引寫錯。這台機器設定的 OBS 端點裡沒有這個桶。

`S3_ENDPOINT` 和 `OBS_ENDPOINT` 雖然有設定，它們指向的是當前這台機器的對象存儲，不是當初 NAR 訓練能讀到 `ttsingnorth` 的那一個。

可以換另一台伺服器試。選曾經用同一條 `s3://ttsingnorth/...` 成功讀過音頻的那台。那台需要有：

- 能 `import moxing` 的 Python
- 這份索引，或原來的 `acctask-180w-acc-caption-cfgs`
- YuE2 代碼和 `/cache/yue2_files/YuE2-Vae`，若 VAE 不在那台，先只做到 `mox.file.copy` 成功也行

在那台機器上仍跑：

```bash
CUDA_VISIBLE_DEVICES=0 PYTHONPATH=src python public/fetch_one_vae_latent.py
```

若那台沒有腳本裡寫死的索引路徑，先把 `public/fetch_one_vae_latent.py` 開頭的 `CFG` 改成該機器上的索引目錄。`mox.file.copy` 不再報 `NoSuchBucket` 之後，才繼續看 VAE latent。

本次沒有更新任何文件。
