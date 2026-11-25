# 這份 log，以及 A100 的 venv 能不能拷過來

V100 現在沒有能用的下載通道。`~/.condarc` 裡有一個指向內網 `10.155.168.114:8080` 的代理，而且帶著帳號密碼；上次 `conda create` 已經因為這個代理失敗。直接訪問 PyPI 也失敗，錯誤是 `Errno 99: Cannot assign requested address`。shell 裡的 `http_proxy` 是空的，所以 pip 不會自動走那個代理。這台機器目前既不能 conda 下載，也不能直接 pip 下載。

`public/log.txt` 裡有這組代理密碼。不要把這個文件提交到 git，並盡快更換該密碼。

A100 上 `/disk_1/projects/jzhao/RL_main/yue2` 這個 venv 不要整份複製到 V100 來運行。venv 裡的 Python 路徑是絕對路徑，複製後解釋器通常對不上。能跑通 YuE2 的環境使用的是專案固定的 torch 2.10，默認 CUDA 12.8 輪子需要大約 570 的驅動；V100 的驅動是 535.183.01，只支援到 CUDA 12.2。文件拷過來之後，`import torch` 仍然會報驅動太舊。

需要看的是版本，不是把整個目錄搬過來。A100 只能看文件的話，把下面這些內容貼回來：

```bash
VENV=/disk_1/projects/jzhao/RL_main/yue2
sed -n '1,40p' "$VENV/pyvenv.cfg"
ls -l "$VENV/bin/python" "$VENV/bin/python3"
find "$VENV/lib" -path '*torch-*.dist-info/METADATA' -print
find "$VENV/lib" -path '*/torch/version.py' -print
```

找到 `METADATA` 和 `version.py` 之後，再各看開頭：

```bash
sed -n '1,20p' 這裡換成上一步印出的METADATA路徑
grep -E 'cuda|__version__' 這裡換成上一步印出的version.py路徑
```

這些文字足以判斷那個環境的 Python 和 CUDA 版本。在 V100 驅動升到 570 或更新之前，不複製這個 venv，也不在 V100 上安裝 torch 2.10。

本次沒有更新任何文件。
