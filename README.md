# 高齢者会話音響分析パイプライン

日本語会話コーパス（CEJC準拠）を対象に、対高齢者発話の音響特徴を自動抽出・比較分析するパイプラインです。  
MFA（Montreal Forced Aligner）による音素アライメントから始まり、Praat／parselmouth による音響計測、  
グループ単位の統計比較、全体統計の可視化、そして多段階の統計検定まで、6つのスクリプトが順に連携します。

---

## ディレクトリ構造

```
E:\DATA\work\                        ← 作業ルート（BASE_DIR）
│
├── ana_mfa_pipeline.py              ← STEP 1: MFAアライメント
├── ana_acoustic.py                  ← STEP 2: 音響特徴量抽出
├── ana_results.py                   ← STEP 3: グループ内比較・可視化
├── ana_total.py                     ← STEP 4: 全ファイル横断集計
├── ana_totalResults.py              ← STEP 5: 全体統計・クロス分析
├── ana_test.py                      ← STEP 6: 統計検定（t検定／ANOVA／LMM等）
│
├── data_session.csv                 ← セッションメタデータ（独自作成）
├── data_participant.csv             ← 話者メタデータ（CEJC準拠）
│
├── mfa_input\                       ← MFA入力（話者IC別フォルダ）
│   └── IC01\
│       ├── C002_001_IC01.wav
│       └── C002_001_IC01.TextGrid
│
├── mfa_output\                      ← MFA出力（話者IC別フォルダ）
│   └── IC01\
│       └── C002_001_IC01.TextGrid   ← phones / words Tier付き
│
├── analysis\                        ← 統合済みTextGrid + WAVの置き場
│   ├── Analysis_ C002_001_IC01.TextGrid
│   └── （WAVはここかD:\CEJC\dataから検索）
│
├── Result\                          ← STEP 2 出力CSV
│   └── Result_Analysis_C002_001_IC01.csv
│
└── Comparison_Result\               ← STEP 3 以降の出力
    ├── C001\                        ← グループ単位の比較結果
    │   ├── Summary_By_File_*.csv
    │   ├── bar_mean_comparison.png
    │   └── ...
    ├── C015\
    │   └── ...
    ├── anaTotal\                    ← STEP 4 出力
    │   ├── Total_File_Stats.csv     ← STEP 6 の入力ファイル
    │   ├── Total_Aggregated_Stats.csv
    │   └── ...
    ├── total\                       ← STEP 5 出力
    │   ├── Total_Raw_Data.csv
    │   ├── Total_Statistics_Summary.csv
    │   └── ...
    └── anaTest\                     ← STEP 6 出力
        ├── Step1_Welch_*.csv
        ├── Step2_Paired_*.csv
        ├── Step3_ANOVA_*.csv
        ├── Step4_LMM_*.csv
        ├── Step5_Interaction_*.csv
        └── *.png（有意差のあった指標のグラフ）
```

> **注意：** 元音声データ（WAV・LUU CSVなど）は `D:\CEJC\data` 以下に CEJC の元フォルダ構成のまま配置してください。  
> `ana_total.py` のみ `E:\CEJC\data` を参照しています。

---

## 入力データ仕様

### data_session.csv（独自作成）

各行が1セッション（1会話ファイル）に対応します。

| カラム名 | 説明 | 例 |
|---|---|---|
| 会話ID | 会話識別子 | `C002_006a` |
| セッションID | セッション識別子 | `C002_006` |
| 本人IC | 対象話者の IC 番号 | `IC01` |
| 会話時間(分) | 会話の長さ | `11` |
| 話者数 | 参加話者の人数 | `3` |
| 会話概要 | フリーテキスト | `飲食店で友人たちと誕生日会` |
| 形式 | 雑談 / インタビュー 等 | `雑談` |
| 場所 | 収録場所 | `自宅` |
| 活動 | 活動の種類 | `付き合い` |
| 話者間の関係性 | 友人知人 / 家族 / 同僚 等 | `友人知人` |
| 収録年 | | `2016年` |
| 対高齢者含む | 65歳以上を含む場合 1 | `1` |
| 対高齢者のみ | 65歳以上のみと話している場合 1 | `0` |
| 対後期高齢者含む | 75歳以上を含む場合 1 | `1` |
| 対後期高齢者のみ | 75歳以上のみと話している場合 1 | `0` |
| 本人が高齢者 | 対象話者自身が高齢者の場合 1 | `0` |

条件ラベルは以下のフラグの組み合わせで自動付与されます：

| ラベル | 条件 |
|---|---|
| `[Non-Elderly]` | 対高齢者含む = 0 |
| `[Elderly]` | 対高齢者のみ = 1 |
| `[Late Elderly]` | 対後期高齢者のみ = 1 |

1セッションが複数フラグを満たす場合、複数ラベルが付与され、各ラベルで独立した行としてデータに格納されます。

---

### data_participant.csv（CEJC準拠）

各行が1話者×1会話に対応します。

| カラム名 | 説明 | 例 |
|---|---|---|
| 会話ID | | `C002_001` |
| 話者ID | | `C002_012` |
| 話者IC | MFAフォルダ名と一致 | `IC01` |
| 話者名 | 匿名化名 | `太郎` |
| 年齢 | 範囲 or `○○歳以上` 形式 | `40-44歳` |
| 性別 | 男性 / 女性 | `男性` |
| 出身地 | | `東京都` |
| 居住地 | | `千葉県` |
| 職業 | | `会社員・役員・公務員・専門職` |
| 協力者からみた関係性 | | `本人` |

年齢は `parse_age()` 関数により数値化されます（範囲は中間値、`○○歳以上` は +5）。

---

### 話者IDの命名規則

話者IDは大きく2種類あります：

| 種別 | 形式 | 例 | 説明 |
|---|---|---|---|
| CEJCコーパス話者 | `C###` | `C001`, `C015` | コーパス収録話者 |
| 外部・テスト話者 | `T###` / `Z##` | `T001`, `Z01A` | 独自追加話者 |

WAVファイルおよびTextGridのファイル名は `{会話ID}_{話者IC}.wav` 形式（例：`C002_001_IC01.wav`）です。

---

## パイプライン概要

```
音声WAV + LUU CSV（書き起こし）
        ↓
[1] ana_mfa_pipeline.py    MFAアライメント → phones/words/LUU/Bunsetsu Tier付きTextGrid
        ↓
[2] ana_acoustic.py        音響特徴量抽出 → Result_Analysis_*.csv（発話単位）
        ↓
[3] ana_results.py         グループ内比較・可視化 → Comparison_Result/{グループID}/
        ↓
[4] ana_total.py           全ファイル横断集計 → Comparison_Result/anaTotal/
        ↓
[5] ana_totalResults.py    全体統計・クロス分析 → Comparison_Result/total/
        ↓
[6] ana_test.py            多段階統計検定 → Comparison_Result/anaTest/
```

> **STEP 6 の入力について：** `ana_test.py` は STEP 5（ana_totalResults.py）の出力ではなく、  
> STEP 4（ana_total.py）が生成する `Comparison_Result/anaTotal/Total_File_Stats.csv` を直接読み込みます。  
> STEP 4 と STEP 5 は並行して実行することも可能です。

---

## 各スクリプトの詳細

---

### [1] ana_mfa_pipeline.py

**目的：** WAVと書き起こしCSV（LUU単位）から MFA用の入力を準備し、  
音素アライメントを実行、結果TextGridを `analysis/` フォルダに集約します。

#### 処理フロー

1. **セッションCSV読み込み**  
   `data_session.csv` から対象ファイルのリスト（タスクリスト）を生成します。  
   対象：`対高齢者含む`・`対高齢者のみ`・`対後期高齢者` フラグが立っているセッション。

2. **データ準備 `prepare_data()`**  
   - WAVを `librosa` で 16kHz モノラル PCM_16 に変換し `mfa_input/{話者IC}/` に保存。
   - LUU CSVを読み込み、発話区間（0.3秒以上のもの）を TextGrid（words Tier）に変換。
   - テキストは `clean_mfa_text()` で記号・括弧を除去。

3. **MFA実行 `run_mfa()`**  
   ```
   mfa align mfa_input/{IC} japanese_mfa japanese_mfa mfa_output/{IC}
       --clean --overwrite -j 4 --beam 100 --retry_beam 400 --one-pass
   ```
   モデル初回実行時に自動ダウンロードします。

4. **後処理 `postprocess()`**  
   MFA出力の TextGrid（phones + words Tier）に  
   LUU Tier と Bunsetsu Tier を追加し `analysis/Analysis_ {ファイル名}.TextGrid` として保存。  
   Bunsetsu は MeCab（unidic-lite）で形態素解析し、文節境界を自動検出します。

5. **リトライ戦略（5フェーズ）**  
   MFA アライメント失敗時に以下の順でリトライします：

   | フェーズ | 戦略 | 追加ファイル数 |
   |---|---|---|
   | Phase 1 | 通常実行 | 0 |
   | Phase 2 | 同一話者のダミーWAVを2本追加 | 2 |
   | Phase 3 | 同一話者のダミーWAVを4本追加 | 4 |
   | Phase 4 | 同一会話の他話者WAVをコンテキストとして追加 | 最大5 |
   | Phase 5 | データルート全体からランダム30本のWAVを追加 | 最大30 |

   各フェーズ後に不要なダミーファイルは削除されます。

#### 主な出力

| パス | 内容 |
|---|---|
| `mfa_input/{IC}/` | MFA入力WAV・TextGrid |
| `mfa_output/{IC}/` | MFA出力TextGrid（phones + words） |
| `analysis/Analysis_ *.TextGrid` | LUU・Bunsetsu Tierを追加した最終TextGrid |

#### 実行方法

```bash
# 全ファイルを処理
python ana_mfa_pipeline.py

# フェーズ指定（例：Phase 1のみ）
python ana_mfa_pipeline.py --phase_start 1 --phase_end 1

# 特定の会話IDのみ処理
python ana_mfa_pipeline.py --target C002_001
```

---

### [2] ana_acoustic.py

**目的：** `analysis/` フォルダの TextGrid と WAV から、  
各発話単位（Section LUU / LUU / Bunsetsu）の音響特徴量を計測し CSV に保存します。

#### 処理フロー

1. **音響オブジェクト生成**  
   parselmouth で Sound、Pitch、Intensity オブジェクトを作成。

2. **Section LUU の構築**  
   LUU Tier のポーズが1秒未満の場合は隣接する LUU を統合し、  
   より大きな発話まとまり（Section LUU）を定義します。

3. **3段階の発話単位で共通解析**  

   | 単位 | Tier名 | 説明 |
   |---|---|---|
   | Section LUU | （自動構築） | ポーズ1秒未満のLUUを統合した発話区間 |
   | LUU | `LUU` | 語用論的発話単位（Lingual Utterance Unit） |
   | Bunsetsu | `Bunsetsu` | MeCabによる文節単位 |

   各単位について以下を計測します：

   | 特徴量 | 説明 |
   |---|---|
   | SpeechRate | 発話速度（モーラ/秒）。phones Tier のモーラ数 / 区間長 |
   | MeanF0_Hz / StdF0_Hz | 平均・標準偏差ピッチ（Hz） |
   | MaxF0_Hz / MinF0_Hz | ピッチの最大・最小値 |
   | MeanF0_Semitone / StdF0_Semitone | ピッチの平均・標準偏差（半音, 基準100Hz） |
   | TerminalRise_Slope_Hz / _Semi | 末尾有声音区間の5点抽出一次近似によるピッチ傾き |
   | MeanIntensity_dB | 平均強度 |
   | MeanVowelDuration_ms | 平均母音長（ms） |
   | VSA_Area | 母音空間面積（F1–F2平面、Shoelace公式） |
   | F1_{a/i/u/e/o} / F2_{a/i/u/e/o} | 各母音の平均フォルマント（Burg法、中央25ms） |

4. **Local Emphasis（相槌等）の抽出**  
   words Tier の全単語について発話ピッチ・強度・長さを記録します（DataType = `Local`）。

5. **CSV 保存**  
   `Result/Result_Analysis_{ファイル名}.csv` に1行1発話区間で保存。

#### IPA音素の処理

