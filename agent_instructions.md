# 上次檢查停在引號錯誤，欄位還沒看完

`200w-001.txt` 的內層已經確認有 `lyric`、`mix_path`、`clamp3_path`、`codec_path`。接著要看歌詞字數，以及三條路徑的後綴和文件是否存在。上一版把這段寫在 `python -c` 裡，shell 把引號截斷，Python 3.9 報了 `SyntaxError`，所以 `exists` 還沒有結果。

這段已改到 `public/inspect_180w_record.py`。它不印歌詞，也不印完整路徑。

```bash
bash public/check_180w_index.sh
```

把 `lyric`、`mix_path`、`clamp3_path`、`codec_path` 那幾行貼回來。`mix_path` 的 `exists` 若是 `False`，這份副本只有索引，音頻不在當前路徑上，還不能抽 VAE latent。

本次更新的文件：`public/check_180w_index.sh`、`public/inspect_180w_record.py`
