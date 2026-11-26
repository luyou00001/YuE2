# 現在要你提供歌詞對照，並另建 SheetSage2 環境

音頻和 VAE latent 已經通了。現在缺兩樣可以立刻做的東西：完整歌詞，以及 SheetSage2 轉出的 ABC。32768 類語義 token 仍然沒有官方工具，這一步先不做。

歌詞請向同事要能對上 `200w-*.txt` 裡欄位 `k` 的文件。索引裡的 `lyric` 是 `unknown`，不能用。可用的形式是 jsonl，每行有 `k` 和完整歌詞，或者一個目錄、檔名等於 `k`、內容是歌詞。把路徑告訴我，先不要把歌詞貼出來。

SheetSage2 必須單獨安裝，不要裝進現在的 PyTorch-2.0.0。它要 Python 3.10 或 3.11，以及已經在用的 ffmpeg。權重放到 `/cache/yue2_files/SheetSage2`。官方步驟使用 CUDA 12.6 的 torch 2.8；這台機器若不能加 `--index-url`，先停下來把錯誤貼回來，不要改現有的 YuE2 環境。

```bash
python3.11 -m venv /cache/yue2_files/venv-sheetsage2
/cache/yue2_files/venv-sheetsage2/bin/python -m pip install huggingface-hub==0.36.0
/cache/yue2_files/venv-sheetsage2/bin/huggingface-cli download m-a-p/SheetSage2 --local-dir /cache/yue2_files/SheetSage2
/cache/yue2_files/venv-sheetsage2/bin/python -m pip install torch==2.8.0 torchaudio==2.8.0 --index-url https://download.pytorch.org/whl/cu126
/cache/yue2_files/venv-sheetsage2/bin/python -m pip install -r /cache/yue2_files/SheetSage2/requirements.txt
```

沒有 `python3.11` 時，把 `python3.10 --version` 的結果貼回來，再用 3.10 建同一個目錄。裝好後只轉寫已經聽過的第一首：

```bash
/cache/yue2_files/venv-sheetsage2/bin/python /cache/yue2_files/SheetSage2/infer.py /cache/yue2_outputs/vae_batch/000/mix.wav --output /cache/yue2_outputs/vae_batch/000/score
```

成功後看 `/cache/yue2_outputs/vae_batch/000/score/score.abc` 是否有旋律、和弦和段落。這份 ABC 是樂譜 `s`。它附帶的 MERT-v2-FullSong 是轉譜編碼器，不是 YuE2 的語義 tokenizer。

本次沒有更新任何文件。
