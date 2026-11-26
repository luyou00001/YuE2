# 一首 10 秒 latent 已抽出；SSH 第一步超過 10 秒會重試

`latent_shape=(1, 64, 250)` 且 `finite=True`。10 秒音頻對應 250 幀，YuE2-Vae 的 25 Hz 壓縮是對的。文件在 `/cache/yue2_outputs/vae_one/latent.npy`。`weight_norm` 仍是警告。

下一步把這段 latent 解回波形，確認人聲加伴奏聽起來是一首歌，而不是錯位或爆音：

```bash
CUDA_VISIBLE_DEVICES=0 PYTHONPATH=src python -m yue2.cli decode /cache/yue2_outputs/vae_one/latent.npy --vae /cache/yue2_files/YuE2-Vae --offline --device cuda --output /cache/yue2_outputs/vae_one/mix.wav
```

聽 `mix.wav`。聽起來正常之後，再從這 180 萬條裡抽一小批 latent 和歌詞。這首的歌詞只有 7 個字，不適合當歌詞樣本。樂譜和 32768 類語義 token 仍未做。

`sync_to_linux.ps1` 的第一步現在最多等 10 秒。逾時會關掉該次 `ssh` 並拋出錯誤，`watch_sync_to_linux.ps1` 的迴圈會在下一輪重跑。正在跑的監視視窗要重新啟動一次。

本次更新的文件：`sync_to_linux.ps1`
