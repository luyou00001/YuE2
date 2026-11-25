# 輸出改到 /cache/yue2_outputs，並額外保存 MP3

V100 這次已經完整生成：樂譜 513 個 token、語義 1474 個 token、聲學 32 步，58.9 秒音頻用了 125.8 秒。聽感和 A100 一致，所以現在的推理配方可以固定下來：`PyTorch-2.0.0`、Python 3.9.11、`torch 2.3.1+cu121`、`--backend torch-eager`、本地權重 `/cache/yue2_files`。不要在這個環境執行 `pip install .` 或 `pip install torch`。

之後不帶 `--output` 時，歌曲寫到 `/cache/yue2_outputs/<歌曲 id>/`。`examples/song.json` 的 id 是 `city_lights`，所以目錄是 `/cache/yue2_outputs/city_lights/`。裡面仍然保留完整的 `audio.flac`、樂譜、token 和 latent。若系統有 `ffmpeg`，會再寫一份較小的 `audio.mp3` 用來試聽。沒有 `ffmpeg` 時 FLAC 照常保存，終端裡的 `mp3` 為 `null`。

在 V100 上更新代碼後這樣跑：

```bash
conda activate PyTorch-2.0.0
cd /home/ma-user/work/YuE2
git pull
which ffmpeg
CUDA_VISIBLE_DEVICES=0 PYTHONPATH=src python -m yue2.cli generate \
  --request examples/song.json \
  --model /cache/yue2_files/YuE2-3B \
  --vae /cache/yue2_files/YuE2-Vae \
  --offline --device cuda --backend torch-eager --budget 30
```

不要再加 `--output outputs/first-song`。完成後看 `/cache/yue2_outputs/city_lights/audio.mp3`。若 `which ffmpeg` 沒有輸出，先讓管理員安裝 ffmpeg，不必改 Python 環境。

推理這條已經跑通。下一步不要開始訓練。先用這台 8 卡機器做聽感對照：每張卡一個進程，分別跑 `cot=full`、`cot=off`，以及改過的 ABC 再渲染。每個任務用不同的 `--output /cache/yue2_outputs/實驗名`，避免寫進同一個 `city_lights` 目錄。訓練要等官方語義 tokenizer，或者另寫訓練代碼；這不是當前這張 V100 上的下一步。

本次更新的文件：`src/yue2/pipeline.py`、`src/yue2/cli.py`
