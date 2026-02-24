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
