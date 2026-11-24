# 現有代碼能不能重啟訓練

要重啟訓練，需要開發訓練代碼。現在的倉庫不具備一套可以跑起來的訓練系統。

它具備的是推理，外加一個可以反傳的模型前向。`YuE2ForCausalLM` 的結構和 `m-a-p/YuE2-3B` 權重相容，可以直接載入。`forward(labels=...)` 會對整個序列做移位交叉熵，`tests/test_model.py` 證明這條損失可以 `backward()`。論文要的 span 遮罩、0.25 權重、flow-matching 損失、數據讀取、四任務混合和分散式訓練都沒有。`nar_velocity` 標了 `@torch.no_grad()`，只負責推理時用 32 步 midpoint 解常微分方程。註釋裡寫了訓練時怎麼把 `vae2llm(x_t)`、時間嵌入和幀位置嵌入打進 NAR 位置，那是規格，不是訓練迴圈。

因此：模型定義可以復用，trainer 要新寫。

中文對照已更新在 [YuE2 研究地圖](/Users/hkrc_music/.cursor/projects/Users-hkrc-music-YuE2/canvases/yue2-research-map.canvas.tsx)。

## 已經有、可以接著用的部分

- 28 層 AR–NAR Mixture-of-Transformers，參數名與公開權重一致。
- token 契約、三種 `cot`、採樣和 CFG，在 `protocol.py` 與 `pipeline.py`。
- VAE 的編碼器和解碼器。`encode()` 產出的是 25 Hz × 64 的聲學 latent `z`。
- `supports_gradient_checkpointing = True`，之後寫 trainer 時可以開梯度檢查點。

## 必須新寫的部分

1. AR 損失。把 prompt 位置的 label 設成忽略，只監督樂譜和語義 span 以及它們的結束符，再乘 0.25。現在的交叉熵會把提示詞也算進去。
2. 聲學損失。`z_t = (1-t) z_0 + t ε`，速度目標是 `ε - z_0`，並且要能對 `x_t` 反傳。不能走現在的 `no_grad` 解碼。
3. 數據。整首打包進 24,576 context，四個任務等比例混合，文字和歌詞可丟棄以支援 CFG。倉庫裡沒有 dataloader。
4. 優化與並行。論文是 BF16、全域 batch 256、梯度裁剪 1.0、64 張 H800，分三段共 106,000 次更新。這些配置不存在。
5. 語義標籤 `c`。官方 32,768 類 CVQ tokenizer 沒有發布，上游 issue #165 仍開著。公開的 MERT-v2-FullSong 是 SheetSage2 用的雙向編碼器，不是這條因果 tokenizer。沒有它，就不能從新錄音打出論文同款的語義 id。

## 實際怎麼開工

訓練包與 `yue2-infer` 分開，import `YuE2ForCausalLM`。起點用現成的 `m-a-p/YuE2-3B`，不要從零復現那 64 張 H800 的預訓練。一張 A100 可以先做 AR 側 LoRA，前提是序列裡已經有合法的文字、ABC 和語義 id。全參微調還要加上 Adam 狀態，需要分片。V100 沒有 BF16，留作資料前處理。

在官方 tokenizer 出來之前，用自己的錄音對齊論文裡的 `c` 會缺工具。這段時間能做的訓練，是模型自己生成、而且你檢查過的 `(文字, ABC, semantic id)` 上的繼續訓練，或者先把 AR 損失寫對。

本次沒有更新任何文件。
