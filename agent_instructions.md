# 伴奏在 S3 上，這台機器還沒有下載客戶端

第一條 `mix_path` 是 `s3://ttsingnorth/AI_Music_Data_vUltra/5sing/track_5_mp3/5_track_inst/` 下的一個 `.mp3`。`which rclone aws s3cmd` 沒有輸出，這三個程式都不在 PATH 裡。所以現在還讀不到這首伴奏，不能抽 VAE latent。

先不要安裝新套件。查這台 V100 上是否已經有其他客戶端，並只報告環境變數有沒有設定，不印出內容：

```bash
python -c 'import importlib.util; mods=["boto3","obs"];
[print(name, "yes" if importlib.util.find_spec(name) else "no") for name in mods]' 
command -v obsutil mc s3fs || true
python - << 'PY'
import os
for key in ("AWS_ACCESS_KEY_ID","AWS_SECRET_ACCESS_KEY","AWS_ENDPOINT_URL","S3_ENDPOINT","OBS_ENDPOINT"):
    print(f"{key}={'set' if os.environ.get(key) else 'unset'}")
PY
```

把這幾行貼回來。有 `boto3` 或 `obsutil`，再試下載這一首 mp3。三個都沒有，而且相關環境變數都是 `unset`，這台機器目前就沒有讀那個桶的條件。

本次沒有更新任何文件。
