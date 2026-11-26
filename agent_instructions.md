# 180 萬索引改讀 YuE2 這份副本

YuE2 要用的索引已經改到 `/cache/yue2_files/datasets/acctask-180w-acc-caption-cfgs`。舊 NAR 配置 `/cache/l00956912/datasets/acctask-180w-acc-caption-cfgs` 沒有改。

運行腳本是 `public/check_180w_index.sh`。它只列出 `pt_all_v1.txt`、`vocal_wav_all.txt`、`wav2len.txt` 和第一個 `200w*.txt` 的欄位名，不打開音頻，也不訓練。

```bash
bash public/check_180w_index.sh
```

把完整輸出貼回來。確認索引還在之後，才從這份副本抽混合音頻的 VAE latent。

本次更新的文件：`public/check_180w_index.sh`
