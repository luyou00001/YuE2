# 可以直接接 NAR 的讀檔，不要接它的 token

`S3_ENDPOINT` 和 `OBS_ENDPOINT` 都已設定，AWS 的 access key 是空的。NAR 不是用 `rclone` 或 `aws` 讀伴奏，而是用 `mox.file.copy` 把 `s3://` 抓到 `/cache/auds<rank>/`，再切 48 kHz 立體聲。這段可以原樣給 YuE2 用。`mix_path` 在舊流程裡是伴奏 mp3，人聲另在 `vocal_wav_all.txt`。

不能原樣接上的是編碼結果。NAR 接著用 MuCodec 做成 25 Hz、16384 類，人聲和伴奏各一條。YuE2 要的是同一條混合波形的 VAE latent，25 Hz × 64。`codec_path` 不能填進 YuE2 的語義 token。

可以逐項補的差距：

1. 讀檔：用 NAR 的 `mox.file.copy` 抓一首伴奏和對應人聲。這是下一步。
2. 混合：兩條波形對齊後相加，得到 YuE2 要的立體聲。
3. 聲學目標：用 `/cache/yue2_files/YuE2-Vae` 編成 latent。先做一首。
4. 歌詞：索引裡有 `lyric`。第一條只有 7 個字，要等抽樣後才知道有多少首歌夠用。
5. 風格文字：`clamp3_path` 是向量，不是句子。YuE2 的風格 prompt 仍要另做。
6. 樂譜：沒有 ABC。SheetSage2 以後再跑在混合音頻上。
7. 語義 token：官方 tokenizer 仍然沒有。MuCodec 不能代替。

先確認目前這個 Python 能不能用 NAR 的下載函數：

```bash
python -c 'import moxing; print("moxing", moxing.__file__)'
```

印出路徑就代表可以沿 NAR 的方式抓一首 `s3://ttsingnorth/...` 的 mp3。若是 `ModuleNotFoundError`，把 NAR 訓練當時用的 Python 路徑貼回來，讀檔用那個環境，VAE 仍用現在這個。

本次沒有更新任何文件。