MFAが出力するIPA表記の音素は `clean_phone_label()` で長音記号（ː）や  
無声化記号（̥）などの付加記号を除去してから分析に使用します。  
母音の対応テーブル（VOWEL_MAP）により、異音（ɐ, ɑ, ɯ 等）を5母音（a/i/u/e/o）に正規化します。

#### 実行方法

```bash
# バッチ処理（analysis/ フォルダ内の全ファイル）
python ana_acoustic.py

# 単一ファイル指定
python ana_acoustic.py path/to/audio.wav path/to/Analysis_audio.TextGrid
```

---

### [3] ana_results.py

**目的：** `Result/` フォルダの CSV を話者グループ（C001, C015 等）ごとに集約し、  
条件（`[Non-Elderly]` / `[Elderly]` / `[Late Elderly]`）間の比較グラフと集計CSVを出力します。

#### グループ判定ロジック

ファイル名のプレフィックス（例：`C001`）でグループを自動検出します。  
`data_session.csv` のフラグに基づき各ファイルに条件ラベルを付与し、  
**ベースライン（`[Non-Elderly]`）と対象条件（`[Elderly]`）の両方が存在するグループのみ**処理します。

#### 主な出力ファイル

| ファイル名 | 内容 |
|---|---|
| `Summary_By_File_*.csv` | ファイル単位の条件別集計値（mean/std） |
| `bar_mean_comparison.png` | 条件別の主要指標棒グラフ |
| `dist_box_*.png` | 各指標の箱ひげ図（DataType別: Section_LUU / LUU / Bunsetsu） |
| `dist_hist_pitch.png` | ピッチ分布ヒストグラム（Hz + Semitone） |
| `dist_vsa_scatter.png` | 母音空間の散布図 |
| `dist_vsa_polygon.png` | 母音空間ポリゴン |
| `dist_local_emphasis.png` | 「うん」相槌の強度・ピッチ・長さの箱ひげ図 |
| `bar_terminal_rise_*_detail.png` | 末尾ライズの DataType 別棒グラフ |

#### 主要集計指標（Summary_By_File）

`SecLUU_*`（Section LUU）、`LUU_*`、`Bun_*`（Bunsetsu）のプレフィックスで各単位の平均値を格納します。

| カラム | 意味 |
|---|---|
| `SecLUU_SpeechRate` | Section LUU 単位の発話速度 |
| `SecLUU_MeanF0_Hz` / `_Semi` | Section LUU 単位の平均ピッチ |
| `SecLUU_StdF0_Hz` | Section LUU 単位のイントネーション（Std F0） |
| `SecLUU_RangeF0_Hz` | ピッチレンジ |
| `SecLUU_Rise_Mean_Hz` / `_Semi` | 末尾ライズ傾き |
| `SecLUU_Intensity` | 平均強度 |
| `SecLUU_MeanVowelDur` | 平均母音長 |
| `SecLUU_VSA` | 母音空間面積 |
| `SecLUU_F1/F2_{a/i/u/e/o}` | 母音フォルマント |
| `Loc_Un_Count` / `_Dur_ms` | 「うん」相槌の出現数・平均長さ |
| `Loc_Un_Pitch_Hz` / `_Intensity_dB` | 「うん」相槌のピッチ・強度 |

#### 実行方法

```bash
python ana_results.py
```

---

### [4] ana_total.py

**目的：** `analysis/` フォルダの TextGrid を直接読み込み（ana_acoustic.py を介さず）、  
全ファイルを一括で音響集計します。`ana_test.py`（STEP 6）の入力となる  
`Total_File_Stats.csv` を生成する重要なステップです。

#### ana_acoustic.py との主な違い

| 項目 | ana_acoustic.py | ana_total.py |
|---|---|---|
| 処理単位 | ファイルごとにCSV保存 | 全ファイルを一括でDataFrame化 |
| 出力先 | `Result/` | `Comparison_Result/anaTotal/` |
| 参照データ | TextGrid + WAV | TextGrid + WAV + session/participant CSV |
| 後続スクリプト | ana_results.py | ana_test.py |

相槌（バックチャンネル）は「うん」「はい」の2種類を Bunsetsu Tier から検出します。  
集計は `ConvID × SpeakerID × Condition` 単位で行い、`Gender` でさらに分割した棒グラフも出力します。

#### 主な出力

| ファイル | 内容 |
|---|---|
| `Total_File_Stats.csv` | ファイル単位の全集計値（**STEP 6 の入力**） |
| `Total_Aggregated_Stats.csv` | 条件 × 性別の平均・中央値 |
| `{ana1/ana2}_{指標}_{Mean/Median}.png` | 指標別棒グラフ（ana1 = ファイル単位, ana2 = 話者単位） |
| `VSA_Polygon_{Male/Female/All}.png` | 性別別母音空間ポリゴン |

#### 実行方法

```bash
python ana_total.py
```

---

### [5] ana_totalResults.py

**目的：** `Comparison_Result/` 以下の全グループの `Summary_By_File_*.csv` を統合し、  
`data_session.csv` と `data_participant.csv` のメタデータを結合した上で、  
全体統計・クロス分析・可視化を行います。

#### 処理フロー

1. **全グループの Summary_By_File_*.csv を収集・統合**  
   `Comparison_Result/*/Summary_By_File_*.csv` を glob で収集し、`df_total` に結合します。

2. **メタデータの結合**  
   各行のIDから会話IDと話者ICを解析し、session/participant CSVから以下の属性を付与します：

   | 属性 | 内容 |
   |---|---|
   | `Gender` | 性別（Male / Female） |
   | `My_Age_Group` | 年齢グループ（元の表記） |
   | `Relation` | 話者間の関係性（元の表記） |
   | `Relation_Simple` | 簡略化した関係性（Family / Friend / Colleague / Other） |
   | `SpeakerCount` | 話者数（数値） |
   | `SpeakerCount_Group` | 話者数グループ（Dyad / Small Group / Large Group） |
   | `Age_Relation` | 相手との年齢差（5段階） |
   | `Age_Diff_3Group` | 相手との年齢差（3グループ） |

3. **全体棒グラフの出力（Overall Bar Comparison）**  
   23指標を4列のサブプロットで条件別に棒グラフ表示します。

4. **クロス分析（Boxplots）**  
   7種類の属性因子（Gender, Age_Relation, Relation 等）と条件のクロス集計CSVおよび箱ひげ図を出力します。

5. **話者差分分析（Delta Scatter）**  
   各グループ内で `[Non-Elderly]` をベースラインとした差分（Δ）を計算し、  
   `[Elderly]` / `[Late Elderly]` の変化量を性別別散布図で可視化します。

6. **単位別詳細比較（Section LUU / LUU / Bunsetsu）**  
   Terminal Rise・Speech Rate について、3単位を比較した棒グラフを出力します。

7. **全体VSAポリゴン**  
   全条件を重ねた母音空間ポリゴン図を出力します。

#### 出力ファイル一覧

| ファイル | 内容 |
|---|---|
| `Total_Raw_Data.csv` | メタデータ結合済みの全データ |
| `Total_Statistics_Summary.csv` | 条件別の記述統計（mean/std/count/median） |
| `Overall_Bar_Comparison.png` | 全指標の条件別棒グラフ |
| `Summary_By_{因子}.csv` | 属性因子ごとのクロス集計 |
| `Boxplot_{因子}_{指標}.png` | 属性因子別箱ひげ図 |
| `Speaker_Differences_Delta.csv` | 非高齢者条件からの差分データ |
| `Delta_Scatter_{指標}.png` | 話者差分散布図 |
| `Overall_{Hz/Semi/Speed}_Detail.png` | 単位別詳細比較棒グラフ |
| `Overall_VSA_Polygon.png` | 全体VSAポリゴン |

#### 実行方法

```bash
python ana_totalResults.py
```

---

### [6] ana_test.py

**目的：** STEP 4（`ana_total.py`）が生成した `Total_File_Stats.csv` を入力とし、  
音響指標に対して5段階の統計検定を順に実施します。  
`[Non-Elderly]` を対照群として `[Elderly]`・`[Late Elderly]` との差異を多角的に検証します。

#### 入力ファイル

```
Comparison_Result/anaTotal/Total_File_Stats.csv
```

#### 分析対象指標

| 表示ラベル | カラム名 |
|---|---|
| Terminal Rise Slope (Hz) | `SectionLUU_slope_hz` |
| Terminal Rise Slope (Semi) | `SectionLUU_slope_semi` |
| Mean Pitch (Hz) | `SectionLUU_mean_f0` |
| Std Pitch (Hz) | `SectionLUU_std_f0` |
| Pitch Range (Hz) | `SectionLUU_range_f0` |
| Speech Rate | `SectionLUU_speech_rate` |
| Mean Vowel Duration | `MeanVowelDur` |
| Backchannel Duration | `BC_Duration` |
| Backchannel Pitch | `BC_Pitch_Hz` |
| VSA | `VSA` |

#### データセットの種類

各検定は以下の2種類のデータセットに対して実行されます：

| データセット | 内容 |
|---|---|
| `Ana1_File` | ファイル単位のデータ（サンプル数最大） |
| `Ana2_Speaker_Mean` | 話者単位の平均（`SpeakerID × Condition × Gender × Relation_Type` で集約） |

`Relation_Type` は `data_session.csv` の「話者間の関係性」を以下の3カテゴリに自動分類します：

| カテゴリ | 対象キーワード |
|---|---|
| `Family` | 家族・母・父・娘・息子・妻・夫・兄弟・姉妹・孫・祖父・祖母・親戚 |
| `Friend` | 友人・知人・友達・同級生・先輩・後輩・同僚・仲間 |
| `Other` | 上記以外 |

#### 5段階の統計検定

---

**Step 1：Welch の t 検定（Ana1 / Ana2 両方）**

等分散を仮定しない2標本 t 検定を `[Non-Elderly]` と `[Elderly]`、  
および `[Non-Elderly]` と `[Late Elderly]` の2ペアに対して実施します。

- サブセット：全体（All）/ 性別別（Male, Female）/ 関係性別（Family, Friend, Other）
- 有意水準 `p < 0.05` の場合のみ CSV・棒グラフを出力
- 効果量として Cohen's *d* を算出
- 有意差の記号：`***` (p<0.001) / `**` (p<0.01) / `*` (p<0.05) / `n.s.`

出力：`Step1_Welch_{データセット名}.csv`、`S1_*.png`（有意差のあった指標のみ）

---

**Step 2：対応のある t 検定 + 二項検定（Ana2 のみ）**

同一話者が `[Non-Elderly]` と `[Elderly]`（または `[Late Elderly]`）の両条件に  
データを持つ場合に、話者内の変化を検定します。

- `SpeakerID` を軸に pivot し、両条件に値がある話者のみを対象とする
- 対応のある t 検定（`stats.ttest_rel`）で平均変化を検定
- 二項検定（`stats.binomtest`）で「増加した話者数」の偏りを検定（tie を除く）
- 出力グラフは減少（青）・変化なし（灰）・増加（赤）の割合を横棒グラフで表示

出力：`Step2_Paired_{データセット名}.csv`、`S2_*.png`

---

**Step 3：一元配置分散分析（ANOVA）+ Tukey HSD 事後検定（Ana1 / Ana2 両方）**

3条件（`[Non-Elderly]` / `[Elderly]` / `[Late Elderly]`）を同時に比較します。

- `stats.f_oneway` で F 検定を実施
- `p < 0.05` の場合に `pairwise_tukeyhsd` で事後検定を実施
- 有意差のある指標をまとめて「Mega Plot」（4列のサブプロット）として出力

出力：`Step3_ANOVA_{データセット名}.csv`、`S3_Mega_*.png`

---

**Step 4：線形混合モデル（LMM）（Ana1 のみ）**

話者（`SpeakerID`）をランダム効果として扱い、  
発話ファイルの反復測定による擬似反復を制御した上で条件効果を推定します。

```python
# 参照水準を [Non-Elderly] に固定
mixedlm(f"{col} ~ C(Condition, Treatment('[Non-Elderly]'))",
        data=clean, groups=clean["SpeakerID"]).fit(reml=False)
```

- `[Non-Elderly]` 対 `[Elderly]`、`[Non-Elderly]` 対 `[Late Elderly]` の2モデルを個別に推定
- 収束しなかった場合は自動的にスキップ
- `p < 0.05` の場合のみ結果を CSV に記録

