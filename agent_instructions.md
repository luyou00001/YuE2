# 10 秒已成功，下一首改完整原音

10 秒轉譜成功：`score.abc` 有 275 字，`abc_error` 是空的，沒有 warnings。`torch_dtype` 那兩行只是提示，可以忽略。譜面是 C 小調、4/4、每分鐘 101 拍，人聲全是休止，伴奏有旋律和 `Fm7`、`D#maj7`。這符合一段前奏，還看不出整首歌的結構。

另外 7 首 10 秒先停著。下一步只做同一首歌的完整原音：人聲和伴奏相加，不經過 VAE。聽的檔是同目錄的 `mix.mp3`。

```bash
PYTHONPATH=src python public/fetch_one_full_mix.py
HF_HUB_OFFLINE=1 PYTHONPATH=src python public/transcribe_one.py --audio /cache/yue2_outputs/full_mix/000/mix.wav --output /cache/yue2_outputs/full_mix/000/score
```

第一行會印 `duration_sec`。第二行會印完整譜的開頭。把兩段輸出都貼回來。若第二行出現 CUDA 顯存不足，再改跑前 180 秒：把第一行換成 `PYTHONPATH=src python public/fetch_one_full_mix.py --seconds 180`。

本次更新的文件：`public/fetch_one_full_mix.py`、`public/transcribe_one.py`
