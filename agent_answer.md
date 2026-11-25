### [2026-11-25 14:29] V100 能否推理，以及權重下載地址

- **修改的文件**：無源碼改動。
- **核心邏輯**：現有推理把模型固定成 BF16，V100（計算能力 7.0）沒有 BF16 Tensor Core。啟動檢查在模擬模式下可能放行，但 FlashAttention、vLLM、FP8 都不適用，官方也沒有 V100 整首歌曲驗收。權重是公開的 Hugging Face 倉庫，推理需要 YuE2-3B 和 YuE2-Vae。
- **AI 備註**：單卡先確認 `is_bf16_supported(including_emulation=False)` 為 False。32GB 才有機會試；16GB 顯存緊。64 張 V100 現在沒有切模型的推理實現，代碼是單卡單請求。公司使用權重仍受 CC BY-NC 約束。

### [2026-11-24 17:49] 把中文 Canvas 放進倉庫，方便公司電腦 clone

- **修改的文件**：`docs/yue2-research-map.canvas.tsx`
- **核心邏輯**：Canvas 原本只在本機 Cursor 目錄，git 裡只有兩份 markdown。把同一份中文報告放進 `docs/`，公司電腦 checkout `agent-auto-draft` 後複製到該機的 Cursor canvases 目錄才能當畫布打開。
- **AI 備註**：遠端是 `git@github.com:luyou00001/YuE2.git` 的 `agent-auto-draft`。直接打開倉庫裡的 `.canvas.tsx` 只會看到源碼，Cursor 只渲染 `~/.cursor/projects/<工作區>/canvases/` 裡的那一份。

### [2026-11-24 17:22] 中文研究地圖，以及現有代碼能不能開訓

- **修改的文件**：無倉庫源碼改動。分析畫布 `yue2-research-map.canvas.tsx` 已改為中文。
- **核心邏輯**：要重啟訓練必須新寫訓練代碼。現倉只有可載入的 MoT 和一條未加遮罩、未加權的因果交叉熵；flow matching、數據管線、四任務混合和分散式訓練都沒有。官方語義 tokenizer 也未發布。
- **AI 備註**：可直接 import `YuE2ForCausalLM` 當模型定義。第一個訓練里程碑是 AR span 遮罩和 0.25 權重，第二個才是可反傳的 flow matching。從 `m-a-p/YuE2-3B` 繼續訓練，不要從零復現 64×H800。

### [2026-11-24 17:25] YuE2 論文與推理倉對照，以及研究起步

- **修改的文件**：無源碼改動。分析畫布在 Cursor canvas `yue2-research-map.canvas.tsx`。
- **核心邏輯**：對照技術報告與 `yue2-infer` 0.1.6，確認本倉實作 AR–NAR 推理與 VAE 解碼；訓練迴圈、語料和官方 32,768 語義 tokenizer 不在倉內。起步應先在 A100 上凍結一條生成 artifact，再把研究切在現成 checkpoint 的樂譜控制上。
- **AI 備註**：這台 Mac 適合讀協議、跑 CPU 測試和寫 trainer；A100 跑 BF16 推理與後續 LoRA；V100 沒有 BF16，適合資料前處理。全量復現論文的 64×H800 配方不適合當第一步。授權上代碼是 Apache-2.0，權重是 CC BY-NC 4.0。
