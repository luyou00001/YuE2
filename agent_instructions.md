# 標題改成一行，下一步先量最後一層的顯存

標題和版本號放在同一行。任務和 GPU 各佔扣掉標題後的一半視窗高度。任務列表一打開就停在最底下。代碼樹在「本次變更」後面列出檔名，超出寬度用省略號。

第 004 首對聽是整體很像，旋律只有部分段落接近。下一步先確認一張 V100 能不能對最後一層做反向，不更新權重，也不寫進基模。在 YuE2 目錄執行：

PYTHONPATH=src HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python public/train_fit32_probe.py

把印出的 peak_gib 和 abc_loss 貼回來。峰值低於 32GB 之後，才對 000 到 007 做小更新，新權重另存。

本次更新的文件：public/v100_panel.py、public/train_fit32_probe.py
