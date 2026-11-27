# 顯存探針通過，峰值 9.54 GiB

最後一層有 100672000 個參數。一次反向的峰值是 **9.54 GiB**，`abc_loss=0.3594`。沒有更新權重，`/cache/yue2_files/YuE2-3B` 沒有改。這個損失和之前第 000 首一樣，因為這一步沒有做 optimizer step。

## 介面

- Git 有新版本時會彈出視窗，裡面有重整畫面按鈕。
- 任務底部的空白收到和 GPU 一樣。
- 代碼狀態欄已刪掉。
- 目前進度和下一步放在訓練流程第 6 步底下。

## 下一步

同步後重新整理。右上角任務會出現第 6 步「32GB 小更新」的執行按鈕。它對 000 到 007 各做一步，只更新最後一層，新權重存到 `/cache/yue2_ckpts/fit32-suno8`。

```bash
PYTHONPATH=src HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python public/train_fit32.py
```

跑完把 `saved=` 和 `fit32_done=8` 那兩行貼回來。

本次更新的文件：`public/v100_panel.py`、`public/train_fit32.py`、`public/panel_flow.json`、`public/panel_state.json`
