# 下一步只抽一首 VAE latent

新機器上的代碼、`/cache` 權重和 datasets 已經就位。先不要訓練，也不要重跑整首歌。跑這條，確認這台伺服器看得到桶 `ttsingnorth`，並能把第一首人聲加伴奏編成 YuE2 latent：

```bash
CUDA_VISIBLE_DEVICES=0 PYTHONPATH=src python public/fetch_one_vae_latent.py
```

成功時輸出 `latent_shape=(1, 64, T)` 和 `finite=True`，文件在 `/cache/yue2_outputs/vae_one/latent.npy`。若仍是 `NoSuchBucket`，這台機器的 OBS 端點同樣沒有 `ttsingnorth`。把完整輸出貼回來。

本次沒有更新任何文件。
