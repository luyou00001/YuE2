# A100 環境路徑要改成 .venv-yue2

上一組命令找的是 `/disk_1/projects/jzhao/RL_main/yue2`。那一層沒有 `pyvenv.cfg`、`bin/python` 和 `lib`，所以四條都是 `No such file or directory`。同事給的環境在它下面的 `.venv-yue2`。

在 A100 上只查看這個新路徑，仍然不要把目錄複製到 V100：

```bash
VENV=/disk_1/projects/jzhao/RL_main/yue2/.venv-yue2
sed -n '1,40p' "$VENV/pyvenv.cfg"
ls -l "$VENV/bin/python" "$VENV/bin/python3"
find "$VENV/lib" -path '*torch-*.dist-info/METADATA' -print
find "$VENV/lib" -path '*/torch/version.py' -print
```

如果 `pyvenv.cfg` 能印出來，再把上一步找到的兩個文件各看開頭：

```bash
sed -n '1,20p' 這裡換成METADATA的完整路徑
grep -E 'cuda|__version__' 這裡換成version.py的完整路徑
```

把這幾段文字貼回來。V100 驅動仍然是 535.183.01，在它升到 570 或更新之前，這個環境即使路徑正確也不能整份拿去 V100 運行。

本次沒有更新任何文件。
