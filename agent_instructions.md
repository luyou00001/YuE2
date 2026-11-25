# V100 探測結果和下一步

`public/log.txt` 已經說明三件事：權重在 `/cache/yue2_files/YuE2-3B`、`YuE2-Vae`、`YuE2-Vae-legacy`；GPU 計算能力是 `(7, 0)`；目前 shell 是 `(PyTorch-2.0.0)`。`including_emulation` 是較新 PyTorch 才有的參數，所以 TypeError 只代表探測腳本和這個舊環境不匹配，不代表要改 YuE2。

下一步離開該 conda 環境，用 Python 3.12 安裝專案固定的 torch 2.10。先確認驅動和一次 BF16 矩陣乘法，再裝包、跑 `yue2 doctor`，最後用 `--backend torch-eager --low-vram` 生成。不要用 vLLM 或 FP8。

本次沒有更新任何文件。
