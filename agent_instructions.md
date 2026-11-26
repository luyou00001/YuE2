# 前 2 萬條都沒有 20 字以上的歌詞

`fetch_vae_batch.py` 沒有失敗在下載或 VAE。它掃了 20000 條，歌詞長度都低於 20，所以一首都沒有保存。第一條之前看到的是 7 個字。這個欄位可能普遍很短，不能先假設它是完整歌詞。

先統計前 5000 條的長度分布，不印歌詞：

```bash
PYTHONPATH=src python public/lyric_length_stats.py --max-scan 5000
```

把 `scanned`、`longest` 和各區間的數量貼回來。若大多數都在 1–7 字，抽樣就不再用 20 字門檻，改為先抽 8 首音頻；歌詞是否能當 YuE2 的條件，等分布出來再定。

本次更新的文件：`public/lyric_length_stats.py`
