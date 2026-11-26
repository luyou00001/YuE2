# 180 萬數據和 YuE2 續訓對得上哪一段

這套 180 萬數據可以當音頻來源，不能直接當 YuE2 的訓練 token。舊 NAR 用的是 MuCodec：48 kHz、25 Hz、16384 類，而且人聲和伴奏分成兩條。YuE2 的語義 token 是另一套 32768 類碼本，聲學目標是 VAE 的 25 Hz × 64 連續 latent。兩套離散 ID 不能混用。

YuE2 每首歌要四樣東西：

| 字段 | YuE2 要什麼 | 180 萬數據裡有什麼 |
|---|---|---|
| 音頻 | 48 kHz 立體聲整曲或長片段，人聲和伴奏在同一條裡 | 有。清單在 `/cache/l00956912/datasets/acctask-180w-acc-caption-cfgs`，子集 `pt_all_v1.txt`，時長 `wav2len.txt`。人聲在 `vocal_wav_all.txt`，伴奏在 jsonl 的 `mix_path`。訓練時隨機切 40–90 秒。 |
| 文字條件 y | 風格描述加歌詞 | 沒有可直接用的歌詞。`clamp3_path` 是風格向量，不是文字。目錄名裡的 caption 這次讀取代碼沒有拿去當 YuE2 的 prompt。 |
| 樂譜 s | ABC：旋律、和弦、調性、拍號、曲式 | 沒有。 |
| 語義 c | MERT2 因果 CVQ，25 Hz，32768 類 | 沒有。現有的是 MuCodec 16384 類，人聲、伴奏各一條。 |
| 聲學 z | YuE2-Vae 編碼出的 25 Hz × 64 | 沒有現成文件。可以用混合後的 48 kHz 波形現編。 |

所以這 180 萬條適合做 YuE2 的原始音頻庫。要用它訓練，得在 V100 上重新抽出 YuE2 自己的目標，而不是讀舊的 `.pt` 或 `<AUDIO_>` token。

能先接上的只有聲學 latent：把人聲和伴奏按時間對齊後相加，得到一條混合立體聲，再用已經放在 `/cache/yue2_files/YuE2-Vae` 的編碼器做成 `z`。這對應論文裡「沒有語義 token、用音頻 latent 做 flow matching」的那一檔，而且 40–90 秒短於論文的整曲打包。樂譜和歌詞仍然空著，官方語義 tokenizer 也仍然沒有，所以現在不能做完整的 `y, s, c, z` 續訓。

建議先在 V100 上只讀索引，不要開訓練。確認這四個文件還在，並看一條 jsonl 裡除了 `mix_path` 以外有沒有歌詞或文字描述：

```bash
CFG=/cache/l00956912/datasets/acctask-180w-acc-caption-cfgs
ls -lh "$CFG/pt_all_v1.txt" "$CFG/vocal_wav_all.txt" "$CFG/wav2len.txt"
wc -l "$CFG/pt_all_v1.txt"
find "$CFG" -name '200w*.txt' -printf '%p %s\n' | head
```

找到一個 `200w*.txt` 之後，看第一條有哪些欄位：

```bash
python -c "import json; p='$CFG/這裡換成檔名'; print(list(json.loads(open(p).readline()).keys()))"
```

把欄位名和 `wc -l` 的行數貼回來。若索引還在，下一步只抽一小批混合音頻的 VAE latent，先不要把 MuCodec token 送進 YuE2。

本次沒有更新任何文件。