出力：`Step4_LMM_{データセット名}.csv`

---

**Step 5：交互作用分析（Condition × Gender）（Ana1 / Ana2 両方）**

条件（Elderly/Late Elderly）と性別の交互作用をOLSで検定します。  
LMMより収束が安定するため、傾向把握を目的としています。

```python
ols(f"{col} ~ C(Condition) * C(Gender)", data=clean).fit()
anova_lm(model, typ=2)  # Type II ANOVA
```

- 交互作用項（`:` を含む項）の `p < 0.05` の場合のみ出力
- 有意な交互作用が見られた場合はポイントプロット（条件 × 性別）を出力

出力：`Step5_Interaction_{データセット名}.csv`、`S5_Int_*.png`

---

#### 出力ファイル一覧

| ファイル | 内容 |
|---|---|
| `Step1_Welch_*.csv` | Welch t 検定の有意結果（p, Cohen's d, 有意記号） |
| `Step2_Paired_*.csv` | 対応あり t 検定・二項検定の有意結果 |
| `Step3_ANOVA_*.csv` | ANOVA の有意結果と Tukey 事後検定のペア |
| `Step4_LMM_*.csv` | LMM の有意結果（係数・p 値） |
| `Step5_Interaction_*.csv` | 交互作用の有意結果 |
| `S1_*.png` | Step 1 有意指標の棒グラフ |
| `S2_*.png` | Step 2 有意指標の増減割合横棒グラフ |
| `S3_Mega_*.png` | Step 3 有意指標の Mega Plot |
| `S5_Int_*.png` | Step 5 有意指標のポイントプロット |

#### 実行方法

```bash
# STEP 4 の完了後に実行すること
python ana_test.py
```

---

## 実行手順まとめ

```bash
# 1. MFAアライメント（最初の1回 or 新規ファイル追加時）
python ana_mfa_pipeline.py

# 2. 音響特徴量抽出
python ana_acoustic.py

# 3. グループ別比較・可視化
python ana_results.py

# 4. 全ファイル横断集計（STEP 6 の前提）
python ana_total.py

# 5. 全体統計・クロス分析（STEP 4 と並行実行可）
python ana_totalResults.py

# 6. 多段階統計検定（STEP 4 完了後に実行）
python ana_test.py
```

---

## 依存ライブラリ

| ライブラリ | 用途 |
|---|---|
| `parselmouth` | Praat ラッパー（F0・強度・フォルマント計測） |
| `textgrid` | TextGrid ファイルの読み書き |
| `pandas` / `numpy` | データ処理・集計 |
| `matplotlib` / `seaborn` | 可視化 |
| `scipy` | t 検定・F 検定・二項検定 |
| `statsmodels` | LMM（mixedlm）・OLS・Tukey HSD |
| `MeCab` + `unidic-lite` | 形態素解析（文節境界検出） |
| `librosa` / `soundfile` | WAV 変換（16kHz, PCM_16） |
| `montreal-forced-aligner` | 音素アライメント |

インストール例：

```bash
pip install parselmouth textgrid pandas numpy matplotlib seaborn scipy statsmodels mecab-python3 unidic-lite soundfile librosa
conda install -c conda-forge montreal-forced-aligner
```

---

## 分析対象指標一覧（TARGET_METRICS）

ana_totalResults.py で扱う23指標です。

| カラム名 | 説明 |
|---|---|
| `SecLUU_SpeechRate` | 発話速度（Section LUU, モーラ/秒） |
| `LUU_SpeechRate` | 発話速度（LUU） |
| `Bun_SpeechRate` | 発話速度（Bunsetsu） |
| `SecLUU_MeanF0_Hz` | 平均ピッチ（Hz, Section LUU） |
| `SecLUU_StdF0_Hz` | ピッチ標準偏差＝イントネーション（Hz） |
| `SecLUU_RangeF0_Hz` | ピッチレンジ（Hz） |
| `Bun_MeanF0_Hz` | 平均ピッチ（Hz, Bunsetsu） |
| `Bun_StdF0_Hz` | イントネーション（Hz, Bunsetsu） |
| `SecLUU_MeanF0_Semi` | 平均ピッチ（半音） |
| `SecLUU_StdF0_Semi` | イントネーション（半音） |
| `SecLUU_Rise_Mean_Hz` | 末尾ライズ傾き（Hz/秒, Section LUU） |
| `Bun_Rise_Mean_Hz` | 末尾ライズ傾き（Hz/秒, Bunsetsu） |
| `SecLUU_Rise_Mean_Semi` | 末尾ライズ傾き（半音/秒, Section LUU） |
| `Bun_Rise_Mean_Semi` | 末尾ライズ傾き（半音/秒, Bunsetsu） |
| `SecLUU_Intensity` | 平均強度（dB, Section LUU） |
| `LUU_Intensity` | 平均強度（dB, LUU） |
| `Bun_Intensity` | 平均強度（dB, Bunsetsu） |
| `SecLUU_MeanVowelDur` | 平均母音長（ms） |
| `SecLUU_VSA` | 母音空間面積（Hz²） |
| `Loc_Un_Count` | 「うん」相槌の出現数 |
| `Loc_Un_Dur_ms` | 「うん」相槌の平均長さ（ms） |
| `Loc_Un_Pitch_Hz` | 「うん」相槌の平均ピッチ（Hz） |
| `Loc_Un_Intensity_dB` | 「うん」相槌の平均強度（dB） |


---
---


# 音響指標の導出方法詳細（ana_acoustic.py）

本ドキュメントでは `ana_acoustic.py` が計算する各音響指標について、  
アルゴリズム・パラメータ・注意事項を実装に即して説明します。

---

## 目次

