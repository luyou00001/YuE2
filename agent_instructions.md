# 聽感正常後，先抽 8 首帶歌詞的 10 秒樣本

這 10 秒的人聲加伴奏可以當 YuE2 的聲學來源。訓練目標仍是在現有 `YuE2-3B` 上做 finetune、後訓練和新功能，不從頭訓練。現在這台 8 張 V100 用來開發。後面大規模訓練用 8 個節點、每節點 8 張，一共 64 張 V100。

下一批只抽 8 首，跳過歌詞短於 20 字的記錄。每首保存 `latent.npy`、`mix.wav` 和 `mix.mp3`。歌詞寫在該目錄的 `lyric.txt`，終端只印字數。下載仍走 NAR 的 `mox.file.copy`。

```bash
CUDA_VISIBLE_DEVICES=0 PYTHONPATH=src python public/fetch_vae_batch.py --count 8
```

結果在 `/cache/yue2_outputs/vae_batch/000` 到 `007`。先聽幾首 `mix.mp3`。若 `mp3=False`，這台機器沒有 `ffmpeg`，WAV 仍在。8 首都正常之後，再把這個抽取接到續訓，而不是一次掃完 183 萬首。樂譜和 32768 類語義 token 仍後做。

本次更新的文件：`public/fetch_vae_batch.py`
