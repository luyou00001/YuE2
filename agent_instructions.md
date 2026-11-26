# Permission denied (publickey) 是密鑰不被接受

`10.155.175.163` 的 `34456` 端口已經連上。SSH 完成握手後，伺服器拒絕了目前這把私鑰，所以顯示 `Permission denied (publickey)`。這不是逾時，也不是代碼路徑錯。`BatchMode=yes` 讓它不會改問密碼，因此直接失敗。

腳本現在送出的是 `C:/Users/c00871154/.ssh/hk-develop.pem`，登入用戶是 `ma-user`。這把私鑰的公鑰不在這台新實例的 `ma-user` 的 `authorized_keys` 裡。同一個 IP 上，`34456` 和之前的 `39404` 或 `7.216.161.45:32138` 是不同的 SSH 實例，已授權的密鑰不必相同。先前 YuE2 那台用的是 `hk-develop-sh.pem`。

要在這台機器上同步，需要把實際獲準登入 `ma-user` 的那把私鑰放進腳本。若平台建立這台機器時綁的是 `hk-develop-sh.pem`，就改回那一把；若要繼續用 `hk-develop.pem`，就把該私鑰對應的公鑰加進這台機器的 `~/.ssh/authorized_keys`。在那之前，`sync_to_linux.ps1` 會一直停在第一步。

本次沒有更新任何文件。
