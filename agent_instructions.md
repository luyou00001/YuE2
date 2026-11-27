# 生成命令改走 yue2.cli

報錯是 `No module named yue2.__main__`。這台環境沒有安裝 yue2 套件，`python -m yue2` 在讀模型和譜之前就退出了。輸出目錄沒有寫入。改用源碼裡的命令列入口，其他參數不變。

```bash
PYTHONPATH=src python -m yue2.cli generate --model /cache/yue2_files/YuE2-3B --vae /cache/yue2_files/YuE2-Vae --backend torch-eager --budget 30 --offline --request public/full_mix_000.json --abc-file /cache/yue2_outputs/full_mix/000/score/score.abc --output /cache/yue2_outputs/full_mix_000_cover
```

整首歌可能要數分鐘。把終端最後一行 JSON 貼回來。歌詞仍是空的段落標籤，聽的時候只比較旋律、和弦和段落。

本次更新的文件：`src/yue2/__main__.py`
