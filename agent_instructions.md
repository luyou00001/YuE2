# 現在要手動下載的只有兩份權重

伺服器上已經有、不用再下的是：

- YuE2-3B：https://huggingface.co/m-a-p/YuE2-3B
- YuE2-Vae：https://huggingface.co/m-a-p/YuE2-Vae
- 180 萬索引：`/cache/yue2_files/datasets/acctask-180w-acc-caption-cfgs`

這一步新要的是轉譜。SheetSage2 自己的權重不夠，它會讀 MERT-v2-FullSong 當編碼器。請下載這兩個完整倉庫，包含權重、config 和 Python 代碼，不要只下一個 safetensors。

| 用途 | 上傳到 | 下載頁 |
|---|---|---|
| 轉成 ABC 樂譜 | `/cache/yue2_files/SheetSage2` | https://huggingface.co/m-a-p/SheetSage2/tree/eab522a8168e8b8b8c4856bf8609cd86198f01fe |
| SheetSage2 的編碼器 | `/cache/yue2_files/MERT-v2-FullSong` | https://huggingface.co/m-a-p/MERT-v2-FullSong/tree/d8ba1c745e733b3908ce6ad16ebeb17ac7600a42 |

不要下載這些：

- MERT-v2-30s：https://huggingface.co/m-a-p/MERT-v2-30s 。那是短音頻版本，不能換進 SheetSage2。
- YuE2 的 32768 類語義 tokenizer。沒有公開倉庫。
- MuCodec。那是舊 NAR 的 16384 類 token，不是 YuE2 的目標。

歌詞仍請同事給能對上 `k` 的文件路徑。MERT-v2-FullSong 不會產生歌詞，也不會產生 YuE2 的語義 token。

兩份都放好之後告訴我。下一步才是在單獨的 Python 3.10 或 3.11 環境裡裝 SheetSage2 的 `requirements.txt`，並轉寫 `/cache/yue2_outputs/vae_batch/000/mix.wav`。不要裝進現在的 PyTorch-2.0.0。

本次沒有更新任何文件。
