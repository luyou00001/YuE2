# YuE2 研究起步：論文與本地推理倉對照

這個倉庫是公開推理包 `yue2-infer` 0.1.6。技術報告裡的歌曲生成模型、token 協議、flow-matching 解碼和立體聲 VAE 都在代碼裡，並且按 Hugging Face 權重的參數名來寫。訓練迴圈、約 34.6 萬小時語料，以及把新錄音編成 32,768 類語義 token 的官方 tokenizer，都不在這個 fork 裡。

可並排打開的整理：[YuE2 research map](/Users/hkrc_music/.cursor/projects/Users-hkrc-music-YuE2/canvases/yue2-research-map.canvas.tsx)。這是一份 Cursor canvas，會在對話旁邊以獨立版面打開，方便回頭看對照表和起步順序。

## 論文在做什麼

YuE2 把一首歌拆成逐級確定的四層：

1. 文字條件 `y`：風格描述和歌詞。
2. 符號樂譜 `s`：ABC，含旋律、和弦、調性、拍號、速度和曲式。
3. 語義 token `c`：25 Hz、32,768 類，約 375 bit/s。
4. 聲學 latent `z`：25 Hz × 64，再由 Oobleck VAE 解成 48 kHz 立體聲。

生成分解是 `p(s, c, z | y) = p_AR(s, c | y) · p_NAR(z | y, s, c)`。同一個約 3.58B 的 checkpoint 負責創作、改譜和翻唱；三者的差別只在樂譜從哪裡來。創作時模型自己寫 `s`。改譜時使用者給定修改後的 `s`。翻唱時 SheetSage2 從參考錄音轉出 `s`，模型再用新的風格描述去演唱。論文強調翻唱沒有用原曲–翻唱配對來訓練。

骨幹是 28 層 AR–NAR Mixture-of-Transformers。每一層有兩套 RMSNorm、QKV、輸出投影和 SwiGLU MLP，注意力計算是共享的。AR 位置只做因果、而且看不到 acoustic latent。NAR 位置看完整個文字、樂譜、語義序列，並在 latent 之間雙向注意。聲學端學的是 conditional flow matching：`z_t = (1-t) z_0 + t ε`，目標速度是 `ε - z_0`。聯合損失是 `L = 0.25 L_AR + L_FM`。AR 交叉熵只落在樂譜和語義的 payload 以及它們的結束符上。

聯合訓練把四個任務等比例混合：完整的樂譜加語義、只有語義、只有樂譜、以及文字直接到音頻。文字和歌詞還會單獨或一起丟掉，用來做 classifier-free guidance。歌是整首裝進 24,576 context，不把一首歌切到兩個樣本裡。

附錄 C 的優化配方：

| 階段 | 更新數 | Context | 學習率 | Adam |
|---|---:|---:|---|---|
| 從零開始的 AR 預訓練 | 60,000 | 16,384 | 5,000 步升到 1e-4，餘弦底 1e-5，終點對準第 95,000 步 | β (0.9, 0.98)，weight decay 0.05 |
| 聯合 AR–NAR | 40,000 | 24,576 | 5,000 步升到 3e-4，餘弦底 1e-4，終點對準第 150,000 步 | β (0.9, 0.95)，weight decay 0.1 |
| Annealing | 6,000 | 24,576 | 無 warmup，從約 2.726e-4 餘弦降到 3e-5 | 與聯合階段相同 |

三個階段都是 BF16、global batch 256、梯度裁剪 1.0、64 張 H800。NAR 專家在聯合訓練開始時從對應的 AR 專家拷貝初始化，優化器在那一刻重置，annealing 沿用聯合階段的優化器狀態。取用的 checkpoint 都在餘弦衰減終點之前。

離線監督由三條凍結管線構成，也都不是這個倉庫的訓練代碼：

