# 同步腳本已改，網頁控制台可以開

Windows PowerShell 5.1 會把沒有 BOM 的中文腳本按系統編碼讀入，括號因此對不上，`sync_to_linux.ps1` 在連線前就退出。提示改回英文。公司電腦上的舊檔自己不會更新，請先在那個倉庫取得這次提交，再執行 `.\sync_to_linux.ps1`。成功時結尾會印 `Files changed in this sync` 和每個變更的路徑。

無譜生成已完成：185.9 秒，樂譜和語義都沒有截斷。請對聽原曲和 `/cache/yue2_outputs/suno_free/suno_013117_free/audio.mp3`。

V100 上啟動控制台，保持這個程序不要關：

```bash
PYTHONPATH=src python public/v100_panel.py
```

公司電腦另開一條連線：

```powershell
ssh -i C:/Users/c00871154/.ssh/Saxphone.pem -p 34456 -L 8765:127.0.0.1:8765 ma-user@10.155.175.163
```

瀏覽器打開 http://127.0.0.1:8765 。頁面有代碼狀態、進度和下一步。按鈕只會跑允許的腳本，日誌寫到 `/cache/yue2_panel/logs/`，同一頁可以下載。現在的按鈕是「匯出對聽路徑」，不載入模型。

本次更新的文件：`sync_to_linux.ps1`、`public/v100_panel.py`、`public/panel_state.json`、`public/panel_export_listen.py`
