# 先用 PyTorch-2.0.0 做一次真實載入

可以，而且應該先用 V100 上現有的 `PyTorch-2.0.0` 環境試。這個環境已經確認是 Python 3.9.11 和 `torch 2.3.1+cu121`，CUDA 可用。不要在這個環境執行 `pip install .` 或 `pip install torch`。那兩條會把現在能用的 CUDA 12.1 版 torch 換成 CUDA 12.8 的 torch 2.10，驅動 535 載入不了。

倉庫裡加了 `public/probe_existing_env.py`。它不安裝任何套件，只把本地權重載進 GPU，並對兩個 token 做一次前向。在 V100 上先更新代碼，再執行：

```bash
conda activate PyTorch-2.0.0
cd /home/ma-user/work/YuE2
git pull
CUDA_VISIBLE_DEVICES=0 python public/probe_existing_env.py
```

把終端完整輸出貼回來。三種結果的含義不同：

- 印出某個套件 `MISSING`：這個環境還沒有 transformers、safetensors 或 numpy。先停在這裡，不要自行安裝 torch。
- 載入權重後在 `scaled_dot_product_attention` 或 `enable_gqa` 報錯：torch 2.3.1 的注意力介面和這份代碼不一致。這是代碼要改的點，不是驅動問題。
- 印出 `forward_ok`：這張 V100 用現有 torch 已經能算一小步。下一步才是接上整首歌的生成流程。

這次只改了探測腳本，沒有改模型。

本次更新的文件：`public/probe_existing_env.py`
