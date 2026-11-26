# 同步伺服器已改到 10.155.175.163:34456

`sync_to_linux.ps1` 現在連 `ma-user@10.155.175.163`，端口 `34456`，密鑰 `C:/Users/c00871154/.ssh/hk-develop.pem`。遠端目錄仍是 `/home/ma-user/work/YuE2`。SSH 的 15 秒逾時還在。

`watch_sync_to_linux.ps1` 不用改，它只呼叫這支同步腳本。正在跑的監視視窗要重新啟動一次。

這台新機器上的 `outputs` 和 `/cache` 底下的輸出是空的，先前 V100 的歌曲、checkpoint 和 VAE latent 不會跟著過去。索引和權重需要在新機器上另行放好。下一步等權重複製完成後，再確認這台機器能不能讀到桶 `ttsingnorth`。

本次更新的文件：`sync_to_linux.ps1`
