# 同步密鑰已改成 Saxphone.pem

`sync_to_linux.ps1` 現在使用 `C:/Users/c00871154/.ssh/Saxphone.pem`。主機仍是 `ma-user@10.155.175.163`，端口 `34456`，遠端目錄仍是 `/home/ma-user/work/YuE2`。

正在跑的 `watch_sync_to_linux.ps1` 要重新啟動一次，才會用到這把密鑰。然後再執行 `.\sync_to_linux.ps1`。若仍是 `Permission denied (publickey)`，就是這台機器的 `authorized_keys` 裡也沒有 `Saxphone.pem` 的公鑰。

本次更新的文件：`sync_to_linux.ps1`
