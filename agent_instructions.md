# SSH 呼叫已改回最初的直接執行

`sync_to_linux_7.ps1` 也失敗，說明不是某一台服務器單獨的問題。兩支腳本共用後來加上的 `Start-Process` 逾時寫法，這段在 Windows PowerShell 裡會把 `ssh` 的結果弄亂。10 秒檢測已經去掉。

現在兩支腳本都恢復成最初的寫法：直接呼叫 `ssh`，連線測試仍是 `echo ok > /dev/null`。目標沒有對調。

- `sync_to_linux.ps1`：`ma-user@10.155.175.163:34456`，`Saxphone.pem`
- `sync_to_linux_7.ps1`：`ma-user@7.216.161.45:32138`，`hk-develop-sh.pem`

先在公司電腦執行：

```powershell
.\sync_to_linux_7.ps1
```

若這次出現 `SSH OK`，腳本已恢復，再試 `.\sync_to_linux.ps1`。若 7 這支仍失敗，把 `ssh` 印出的那一行原文貼回來。

本次更新的文件：`sync_to_linux.ps1`、`sync_to_linux_7.ps1`
