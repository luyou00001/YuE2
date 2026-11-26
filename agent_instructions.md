# 監視一直重試，是因為 SSH 在第一步失敗

`watch_sync_to_linux.ps1` 看到本機是 `1d59096`，GitHub 是 `9625d68`，所以每 10 秒都去跑 `sync_to_linux.ps1`。同步腳本在測試 SSH 時失敗，後面的 `git pull` 和推送到 Linux 都沒有執行。本機提交不變，下一輪仍認為有更新，於是不停重試。

失敗有兩種：

- 大約 1 秒就出現 `SSH command failed`：SSH 已經得到結果並返回非 0。這和之前的 `Permission denied (publickey)` 是同一類，伺服器沒有接受目前的 `Saxphone.pem`。現在的逾時寫法沒有把 `ssh` 自己的錯誤文字印出來，所以畫面上只剩這句。
- `SSH timed out after 10s`：端口在 10 秒內沒有完成連線，腳本把該次 `ssh` 關掉了。這是逾時生效，不是卡住。

所以公司電腦這段時間並沒有把新代碼同步到 `10.155.175.163`。要麼這台新實例的 `ma-user` 仍未授權 `Saxphone.pem` 的公鑰，要麼 `34456` 這條連線不穩定。在 SSH 測試印出 `SSH OK` 之前，不需要再看後面的推送步驟。

本次沒有更新任何文件。
