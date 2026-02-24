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

$$\text{MeanF0\_Hz} = \frac{1}{N} \sum_{t \in \text{voiced}} f_0(t)$$

対象区間内の有声フレームのみを対象に `np.nanmean()` で算出します。

### 4.2 ピッチ標準偏差・イントネーション（StdF0_Hz）

$$\text{StdF0\_Hz} = \sqrt{\frac{1}{N} \sum_{t \in \text{voiced}} (f_0(t) - \overline{f_0})^2}$$

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

$$\text{MeanVowelDuration\_ms} = \overline{v\_dur} \times 1000$$

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
