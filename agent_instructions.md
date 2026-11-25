# 同步腳本已改到這次 YuE2 機器

`sync_to_linux.ps1` 的連線已改成：

- 主機：`ma-user@7.216.161.45`
- 端口：`32138`
- 密鑰：`C:/Users/c00871154/.ssh/hk-develop-sh.pem`
- 遠端目錄：`/home/ma-user/work/YuE2`

公司電腦在倉庫目錄直接執行 `.\sync_to_linux.ps1`。它仍把當前 HEAD 推到伺服器倉庫的 `main`。

`watch_sync_to_linux.ps1` 和 `watch_git_pull.sh` 裡沒有上一個任務的地址、端口或密鑰。前者只是週期呼叫 `sync_to_linux.ps1`，後者只對 GitHub upstream 做 `git pull`。這兩支不用改。

本次更新的文件：`sync_to_linux.ps1`
