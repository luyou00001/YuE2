# 從 YuE2-3B 續訓，不要從頭訓練

基模是已經在 V100 上跑通的 `YuE2-3B`，本地路徑 `/cache/yue2_files/YuE2-3B`。它是約 3.58B 的 AR–NAR 歌曲模型。`/cache/yue2_files/YuE2-Vae` 只負責把 latent 解成波形，續訓時保持凍結，不把它當基模。

不要從頭訓練。論文裡的從零開始是 64 張 H800、約 34.6 萬小時音頻、10.6 萬次更新。這台機器是 8 張 V100 32GB，沒有原生 BF16。從頭訓既裝不下論文的 batch，也會丟掉現在已經聽起來正常的歌曲能力。續訓的起點就是這份 checkpoint。

官方語義 tokenizer 確實沒有。所以現在不能從新錄音做出論文裡的語義 token `c`。已經生成的歌曲目錄裡有 `prefix.npy` 和 `semantic.npy`，可以先用來檢查訓練代碼會不會算損失、會不會反傳。這只證明訓練迴圈，不代表已經有新數據。

倉庫裡加了 `public/train_loss_check.py`。它載入 YuE2-3B，用一首已生成歌曲的前 64 個語義 token 算自迴歸交叉熵，做一次 backward，然後明確不存檔、不改權重。在 V100 上：

```bash
conda activate PyTorch-2.0.0
cd /home/ma-user/work/YuE2
git pull
CUDA_VISIBLE_DEVICES=0 PYTHONPATH=src python public/train_loss_check.py \
  --song outputs/first-song/city_lights \
  --model /cache/yue2_files/YuE2-3B
```

成功時會印出有限的 `ar_loss` 和 `lm_head_grad_finite=True`，以及 `no weights were updated or saved`。若顯存不夠，把 `--max-semantic` 改成 `16`。不要執行 `pip install .` 或 `pip install torch`。

損失下降本身不能判斷好聽。在 V100 上用同一套聽覺對照：

1. 留著未改過的 `/cache/yue2_files/YuE2-3B`，任何續訓都另存目錄。
2. 固定 4 到 8 條提示詞和 seed。每次只改訓練步數，其餘用現在這套 `torch-eager` 推理。
3. 未訓練和訓練後的歌放進 `/cache/yue2_outputs/` 的不同子目錄，比歌詞是否還在、結構是否完整、有沒有新增噪聲或反覆同一句。
4. 訓練後若明顯比第 0 步的原 checkpoint 差，就停，不要因為 loss 變小而繼續。
5. 一張卡先跑通這個損失檢查。8 張卡以後做資料並行的小學習率續訓，不把一個 3.58B 模型切到 8 張卡上從頭訓。

全參 Adam 狀態放不進 32GB。損失檢查通過之後，下一步才是只更新一小部分 AR 權重的續訓，然後按上面的聽感對照決定好不好。聲學 flow matching 和真正的新數據還要另做；在語義 tokenizer 出現之前，不要把新錄音直接當成完整的 `s, c, z` 監督。

本次更新的文件：`public/train_loss_check.py`
