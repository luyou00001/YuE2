# SheetSage2 環境檢查結果

腳本裡的 `present` 只代表這個名字能 import，不代表版本符合 `requirements.txt`。目前環境是 Python 3.9.11、torch 2.3.1+cu121、torchaudio 2.3.1+cu121、transformers 4.57.6、numpy 1.23.5。這些都留著，不要執行 `pip install -r requirements.txt`，那會去裝 torch 2.8，把現在能跑 YuE2 的 CUDA 12.1 換掉。

真正缺的只有兩個包：`mir_eval` 和 `pretty_midi`。用 `--no-deps` 安裝，避免 pip 順手升級 numpy 或 torch。

```bash
python -m pip install mir_eval==0.8.2 pretty_midi==0.2.10 --no-deps
python -c "import mir_eval, pretty_midi; print('imports ok')"
```

SheetSage2 目錄裡有權重文件。MERT-v2-FullSong 只有 `config.json`，頂層沒有 `.safetensors` 或 `.bin`。完整權重應是這兩個檔，大小必須完全一致：

- `/cache/yue2_files/SheetSage2/model.safetensors`：228738564 bytes
- `/cache/yue2_files/MERT-v2-FullSong/model.safetensors`：2529812848 bytes

先印出實際大小。若 MERT 那個檔不在、或只有一百多 bytes 的 Git LFS 指標，請把 2.53 GB 的 `model.safetensors` 再傳到上面那個路徑。

```bash
python -c "from pathlib import Path
for root in (Path('/cache/yue2_files/SheetSage2'), Path('/cache/yue2_files/MERT-v2-FullSong')):
    print('DIR', root)
    found=False
    for p in root.rglob('*'):
        if p.is_file() and (p.suffix in ('.safetensors','.bin') or p.stat().st_size>1000000):
            print(p, p.stat().st_size); found=True
    if not found: print('no weight file')"
```

兩個包裝好、兩個 safetensors 大小正確之後，把這段輸出貼回來，再跑第一首轉譜。

本次更新的文件：無（只根據 `public/log.txt` 解讀，沒有改源碼）。
