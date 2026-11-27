# 頁面改為自帶狀態，通道不再登入伺服器

「讀取中」是頁面在等第二個請求。那個請求若被 git 卡住，畫面就停住。現在打開頁面時直接帶上狀態，不等那一下。

已經連進伺服器的視窗輸入 `exit`，回到公司電腦。之後用這個腳本開通道，它只轉 port，不進入伺服器，視窗仍留在本機：

```powershell
.\open_panel_tunnel.ps1
```

然後重新打開 http://127.0.0.1:8765 。若標題底下仍是「讀取中」，在 V100 上把控制台 Ctrl+C 後再執行 `PYTHONPATH=src python public/v100_panel.py`。

本次更新的文件：`public/v100_panel.py`、`open_panel_tunnel.ps1`
