# 這次是腳本自己在空訊息上崩潰

`You cannot call a method on a null-valued expression` 出在 `sync_to_linux.ps1` 第 53 行。SSH 結束後，錯誤輸出是空的，`$detail` 為空，腳本仍對它呼叫 `.Trim()`，所以真正的 `ssh` 退出碼和原文都沒印出來。這不是 `echo` 或 `true` 的語法問題，也不能從這一行判斷密鑰有沒有被接受。

已改成先等待程序完全結束，退出碼為空時不當成成功，只在有文字時才 Trim。失敗時會顯示 `SSH failed (退出碼): ssh 的原文`。監視視窗重新啟動後再跑 `.\sync_to_linux.ps1`。若看到 `Permission denied (publickey)`，才是 `Saxphone.pem` 仍未被授權；若看到 `SSH OK`，第一步就已經通過。

本次更新的文件：`sync_to_linux.ps1`
