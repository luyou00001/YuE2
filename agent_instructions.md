# 100 首 Suno 先對檔，初步訓練只預測樂譜

這 100 首可以用來做第一段訓練：給歌詞和 style，讓 YuE2 預測 SheetSage2 轉出的 ABC。完整音頻微調還做不了。原曲的語義 token 沒有公開 tokenizer，3B 全參數的 Adam 狀態也放不進 32GB。倉庫裡的 `train_cn_partial.jsonl` 只有 4 首；完整資訊應在 `/cache/yue2_files/datasets/suno_100/train_cn.jsonl`。混音用 `suno_wav`，不用伴奏或人聲分離軌。

先確認 100 首都能對上音頻，並寫出第 1 首的歌詞和 style。這條不印歌詞、不載入模型。

```bash
PYTHONPATH=src python public/suno_prepare.py
```

看 `matched`、`missing_meta`、`missing_audio`。三個數字貼回來。`matched=100` 之後，再轉第 1 首並計算 ABC loss，仍然不更新權重。

本次更新的文件：`public/suno_prepare.py`、`public/train_abc_loss.py`
