# YuE2 推理流程

網頁讀 `public/panel_flow.json`。情況變了就改那個檔的 `status`：`done`、`current`、`later`。改完要重新啟動 `public/v100_panel.py`，頁面才會換上新的版面；流程文字每次重新整理都會重讀。

目前停在第 7 步「對聽原曲和無譜生成」。前 6 步已經跑通。

1. 環境與本地權重。PyTorch-2.0.0 裡是 Python 3.9.11、torch 2.3.1+cu121。YuE2-3B、YuE2-Vae、SheetSage2、MERT-v2-FullSong 都在 `/cache/yue2_files`。轉譜約 3.8GB。
2. 對上 Suno 混音、歌詞和 style。100 首都能對上。第 1 首 `suno_cn_013117` track 0，174.80 秒。
3. SheetSage2 把混音轉成完整 ABC。第 1 首 2312 字，有段落和和弦。樂器軌在主歌和副歌大多是休止。
4. 把歌詞、style 和 ABC 打成前綴。2262 token，其中 1770 個是樂譜 token。
5. 有譜生成。YuE2 沿用外部 ABC。先前那首聽起來是同一首歌，伴奏較少，人聲較怪。
6. 無譜生成。只給歌詞和 style。第 1 首生成 185.9 秒，沒有截斷。mp3 在 `/cache/yue2_outputs/suno_free/suno_013117_free/audio.mp3`。
7. 對聽原曲和無譜生成。原曲是 `/cache/yue2_files/datasets/suno_100/suno_wav/suno_cn_013117_0.mp3`。只比較旋律和段落。
8. 再決定要不要更新權重。樂譜損失 0.3594，先不改權重。完整音頻微調還缺語義 tokenizer。
