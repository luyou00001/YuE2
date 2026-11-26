# 回到開發：先抽 8 首可聽的樣本

同步腳本已恢復，7.216 那次能跑通，說明直接呼叫 `ssh` 是對的。開發繼續在現在這台能讀 `ttsingnorth` 的服務器上進行。

10 秒的人聲加伴奏聽起來正常。下一步抽 8 首歌詞不少於 20 字的片段，每首 10 秒，保存 `latent.npy`、`mix.wav` 和 `mix.mp3`。終端只印歌詞字數。

```bash
CUDA_VISIBLE_DEVICES=0 PYTHONPATH=src python public/fetch_vae_batch.py --count 8
```

聽 `/cache/yue2_outputs/vae_batch/000` 到 `007` 裡的 `mix.mp3`。若某一首 `mp3=False`，WAV 仍在。8 首都像正常歌曲之後，再把這個抽取接到 `YuE2-3B` 的 finetune。不從頭訓練。現在用這台 8 張 V100 開發，大規模訓練再使用 8 個節點共 64 張 V100。樂譜和 32768 類語義 token 仍後做。

本次沒有更新任何文件。
