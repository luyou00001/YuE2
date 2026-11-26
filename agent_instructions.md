# 180 萬記錄裡有歌詞和三條路徑

`200w-001.txt` 的內層欄位是 `lyric`、`mix_path`、`clamp3_path`、`codec_path`。歌詞文字在，這是 YuE2 文字條件的一部分。`mix_path` 在舊 NAR 裡是伴奏音頻。`clamp3_path` 是風格向量，不是風格句子。`codec_path` 是舊的 MuCodec 文件，不是 YuE2 的 32768 類語義 token。樂譜和 VAE latent 仍然沒有。

檢查腳本現在會看第一條記錄：歌詞只印字數，路徑只印後綴和文件是否存在，不印歌詞內容，也不印完整路徑。

```bash
bash public/check_180w_index.sh
```

若 `mix_path` 的 `exists` 是 `False`，這份副本只有索引，音頻還在原來的路徑上，現在不能抽 VAE latent。把新輸出貼回來。

本次更新的文件：`public/check_180w_index.sh`
