# 180 萬索引在，欄位包在 v 裡面

`pt_all_v1.txt` 有 1,833,083 行。`vocal_wav_all.txt` 和 `wav2len.txt` 都在 `/cache/yue2_files/datasets/acctask-180w-acc-caption-cfgs`。`200w-001.txt` 的外層只有 `k` 和 `v`。舊 NAR 讀法是把 `v` 當成真正的歌曲記錄，裡面才可能有 `mix_path`。

檢查腳本已改成印出 `v` 裡面的欄位名，仍然不印路徑、不打開音頻。

```bash
bash public/check_180w_index.sh
```

把新的 `record_keys` 貼回來。有 `mix_path` 才能接著對人聲和伴奏；沒有的話，這份副本還缺伴奏路徑，不能抽 VAE latent。

本次更新的文件：`public/check_180w_index.sh`
