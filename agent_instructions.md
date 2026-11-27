# 100 首已對上，接著算第 1 首的樂譜損失

`matched=100`，`missing_meta=0`，`missing_audio=0`。混音檔 200 個，對應 100 首的兩個 track。第 1 首是 `suno_cn_013117` track 0，174.80 秒，歌詞 608 字，11 個段落。

下一條會轉這首混音、打成前綴，再算 YuE2 在樂譜 token 上的 loss。不更新權重。174 秒的轉譜加上一次 3B 前向，可能要數分鐘。

```bash
HF_HUB_OFFLINE=1 PYTHONPATH=src python public/suno_first.py
```

把最後的 `abc_loss=` 那一行貼回來。若中途報錯，整段輸出都貼回來。

本次更新的文件：`public/suno_first.py`、`public/pack_suno_one.py`