- SheetSage2-AR：約 28,400 小時，把整首歌轉成可編輯的 lead sheet，再編成 ABC。公開權重在 `m-a-p/SheetSage2`。
- MERT2：基礎預訓練約 70 萬小時。雙向的 MERT2-FS 供給 SheetSage2。因果分支再經過 CTC、mel/chroma 和 CVQ，部署時只留 ConvNeXt、Conformer 第 0–13 層和 32,768 碼本，這才是 YuE2 的語義 tokenizer。
- VAE：沿 Stable Audio Open 的 Oobleck，48 kHz 立體聲壓縮 1,920 倍，得到 25 Hz、64 維。聽歌用 `m-a-p/YuE2-Vae`，對論文數字用 `m-a-p/YuE2-Vae-legacy`。

文字條件來自 Qwen3-Omni 的風格與人聲描述、SongFormer 的段落，以及 Qwen3-ASR 的歌詞。語料主要是 CC0 音樂加上 Tokenwave.AI 授權的合成數據，這份語料沒有公開。

WildSongBench 有 192 條提示。標準 YuE2 在兩個候選裡留音素錯誤率較低的那條，SongBench Global Avg 是 6.7316。Best-of-8 先看 Musicality，再看提示對齊，再看音素錯誤率，達到 6.9632。論文把這組數字放在已評估系統裡的最高觀察均值，並寫明頂部差距沒有做顯著性宣稱。

## 這個倉庫裡實際有什麼

包名是 `yue2-infer`，版本 0.1.6。Python 入口是 `yue2`。核心都在 `src/yue2/`：

| 模組 | 職責 |
|---|---|
| `protocol.py` | 詞表切分、三種 `cot` 指令、採樣預設、CFG 的 negative prefix、聲學分塊 |
| `pipeline.py` | `plan` → `generate_semantic` → `synthesize` → `decode`，並把樂譜、token、latent、音頻和雜湊一起存下來 |
| `modeling_yue2.py` | 28 層 MoT。預設 hidden 2048、FFN 6144、16 個 query head、8 個 KV head、head dim 128、詞表 184704、context 24576、latent 64 |
| `nar.py` | 32 步 midpoint ODE。每個聲學塊先做一次 AR prefill，再解 velocity |
| `modeling_vae.py` | Oobleck 編碼器和解碼器。推理管線解碼時用 decoder |
| `sampling.py` / `cuda_graph.py` / `fast.py` | 自迴歸採樣、CUDA graph、可選 vLLM |
| `quantization.py` / `placement.py` | NVIDIA 上的 FP8 AR，以及低顯存時只把當前 AR 或 NAR 專家放上加速器 |
| `cli.py` | `generate`、`batch`、`validate`、`inspect`、`decode`、`export`、`doctor` |

`forward()` 能算因果交叉熵，測試裡也檢查了這條 loss 可以反傳。這條 loss 沒有論文裡的 span mask，也沒有 0.25 的權重。`nar_velocity` 標了 `@torch.no_grad()`，裡面的註釋寫明了訓練時怎麼把 `vae2llm(x_t)`、時間嵌入和幀位置嵌入打進全部 NAR 位置。那是聲學損失的規格說明，函式本身只服務推理。

預設採樣和論文的翻唱設定一致的部分：語義溫度 1.0、top-p 0.95、top-k 100、重複懲罰 1.2、窗口 50、最多 9,000 token；聲學 32 步 midpoint。樂譜階段更保守：溫度 0.7、top-p 0.9、top-k 30、重複懲罰 1.005、最多 4,096 token。`cot=full` 和 `melody` 的預設 CFG 是 1.0，`cot=off` 是 1.01。

`tests/` 在 CPU 上、不下載權重就能跑架構、協議、分塊和 artifact 完整性。`skills/yue2-music/` 是給 agent 用的生成、改譜、翻唱和器樂流程。`docs/` 是生成、硬體、benchmark、改譜和翻唱說明。官方支援的推理起點寫在 README：Linux、Python 3.12、支援 BF16 的 NVIDIA、24 GB 顯存。

## 和論文對不上、會卡住研究的地方

模型前向和推理協議是齊的。下面這些在論文裡是訓練系統的一部分，在這個倉裡沒有實作：

