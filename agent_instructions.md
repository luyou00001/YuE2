# SSH 連線測試不再無限等待

`watch_sync_to_linux.ps1` 卡住的第一步在 `sync_to_linux.ps1`。原來的 `ssh` 沒有連線逾時，也沒有關掉密碼詢問，遠端沒回應時會一直停在 `Testing SSH connectivity`。

現在 SSH 使用 `BatchMode=yes`、`ConnectTimeout=15`、`ConnectionAttempts=1`。15 秒內連不上就失敗並回到監視迴圈，下一輪再試。`git push` 走同一組選項。

監視視窗需要重新啟動一次，才會用到新的 `sync_to_linux.ps1`。

本次更新的文件：`sync_to_linux.ps1`
