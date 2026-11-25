# 目前這份 log 說明了什麼

機器本身可以用來做單卡推理：8 張 Tesla V100-PCIE-32GB，都空閒，每張 32768 MiB。顯存夠，`--budget 30` 適合，第一首歌只用第 0 張卡。

現在還不能安裝 torch 2.10，也不能繼續 `conda create`。

驅動是 `535.183.01`，`nvidia-smi` 顯示的 CUDA 版本是 12.2。默認 `pip install torch==2.10.0` 裝的是 CUDA 12.8 輪子，這個輪子需要大約 570 的驅動。在 535 上裝完後，`import torch` 會報驅動太舊，CUDA 用不起來。所以先不要執行上一份說明裡的 `pip install torch==2.10.0` 和 `pip install .`。

`conda create -n yue2 python=3.12 -y` 失敗是代理錯誤 `ProxyError`，不是顯卡問題。base 環境是 Python 3.9，低於 YuE2 要求的 3.10，不能拿來裝這個專案。

請在同一台機器上只收集下面這些資訊，先不要裝 torch：

```bash
echo "http_proxy=$http_proxy"
echo "https_proxy=$https_proxy"
echo "HTTP_PROXY=$HTTP_PROXY"
echo "HTTPS_PROXY=$HTTPS_PROXY"
conda env list
python3 --version
command -v python3.10; command -v python3.11; command -v python3.12
conda activate PyTorch-2.0.0
python -V
python -c "import torch; print(torch.__version__, torch.version.cuda, torch.cuda.is_available())"
```

把完整輸出貼回來。

若管理員能把 NVIDIA 驅動升到 570 或更新，升完再回到 conda 或 pip 安裝，那是和專案固定的 torch 2.10 匹配的路。驅動不能升的話，官方這個版本的輪子在這台機器上跑不起 CUDA，下一步才是改用驅動 535 能載入的舊版 CUDA 輪子，並檢查代碼能不能在那個 torch 上運行。

本次沒有更新任何文件。
