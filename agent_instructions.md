# 控制台重啟一次後，同步會自動換頁

現在這個程序還是舊版。在跑著 `public/v100_panel.py` 的那個終端按 Ctrl+C，再執行：

```bash
PYTHONPATH=src python public/v100_panel.py
```

瀏覽器重新打開 http://127.0.0.1:8765 。日誌直接顯示在下方，按「複製完整日誌」即可貼回來。

這次重啟之後，git 同步進新提交、而且沒有任務在跑時，控制台會自己重啟，頁面也會跟著重新整理。有任務在跑時會等它結束再重啟。

本次更新的文件：`public/v100_panel.py`、`docs/inference-flow.md`
