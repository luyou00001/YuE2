### [2026-11-24 17:22] 中文研究地圖，以及現有代碼能不能開訓

- **修改的文件**：無倉庫源碼改動。分析畫布 `yue2-research-map.canvas.tsx` 已改為中文。
- **核心邏輯**：要重啟訓練必須新寫訓練代碼。現倉只有可載入的 MoT 和一條未加遮罩、未加權的因果交叉熵；flow matching、數據管線、四任務混合和分散式訓練都沒有。官方語義 tokenizer 也未發布。
- **AI 備註**：可直接 import `YuE2ForCausalLM` 當模型定義。第一個訓練里程碑是 AR span 遮罩和 0.25 權重，第二個才是可反傳的 flow matching。從 `m-a-p/YuE2-3B` 繼續訓練，不要從零復現 64×H800。

### [2026-11-24 17:25] YuE2 論文與推理倉對照，以及研究起步

- **修改的文件**：無源碼改動。分析畫布在 Cursor canvas `yue2-research-map.canvas.tsx`。
- **核心邏輯**：對照技術報告與 `yue2-infer` 0.1.6，確認本倉實作 AR–NAR 推理與 VAE 解碼；訓練迴圈、語料和官方 32,768 語義 tokenizer 不在倉內。起步應先在 A100 上凍結一條生成 artifact，再把研究切在現成 checkpoint 的樂譜控制上。
- **AI 備註**：這台 Mac 適合讀協議、跑 CPU 測試和寫 trainer；A100 跑 BF16 推理與後續 LoRA；V100 沒有 BF16，適合資料前處理。全量復現論文的 64×H800 配方不適合當第一步。授權上代碼是 Apache-2.0，權重是 CC BY-NC 4.0。
