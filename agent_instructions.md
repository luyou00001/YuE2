# 索引在，音頻文件不在這台 V100 上

`pt_all_v1.txt` 有 1,833,083 行，人聲清單和時長文件也在。第一條記錄的歌詞只有 7 個字。三條路徑都打不開：

- `mix_path` 是 `.mp3`，`exists=False`
- `clamp3_path` 是 `.npy`，`exists=False`
- `codec_path` 沒有後綴，`exists=False`

因此現在複製過來的是索引，不是音頻。`mix_path` 仍指向原來的位置，這台機器上沒有那些 mp3，不能抽 VAE latent，也不能把 MuCodec 文件拿來當 YuE2 的語義 token。

檢查腳本已加上每條路徑的父目錄，仍然不印文件名和歌詞。

```bash
bash public/check_180w_index.sh
```

把三行 `parent=` 貼回來。那個目錄才是還需要複製或掛載的音頻位置。

本次更新的文件：`public/inspect_180w_record.py`
