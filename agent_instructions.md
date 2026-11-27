# 樂譜損失已經很低，先聽無譜生成

第 1 首轉譜成功：2312 字，`abc_error` 為空。前綴 2262 token，其中 1770 個是樂譜 token。`abc_loss=0.3594`，下一個樂譜 token 的困惑度大約 1.43。基模在看到前面正確音符時，已經很會往下接，所以這首歌先不更新權重。樂器軌在主歌和副歌仍大多是休止，譜上記的是人聲旋律加和弦。

下一條不餵這份 ABC，只用這首歌的歌詞和 style 生成。整首大約要數分鐘。對聽這兩個檔：

- 原音：`/cache/yue2_outputs/suno_prep/000/audio.path` 裡的那條 mp3
- 生成：`/cache/yue2_outputs/suno_free/suno_013117_free/audio.mp3`

```bash
PYTHONPATH=src python public/suno_free.py
```

把最後一行 JSON 貼回來，並告訴我旋律和段落像不像同一首歌。

本次更新的文件：`public/suno_free.py`
