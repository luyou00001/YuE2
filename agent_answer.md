### [2026-11-24 17:25] YuE2 論文與推理倉對照，以及研究起步

- **修改的文件**：無源碼改動。分析畫布在 Cursor canvas `yue2-research-map.canvas.tsx`。
- **核心邏輯**：對照技術報告與 `yue2-infer` 0.1.6，確認本倉實作 AR–NAR 推理與 VAE 解碼；訓練迴圈、語料和官方 32,768 語義 tokenizer 不在倉內。起步應先在 A100 上凍結一條生成 artifact，再把研究切在現成 checkpoint 的樂譜控制上。
- **AI 備註**：這台 Mac 適合讀協議、跑 CPU 測試和寫 trainer；A100 跑 BF16 推理與後續 LoRA；V100 沒有 BF16，適合資料前處理。全量復現論文的 64×H800 配方不適合當第一步。授權上代碼是 Apache-2.0，權重是 CC BY-NC 4.0。
