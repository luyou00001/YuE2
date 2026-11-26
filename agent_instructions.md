# 歌詞欄位最長只有 7 個字

前 5000 條全部落在 1–7 字，`longest=7`。沒有 0 字，也沒有 8 字以上。這個 `lyric` 不是 YuE2 要的完整歌詞，不能用 20 字門檻篩選。抽樣腳本的下限已改成 1。

重新抽 8 首 10 秒音頻，每首仍保存 latent、WAV 和 MP3：

```bash
CUDA_VISIBLE_DEVICES=0 PYTHONPATH=src python public/fetch_vae_batch.py --count 8
```

聽 `/cache/yue2_outputs/vae_batch/` 裡的 `mix.mp3`。歌詞原文仍寫在各目錄的 `lyric.txt`，終端只印字數。這 8 首用來確認不同歌曲的混合音頻是否穩定。完整歌詞、風格句子、樂譜和語義 token 都還要另外做。

本次更新的文件：`public/fetch_vae_batch.py`
