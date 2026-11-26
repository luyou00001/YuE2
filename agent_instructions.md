# 損失反傳已經通過

這次檢查成功。707 個 token 裡，前 642 個是條件，65 個被計入損失。`ar_loss=3.6250`，對應的 0.25 加權值是 0.9062。`lm_head` 的梯度有限，範數 5.3195。最後一行確認權重沒有被改動。

3.625 是原模型在自己生成出的 token 上的交叉熵。184704 類若完全隨機，交叉熵約是 12.1，所以這個數字只說明原 checkpoint 仍然認得這些 token。它不是音質分數，也不能用來決定訓練好不好。

下一步做一個分開存放的過擬合測試：只更新輸出層 5 步，存到 `/cache/yue2_ckpts/lmhead-city-lights`，原目錄 `/cache/yue2_files/YuE2-3B` 不會被寫入。

```bash
CUDA_VISIBLE_DEVICES=0 PYTHONPATH=src python public/train_lm_head_steps.py \
  --song outputs/first-song/city_lights \
  --model /cache/yue2_files/YuE2-3B \
  --output /cache/yue2_ckpts/lmhead-city-lights
```

然後用新權重生成同一首歌，和原來的 `outputs/first-song/city_lights/audio.flac` 對聽：

```bash
CUDA_VISIBLE_DEVICES=0 PYTHONPATH=src python -m yue2.cli generate \
  --request examples/song.json \
  --model /cache/yue2_ckpts/lmhead-city-lights \
  --vae /cache/yue2_files/YuE2-Vae \
  --offline --device cuda --backend torch-eager --budget 30 \
  --output /cache/yue2_outputs/lmhead-city-lights
```

這 5 步只記住這一小段 token。同一首歌的 loss 應該下降；其他提示詞變差是正常的，說明訓練迴圈生效，不說明模型變好。對聽之後就停。若新歌比原 checkpoint 差，繼續使用 `/cache/yue2_files/YuE2-3B`，不要拿這個過擬合權重當新基模。

本次更新的文件：`public/train_lm_head_steps.py`