- 沒有 dataloader、任務混合、CFG dropout、分散式訓練和優化器配置。
- `forward()` 的交叉熵會算進整個序列。要對齊論文，得把 prompt 位置的 label 設成忽略，只監督樂譜與語義 span，再乘 0.25。
- Flow-matching 損失要另寫。訓練前向必須能對 `x_t` 反傳，不能走現在的 `no_grad` 解碼。
- 官方語義 tokenizer 沒有隨權重發布。`multimodal-art-projection/YuE` 的 issue #165 仍然開著，問的就是這件事。`YuE2VAE.encode()` 給的是連續聲學 latent `z`。公開的 `m-a-p/MERT-v2-FullSong` 是 SheetSage2 用的雙向 encoder，是因果 CVQ tokenizer 的另一條分支。
- 因此現在可以從新錄音得到歌詞、ABC（用 SheetSage2）和 latent `z`（用 VAE encoder）。對齊論文的語義標籤 `c` 仍然缺官方工具。社群有人用 MERT 特徵去近似這組 codebook，那是非官方近似，不能當成論文 tokenizer。

授權也要先定下來。倉庫代碼是 Apache-2.0。`YuE2-3B` 和兩個 VAE 權重是 CC BY-NC 4.0，另外允許個人創作者，以及非商業的學術研究。公司把權重拿去商用需要另談授權。分享微調後的權重仍然要署名。

## 三台機器怎麼分

這台電腦是 macOS。文件把 Apple Silicon 標成實驗路徑，原生整首歌的驗收仍然掛著。它適合讀 `protocol.py`、跑 `pytest`、改 ABC、設計訓練樣本格式，以及用縮小的 config 把 loss 寫對。

A100 有 BF16，和論文的數值格式一致。第一件實事是把 `examples/song.json` 跑通，留下 `score.abc`、`semantic.npy`、`latent.npy` 和 `audio.flac`。這份目錄就是以後 trainer 要對齊的契約。一張 A100 夠做推理，也夠開始 AR 側的 LoRA。3.58B 的全參微調還要再加上 Adam 狀態，需要分片，不適合單卡硬上。從零走完 106,000 次、batch 256 的更新，論文用的是 64 張 H800，不該當你的第一個實驗。

V100 是 Volta，沒有 BF16。它適合歌詞、段落、SheetSage2 和 VAE 編碼這類前處理，數值用 FP16 或 FP32。論文的 BF16 訓練和 NVIDIA FP8 AR 推理都不要排到 V100 上。

## 建議的開始順序

1. 在這台 Mac 上裝一個 CPU 環境，跑 `python -m pytest -q`。目標是確認協議和張量形狀，而不是在 Mac 上出歌。
2. 在 A100 上用 Python 3.12 執行 `pip install .`，再跑 `python examples/generate.py --output outputs/first-song`。聽 `YuE2-Vae`。只有在復現論文表格時才換 `YuE2-Vae-legacy`，並且用同一組 latent 解碼，避免把採樣噪聲算進解碼器差異。
3. 研究題先選現成 checkpoint 就能做的：`cot=full` 對 `cot=off` 的樂譜規劃、改 ABC 後整首重渲、以及 SheetSage2 樂譜加新風格的翻唱。這三條就是論文第 5 節的白盒接口，數據需求只是提示詞、歌詞和你有權使用的參考音頻。
4. 訓練代碼另開一個包，import 這個倉庫的 `YuE2ForCausalLM`，不要把推理發行版改成一套半成品 trainer。第一個訓練里程碑是 AR 交叉熵的 mask 和 0.25 權重。第二個才是 flow matching。語義標籤 `c` 在官方 tokenizer 出來之前，用你自己的錄音做「論文同款」監督會缺一截。在那之前，繼續訓練應優先使用模型自己生成、而且你檢查過的 `(文字, ABC, semantic id)`，或者只做樂譜與解碼控制實驗。

本次沒有更新任何文件。
