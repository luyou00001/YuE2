# A100 環境版本已經確認

`.venv-yue2` 的內容是：

- Python 3.12.11，解釋器在 `/disk_1/projects/jzhao/RL_main/yue2/runtime/yue2/python/cpython-3.12.11-linux-x86_64-gnu/bin/python3.12`
- 由 uv 0.8.22 建立
- PyTorch 目錄名是 `torch-2.10.0+cu128.dist-info`，也就是 torch 2.10.0 的 CUDA 12.8 輪子

這和 YuE2 專案固定的版本一致，也解釋了它為什麼能在 A100 上跑。CUDA 12.8 需要大約 570 的 NVIDIA 驅動。V100 的驅動是 535.183.01，`nvidia-smi` 顯示只支援到 CUDA 12.2。把 `.venv-yue2` 和旁邊的 `cpython-3.12.11` 複製到 V100 之後，Python 也許能啟動，但 `import torch` 使用 CUDA 時會報驅動太舊。所以現在不要複製。

`METADATA` 和 `version.py` 不用再看，目錄名已經寫明 `2.10.0+cu128`。

下一步只有一件事：請管理員把 V100 的 NVIDIA 驅動升到 570 或更新。升完之後在 V100 上重新執行 `nvidia-smi`，把驅動版本和其中的 CUDA Version 貼回來。驅動還沒升之前，不在 V100 上安裝 torch 2.10，也不複製這個虛擬環境。

本次沒有更新任何文件。
