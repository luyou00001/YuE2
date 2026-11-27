完成，Suno 數據已下載到 suno_100/。
結果
來源：/hdd/hdd_1/jzhao/wav/
- suno_wav（原始混音）、suno_bgm（伴奏）、suno_vocal（人聲），全部是 mp3（副檔名為 .mp3，非 .wav）
- 全量：suno_wav 118,682 檔 ≈ 12w 首（每首 2 個 track），三目錄共有 89,869 個同名檔
已抽取 100 首（每首含 track 0/1，三目錄各 200 檔，共 600 個 mp3）：
suno_100\
├── suno_wav\          200 個 mp3 (897 MB)
├── suno_bgm\          200 個 mp3 (966 MB)
├── suno_vocal\        200 個 mp3 (966 MB)
├── train_cn.jsonl     完整資訊檔 (476 MB, 49,516 行)
└── selected_song_ids.txt   這 100 首的 song_id 清單
挑選方式：從 train_cn.jsonl 有歌詞資訊的歌曲中，取前 100 首「三目錄 + 兩個 track 都存在」的歌，確保 wav/bgm/vocal 完全配對。
驗證：抽樣檔案 md5 與遠端一致（7fd51f59...），tar 串流 exit=0，600 檔全數解出。
補充說明
- 歌詞在 jsonl 裡：train_cn.jsonl 每行含 song_id、track_index、style、sections（每段有 text 歌詞欄位）、audio_path、style_sim。沒有獨立的 .lrc/.txt 歌詞檔。
- 該 jsonl 涵蓋 24,875 首（每首 2 track，共 49,516 行），其中 100 首已下載音檔；若要「100 首的子集 jsonl」，之後可用 selected_song_ids.txt 過濾。
- suno_vocal/wav_to_mp3_failures.json 顯示有 56,208 個 vocal 轉檔失敗紀錄（ffmpeg 格式問題），不影響本次抽取的檔案。
- 伺服器全程只讀，未做任何寫入。
