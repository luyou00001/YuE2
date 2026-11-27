# 聽感可用，先把一首歌打成訓練前綴

骨架像同一首歌。伴奏少，是因為轉譜裡主歌和副歌的樂器軌大多是休止，生成主要跟著和弦符號走。人聲怪，是因為這次沒有歌詞。12 萬首 Suno 帶歌詞，之後用這批；180 萬那批先放著。

路徑找到後，先給 1 首，不要一次給 12 萬。每首需要三樣：音頻、歌詞文本，以及 Suno 的 style 或 prompt（有就一起給）。

現在先把打包跑通。這條只做分詞，不載入 3B，也不重新轉譜。這首仍是空歌詞，用來確認前綴能寫出來。

```bash
PYTHONPATH=src python public/pack_suno_one.py --audio /cache/yue2_outputs/full_mix/000/mix.wav --lyrics-file public/full_mix_000_lyrics.txt --score /cache/yue2_outputs/full_mix/000/score/score.abc --style "Vocal and accompaniment, 6/8, around 90 BPM" --id full_mix_000 --output /cache/yue2_outputs/packed/000
```

它會印 `audio_sec`、`lyric_chars`、`abc_chars`、`prefix_len`。把這一行貼回來。語義 tokenizer 還沒有公開權重，所以這包先不能做完整微調；等一首真實歌詞到了，再算「歌詞加風格預測這份譜」的 loss。

本次更新的文件：`public/pack_suno_one.py`、`public/full_mix_000_lyrics.txt`
