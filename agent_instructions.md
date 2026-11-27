# 環境已齊，轉第一首 10 秒

`mir_eval 0.8.2` 和 `pretty_midi 0.2.10` 已裝上，import 成功。兩個權重字節數也正確：SheetSage2 `model.safetensors` 是 228738564，MERT-v2-FullSong `model.safetensors` 是 2529812848。pip 提示升級可以忽略，torch 維持 2.3.1+cu121。

自帶的 `infer.py` 會按設定去找 Hub 上的 `m-a-p/MERT-v2-FullSong`。這次改走已經放在 `/cache/yue2_files/MERT-v2-FullSong` 的本地目錄，並做完整轉譜（旋律、和弦、段落），輸出到這首 10 秒音頻旁邊。V100 上用 fp32。

```bash
HF_HUB_OFFLINE=1 PYTHONPATH=src python public/transcribe_one.py
```

成功時會印出 `score_exists True`，以及 `/cache/yue2_outputs/vae_batch/000/score/score.abc` 的開頭。把完整輸出貼回來。若中途報缺模組或 CUDA 錯誤，也原樣貼回來，先不要改 torch。

本次更新的文件：`public/transcribe_one.py`
