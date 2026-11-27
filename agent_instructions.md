# 流程已寫進網頁，下一步是對聽

日誌確認兩個檔都在：原曲 `/cache/yue2_files/datasets/suno_100/suno_wav/suno_cn_013117_0.mp3`（4083837 bytes），無譜生成 `/cache/yue2_outputs/suno_free/suno_013117_free/audio.mp3`（4043445 bytes）。推理主鏈前 6 步已完成，目前是第 7 步對聽。只比較旋律和段落，這一步不跑模型。

流程保存在 `docs/inference-flow.md`。網頁讀 `public/panel_flow.json`，之後改那個檔的 `status`（done、current、later）即可。重新啟動控制台後，頁面會顯示「已完成 6 / 8」。

```bash
PYTHONPATH=src python public/v100_panel.py
```

本次更新的文件：`public/v100_panel.py`、`public/panel_flow.json`、`public/panel_state.json`、`docs/inference-flow.md`
