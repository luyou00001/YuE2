# 探針按鈕已放進任務欄

## 這輪介面

- 第 5 步「32GB 顯存探針」有執行按鈕。
- 本輪回答用標題、段落和程式碼區塊顯示。
- 任務和 GPU 都在自己的區塊裡捲動。
- 頁面滾到最底時，右下空隙保持 12px。

## 下一步

同步後重新整理。在右上角任務按第 5 步的執行。跑完把 `peak_gib` 和 `abc_loss` 貼回來。這一步不更新權重，也不寫進基模。

同一條指令是：

```bash
PYTHONPATH=src HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python public/train_fit32_probe.py
```

峰值明顯低於 32GB 之後，才對 000 到 007 做小更新，新權重另存。

本次更新的文件：`public/v100_panel.py`
