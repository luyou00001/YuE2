# 五步輸出層更新和重新生成都完成了

訓練損失從 3.6250 降到 3.6094，第 3 步之後不再變化。新權重寫在 `/cache/yue2_ckpts/lmhead-city-lights`，`/cache/yue2_files/YuE2-3B` 沒有被改。接著用這份權重生成了完整的一首歌：樂譜 513 個 token，語義 1522 個 token，60.8 秒音頻，耗時 125.6 秒，沒有截斷。MP3 已寫出：

`/cache/yue2_outputs/lmhead-city-lights/city_lights/audio.mp3`

請把它和原來的 `outputs/first-song/city_lights/audio.flac` 對聽。損失只降了 0.016，而且只動了輸出層，聽感應該和原版非常接近。若幾乎一樣，就說明存檔、重新載入和生成這條鏈是通的。`torch_dtype` 和 `weight_norm` 仍是警告，不是失敗。

這個 checkpoint 到此為止。不要再對它加步數，也不要把它當成新的基模。它只記住了 65 個 token。之後的續訓仍從 `/cache/yue2_files/YuE2-3B` 開始，結果繼續另存。

V100 上現在已經證明三件事：原模型能出歌、損失能反傳、改過的權重能再出歌。下一步不是繼續這個過擬合。下一步是用多條固定提示詞做聽感對照，每次只改一種訓練設定，並和原模型比。在有新的歌曲數據和語義 token 之前，不再增加訓練步數。

本次沒有更新任何文件。
