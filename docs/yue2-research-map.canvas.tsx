import {
  BarChart,
  Callout,
  Divider,
  Grid,
  H1,
  H2,
  H3,
  Stack,
  Stat,
  Table,
  Text,
} from "cursor/canvas";

export default function Yue2ResearchMap() {
  return (
    <Stack gap={24}>
      <Stack gap={8}>
        <H1>YuE2 研究地圖</H1>
        <Text tone="secondary">
          這個倉庫是公開推理包 yue2-infer 0.1.6。模型結構和技術報告對得上。訓練迴圈、約 34.6 萬小時語料，以及官方語義 tokenizer，都不在倉庫裡。要重啟訓練，需要另外開發訓練代碼。
        </Text>
      </Stack>

      <Grid columns={4} gap={16}>
        <Stat value="3.58B" label="論文參數量" />
        <Stat value="28 × 2048" label="層數 × 隱藏寬度" />
        <Stat value="24,576" label="上下文長度（位置）" />
        <Stat value="只有推理" label="這個倉庫已實現的部分" tone="warning" />
      </Grid>

      <Callout tone="warning" title="現有代碼不能直接開訓">
        forward() 能算一條普通的因果交叉熵，測試裡也證明損失可以反傳。這還不是訓練系統。論文的 span 遮罩、0.25 權重、flow-matching 損失、數據讀取、四任務混合和分散式訓練都要新寫。nar_velocity 標了 no_grad，只負責推理時解常微分方程。
      </Callout>

      <Stack gap={8}>
        <H2>重啟訓練時，代碼裡已經有什麼</H2>
        <Table
          headers={["訓練所需", "現況", "要不要新寫"]}
          rows={[
            [
              "模型結構 YuE2ForCausalLM",
              "28 層 AR–NAR，參數名與權重相容，可載入 m-a-p/YuE2-3B",
              "可直接 import，不必重寫結構",
            ],
            [
              "自迴歸交叉熵",
              "forward(labels=...) 對整個序列做移位交叉熵，沒有忽略 prompt",
              "要加上論文的 span 遮罩，再乘 0.25",
            ],
            [
              "聲學 flow matching",
              "推理側有 32 步 midpoint。訓練注入方式只寫在 nar_velocity 的註釋裡",
              "要新寫可反傳的速度場損失",
            ],
            [
              "數據與四個任務",
              "推理有 cot=full / melody / off。沒有資料集、打包和任務採樣",
              "要新寫",
            ],
            [
              "優化器與分散式",
              "沒有 trainer、沒有 DeepSpeed / FSDP 配置",
              "要新寫。論文用 64 張 H800、batch 256、BF16",
            ],
            [
              "新錄音的語義標籤 c",
              "官方 32,768 類 CVQ tokenizer 未發布。VAE.encode 只產出 latent z",
              "缺官方工具。不能靠現有代碼從音頻打出 c",
            ],
          ]}
          rowTone={["success", "warning", "danger", "danger", "danger", "danger"]}
          striped
        />
        <Text size="small" tone="tertiary">
          依據：src/yue2/modeling_yue2.py 的 forward 與 nar_velocity，tests/test_model.py 的反傳測試，以及上游 issue #165。
        </Text>
      </Stack>

      <Stack gap={8}>
        <H2>一首歌怎麼生成</H2>
        <Text tone="secondary">
          論文裡的分解：p(s, c, z | y) = p_AR(s, c | y) × p_NAR(z | y, s, c)。創作、改譜、翻唱共用同一個權重，差別只在樂譜從哪裡來。
        </Text>
        <Table
          headers={["階段", "介面", "確定下來的內容", "速率"]}
          columnAlign={["left", "left", "left", "right"]}
          rows={[
            ["文字與歌詞 y", "SongRequest", "風格、段落標記、演唱歌詞", "提示詞"],
            ["樂譜 s", "pipeline.plan", "ABC 旋律、和弦、調性、拍號、曲式", "BPE 文字 token"],
            ["語義 c", "generate_semantic", "離散的音樂軌跡", "25 Hz，32,768 類"],
            ["潛變量 z", "synthesize", "flow matching，32 步 midpoint", "25 Hz × 64"],
            ["波形 x", "decode", "Oobleck VAE 解出的立體聲", "48 kHz"],
          ]}
          rowTone={["neutral", "info", "info", "success", "success"]}
        />
        <Text size="small" tone="tertiary">
          token 契約在 src/yue2/protocol.py：EOD 151643，ABC 151847–151848，音樂 151851–151852，codec 起點 151853，latent 標記 184621–184623，詞表大小 184704。
        </Text>
      </Stack>

      <Stack gap={8}>
        <H2>WildSongBench 的 SongBench 總分</H2>
        <Text tone="secondary">
          越高越好。數值是 SongBench Global Avg，沒有物理單位。兩條 YuE2 都使用符號樂譜規劃和 legacy VAE。
        </Text>
        <BarChart
          horizontal
          beginAtZero={false}
          yMin={4}
          yMax={7.2}
          height={280}
          categories={[
            "YuE2 八選一",
            "Mureka 9",
            "Suno v5",
            "YuE2（兩個候選）",
            "Suno v4.5",
            "HeartMuLa",
            "YuE 1",
          ]}
          series={[
            {
              name: "SongBench 總分",
              tone: "info",
              data: [6.9632, 6.9377, 6.8721, 6.7316, 6.6995, 6.2483, 4.9165],
            },
          ]}
        />
        <Text size="small" tone="tertiary">
          來源：docs/benchmarks.md，192 條提示，記錄於 2026-09-12。標準設定在兩個候選中保留音素錯誤率較低的一條。八選一先看 Musicality，再看提示對齊，再看音素錯誤率。頂部差距是描述性數字，論文沒有做顯著性檢驗。
        </Text>
      </Stack>

      <Stack gap={8}>
        <H2>論文有、這個倉庫沒有</H2>
        <Table
          headers={["組成", "論文", "這個倉庫"]}
          rows={[
            [
              "AR–NAR Mixture-of-Transformers",
              "28 層。歸一化、QKV、輸出投影和 MLP 各有 AR / NAR 兩套，注意力計算共享",
              "已寫在 modeling_yue2.py，參數名與 checkpoint 相容",
            ],
            [
              "混合注意力",
              "AR 查詢是因果的，而且看不到 latent。NAR 查詢看得到全部計劃和全部 latent",
              "nar_velocity 裡有。generate() 只走因果 AR",
            ],
            [
              "損失",
              "樂譜和語義 span 的交叉熵乘 0.25，再加上 latent 的 flow matching",
              "forward() 是不帶權重的全序列交叉熵。沒有 flow-matching 損失",
            ],
            [
              "四個訓練任務",
              "完整規劃、去掉樂譜、去掉語義 token、文字直接到音頻，等比例混合",
              "推理有 cot=full、melody、off。沒有任務採樣器",
            ],
            [
              "聲學目標 z",
              "Oobleck VAE。48 kHz 立體聲壓縮 1920 倍，得到 25 Hz、64 維",
              "modeling_vae.py 有編碼器和解碼器。聽歌時管線只載入解碼器",
            ],
            [
              "語義目標 c",
              "因果 MERT2，CVQ 碼本 32,768，約 375 bit/s",
              "未隨倉庫發布。公開的 MERT-v2-FullSong 是 SheetSage2 用的雙向編碼器",
            ],
            [
              "符號目標 s",
              "SheetSage2-AR，約 28,400 小時轉譜標籤，再編成 ABC",
              "轉譜是另一個 Hugging Face 模型。這個倉庫只接收 ABC 文字",
            ],
            [
              "優化",
              "BF16，全域 batch 256，64 張 H800。AR 6 萬步，聯合 4 萬步，退火 6 千步",
              "沒有 trainer、dataloader 或分散式配置",
            ],
          ]}
          rowTone={[
            "success",
            "success",
            "warning",
            "warning",
            "info",
            "danger",
            "info",
            "danger",
          ]}
          striped
        />
      </Stack>

      <Stack gap={8}>
        <H2>若要對齊論文，訓練配方是這些</H2>
        <Text>
          附錄 C。聯合訓練開始時，把 NAR 專家從對應的 AR 專家拷貝過來，並重置優化器。退火階段沿用聯合訓練的優化器狀態。歌曲整首打包，一首歌不切到兩個樣本裡。
        </Text>
        <Table
          headers={["階段", "更新數", "上下文", "學習率", "Adam"]}
          columnAlign={["left", "right", "right", "left", "left"]}
          rows={[
            [
              "從零開始的 AR 預訓練",
              "60,000",
              "16,384",
              "5,000 步升到 1e-4，餘弦底 1e-5，終點對準第 95,000 步",
              "β (0.9, 0.98)，weight decay 0.05",
            ],
            [
              "聯合 AR–NAR",
              "40,000",
              "24,576",
              "5,000 步升到 3e-4，餘弦底 1e-4，終點對準第 150,000 步",
              "β (0.9, 0.95)，weight decay 0.1",
            ],
            [
              "退火",
              "6,000",
              "24,576",
              "沒有 warmup。從約 2.726e-4 餘弦降到 3e-5",
              "與聯合階段相同",
            ],
          ]}
        />
        <Text size="small" tone="tertiary">
          來源：YuE2 技術報告附錄 C，表 13–15。三個階段都是 bfloat16、全域 batch 256、梯度裁剪 1.0、64 張 H800。聯合損失 L = 0.25 L_AR + L_FM，其中 z_t = (1 − t) z_0 + t ε，速度目標是 ε − z_0。
        </Text>
      </Stack>

      <Divider />

      <Stack gap={8}>
        <H2>這台 Mac、A100、V100 怎麼分</H2>
        <Table
          headers={["機器", "適合先做", "不適合"]}
          rows={[
            [
              "這台 Mac",
              "讀協議、跑 CPU 測試、改 ABC、設計樣本格式、用小 config 把損失寫對",
              "作為正式出歌機器。macOS 仍是實驗路徑，整首歌的原生驗收還沒完成",
            ],
            [
              "A100",
              "BF16 推理、留下一條完整 artifact、LoRA 或從現成權重繼續訓練。A100 支援 BF16",
              "從零復現 106,000 次更新、batch 256。那個配方用的是 64 張 H800",
            ],
            [
              "V100",
              "FP16 或 FP32 的資料前處理：歌詞、段落、SheetSage2、VAE 編碼、打包檢查",
              "論文的 BF16 訓練器。Volta 沒有 bfloat16。FP8 的 AR 推理也不在這代卡上",
            ],
          ]}
          rowTone={["info", "success", "warning"]}
        />
      </Stack>

      <Stack gap={8}>
        <H2>訓練代碼建議怎麼開始寫</H2>
        <H3>1. 先在 A100 上跑通推理契約</H3>
        <Text>
          安裝 Python 3.12 和這個包，對 examples/song.json 跑 examples/generate.py。留下 score.abc、semantic.npy、latent.npy 和 audio.flac。這個目錄就是 trainer 以後要對齊的樣本格式。聽歌用 YuE2-Vae。只有在復現論文表格時才換 YuE2-Vae-legacy，並且用同一組 latent 解碼。
        </Text>
        <H3>2. 訓練包與推理包分開</H3>
        <Text>
          import 現有的 YuE2ForCausalLM，不要把 yue2-infer 改成一套半成品 trainer。第一個里程碑只做 AR：把 prompt 位置的 label 設成忽略，只監督樂譜和語義 span，再乘 0.25。第二個里程碑按 nar_velocity 註釋裡的注入方式，寫可反傳的 flow matching。
        </Text>
        <H3>3. 從現成權重繼續訓練，而不是從零預訓練</H3>
        <Text>
          m-a-p/YuE2-3B 是現實的起點。一張 A100 可以開始做 AR 側 LoRA，前提是你已經有合法的「文字、ABC、語義 id」序列。3.58B 全參微調還要加上 Adam 狀態，需要分片。官方語義 tokenizer 發布之前，用新錄音對齊論文裡的 c 這一截會缺工具。
        </Text>
      </Stack>

      <Callout tone="info" title="動訓練之前先看授權">
        這個倉庫的代碼是 Apache 2.0。YuE2-3B 和兩個 VAE 權重是 CC BY-NC 4.0，另有個人創作者許可，以及非商業學術使用。分享微調後的權重仍然要署名。公司把權重拿去商用，需要另外向作者取得授權。論文語料主要是 CC0 加上 Tokenwave.AI 授權的合成數據，語料本身沒有公開。
      </Callout>
    </Stack>
  );
}
