# 這台 V100 仍然看不到桶 ttsingnorth

這次和上一輪是同一個錯誤。`moxing` 連上了 OBS，服務回 `404 NoSuchBucket`，桶名是 `ttsingnorth`。請求 ID 換了，結果沒變。再在這台機器上重跑 `fetch_one_vae_latent.py` 不會成功。

換到曾經用 `s3://ttsingnorth/AI_Music_Data_vUltra/...` 成功讀過音頻的那台伺服器。那台需要能 `import moxing`、這份 180 萬索引，以及 YuE2 代碼。VAE 可以後補；先讓下載不再報 `NoSuchBucket`。

索引若不在 `/cache/yue2_files/datasets/acctask-180w-acc-caption-cfgs`，把 `public/fetch_one_vae_latent.py` 裡的 `CFG` 改成那台機器上的目錄，然後執行：

```bash
CUDA_VISIBLE_DEVICES=0 PYTHONPATH=src python public/fetch_one_vae_latent.py
```

本次沒有更新任何文件。
