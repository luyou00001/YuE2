# `echo ok > /dev/null` 不是失敗原因

`SSH command failed: echo ok > /dev/null` 是腳本把當時交給遠端的命令原文貼進錯誤訊息。`ssh` 的退出碼不是 0，所以這句會出現。遠端的 `echo` 和 `/dev/null` 沒有語法問題。上一輪能看到的原文是 `Permission denied (publickey)`，也就是這把私鑰沒被 `ma-user` 接受。

改了兩處，避免再被這行字誤導：連線測試改為遠端執行 `true`，失敗時把 `ssh` 自己的錯誤文字印出來。10 秒逾時仍在。監視視窗要重新啟動後再跑 `.\sync_to_linux.ps1`。若新錯誤裡仍有 `Permission denied (publickey)`，就是 `Saxphone.pem` 還沒被這台機器授權。

本次更新的文件：`sync_to_linux.ps1`
