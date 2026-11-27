# 用這份完整譜生成一首對照

3 分 56 秒的原音已經轉成 2917 字的 ABC。譜裡有 intro、verse、chorus，人聲有音符，也有和弦，`abc_error` 為空。3.8 GB 顯存說明轉譜可以放在 V100 上跑。180 萬首先保持不動。

這一步把這份譜交給現有的 YuE2-3B，`cot=full`，生成對照音頻。歌詞仍是空的段落標籤，聽的時候只比較旋律、和弦和段落，不評價唱詞。對照的原音是 `/cache/yue2_outputs/full_mix/000/mix.mp3`。生成結果裡會有 `audio.mp3`。整首歌可能要數分鐘。

```bash
PYTHONPATH=src python -m yue2 generate --model /cache/yue2_files/YuE2-3B --vae /cache/yue2_files/YuE2-Vae --backend torch-eager --budget 30 --offline --request public/full_mix_000.json --abc-file /cache/yue2_outputs/full_mix/000/score/score.abc --output /cache/yue2_outputs/full_mix_000_cover
```

把終端最後一行 JSON 貼回來。微調還要等同事提供、能用索引欄位 `k` 對上的真實歌詞；語義 tokenizer 目前沒有公開權重，這一步不做訓練。

本次更新的文件：`public/full_mix_000.json`
