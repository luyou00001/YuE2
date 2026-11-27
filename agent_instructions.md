# 對照音頻已生成，請對聽

生成完成。輸出 235.2 秒，原曲是 235.96 秒。`truncated` 裡的 abc 和 semantic 都是 false，譜和音頻都沒有被截斷。`torch_dtype` 和 `weight_norm` 兩行只是提示。總耗時 483.5 秒。

請對聽這兩個 mp3。只比較旋律、和弦走向和段落，不評價唱詞，因為這次歌詞是空的段落標籤。

- 原音：`/cache/yue2_outputs/full_mix/000/mix.mp3`
- 生成：`/cache/yue2_outputs/full_mix_000_cover/full_mix_000/audio.mp3`

聽完告訴我骨架像不像同一首歌。在這之前，180 萬首先保持不動，也不開始微調。微調還要等能用索引欄位 `k` 對上的真實歌詞；語義 tokenizer 目前沒有公開權重。

本次沒有更新任何文件。
