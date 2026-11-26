# 用同一套腳本另測原來的 7.216 服務器

`sync_to_linux.ps1` 沒有改，仍指向 `ma-user@10.155.175.163:34456` 和 `Saxphone.pem`。

新文件是 `sync_to_linux_7.ps1`。它用同一套連線測試，目標改回 `ma-user@7.216.161.45`，端口 `32138`，密鑰 `C:/Users/c00871154/.ssh/hk-develop-sh.pem`。遠端目錄仍是 `/home/ma-user/work/YuE2`。git remote 用 `v100-7`，不會改掉目前的 `rl-node`。

在公司電腦的倉庫裡執行：

```powershell
.\sync_to_linux_7.ps1
```

若出現 `SSH OK` 並走到 `Done`，目前這套腳本可以連上舊服務器，問題在新服務器的 SSH 授權或端口。若這份也在第一步失敗，把完整輸出貼回來，那就是腳本本身的呼叫方式有問題。

本次更新的文件：`sync_to_linux_7.ps1`
