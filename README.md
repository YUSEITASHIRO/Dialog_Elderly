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

$$\text{MeanF0}\_\text{Hz} = \frac{1}{N} \sum_{t \in \text{voiced}} f_0(t)$$

対象区間内の有声フレームのみを対象に `np.nanmean()` で算出します。

### 4.2 ピッチ標準偏差・イントネーション（StdF0_Hz）

$$\text{StdF0}\_\text{Hz} = \sqrt{\frac{1}{N} \sum_{t \in \text{voiced}} (f_0(t) - \overline{f_0})^2}$$

`np.nanstd()` で算出します（母集団標準偏差、`ddof=0`）。  
発話内のイントネーション変動の大きさを表します。

### 4.3 ピッチ最大値・最小値（MaxF0_Hz / MinF0_Hz）

有声フレームの `np.nanmax()` / `np.nanmin()` です。  
`ana_results.py` でこれらの差から `F0_Range_Hz` を計算します：

$$\text{F0\_Range\_Hz} = \text{MaxF0\_Hz} - \text{MinF0\_Hz}$$

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

$$\text{Slope\_Hz} = \frac{\Delta f_0 \text{（Hz）}}{\Delta t \text{（秒）}}$$

$$\text{Slope\_Semi} = \frac{\Delta f_0 \text{（半音）}}{\Delta t \text{（秒）}}$$

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

$$\text{MeanVowelDuration\_ms} = \overline{v_{\text{dur}}} \times 1000$$

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

ここで $x_i = F1_i$、$y_i = F2_i$（インデックスは環状）。

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
