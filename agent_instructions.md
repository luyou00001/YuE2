# 權重已經在 V100 上載入，前向卡在一個 torch 2.3 沒有的函數

`PyTorch-2.0.0` 這次的結果是：

- Python 3.9.11，`torch 2.3.1+cu121`，CUDA 可用
- GPU 是 Tesla V100-PCIE-32GB，計算能力 `(7, 0)`，顯存 31.7 GiB
- `transformers 4.57.6`、`safetensors 0.4.3`、`numpy 1.23.5` 都在，足夠把 `/cache/yue2_files/YuE2-3B` 載入 GPU
- `torch_dtype is deprecated` 只是警告，不是失敗原因
- 真正的錯誤是 `torch.backends.cuda` 沒有 `is_flash_attention_available`。這個函數在 torch 2.3.1 裡不存在，前向在第一層注意力停下

代碼已改成：沒有這個函數時就當作 FlashAttention 不可用，並把分組的 KV 頭展開後再做普通注意力。torch 2.3.1 的 `scaled_dot_product_attention` 如果也不接受 `enable_gqa`，就不再傳這個參數。新版 torch 上的原有行為保持不變。

在 V100 上更新後重跑同一條探測，仍然不要 `pip install .` 或 `pip install torch`：

```bash
conda activate PyTorch-2.0.0
cd /home/ma-user/work/YuE2
git pull
CUDA_VISIBLE_DEVICES=0 python public/probe_existing_env.py
```

把完整輸出貼回來。若印出 `forward_ok`，這張 V100 用現有環境已經能算模型前向，下一步再接整首歌生成。若是新的報錯，用那一段繼續改。

本次更新的文件：`src/yue2/modeling_yue2.py`、`src/yue2/cuda_graph.py`
