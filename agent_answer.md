### [2026-11-25 16:35] V100 改為 conda 環境和默認 pip

- **修改的文件**：無源碼改動。`agent_instructions.md` 換成完整安裝命令。
- **核心邏輯**：用 `conda create -n yue2 python=3.12`，然後 `pip install torch==2.10.0` 和 `pip install .`。Linux 上這個默認輪子是 CUDA 12.8，包含 V100 的 sm_70，所以不加 `--index-url`。
- **AI 備註**：之後仍先做 BF16 矩陣乘法，再 `yue2 doctor` 和 `--backend torch-eager --low-vram` 生成。權重路徑維持 `/cache/yue2_files/`。

### [2026-11-25 16:32] 把 V100 完整操作步驟寫進 agent_instructions.md

- **修改的文件**：無源碼改動。`agent_instructions.md` 改為上一則完整回覆，含可直接貼上 V100 的命令。
- **核心邏輯**：伺服器要跑的是完整步驟，不是摘要。之後每次回覆都整段寫入 `agent_instructions.md`。
- **AI 備註**：文件內容與對話中的 V100 安裝、BF16 矩陣乘法、`yue2 doctor` 和 `torch-eager` 生成命令一致。

### [2026-11-25 16:27] V100 探測記錄的下一步

- **修改的文件**：無源碼改動。
- **核心邏輯**：`including_emulation` 在 PyTorch 2.0.0 不存在，所以探測在印出計算能力 7.0 和 `is_bf16_supported()==True` 之後中斷。權重已在 `/cache/yue2_files/`。下一步離開這個 conda 環境，用 Python 3.12 安裝 torch 2.10，先做一次 BF16 矩陣乘法，再跑 `yue2 doctor` 和 eager 推理。
- **AI 備註**：不要用 vLLM 或 FP8。默認 CUDA graph 先關掉，用 `--backend torch-eager --low-vram`。cu128 輪子若沒有 sm_70，改裝 cu126。

### [2026-11-25 15:07] 把同步腳本改到 YuE2 的 V100 機器

- **修改的文件**：`sync_to_linux.ps1`
- **核心邏輯**：只改 SSH 主機、端口、密鑰和遠端目錄。`watch_sync_to_linux.ps1` 呼叫同一支同步腳本，本身沒有地址；`watch_git_pull.sh` 只對 GitHub 做 pull，也不含這組連線。
- **AI 備註**：新目標是 `ma-user@7.216.161.45:32138`，目錄 `/home/ma-user/work/YuE2`，密鑰 `C:/Users/c00871154/.ssh/hk-develop-sh.pem`。推送分支仍是伺服器上的 `main`。

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