1. [前処理：発話単位の定義](#1-前処理発話単位の定義)
2. [前処理：音素ラベルの正規化](#2-前処理音素ラベルの正規化)
3. [発話速度（Speech Rate）](#3-発話速度speech-rate)
4. [基本周波数（F0）関連指標](#4-基本周波数f0関連指標)
5. [強度（Intensity）](#5-強度intensity)
6. [末尾ピッチ傾き（Terminal Rise Slope）](#6-末尾ピッチ傾きterminal-rise-slope)
7. [母音長（Vowel Duration）](#7-母音長vowel-duration)
8. [フォルマント・母音空間面積（VSA）](#8-フォルマント母音空間面積vsa)
9. [Local Emphasis（相槌等の単語レベル指標）](#9-local-emphasis相槌等の単語レベル指標)

---

## 1. 前処理：発話単位の定義

ana_acoustic.py は1つの TextGrid に対して3種類の発話単位を並行して分析します。

### 1.1 LUU（Lingual Utterance Unit）

TextGrid の `LUU` Tier からそのまま読み込みます。  
無音ラベル（`""`, `<eps>`, `sil`, `sp`, `silent`, `pause`, `spn`）を除いた区間が分析対象です。

### 1.2 Section LUU（セクションLUU）

**LUU 同士の間のポーズ長**を基準に、隣接する LUU を統合した発話まとまりです。  
プログラム内で以下のアルゴリズムにより動的に構築されます。

```
入力: LUU Tier の全区間（テキスト付き・無音を含む）

current_start = None
current_end   = None
current_text_parts = []

for 各区間 interval in LUU Tier:
    if interval に発話テキストあり:
        if current_start が未設定:
            current_start = interval.minTime
        current_end = interval.maxTime
        current_text_parts に interval.text を追加
    else (無音区間):
        if current_start が設定済み:
            if 無音区間の長さ >= 1.0秒:
                → Section LUU を確定して保存
                current_start / current_end / text をリセット
            else:
                → 1秒未満のポーズは「続き」とみなし current_end を延長
```

**ポイント：** ポーズが 1.0 秒未満であれば LUU をまたいで発話をつなぎ、  
1.0 秒以上のポーズで区切ります。これにより、短い間（ま）を含む連続発話を  
ひとつの発話区間（Section LUU）として扱います。

### 1.3 Bunsetsu（文節）

TextGrid の `Bunsetsu` Tier から読み込みます。  
Bunsetsu Tier は `ana_mfa_pipeline.py` の後処理で MeCab を用いて自動生成されています。

---

## 2. 前処理：音素ラベルの正規化

MFA（Montreal Forced Aligner）は IPA 表記で音素を出力しますが、  
長音記号や無声化記号などの付加記号が付く場合があります。  
これらを除去し、純粋な音素として扱うために以下の正規化を行います。

### 2.1 付加記号の除去 `clean_phone_label()`

```python
cleaned = re.sub(r'[ːˑ̥ˌˈ̄́̀̆̂̌_0-9]', '', ph)
```

除去する記号の例：

| 記号 | 意味 |
|---|---|
| `ː` | IPA 長音記号 |
| `ˑ` | IPA 半長音 |
| `̥` | 無声化（diacritic） |
| `ˌˈ` | 強勢記号 |
| `0-9` | 数字（声調番号等） |

### 2.2 母音の正規化 `get_base_vowel()`

クリーニング後の音素を5母音（a / i / u / e / o）にマッピングします。

| 入力音素 | 正規化後 |
|---|---|
| `a`, `A`, `ɐ`, `ɑ` | `a` |
| `i`, `I`, `ɪ` | `i` |
| `u`, `U`, `ɯ`, `ɨ`, `ʊ` | `u` |
| `e`, `E`, `ɛ` | `e` |
| `o`, `O`, `ɔ` | `o` |

マッピングに存在しない音素（子音等）は `None` を返します。

### 2.3 有声音の判定 `is_voiced_phone()`

末尾ピッチ傾きの計算（後述）において「ピッチ取得可能な有声音」かを判定します。

- **母音**（`get_base_vowel()` が `None` でない）→ 有声
- **有声子音**：`n, m, g, z, d, b, r, y, w, j, ɾ, N, ɴ, ŋ, ɲ` → 有声
- それ以外（無声子音・無音）→ 非有声

---

## 3. 発話速度（Speech Rate）

### 指標名

`SpeechRate`（単位：モーラ/秒）

### 算出式

$$\text{SpeechRate} = \frac{\text{モーラ数}}{\text{区間長（秒）}}$$

### モーラのカウント `count_moras()`

`phones` Tier を走査し、対象区間内の各音素について以下のいずれかに該当する場合に1モーラとカウントします。

**① 母音**：`get_base_vowel()` が `None` でない音素（a, i, u, e, o およびその異音）

**② 特殊拍**：以下のラベルに該当する音素

| ラベル | 意味 |
|---|---|
| `n`, `N`, `ɴ`, `ŋ`, `ɲ` | 撥音（ん） |
| `q`, `Q` | 促音（っ）の閉鎖区間 |
| `っ`, `ん` | 仮名表記の特殊拍 |

**実装の注意点：**  
区間の判定は `interval.minTime >= end_time` で打ち切り、  
`interval.maxTime > start_time` で区間内に含まれるかを判定しています。  
音素区間が発話単位の境界をまたぐ場合でも、重なりがあればカウント対象に含まれます。

---

## 4. 基本周波数（F0）関連指標

### 音響オブジェクトの生成

```python
snd = parselmouth.Sound(wav_path)
pitch = snd.to_pitch()  # Praat デフォルト設定（SHS法）
```

`to_pitch()` は Praat の `Sound: To Pitch (ac)...` に対応し、  
デフォルトパラメータ（時間ステップ 0.0 = 自動、最小 75 Hz、最大 600 Hz）を使用します。

### ピッチ値の抽出

```python
pitch_times = pitch.xs()           # 各フレームの時刻
pitch_vals  = pitch.selected_array['frequency']  # 各フレームのF0値（Hz）
```

有声フレームは `pitch_vals > 0` でフィルタリングします（0 は無声フレーム）。

### 4.1 平均ピッチ（MeanF0_Hz）

$$\text{MeanF0} \_ \text{Hz} = \frac{1}{N} \sum_{t \in \text{voiced}} f_0(t)$$

対象区間内の有声フレームのみを対象に `np.nanmean()` で算出します。

### 4.2 ピッチ標準偏差・イントネーション（StdF0_Hz）

$$\text{StdF0} \_ \text{Hz} = \sqrt{\frac{1}{N} \sum_{t \in \text{voiced}} (f_0(t) - \overline{f_0})^2}$$

`np.nanstd()` で算出します（母集団標準偏差、`ddof=0`）。  
発話内のイントネーション変動の大きさを表します。

### 4.3 ピッチ最大値・最小値（MaxF0_Hz / MinF0_Hz）

有声フレームの `np.nanmax()` / `np.nanmin()` です。  
`ana_results.py` でこれらの差から `F0_Range_Hz` を計算します：

$$\text{F0}\textunderscore\text{Range}\textunderscore\text{Hz} = \text{MaxF0}\textunderscore\text{Hz} - \text{MinF0}\textunderscore\text{Hz}$$

### 4.4 半音換算ピッチ（MeanF0_Semitone / StdF0_Semitone）

基準周波数 100 Hz を用いた半音換算です。

$$\text{Semitone} = 12 \times \log_2\left(\frac{f_0}{100}\right)$$

**平均の換算（MeanF0_Semitone）：**

```python
mean_f0_semi = 12 * math.log2(mean_f0 / 100.0)  if mean_f0 > 0 else np.nan
```

平均F0（Hz）を一度計算してから半音に変換しています（フレームごとに変換して平均するのとは異なります）。

**標準偏差の換算（StdF0_Semitone）：**

```python
std_f0_semi  = 12 * math.log2(std_f0  / 100.0)  if std_f0  > 0 else np.nan
```

同様に Hz での標準偏差を半音に変換しています。  
`std_f0 <= 0` の場合（単調発話など）は `np.nan` を返します。

---

## 5. 強度（Intensity）

### 音響オブジェクトの生成

```python
intensity = snd.to_intensity()  # Praat デフォルト設定
```

`to_intensity()` は Praat の `Sound: To Intensity...` に対応し、  
デフォルトパラメータ（最小ピッチ 100 Hz、時間ステップ 0.0 = 自動）を使用します。

### 指標名

`MeanIntensity_dB`（単位：dB）

### 算出式

```python
mask_i = (int_times >= start_t) & (int_times <= end_t)
i_vals_sub = int_vals[mask_i]
mean_int = np.nanmean(i_vals_sub)
```

対象区間内の全フレーム（有声・無声を含む）の強度の平均値です。  
無声区間（ポーズ・子音）も含まれるため、発話区間が長いほどポーズの影響を受けます。

---

## 6. 末尾ピッチ傾き（Terminal Rise Slope）

発話末尾の音調変化（上昇・下降）を定量化する指標です。

### 指標名

| 指標 | 単位 |
|---|---|
| `TerminalRise_Slope_Hz` | Hz/秒 |
| `TerminalRise_Slope_Semi` | 半音/秒 |

### Step 1：末尾有声音区間の特定

`phones` Tier を**末尾から**走査し、発話終了時刻から 0.5 秒以内にある  
最初の有声音（`is_voiced_phone()` が True）の区間を取得します。

```python
for ph_int in reversed(tg_phones):
    if ph_int.maxTime <= start_t: break
    if ph_int.minTime < end_t:
        if ph_int.maxTime > end_t - 0.5 and is_voiced_phone(raw_mark):
            last_voiced_start = ph_int.minTime
            last_voiced_end   = ph_int.maxTime
            break
```

**判定範囲：** 発話終端から 0.5 秒以内（`ph_int.maxTime > end_t - 0.5`）。  
発話末尾に無声子音や無音が続く場合でも、直前の有声音まで遡って取得します。

### Step 2：5点サンプリングによる一次近似 `calculate_rise_slope_5points()`

末尾有声音区間 `[last_voiced_start, last_voiced_end]` を等間隔に5分割し、  
各時刻のピッチ値を取得します。

```python
times = np.linspace(start_time, end_time, 5)
for t in times:
    val_hz = pitch_obj.get_value_at_time(t)
    if not math.isnan(val_hz) and val_hz > 0:
        hz_values.append(val_hz)
        semi_values.append(12 * math.log2(val_hz / 100.0))
        valid_times.append(t)
```

有効点が2点以上の場合、`np.polyfit` で一次回帰を行い傾きを取得します：

$$\text{Slope} \_ \text{Hz} = \frac{\Delta f_0 \text{（Hz）}}{\Delta t \text{（秒）}}$$

$$\text{Slope} \_ \text{Semi} = \frac{\Delta f_0 \text{（半音）}}{\Delta t \text{（秒）}}$$

**正の傾き** → 末尾上昇（疑問調・継続の意志など）  
**負の傾き** → 末尾下降（断言・発話完了など）

有効点が1点以下の場合（無声区間が多い、ピッチが取れない等）は `np.nan` を返します。

---

## 7. 母音長（Vowel Duration）

### 指標名

`MeanVowelDuration_ms`（単位：ミリ秒）

### 算出方法

対象区間内の `phones` Tier を走査し、`get_base_vowel()` が `None` でない音素（母音）の  
区間長を収集します。区間が発話単位の境界をまたぐ場合は、境界でクリップします。

```python
ph_start = max(start_t, ph_int.minTime)
ph_end   = min(end_t,   ph_int.maxTime)
v_dur    = ph_end - ph_start
vowel_durs.append(v_dur)
```

収集した全母音長の平均値をミリ秒換算して出力します：

$$\text{MeanVowelDuration} \_ \text{ms} = \overline{v_{\text{dur}}} \times 1000$$

特殊拍（撥音・促音）は母音としてカウントしません。

---

## 8. フォルマント・母音空間面積（VSA）

### 8.1 フォルマントの計測

各母音区間の**中央時刻（center_t）前後 25ms**を切り出し、Burg 法でフォルマント分析を行います。

```python
center_t = ph_start + v_dur / 2.0
snd_part = snd.extract_part(
    from_time = max(0, center_t - 0.025),
    to_time   = min(snd.get_total_duration(), center_t + 0.025)
)
fmt = snd_part.to_formant_burg(
    time_step              = 0.01,
    max_number_of_formants = 5,
    maximum_formant        = 5500.0   # 単位：Hz
)
f1 = fmt.get_value_at_time(1, center_t - max(0, center_t - 0.025))
f2 = fmt.get_value_at_time(2, center_t - max(0, center_t - 0.025))
```

**パラメータの選択理由：**

| パラメータ | 値 | 理由 |
|---|---|---|
| 抽出窓幅 | ±25ms（計50ms） | 母音の定常部を捉えつつ短い母音にも対応 |
| max_number_of_formants | 5 | F1〜F4 を安定して取得するため |
| maximum_formant | 5500 Hz | 女性・高齢者の高いF2にも対応（標準は5500Hz） |

各母音（a/i/u/e/o）について発話単位内の全出現例を収集し、  
`np.nanmean()` で平均値を出力します：

```
F1_{a/i/u/e/o}  # 各母音の平均F1値（Hz）
F2_{a/i/u/e/o}  # 各母音の平均F2値（Hz）
```

### 8.2 母音空間面積（VSA_Area）

5母音の平均フォルマント座標（F1, F2）を頂点とする多角形の面積を  
**Shoelace 公式（測量公式）**で計算します。

使用する母音の順序：`['a', 'e', 'i', 'u', 'o']`

```python
vsa_area = 0.5 * np.abs(
    np.dot(pts_x, np.roll(pts_y, 1)) -
    np.dot(pts_y, np.roll(pts_x, 1))
)
```

$$\text{VSA} = \frac{1}{2} \left| \sum_{i=0}^{n-1} (x_i y_{i+1} - y_i x_{i+1}) \right|$$

ここで $x_i = F1_i$、 $y_i = F2_i$（インデックスは環状）。

**計算条件：** F1・F2 が両方とも有効な母音が3点以上ある場合のみ計算します（3点未満は `np.nan`）。

**単位：** Hz²

**解釈：** 値が大きいほど母音が音響的に明瞭に分化していることを示します。  
対高齢者発話では VSA が拡大するか縮小するかが研究上の関心事の一つです。

---

## 9. Local Emphasis（相槌等の単語レベル指標）

`words` Tier の各区間について、発話単位（LUU 等）に依らず  
**単語（word）単位**でピッチ・強度・長さを記録します。

### 処理対象

無音ラベルを除いた `words` Tier の全区間。  
主に相槌（「うん」「はい」等）や強調語の分析に使用します。

### 記録される指標

| カラム名 | 算出方法 |
|---|---|
| `Pitch_Hz` | 単語区間内の有声フレームの平均F0（Hz） |
| `Pitch_Semitone` | 上記を `12 * log2(f0 / 100)` で半音換算 |
| `Intensity_dB` | 単語区間内の全フレームの平均強度（dB） |
| `Duration_ms` | 単語区間長（ミリ秒） |

```python
w_f0 = np.nanmean(p_vals_w) if len(p_vals_w) > 0 else np.nan
w_f0_semi = 12 * math.log2(w_f0 / 100.0) if w_f0 > 0 else np.nan
w_int = np.nanmean(i_vals_w) if len(i_vals_w) > 0 else np.nan
```

これらのレコードは CSV に `DataType = 'Local'` として書き出されます。  
`ana_results.py` では `Text == 'うん'` でフィルタリングして相槌の分析に使用します。

---

## 出力 CSV のカラム一覧

`Result/Result_Analysis_{ファイル名}.csv` の各行は1発話区間（または1単語）に対応します。

### Section_LUU / LUU / Bunsetsu の共通カラム

| カラム名 | 型 | 説明 |
|---|---|---|
| `BaseName` | str | 元ファイル名（拡張子なし） |
| `DataType` | str | `Section_LUU` / `LUU` / `Bunsetsu` |
| `Text` | str | 発話テキスト |
| `StartTime` | float | 区間開始時刻（秒） |
| `EndTime` | float | 区間終了時刻（秒） |
| `Duration_ms` | float | 区間長（ms） |
| `SpeechRate` | float | 発話速度（モーラ/秒） |
| `MeanF0_Hz` | float | 平均F0（Hz） |
| `StdF0_Hz` | float | F0標準偏差（Hz） |
| `MaxF0_Hz` | float | F0最大値（Hz） |
| `MinF0_Hz` | float | F0最小値（Hz） |
| `MeanF0_Semitone` | float | 平均F0（半音、基準100Hz） |
| `StdF0_Semitone` | float | F0標準偏差（半音） |
| `TerminalRise_Slope_Hz` | float | 末尾ピッチ傾き（Hz/秒） |
| `TerminalRise_Slope_Semi` | float | 末尾ピッチ傾き（半音/秒） |
| `MeanIntensity_dB` | float | 平均強度（dB） |
| `MeanVowelDuration_ms` | float | 平均母音長（ms） |
| `VSA_Area` | float | 母音空間面積（Hz²） |
| `F1_a` / `F2_a` | float | 母音 /a/ の平均F1・F2（Hz） |
| `F1_i` / `F2_i` | float | 母音 /i/ の平均F1・F2（Hz） |
| `F1_u` / `F2_u` | float | 母音 /u/ の平均F1・F2（Hz） |
| `F1_e` / `F2_e` | float | 母音 /e/ の平均F1・F2（Hz） |
| `F1_o` / `F2_o` | float | 母音 /o/ の平均F1・F2（Hz） |

### Local（単語レベル）のカラム

| カラム名 | 型 | 説明 |
|---|---|---|
| `BaseName` | str | 元ファイル名 |
| `DataType` | str | `Local` 固定 |
| `Text` | str | 単語テキスト（「うん」「はい」等） |
| `StartTime` | float | 単語開始時刻（秒） |
| `EndTime` | float | 単語終了時刻（秒） |
| `Duration_ms` | float | 単語長（ms） |
| `Pitch_Hz` | float | 平均F0（Hz） |
| `Pitch_Semitone` | float | 平均F0（半音） |
| `Intensity_dB` | float | 平均強度（dB） |

---

## 欠損値（NaN）が発生する条件

| 指標 | NaN となる条件 |
|---|---|
| MeanF0_Hz 系 | 有声フレームが1つも存在しない（完全無声発話） |
| StdF0_Semitone | std_f0 <= 0（単調発話で標準偏差がゼロ） |
| TerminalRise_Slope | 末尾0.5秒以内に有声音が存在しない、またはピッチ有効点が1点以下 |
| MeanVowelDuration_ms | 区間内に母音が1つも含まれない |
| VSA_Area | 有効なフォルマント値を持つ母音が3種類未満 |
| F1_{v} / F2_{v} | 当該母音が区間内に出現しない、またはフォルマント推定失敗 |
| MeanIntensity_dB | 強度フレームが0件（区間が極めて短い場合） |


---

---

# 発話レベル統計分析パイプライン詳細ドキュメント

このドキュメントでは、発話レベルデータの統合から統計分析までを担う2つのスクリプトについて、  
実装の詳細・アルゴリズム・統計手法を詳しく解説します。

---

## 目次

1. [ana_make_utterance_data.py - 発話レベルデータ統合](#1-ana_make_utterance_datapy---発話レベルデータ統合)
2. [ana_test_LMM.py - 発話レベル統計検定](#2-ana_test_lmmpy---発話レベル統計検定)

---

# 1. ana_make_utterance_data.py - 発話レベルデータ統合

## 1.1 目的と概要

`ana_make_utterance_data.py` は、`ana_acoustic.py` が生成した発話単位の音響特徴量CSVファイルを  
統合し、メタデータ（会話ID、話者ID、性別、条件ラベル）を付与して、  
発話レベルの包括的なデータセットを構築します。

### 主な機能

- **複数CSVファイルの統合**：`Result/` フォルダ内の全 `Result_Analysis_*.csv` を結合
- **ID情報の自動抽出**：ファイル名から ConvID と SpeakerID を解析
- **メタデータの付与**：セッション・参加者情報から条件と性別を取得
- **特徴量の計算**：F0_Range_Hz の算出
- **条件ごとのデータ複製**：複数条件に該当するセッションを適切に展開

---

## 1.2 入力ファイル

### 1.2.1 音響特徴量CSV（必須）

**パス：** `Result/Result_Analysis_*.csv`

`ana_acoustic.py` の出力ファイル。1行が1発話区間（Section_LUU / LUU / Bunsetsu）または  
1単語（Local）に対応します。

**主要カラム：**

| カラム名 | 型 | 説明 |
|---|---|---|
| BaseName | str | 元ファイル名（拡張子なし） |
| DataType | str | 発話単位タイプ（Section_LUU / LUU / Bunsetsu / Local） |
| Text | str | 発話テキスト |
| StartTime / EndTime | float | 区間時刻（秒） |
| Duration_ms | float | 区間長（ms） |
| SpeechRate | float | 発話速度（モーラ/秒） |
| MeanF0_Hz | float | 平均F0（Hz） |
| StdF0_Hz | float | F0標準偏差（Hz） |
| MaxF0_Hz / MinF0_Hz | float | F0最大・最小値（Hz） |
| MeanF0_Semitone / StdF0_Semitone | float | ピッチ（半音） |
| TerminalRise_Slope_Hz / _Semi | float | 末尾ピッチ傾き |
| MeanIntensity_dB | float | 平均強度（dB） |
| MeanVowelDuration_ms | float | 平均母音長（ms） |
| VSA_Area | float | 母音空間面積（Hz²） |
| F1_{a/i/u/e/o} / F2_{a/i/u/e/o} | float | 各母音のフォルマント |

---

### 1.2.2 data_session.csv（必須）

**パス：** `data_session.csv`（BASE_DIR直下）

各セッションのメタデータ。条件ラベルの判定に使用します。

**重要カラム：**

| カラム名 | 型 | 説明 |
|---|---|---|
| 会話ID | str | 会話識別子（例：C002_006a） |
| 対高齢者含む | int | 65歳以上で構成される場合 1 |
| 対後期高齢者含む | int | 75歳以上で構成される場合 1 |

**条件判定ロジック：**

```python
if r.get('対高齢者含む') == 0:
    conditions.append("[Non-Elderly]")
if r.get('対高齢者のみ') == 1:
    conditions.append("[Elderly]")
if r.get('対後期高齢者のみ') == 1:
    conditions.append("[Late Elderly]")
```

- **[Non-Elderly]**：参加者全員が0-64歳（対高齢者含む = 0）
- **[Elderly]**：65歳以上の参加者だけ（対高齢者のみ = 1）
- **[Late Elderly]**：75歳以上の参加者だけ（対後期高齢者のみ = 1）

**重要：** 1つのセッションが複数条件を満たす場合（例：75歳以上の場合は自動的に65歳以上）、  
`[Elderly]` と `[Late Elderly]` の両方のラベルが付与されます。

---

### 1.2.3 data_participant.csv（必須）

**パス：** `data_participant.csv`（BASE_DIR直下）

各話者のメタデータ。性別情報の取得に使用します。

**重要カラム：**

| カラム名 | 型 | 説明 |
|---|---|---|
| 会話ID | str | 会話識別子 |
| 話者IC | str | 話者識別子（例：IC01） |
| 性別 | str | 男性 / 女性 |

**性別の変換：**

```python
if g == '男性': gender = 'Male'
elif g == '女性': gender = 'Female'
else: gender = g
```

---

## 1.3 処理フロー詳細

### 1.3.1 初期化とメタデータ読み込み

```python
def generate_all_utterance_data():
    setup_dirs()  # OUTPUT_DIR を作成
    
    # メタデータ読み込み（エンコーディング自動判定）
    try:
        df_ses = pd.read_csv(SESSION_CSV, encoding='cp932')
        df_par = pd.read_csv(PARTICIPANT_CSV, encoding='cp932')
    except:
        df_ses = pd.read_csv(SESSION_CSV, encoding='utf-8')
        df_par = pd.read_csv(PARTICIPANT_CSV, encoding='utf-8')
    
    # カラム名の空白除去
    df_ses.columns = [c.strip() for c in df_ses.columns]
    df_par.columns = [c.strip() for c in df_par.columns]
```

**エンコーディング処理：**
- 日本語CSVは cp932（Shift-JIS）または UTF-8 の可能性があるため、  
  cp932 で試行し、失敗した場合は UTF-8 にフォールバック

**カラム名の正規化：**
- Excel等で作成されたCSVにはカラム名の前後に空白が含まれる場合があるため、  
  `.strip()` で除去

---

### 1.3.2 CSVファイルの収集

```python
csv_files = glob.glob(os.path.join(RESULT_DIR, "Result_Analysis_*.csv"))
if not csv_files:
    print("No utterance CSV files found in Result/ directory.")
    return

print(f"Integrating {len(csv_files)} files...")
```

**検索パターン：** `Result/Result_Analysis_*.csv`
- `Result_Analysis_C002_001_IC01.csv` 等のファイルを収集

---

### 1.3.3 ファイル名からのID抽出

各CSVファイルのファイル名から ConvID（会話ID）と SpeakerID（話者IC）を抽出します。

```python
base_name = os.path.basename(file_path).replace("Result_Analysis_", "").replace(".csv", "").strip()

# 正規表現で抽出を試行
match = re.match(r'(.+)_(IC\d+|Z\d+[A-Z]?|[A-Z]+\d+)', base_name)
if match:
    conv_id = match.group(1)      # 例：C002_001
    speaker_id = match.group(2)   # 例：IC01
else:
    # フォールバック：アンダースコアで分割
    parts = base_name.split('_')
    conv_id = parts[0]
    speaker_id = parts[-1] if len(parts) > 1 else "Unknown"
```

**正規表現パターンの詳細：**

```
(.+)_(IC\d+|Z\d+[A-Z]?|[A-Z]+\d+)
```

- `(.+)`：会話ID部分（最初のグループ）
- `_`：区切り文字
- `(IC\d+|Z\d+[A-Z]?|[A-Z]+\d+)`：話者ID部分（第2グループ）
  - `IC\d+`：標準形式（IC01, IC02, ...）
  - `Z\d+[A-Z]?`：テスト話者形式（Z01, Z01A, ...）
  - `[A-Z]+\d+`：その他の形式（ABC01, ...）

**具体例：**

| ファイル名（拡張子なし） | ConvID | SpeakerID |
|---|---|---|
| `C002_001_IC01` | `C002_001` | `IC01` |
| `C015_012a_IC03` | `C015_012a` | `IC03` |
| `T001_test_Z01A` | `T001_test` | `Z01A` |

---

### 1.3.4 条件ラベルの付与

```python
# セッション情報から条件を判定
conditions = []
ses_row = df_ses[df_ses['会話ID'] == conv_id]

if ses_row.empty:
    # プレフィックスマッチングを試行（C002_001a → C002_001）
    short_id = conv_id.split('_')[0]
    ses_row = df_ses[df_ses['会話ID'] == short_id]

if not ses_row.empty:
    r = ses_row.iloc[0]
    
    # 非対高齢者: 参加者全員が0-64歳
    if r.get('対高齢者含む') == 0:
        conditions.append("[Non-Elderly]")
    
    # 対高齢者: 65歳以上の参加者が含まれる
    if r.get('対高齢者のみ') == 1:
        conditions.append("[Elderly]")
    
    # 対後期高齢者: 75歳以上の参加者が含まれる
    if r.get('対後期高齢者のみ') == 1:
        conditions.append("[Late Elderly]")
else:
    conditions.append("Unknown")
```

**フォールバック機構：**
1. 完全一致で検索（`C002_001a`）
2. 失敗した場合、最初のアンダースコアまでを使用（`C002`）
3. それでも見つからない場合、"Unknown" を付与

**条件の複数付与：**
- 例：65歳と75歳の両方が参加するセッション
  - `conditions = ["[Elderly]", "[Late Elderly]"]`
  - 後述の処理で、各条件ごとにデータを複製

---

### 1.3.5 性別情報の付与

```python
gender = "Unknown"
par_row = df_par[(df_par['会話ID'] == conv_id) & (df_par['話者IC'] == speaker_id)]

if par_row.empty and '_' in conv_id:
    # プレフィックスマッチングを試行
    par_row = df_par[(df_par['会話ID'] == conv_id.split('_')[0]) & (df_par['話者IC'] == speaker_id)]

if not par_row.empty:
    g = par_row.iloc[0].get('性別', 'Unknown')
    if g == '男性': gender = 'Male'
    elif g == '女性': gender = 'Female'
    else: gender = g
```

**検索戦略：**
1. 会話IDと話者ICの完全一致で検索
2. 失敗した場合、会話IDのプレフィックスで再検索
3. それでも見つからない場合、"Unknown"

---

### 1.3.6 発話レベルデータの読み込みと処理

```python
try:
    df_utterance = pd.read_csv(file_path)
    
    # F0_Range_Hz を計算
    if 'MaxF0_Hz' in df_utterance.columns and 'MinF0_Hz' in df_utterance.columns:
        df_utterance['F0_Range_Hz'] = df_utterance['MaxF0_Hz'] - df_utterance['MinF0_Hz']
    
    # メタデータを追加
    df_utterance['ConvID'] = conv_id
    df_utterance['SpeakerID'] = speaker_id
    df_utterance['Gender'] = gender
    
    # 条件ごとにデータを複製して格納
    for c in conditions:
        df_cond = df_utterance.copy()
        df_cond['Condition'] = c
        all_rows.append(df_cond)
        
except Exception as e:
    print(f"Error reading {base_name}: {e}")
```

**F0_Range_Hz の計算：**

$$\text{F0}\textunderscore\text{Range}\textunderscore\text{Hz} = \text{MaxF0}\textunderscore\text{Hz} - \text{MinF0}\textunderscore\text{Hz}$$

これは発話内のピッチ変動幅を表します。  
`ana_acoustic.py` では MaxF0_Hz と MinF0_Hz のみを出力するため、  
ここで差分を計算して新しいカラムとして追加します。

**条件ごとの複製：**

重要なポイントとして、1つのファイルが複数条件に該当する場合、  
**各条件ごとに独立した行としてデータを複製**します。

**例：**

| 元データ | 条件リスト | 出力データ |
|---|---|---|
| 発話1（会話A） | `["[Elderly]", "[Late Elderly]"]` | 発話1（条件=[Elderly]）<br>発話1（条件=[Late Elderly]） |
| 発話2（会話A） | `["[Elderly]", "[Late Elderly]"]` | 発話2（条件=[Elderly]）<br>発話2（条件=[Late Elderly]） |

これにより、統計分析時に各条件を独立したグループとして扱えます。

---

### 1.3.7 統合とCSV保存

```python
if all_rows:
    df_all = pd.concat(all_rows, ignore_index=True)
    out_path = os.path.join(OUTPUT_DIR, "All_Total_File_Stats.csv")
    df_all.to_csv(out_path, index=False, encoding='utf-8-sig')
    print(f"Completed! Total utterance rows: {len(df_all)}")
    print(f"Saved to: {out_path}")
else:
    print("No valid data could be aggregated.")
```

**出力ファイル：** `Comparison_Result/anaTotal/All_Total_File_Stats.csv`

**エンコーディング：** `utf-8-sig`（BOM付きUTF-8）
- Excel等で開いた際に文字化けを防ぐため

**ignore_index=True：** 行インデックスをリセット（0から振り直す）

---

## 1.4 出力データ構造

### 1.4.1 All_Total_File_Stats.csv のカラム一覧

| カラム名 | 型 | 説明 | 由来 |
|---|---|---|---|
| **メタデータ（追加）** | | | |
| ConvID | str | 会話ID | ファイル名から抽出 |
| SpeakerID | str | 話者IC | ファイル名から抽出 |
| Gender | str | 性別（Male / Female） | data_participant.csv |
| Condition | str | 条件ラベル | data_session.csv |
| **元の音響特徴量** | | | |
| BaseName | str | 元ファイル名 | Result_Analysis_*.csv |
| DataType | str | 発話単位タイプ | Result_Analysis_*.csv |
| Text | str | 発話テキスト | Result_Analysis_*.csv |
| StartTime / EndTime | float | 区間時刻（秒） | Result_Analysis_*.csv |
| Duration_ms | float | 区間長（ms） | Result_Analysis_*.csv |
| SpeechRate | float | 発話速度（モーラ/秒） | Result_Analysis_*.csv |
| MeanF0_Hz | float | 平均F0（Hz） | Result_Analysis_*.csv |
| StdF0_Hz | float | F0標準偏差（Hz） | Result_Analysis_*.csv |
| MaxF0_Hz / MinF0_Hz | float | F0最大・最小値（Hz） | Result_Analysis_*.csv |
| **計算された特徴量** | | | |
| F0_Range_Hz | float | ピッチレンジ（Hz） | MaxF0_Hz - MinF0_Hz |
| MeanF0_Semitone / StdF0_Semitone | float | ピッチ（半音） | Result_Analysis_*.csv |
| TerminalRise_Slope_Hz / _Semi | float | 末尾ピッチ傾き | Result_Analysis_*.csv |
| MeanIntensity_dB | float | 平均強度（dB） | Result_Analysis_*.csv |
| MeanVowelDuration_ms | float | 平均母音長（ms） | Result_Analysis_*.csv |
| VSA_Area | float | 母音空間面積（Hz²） | Result_Analysis_*.csv |
| F1_{a/i/u/e/o} / F2_{a/i/u/e/o} | float | 各母音のフォルマント | Result_Analysis_*.csv |

---

### 1.4.2 データサイズの例

**仮定：**
- 話者数：50人
- 1話者あたり平均5ファイル
- 1ファイルあたり平均200発話（Section_LUU + LUU + Bunsetsu）
- 条件複製係数：1.5（一部のファイルが複数条件に該当）

**計算：**

```
総行数 = 50人 × 5ファイル × 200発話 × 1.5（複製）
      = 75,000 行
```

実際のデータセットでは数万〜数十万行になることがあります。

---

## 1.5 エラーハンドリング

### 1.5.1 ファイル読み込みエラー

```python
try:
    df_utterance = pd.read_csv(file_path)
    # ... 処理 ...
except Exception as e:
    print(f"Error reading {base_name}: {e}")
```

個別のCSVファイル読み込みエラーが発生しても、スクリプト全体は継続します。  
エラーが発生したファイルはスキップされ、ログに記録されます。

---

### 1.5.2 メタデータ欠損への対応

**セッション情報が見つからない場合：**

```python
if ses_row.empty:
    # プレフィックスで再検索
    short_id = conv_id.split('_')[0]
    ses_row = df_ses[df_ses['会話ID'] == short_id]
    
if not ses_row.empty:
    # 条件判定処理
else:
    conditions.append("Unknown")  # 最終フォールバック
```

**話者情報が見つからない場合：**

```python
if not par_row.empty:
    g = par_row.iloc[0].get('性別', 'Unknown')
    # 性別変換
else:
    gender = "Unknown"  # デフォルト値
```

**Unknown データの扱い：**
- 条件が "Unknown" のデータは統計分析時に除外されます
- 性別が "Unknown" のデータも同様に除外可能

---

## 1.6 実行例

### 1.6.1 基本的な実行

```bash
cd /path/to/project
python ana_make_utterance_data.py
```

**標準出力例：**

```
Loading Metadata...
Integrating 127 files...
Completed! Total utterance rows: 58342
Saved to: E:\DATA\work\Comparison_Result\anaTotal\All_Total_File_Stats.csv
```

---

### 1.6.2 実行前の確認事項

**チェックリスト：**

- [ ] `Result/` フォルダに `Result_Analysis_*.csv` が存在する
- [ ] `data_session.csv` が BASE_DIR に存在する
- [ ] `data_participant.csv` が BASE_DIR に存在する
- [ ] `Comparison_Result/anaTotal/` ディレクトリの書き込み権限がある

**確認コマンド：**

```bash
# CSVファイル数の確認
ls Result/Result_Analysis_*.csv | wc -l

# メタデータの確認
head -n 5 data_session.csv
head -n 5 data_participant.csv
```

---

## 1.7 トラブルシューティング

### 1.7.1 「No utterance CSV files found」エラー

**原因：** `Result/` フォルダにCSVファイルが存在しない

**解決策：**

```bash
# ana_acoustic.py を実行して音響特徴量を抽出
python ana_acoustic.py
```

---

### 1.7.2 エンコーディングエラー

**原因：** メタデータCSVのエンコーディングが cp932 でも utf-8 でもない

**解決策：**

```python
# スクリプトを修正して他のエンコーディングを試す
df_ses = pd.read_csv(SESSION_CSV, encoding='latin-1')  # 例
```

---

### 1.7.3 ID抽出失敗

**原因：** ファイル名形式が想定外のパターン

**症状：** `speaker_id = "Unknown"`

**デバッグ方法：**

```python
# スクリプトに以下を追加
print(f"Parsing: {base_name}")
print(f"  -> ConvID: {conv_id}, SpeakerID: {speaker_id}")
```

**解決策：** 正規表現パターンを修正

---

# 2. ana_test_LMM.py - 発話レベル統計検定

## 2.1 目的と概要

`ana_test_LMM.py` は、`ana_make_utterance_data.py` が生成した発話レベルデータに対して、  
3種類の統計検定を実施します：

1. **Welch の t 検定**：基本的な条件間比較
2. **Speaker-Only LMM**：話者を変量効果として制御
3. **Hierarchical LMM**：話者+セッションの2層階層モデル

### 主な特徴

- **包括的な指標分析**：24種類の音響指標すべてを対象
- **3つの発話単位タイプ**：Section_LUU / LUU / Bunsetsu を独立分析
- **3つの比較ペア**：Non vs Elderly、Non vs Late Elderly、Elderly vs Late Elderly
- **尤度比検定（LRT）**：LMMの有意性をより厳密に評価
- **自動フォールバック**：Hierarchical LMM が収束しない場合、Speaker-Only に自動切替

---

## 2.2 入力ファイル

### 2.2.1 All_Total_File_Stats.csv

**パス：** `Comparison_Result/anaTotal/All_Total_File_Stats.csv`

`ana_make_utterance_data.py` の出力ファイル。

**必須カラム：**

| カラム名 | 型 | 説明 |
|---|---|---|
| ConvID | str | 会話ID（例：C002_001） |
| SpeakerID | str | 話者IC（例：IC01） |
| Gender | str | 性別（Male / Female） |
| Condition | str | 条件（[Non-Elderly] / [Elderly] / [Late Elderly]） |
| DataType | str | 発話単位タイプ（Section_LUU / LUU / Bunsetsu） |
| 音響特徴量 | float | Duration_ms, SpeechRate, MeanF0_Hz, ... 等 |

---

## 2.3 分析対象指標

### 2.3.1 24種類の音響指標

```python
METRICS = [
    'Duration_ms', 'SpeechRate',
    'MeanF0_Hz', 'StdF0_Hz', 'MaxF0_Hz', 'MinF0_Hz', 'F0_Range_Hz',
    'MeanF0_Semitone', 'StdF0_Semitone',
    'TerminalRise_Slope_Hz', 'TerminalRise_Slope_Semi',
    'MeanIntensity_dB', 'MeanVowelDuration_ms', 'VSA_Area',
    'F1_a', 'F2_a', 'F1_i', 'F2_i', 'F1_u', 'F2_u', 'F1_e', 'F2_e', 'F1_o', 'F2_o'
]
```

**カテゴリ別分類：**

| カテゴリ | 指標 | 個数 |
|---|---|---|
| **時間** | Duration_ms, SpeechRate | 2 |
| **ピッチ（Hz）** | MeanF0_Hz, StdF0_Hz, MaxF0_Hz, MinF0_Hz, F0_Range_Hz | 5 |
| **ピッチ（半音）** | MeanF0_Semitone, StdF0_Semitone | 2 |
| **末尾ピッチ傾き** | TerminalRise_Slope_Hz, TerminalRise_Slope_Semi | 2 |
| **その他** | MeanIntensity_dB, MeanVowelDuration_ms, VSA_Area | 3 |
| **フォルマント** | F1_{a/i/u/e/o}, F2_{a/i/u/e/o} | 10 |

---

## 2.4 比較ペアとデータタイプ

### 2.4.1 3つの比較ペア

```python
PAIRS = [
    {"target": "[Elderly]", "baseline": "[Non-Elderly]", "pair_name": "Non vs Elderly"},
    {"target": "[Late Elderly]", "baseline": "[Non-Elderly]", "pair_name": "Non vs Late Elderly"},
    {"target": "[Late Elderly]", "baseline": "[Elderly]", "pair_name": "Elderly vs Late Elderly"}
]
```

**分析の意図：**

| ペア | 研究上の意義 |
|---|---|
| Non vs Elderly | 高齢者への適応的発話の基本パターン |
| Non vs Late Elderly | 後期高齢者への特殊な配慮 |
| Elderly vs Late Elderly | 前期・後期高齢者への段階的変化 |

---

### 2.4.2 3つのデータタイプ

```python
DATA_TYPES = ['Section_LUU', 'LUU', 'Bunsetsu']
```

各データタイプは独立して分析されます。  
これにより、発話単位の粒度による違いを検証できます。

**分析回数の計算：**

```
総分析数 = 24指標 × 3ペア × 3データタイプ = 216 回（検定ごと）
```

---

## 2.5 前処理：グループ変数の生成

```python
def main():
    df = pd.read_csv(INPUT_FILE)
    
    # 話者グループを抽出
    df['SpeakerGroup'] = df['ConvID'].astype(str).str.split('_').str[0]
    
    # セッションを抽出（末尾のアルファベットを削除）
    df['Session'] = df['ConvID'].astype(str).str.replace(r'[a-zA-Z]+$', '', regex=True)
```

### 2.5.1 SpeakerGroup の定義

**目的：** 同一話者の複数セッション・複数条件のデータをグループ化

**抽出ロジック：**

```python
ConvID.split('_')[0]
```

**例：**

| ConvID | SpeakerGroup |
|---|---|
| C002_001 | C002 |
| C002_001a | C002 |
| C002_001b | C002 |
| C015_012 | C015 |
| T001_test | T001 |

**解釈：**
- C002 という話者は複数のセッション（001, 001a, 001b等）でデータを持つ
- LMMでは SpeakerGroup をランダム効果として扱い、話者内の相関を制御

---

### 2.5.2 Session の定義

**目的：** 同一会話セッション内の発話をグループ化

**抽出ロジック：**

```python
ConvID.replace(r'[a-zA-Z]+$', '', regex=True)
```

**正規表現の説明：**
- `[a-zA-Z]+`：1文字以上のアルファベット
- `$`：文字列の末尾
- 末尾のアルファベット（a, b, c等）を削除

**例：**

| ConvID | Session |
|---|---|
| C002_001 | C002_001 |
| C002_001a | C002_001 |
| C002_001b | C002_001 |
| C015_012_test | C015_012_test |

**解釈：**
- 同一セッション（001, 001a, 001b）は同じ会話の異なる部分
- Hierarchical LMMでは Session をネストした変量効果として扱う

---

## 2.6 統計検定1：Welch の t 検定

### 2.6.1 目的

等分散を仮定しない2標本 t 検定により、条件間の平均値差を評価します。

### 2.6.2 実装

```python
def run_utterance_ttest(df):
    results = []
    
    for dtype in DATA_TYPES:
        df_dtype = df[df['DataType'] == dtype].copy()
        
        for pair in PAIRS:
            baseline = pair["baseline"]
            target = pair["target"]
            
            d_base = df_dtype[df_dtype['Condition'] == baseline]
            d_target = df_dtype[df_dtype['Condition'] == target]
            
            for metric in METRICS:
                v_base = d_base[metric].dropna()
                v_target = d_target[metric].dropna()
                
                if len(v_base) < 2 or len(v_target) < 2:
                    # サンプル不足
                    results.append({..., 'Sig': "Insufficient Data"})
                    continue
                
                try:
                    # Welch の t 検定（等分散を仮定しない）
                    t, p = stats.ttest_ind(v_target, v_base, equal_var=False)
                    
                    # Cohen's d（効果量）
                    d_val = cohen_d(v_target, v_base)
                    
                    sig = get_sig_char(p)
                    
                    results.append({
                        'DataType': dtype,
                        'Pair': pair_name,
                        'Metric': metric,
                        'N_Baseline': len(v_base),
                        'N_Target': len(v_target),
                        'Mean_Baseline': v_base.mean(),
                        'Mean_Target': v_target.mean(),
                        't_stat': t,
                        'p_value': p,
                        'Cohen_d': d_val,
                        'Sig': sig
                    })
                except Exception as e:
                    # エラー処理
```

### 2.6.3 効果量：Cohen's d

```python
def cohen_d(x, y):
    nx, ny = len(x), len(y)
    dof = nx + ny - 2
    if dof <= 0: return np.nan
    
    # プールされた標準偏差
    pooled_std = np.sqrt(((nx - 1) * np.var(x, ddof=1) + (ny - 1) * np.var(y, ddof=1)) / dof)
    
    # Cohen's d
    return (np.mean(x) - np.mean(y)) / pooled_std if pooled_std > 0 else np.nan
```

**数式：**

$$d = \frac{\bar{x}_1 - \bar{x}_2}{s_{\text{pooled}}}$$

$$s_{\text{pooled}} = \sqrt{\frac{(n_1 - 1)s_1^2 + (n_2 - 1)s_2^2}{n_1 + n_2 - 2}}$$

**解釈：**

| |d| | 効果の大きさ |
|---|---|
| 0.2 | 小 |
| 0.5 | 中 |
| 0.8 | 大 |

---

### 2.6.4 出力ファイル

**パス：** `Comparison_Result/anaTest/Step4_ttest_All_Utterances_Comprehensive.csv`

**カラム：**

| カラム名 | 型 | 説明 |
|---|---|---|
| DataType | str | 発話単位タイプ |
| Pair | str | 比較ペア名 |
| Baseline | str | ベースライン条件 |
| Target | str | 対象条件 |
| Metric | str | 音響指標名 |
| N_Total | int | 総サンプル数 |
| N_Baseline | int | ベースラインのサンプル数 |
| N_Target | int | 対象のサンプル数 |
| Mean_Baseline | float | ベースラインの平均値 |
| Mean_Target | float | 対象の平均値 |
| t_stat | float | t 統計量 |
| p_value | float | p 値 |
| Cohen_d | float | 効果量 |
| Sig | str | 有意性記号（***, **, *, n.s.） |

---

## 2.7 統計検定2：Speaker-Only LMM（話者のみ変量効果）

### 2.7.1 目的

話者（SpeakerGroup）をランダム効果として扱い、  
発話の反復測定による擬似反復を制御した上で条件効果を推定します。

### 2.7.2 モデル式

**フルモデル（条件効果あり）：**

$$y_{ij} = \beta_0 + \beta_1 \times \text{Condition}_{ij} + u_i + \epsilon_{ij}$$

- $y_{ij}$：話者 $i$ の発話 $j$ における音響特徴量
- $\beta_0$：切片（ベースライン条件の平均）
- $\beta_1$：条件効果（ベースラインから対象への変化量）
- $u_i \sim N(0, \sigma_u^2)$：話者 $i$ のランダム効果
- $\epsilon_{ij} \sim N(0, \sigma_\epsilon^2)$：残差

**Nullモデル（条件効果なし）：**

$$y_{ij} = \beta_0 + u_i + \epsilon_{ij}$$

---

### 2.7.3 実装

```python
def run_utterance_lmm_speaker_only(df):
    results = []
    
    for dtype in DATA_TYPES:
        df_dtype = df[df['DataType'] == dtype].copy()
        
        for pair in PAIRS:
            baseline = pair["baseline"]
            target = pair["target"]
            
            sub = df_dtype[df_dtype['Condition'].isin([baseline, target])].copy()
            
            for metric in METRICS:
                # 欠損値除外
                clean = sub.dropna(subset=[metric, 'Condition', 'SpeakerGroup'])
                
                n_total = len(clean)
                n_speakers = clean['SpeakerGroup'].nunique()
                
                # 最小サンプル数チェック
                if n_total < 10 or n_speakers < 2:
                    results.append({..., 'Sig': "Insufficient Data"})
                    continue
                
                try:
                    # ① フルモデル（Conditionあり）
                    formula_full = f"{metric} ~ C(Condition, Treatment('{baseline}'))"
                    model_full = smf.mixedlm(formula_full, clean, groups=clean["SpeakerGroup"])
                    fit_full = model_full.fit(reml=False)  # 最尤推定
                    
                    # ② Nullモデル（Conditionなし：切片のみ）
                    formula_null = f"{metric} ~ 1"
                    model_null = smf.mixedlm(formula_null, clean, groups=clean["SpeakerGroup"])
                    fit_null = model_null.fit(reml=False)
                    
                    # ③ 尤度比検定（Likelihood Ratio Test）
                    lr_stat = -2 * (fit_null.llf - fit_full.llf)
                    p_val_lrt = chi2.sf(lr_stat, 1)  # 自由度1のχ²分布
                    sig = get_sig_char(p_val_lrt)
                    
                    # 条件効果の係数を取得
                    target_param_name = f"C(Condition, Treatment('{baseline}'))[T.{target}]"
                    if target_param_name in fit_full.pvalues.index:
                        coef = fit_full.params[target_param_name]
                        std_err = fit_full.bse[target_param_name]
                    else:
                        coef = fit_full.params.iloc[1]
                        std_err = fit_full.bse.iloc[1]
                    
                    results.append({
                        'DataType': dtype,
                        'Pair': pair_name,
                        'Metric': metric,
                        'N_Total': n_total,
                        'N_Speakers': n_speakers,
                        'Coef (Beta)': coef,
                        'Std_Err': std_err,
                        'LR_chi2': lr_stat,
                        'LRT_p_value': p_val_lrt,
                        'Sig': sig
                    })
                
                except Exception as e:
                    # 収束エラー
                    results.append({..., 'Sig': "Convergence Error"})
```

---

### 2.7.4 尤度比検定（Likelihood Ratio Test）の詳細

**仮説：**

- $H_0$：条件効果なし（Nullモデルが真）
- $H_1$：条件効果あり（フルモデルが真）

**検定統計量：**

$$\text{LR} = -2 \times (\ell_{\text{null}} - \ell_{\text{full}})$$

- $\ell_{\text{null}}$：Nullモデルの対数尤度
- $\ell_{\text{full}}$：フルモデルの対数尤度

**分布：**

$H_0$ のもとで、LR は自由度 $df = k_{\text{full}} - k_{\text{null}}$ の $\chi^2$ 分布に従います。

本分析では：
- $k_{\text{full}} = 2$（切片 + 条件）
- $k_{\text{null}} = 1$（切片のみ）
- $df = 1$

**p 値の計算：**

```python
p_val_lrt = chi2.sf(lr_stat, 1)
```

`chi2.sf()` は $\chi^2$ 分布の生存関数（survival function）：

$$p = P(\chi^2_1 \geq \text{LR})$$

---

### 2.7.5 REML vs ML

**REML（制限付き最尤推定）：**
- 固定効果のパラメータ数を考慮した推定
- 分散成分の推定にバイアスが少ない
- モデル比較には使用できない

**ML（最尤推定）：**
- 尤度を直接最大化
- モデル比較に使用可能
- 本分析では `reml=False` を指定

---

### 2.7.6 出力ファイル

**パス：** `Comparison_Result/anaTest/Step4_LMM_SpeakerOnly_All_Utterances.csv`

**カラム：**

| カラム名 | 説明 |
|---|---|
| DataType | 発話単位タイプ |
| Pair | 比較ペア名 |
| Baseline / Target | ベースライン条件 / 対象条件 |
| Metric | 音響指標名 |
| N_Total | 総発話数 |
| N_Baseline / N_Target | 各条件の発話数 |
| N_Speakers | 話者数 |
| Coef (Beta) | 条件効果の推定値（$\beta_1$） |
| Std_Err | 標準誤差 |
| LR_chi2 | 尤度比統計量 |
| LRT_p_value | p 値 |
| Sig | 有意性記号 |

---

## 2.8 統計検定3：Hierarchical LMM（階層型）

### 2.8.1 目的

話者（SpeakerGroup）とセッション（Session）の2層をランダム効果として扱い、  
より詳細な階層構造を考慮します。

**階層構造：**

```
話者（SpeakerGroup）
  └── セッション（Session）
        └── 発話（個別の観測値）
```

---

### 2.8.2 モデル式

**フルモデル：**

$$y_{ijk} = \beta_0 + \beta_1 \times \text{Condition}_{ijk} + u_i + v_{ij} + \epsilon_{ijk}$$

- $y_{ijk}$：話者 $i$、セッション $j$、発話 $k$ の音響特徴量
- $u_i \sim N(0, \sigma_u^2)$：話者 $i$ のランダム効果
- $v_{ij} \sim N(0, \sigma_v^2)$：セッション $ij$ のランダム効果
- $\epsilon_{ijk} \sim N(0, \sigma_\epsilon^2)$：残差

**Nullモデル：**

$$y_{ijk} = \beta_0 + u_i + v_{ij} + \epsilon_{ijk}$$

---

### 2.8.3 実装

```python
def run_utterance_lmm_hierarchical(df):
    results = []
    
    for dtype in DATA_TYPES:
        df_dtype = df[df['DataType'] == dtype].copy()
        
        for pair in PAIRS:
            baseline = pair["baseline"]
            target = pair["target"]
            
            sub = df_dtype[df_dtype['Condition'].isin([baseline, target])].copy()
            
            for metric in METRICS:
                clean = sub.dropna(subset=[metric, 'Condition', 'SpeakerGroup', 'Session'])
                
                n_total = len(clean)
                n_speakers = clean['SpeakerGroup'].nunique()
                n_sessions = clean['Session'].nunique()
                
                if n_total < 10 or n_speakers < 2 or n_sessions < 2:
                    results.append({..., 'Sig': "Insufficient Data"})
                    continue
                
                try:
                    # Variance Components Formula（セッションをネストした変量効果）
                    vcf = {"Session": "0 + C(Session)"}
                    
                    # ① フルモデル
                    formula_full = f"{metric} ~ C(Condition, Treatment('{baseline}'))"
                    model_full = smf.mixedlm(
                        formula_full, clean, 
                        groups=clean["SpeakerGroup"],
                        vc_formula=vcf
                    )
                    fit_full = model_full.fit(reml=False)
                    
                    # ② Nullモデル
                    formula_null = f"{metric} ~ 1"
                    model_null = smf.mixedlm(
                        formula_null, clean,
                        groups=clean["SpeakerGroup"],
                        vc_formula=vcf
                    )
                    fit_null = model_null.fit(reml=False)
                    
                    # ③ 尤度比検定
                    lr_stat = -2 * (fit_null.llf - fit_full.llf)
                    p_val_lrt = chi2.sf(lr_stat, 1)
                    sig = get_sig_char(p_val_lrt)
                    
                    # 係数取得
                    # ... (Speaker-Only LMMと同様) ...
                    
                    results.append({
                        'DataType': dtype,
                        'Pair': pair_name,
                        'Metric': metric,
                        'N_Total': n_total,
                        'N_Speakers': n_speakers,
                        'N_Sessions': n_sessions,
                        'Coef (Beta)': coef,
                        'Std_Err': std_err,
                        'LR_chi2': lr_stat,
                        'LRT_p_value': p_val_lrt,
                        'Sig': sig
                    })
                
                except Exception as e:
                    # 収束エラー → フォールバック
                    try:
                        # Sessionを除外してSpeaker-Only LMMで再試行
                        model_full_fb = smf.mixedlm(formula_full, clean, groups=clean["SpeakerGroup"])
                        fit_full_fb = model_full_fb.fit(reml=False)
                        
                        model_null_fb = smf.mixedlm(formula_null, clean, groups=clean["SpeakerGroup"])
                        fit_null_fb = model_null_fb.fit(reml=False)
                        
                        lr_stat = -2 * (fit_null_fb.llf - fit_full_fb.llf)
                        p_val_lrt = chi2.sf(lr_stat, 1)
                        sig = get_sig_char(p_val_lrt)
                        
                        # ... 係数取得 ...
                        
                        results.append({
                            ...,
                            'Sig': sig + " (Fallback)"  # フォールバックを明示
                        })
                    except Exception as fallback_e:
                        # フォールバックも失敗
                        results.append({..., 'Sig': "Convergence Error"})
```

---

### 2.8.4 Variance Components Formula

```python
vc_formula = {"Session": "0 + C(Session)"}
```

**意味：**
- `Session` をカテゴリカル変量効果として追加
- `0 +` は切片を含めない（各セッションが独立した効果を持つ）

**statsmodelsの仕様：**
- `groups` パラメータ：主要なランダム効果（SpeakerGroup）
- `vc_formula` パラメータ：追加のランダム効果（Session）

**ネスト構造：**
- Session は SpeakerGroup にネストされている
- 同一 SpeakerGroup 内の Session 間の変動を捉える

---

### 2.8.5 フォールバック機構

**目的：** 階層モデルの収束失敗時に自動的に簡略化

**動作：**

1. Hierarchical LMM を試行
2. 収束エラーが発生
3. Session を除外して Speaker-Only LMM で再試行
4. 結果の `Sig` カラムに `" (Fallback)"` を付加

**利点：**
- データ損失を最小化
- 完全失敗よりも簡略化モデルの結果を得る方が有益

---

### 2.8.6 出力ファイル

**パス：** `Comparison_Result/anaTest/Step4_LMM_Hierarchical_All_Utterances.csv`

**カラム：**

| カラム名 | 説明 |
|---|---|
| DataType | 発話単位タイプ |
| Pair | 比較ペア名 |
| Baseline / Target | ベースライン条件 / 対象条件 |
| Metric | 音響指標名 |
| N_Total | 総発話数 |
| N_Baseline / N_Target | 各条件の発話数 |
| N_Speakers | 話者数 |
| N_Sessions | セッション数 |
| Coef (Beta) | 条件効果の推定値 |
| Std_Err | 標準誤差 |
| LR_chi2 | 尤度比統計量 |
| LRT_p_value | p 値 |
| Sig | 有意性記号（フォールバック時は "(Fallback)" 付加） |

---

## 2.9 有意性記号

```python
def get_sig_char(p):
    if pd.isna(p): return "n.s."
    if p < 0.001: return "***"
    if p < 0.01: return "**"
    if p < 0.05: return "*"
    return "n.s."
```

| 記号 | p 値範囲 | 解釈 |
|---|---|---|
| `***` | p < 0.001 | 極めて有意 |
| `**` | p < 0.01 | 非常に有意 |
| `*` | p < 0.05 | 有意 |
| `n.s.` | p ≥ 0.05 | 有意差なし（not significant） |

---

## 2.10 実行フロー

```python
def main():
    print("Loading All Utterance Data...")
    if not os.path.exists(INPUT_FILE):
        print(f"Input file not found: {INPUT_FILE}")
        return
    
    df = pd.read_csv(INPUT_FILE)
    setup_dirs()
    
    # グループ変数を生成
    df['SpeakerGroup'] = df['ConvID'].astype(str).str.split('_').str[0]
    df['Session'] = df['ConvID'].astype(str).str.replace(r'[a-zA-Z]+$', '', regex=True)
    
    # 全ての検定を順番に実行
    run_utterance_ttest(df)
    run_utterance_lmm_speaker_only(df)
    run_utterance_lmm_hierarchical(df)
    
    print("\nAll analyses completed successfully.")
```

**実行順序：**

1. データ読み込み
2. グループ変数生成（SpeakerGroup, Session）
3. t検定（216回）
4. Speaker-Only LMM（216回）
5. Hierarchical LMM（216回）

**総検定回数：** 648回（24指標 × 3ペア × 3データタイプ × 3検定）

---

## 2.11 実行例

### 2.11.1 基本的な実行

```bash
cd /path/to/project
python ana_test_LMM.py
```

### 2.11.2 標準出力例

```
Loading All Utterance Data...

==========================================================
--- Running Welch's t-test on all utterances ---
==========================================================
Integrating 127 files...

==========================================================
--- Running Step 4: Speaker-Only LMM (Likelihood Ratio Test) ---
==========================================================
[LMM Speaker-Only] Section_LUU  | Non vs Elderly            | MeanF0_Hz                 -> N= 3421, Speakers=28, Chi2= 15.34, Sig=***
[LMM Speaker-Only] Section_LUU  | Non vs Elderly            | StdF0_Hz                  -> N= 3421, Speakers=28, Chi2=  8.92, Sig=**
[LMM Speaker-Only] Section_LUU  | Non vs Elderly            | TerminalRise_Slope_Hz     -> N= 3156, Speakers=28, Chi2= 22.18, Sig=***
...

==========================================================
--- Running Step 4: Hierarchical LMM (Likelihood Ratio Test) ---
==========================================================
[LMM Hierarchical] Section_LUU  | Non vs Elderly            | MeanF0_Hz                 -> N= 3421, Speakers=28, Sessions=42, Chi2= 16.21, Sig=***
[LMM Fallback] Section_LUU  | Non vs Elderly            | VSA_Area                  -> (Session removed), Chi2= 3.14, Sig=n.s. (Fallback)
...

All analyses completed successfully.
```

---

### 2.11.3 実行時間の目安

**データ規模：**
- 総発話数：50,000
- 話者数：30
- セッション数：60

**実行時間（概算）：**

| 検定 | 時間 |
|---|---|
| t検定 | 2-5分 |
| Speaker-Only LMM | 30-60分 |
| Hierarchical LMM | 60-120分 |
| **合計** | **約2-3時間** |

**注意：**
- LMMの収束計算はデータサイズに強く依存
- 数十万発話の大規模データでは数時間〜半日かかる場合あり

---

## 2.12 結果の解釈

### 2.12.1 3つの検定の比較

| 検定 | 制御する変動 | 保守性 | 適用場面 |
|---|---|---|---|
| Welch t検定 | なし | 低 | 探索的分析、全体傾向 |
| Speaker-Only LMM | 話者内相関 | 中 | 話者差を考慮した推論 |
| Hierarchical LMM | 話者+セッション内相関 | 高 | 厳密な統計的推論 |

**保守性：** 有意差が出にくいほど保守的

---

### 2.12.2 結果の優先順位

**推奨される解釈の順序：**

1. **Hierarchical LMM の結果を優先**（最も厳密）
2. フォールバックの場合は Speaker-Only LMM の結果を参照
3. t検定は参考情報として活用

**論文での報告例：**

> Terminal Rise Slope (Hz) は、非高齢者条件と比較して高齢者条件で有意に増加した  
> （Hierarchical LMM: β = 12.3, SE = 3.2, χ² = 14.6, p < 0.001）。

---

### 2.12.3 効果の方向性

**Coef (Beta) の解釈：**

- **正の値**：対象条件 > ベースライン条件（増加）
- **負の値**：対象条件 < ベースライン条件（減少）

**例：**

| Metric | Baseline | Target | Beta | 解釈 |
|---|---|---|---|---|
| MeanF0_Hz | [Non-Elderly] | [Elderly] | +8.5 | 高齢者への発話でピッチが高くなる |
| SpeechRate | [Non-Elderly] | [Elderly] | -0.3 | 高齢者への発話で速度が遅くなる |

---

## 2.13 トラブルシューティング

### 2.13.1 収束エラーが多発する

**原因：**
- データ数が少ない
- 分散成分の推定が不安定
- カテゴリ変数の水準が多すぎる

**対処法：**

1. データを増やす（より多くのファイルを処理）
2. 最小サンプル数の閾値を調整：

```python
if n_total < 20 or n_speakers < 5:  # より厳しい条件
```

3. フォールバック機構を信頼する（Speaker-Only でも十分）

---

### 2.13.2 メモリ不足エラー

**原因：** 大規模データセット（数十万行）でメモリを使い果たす

**対処法：**

1. データタイプごとに分割して実行：

```python
# Section_LUU のみを分析
df_section = df[df['DataType'] == 'Section_LUU']
run_utterance_lmm_speaker_only(df_section)
```

2. 指標を絞る：

```python
METRICS = ['MeanF0_Hz', 'SpeechRate', 'TerminalRise_Slope_Hz']  # 主要指標のみ
```

---

### 2.13.3 実行時間が長すぎる

**対処法：**

1. 並列実行（複数のターミナルで異なるデータタイプを実行）
2. サーバー・クラスタでの実行
3. サブサンプリング（分析を急ぐ場合）：

```python
# 10%をサンプリング
df_sample = df.sample(frac=0.1, random_state=42)
```

---

## 2.14 統計的妥当性の確認

### 2.14.1 前提条件のチェック

**LMMの前提：**

1. **残差の正規性**：QQプロットで確認
2. **等分散性**：残差プロットで確認
3. **ランダム効果の正規性**：BLUPプロットで確認

**確認コード例：**

```python
import matplotlib.pyplot as plt

# 残差のQQプロット
from scipy import stats
residuals = fit_full.resid
stats.probplot(residuals, dist="norm", plot=plt)
plt.title("QQ Plot of Residuals")
plt.show()
```

---

### 2.14.2 多重比較補正

**問題：** 216回（または648回）の検定を行うため、偽陽性のリスクが高い

**対処法：**

1. **Bonferroni補正**（保守的）：

```python
alpha_corrected = 0.05 / 216  # ≈ 0.000231
```

2. **FDR（False Discovery Rate）補正**（推奨）：

```python
from statsmodels.stats.multitest import multipletests

p_values = results_df['LRT_p_value'].values
reject, p_adj, _, _ = multipletests(p_values, alpha=0.05, method='fdr_bh')
results_df['p_adj_FDR'] = p_adj
```

3. **研究上の重要性で絞る**：主要な指標（3-5個）に焦点を当てる

---

## 2.15 まとめ

### 2.15.1 ana_test_LMM.py の特徴

✓ **包括的**：24指標 × 3ペア × 3データタイプ = 216パターンを網羅  
✓ **多層的**：3種類の統計検定で異なる視点から評価  
✓ **堅牢**：フォールバック機構により収束エラーを最小化  
✓ **厳密**：尤度比検定により条件効果の有意性を正確に評価  
✓ **実用的**：CSV出力により結果の二次利用が容易

---

### 2.15.2 推奨される使用方法

1. **探索段階**：t検定で全体的な傾向を把握
2. **検証段階**：Speaker-Only LMM で話者差を制御
3. **論文執筆**：Hierarchical LMM の結果を主に報告
4. **補足資料**：3つの検定結果を比較表として提示

---

### 2.15.3 今後の拡張可能性

- **交互作用の追加**：Condition × Gender 等
- **共変量の追加**：年齢・会話時間等
- **ベイズ統計**：brms パッケージ（R）での実装
- **機械学習**：ランダムフォレストでの特徴量重要度評価

---
