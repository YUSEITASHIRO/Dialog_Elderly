import parselmouth
import textgrid
import pandas as pd
import numpy as np
import os
import math
import argparse
import sys
import shutil
import glob
import traceback
import re

# --- 定数・設定 ---
DATA_SEARCH_ROOT = r"D:\CEJC\data"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ANALYSIS_DIR = os.path.join(BASE_DIR, "analysis")
RESULT_DIR = os.path.join(BASE_DIR, "Result")

# IPA母音を標準5母音にマッピングする辞書
VOWEL_MAP = {
    'a': 'a', 'A': 'a', 'ɐ': 'a', 'ɑ': 'a',
    'i': 'i', 'I': 'i', 'ɪ': 'i',
    'u': 'u', 'U': 'u', 'ɯ': 'u', 'ɨ': 'u', 'ʊ': 'u',
    'e': 'e', 'E': 'e', 'ɛ': 'e',
    'o': 'o', 'O': 'o', 'ɔ': 'o'
}

# モーラとみなす特殊拍（撥音・促音）
SPECIAL_MORAS = {'n', 'N', 'ɴ', 'ŋ', 'ɲ', 'q', 'Q', 'っ', 'ん'}

# 無音ラベル
SILENCE_LABELS = {"", "<eps>", "sil", "sp", "silent", "pause", "spn"}

# --- ユーティリティ ---
def setup_directories():
    os.makedirs(RESULT_DIR, exist_ok=True)

def search_file_recursive(filename, search_root):
    for root, dirs, files in os.walk(search_root):
        if filename in files:
            return os.path.join(root, filename)
    return None

def find_textgrid_tier(tg, tier_name):
    """名前でTierを検索。大文字小文字を無視して一致するものを返す"""
    for tier in tg.tiers:
        if tier.name.lower() == tier_name.lower():
            return tier
    return None

def clean_phone_label(ph):
    """音素ラベルから長音記号(ː)や無声化記号(̥)などの付加記号を削除し、純粋な音素にする"""
    # IPAの長音、半長音、無声化、声調などの記号を削除
    cleaned = re.sub(r'[ːˑ̥ˌˈ̄́̀̆̂̌_0-9]', '', ph)
    return cleaned.strip()

def get_base_vowel(ph):
    """音素が母音であれば標準母音(a,i,u,e,o)を返し、そうでなければNoneを返す"""
    cleaned_ph = clean_phone_label(ph)
    return VOWEL_MAP.get(cleaned_ph, None)

def is_voiced_phone(ph):
    """ピッチ取得可能な有声音（母音＋有声子音＋撥音）か判定"""
    if get_base_vowel(ph) is not None:
        return True
    cleaned_ph = clean_phone_label(ph)
    voiced_consonants = {'n', 'm', 'g', 'z', 'd', 'b', 'r', 'y', 'w', 'j', 'ɾ', 'N', 'ɴ', 'ŋ', 'ɲ'}
    return cleaned_ph in voiced_consonants

def count_moras(tg_phones, start_time, end_time):
    count = 0
    for interval in tg_phones:
        if interval.minTime >= end_time: break
        if interval.maxTime > start_time:
            ph = interval.mark.strip()
            cleaned_ph = clean_phone_label(ph)
            # 母音または特殊拍であればモーラとしてカウント
            if get_base_vowel(ph) is not None or cleaned_ph in SPECIAL_MORAS:
                count += 1
    return count

# --- 音響指標計算 (5点抽出・一次近似) ---
def calculate_rise_slope_5points(pitch_obj, start_time, end_time):
    if end_time <= start_time:
        return np.nan, np.nan
        
    times = np.linspace(start_time, end_time, 5)
    hz_values = []
    semi_values = []
    valid_times = []
    
    for t in times:
        val_hz = pitch_obj.get_value_at_time(t)
        if not math.isnan(val_hz) and val_hz > 0:
            hz_values.append(val_hz)
            semi_values.append(12 * math.log2(val_hz / 100.0))
            valid_times.append(t)
            
    if len(valid_times) >= 2:
        slope_hz, _ = np.polyfit(valid_times, hz_values, 1)
        slope_semi, _ = np.polyfit(valid_times, semi_values, 1)
        return slope_hz, slope_semi
    else:
        return np.nan, np.nan

# --- メイン解析処理 ---
def process_single_pair(wav_path, tg_path, base_name):
    print(f"Processing: {base_name}")
    try:
        snd = parselmouth.Sound(wav_path)
        pitch = snd.to_pitch()
        intensity = snd.to_intensity()

        pitch_times = pitch.xs()
        pitch_vals = pitch.selected_array['frequency']
        int_times = intensity.xs()
        int_vals = intensity.values[0]

        tg = textgrid.TextGrid.fromFile(tg_path)
        
        # Tierの安全な取得
        tg_phones = find_textgrid_tier(tg, "phones")
        if tg_phones is None: tg_phones = tg.tiers[0] # フォールバック
            
        tg_words = find_textgrid_tier(tg, "words")
        if tg_words is None: tg_words = tg.tiers[1] # フォールバック
        
        tg_bunsetsu = find_textgrid_tier(tg, "Bunsetsu")
        tg_luu = find_textgrid_tier(tg, "LUU")
        if not tg_luu and len(tg.tiers) >= 4:
            tg_luu = tg.tiers[3]

        results = []

        # ==========================================
        # 0. Section LUU (ポーズが1秒未満のLUUを統合)
        # ==========================================
        section_luus = []
        if tg_luu:
            current_start = None
            current_end = None
            current_text_parts = []
            
            for interval in tg_luu:
                text = interval.mark.strip()
                dur = interval.maxTime - interval.minTime
                
                if text and text not in SILENCE_LABELS:
                    if current_start is None:
                        current_start = interval.minTime
                    current_end = interval.maxTime
                    current_text_parts.append(text)
                else:
                    if current_start is not None:
                        if dur >= 1.0:
                            section_luus.append({
                                'start': current_start,
                                'end': current_end,
                                'text': " ".join(current_text_parts)
                            })
                            current_start = None
                            current_end = None
                            current_text_parts = []
                        else:
                            current_end = interval.maxTime
            if current_start is not None:
                section_luus.append({
                    'start': current_start,
                    'end': current_end,
                    'text': " ".join(current_text_parts)
                })

        # ==========================================
        # 1. 共通解析関数
        # ==========================================
        def analyze_tier(intervals_data, data_type):
            for item in intervals_data:
                start_t = item['start']
                end_t = item['end']
                text = item['text']
                if not text or text in SILENCE_LABELS:
                    continue

                mask_p = (pitch_times >= start_t) & (pitch_times <= end_t)
                p_vals_sub = pitch_vals[mask_p]
                p_vals_voiced = p_vals_sub[p_vals_sub > 0]
                
                mask_i = (int_times >= start_t) & (int_times <= end_t)
                i_vals_sub = int_vals[mask_i]

                if len(p_vals_voiced) > 0:
                    mean_f0 = np.nanmean(p_vals_voiced)
                    std_f0 = np.nanstd(p_vals_voiced)
                    max_f0 = np.nanmax(p_vals_voiced)
                    min_f0 = np.nanmin(p_vals_voiced)
                    mean_f0_semi = 12 * math.log2(mean_f0 / 100.0) if mean_f0 > 0 else np.nan
                    std_f0_semi = 12 * math.log2(std_f0 / 100.0) if std_f0 > 0 else np.nan
                else:
                    mean_f0 = std_f0 = max_f0 = min_f0 = mean_f0_semi = std_f0_semi = np.nan

                mean_int = np.nanmean(i_vals_sub) if len(i_vals_sub) > 0 else np.nan

                # --- Speech Rate ---
                dur = end_t - start_t
                moras = count_moras(tg_phones, start_t, end_t)
                speech_rate = moras / dur if dur > 0 else np.nan

                # --- VSA & 母音長 (IPAクリーニング対応) ---
                f1_means, f2_means = {v: [] for v in ['a','i','u','e','o']}, {v: [] for v in ['a','i','u','e','o']}
                vowel_durs = []
                
                for ph_int in tg_phones:
                    if ph_int.minTime >= end_t: break
                    if ph_int.maxTime > start_t:
                        raw_mark = ph_int.mark.strip()
                        base_v = get_base_vowel(raw_mark)
                        
                        if base_v is not None:
                            ph_start, ph_end = max(start_t, ph_int.minTime), min(end_t, ph_int.maxTime)
                            v_dur = ph_end - ph_start
                            vowel_durs.append(v_dur)
                            
                            center_t = ph_start + v_dur / 2.0
                            snd_part = snd.extract_part(from_time=max(0, center_t-0.025), to_time=min(snd.get_total_duration(), center_t+0.025))
                            try:
                                fmt = snd_part.to_formant_burg(time_step=0.01, max_number_of_formants=5, maximum_formant=5500.0)
                                f1 = fmt.get_value_at_time(1, center_t - max(0, center_t-0.025))
                                f2 = fmt.get_value_at_time(2, center_t - max(0, center_t-0.025))
                                if not math.isnan(f1): f1_means[base_v].append(f1)
                                if not math.isnan(f2): f2_means[base_v].append(f2)
                            except: pass

                v_f1 = {v: np.nanmean(f1_means[v]) if f1_means[v] else np.nan for v in ['a','i','u','e','o']}
                v_f2 = {v: np.nanmean(f2_means[v]) if f2_means[v] else np.nan for v in ['a','i','u','e','o']}
                mean_v_dur = np.nanmean(vowel_durs) * 1000 if vowel_durs else np.nan

                vsa_area = np.nan
                v_list = ['a', 'e', 'i', 'u', 'o']
                pts_x = [v_f1[v] for v in v_list if not np.isnan(v_f1[v]) and not np.isnan(v_f2[v])]
                pts_y = [v_f2[v] for v in v_list if not np.isnan(v_f1[v]) and not np.isnan(v_f2[v])]
                if len(pts_x) >= 3:
                    vsa_area = 0.5 * np.abs(np.dot(pts_x, np.roll(pts_y, 1)) - np.dot(pts_y, np.roll(pts_x, 1)))

                # --- Terminal Rise Slope (IPAクリーニング対応) ---
                last_voiced_start = None
                last_voiced_end = None
                for ph_int in reversed(tg_phones):
                    if ph_int.maxTime <= start_t: break
                    if ph_int.minTime < end_t:
                        raw_mark = ph_int.mark.strip()
                        # 末尾付近の有声音を正確に判定
                        if ph_int.maxTime > end_t - 0.5 and is_voiced_phone(raw_mark):
                            last_voiced_start = ph_int.minTime
                            last_voiced_end = ph_int.maxTime
                            break
                
                rise_slope_hz = np.nan
                rise_slope_semi = np.nan
                if last_voiced_start and last_voiced_end:
                    rise_slope_hz, rise_slope_semi = calculate_rise_slope_5points(pitch, last_voiced_start, last_voiced_end)

                res = {
                    'BaseName': base_name, 'DataType': data_type, 'Text': text,
                    'StartTime': start_t, 'EndTime': end_t, 'Duration_ms': dur * 1000,
                    'SpeechRate': speech_rate,
                    'MeanF0_Hz': mean_f0, 'StdF0_Hz': std_f0,
                    'MaxF0_Hz': max_f0, 'MinF0_Hz': min_f0,
                    'MeanF0_Semitone': mean_f0_semi, 'StdF0_Semitone': std_f0_semi,
                    'TerminalRise_Slope_Hz': rise_slope_hz,
                    'TerminalRise_Slope_Semi': rise_slope_semi,
                    'MeanIntensity_dB': mean_int,
                    'MeanVowelDuration_ms': mean_v_dur,
                    'VSA_Area': vsa_area
                }
                for v in ['a','i','u','e','o']:
                    res[f'F1_{v}'] = v_f1[v]
                    res[f'F2_{v}'] = v_f2[v]
                results.append(res)

        # 解析実行
        analyze_tier(section_luus, 'Section_LUU')
        if tg_luu:
            luu_intervals = [{'start': i.minTime, 'end': i.maxTime, 'text': i.mark.strip()} for i in tg_luu]
            analyze_tier(luu_intervals, 'LUU')
        if tg_bunsetsu:
            bun_intervals = [{'start': i.minTime, 'end': i.maxTime, 'text': i.mark.strip()} for i in tg_bunsetsu]
            analyze_tier(bun_intervals, 'Bunsetsu')

        # ==========================================
        # 2. Local Emphasis (相槌等)
        # ==========================================
        for word in tg_words:
            w_text = word.mark.strip()
            if w_text in SILENCE_LABELS: continue
            
            w_start, w_end = word.minTime, word.maxTime
            mask_p_w = (pitch_times >= w_start) & (pitch_times <= w_end)
            p_vals_w = pitch_vals[mask_p_w]
            p_vals_w = p_vals_w[p_vals_w > 0]
            
            mask_i_w = (int_times >= w_start) & (int_times <= w_end)
            i_vals_w = int_vals[mask_i_w]

            w_f0 = np.nanmean(p_vals_w) if len(p_vals_w) > 0 else np.nan
            w_f0_semi = 12 * math.log2(w_f0 / 100.0) if w_f0 > 0 else np.nan
            w_int = np.nanmean(i_vals_w) if len(i_vals_w) > 0 else np.nan
            
            results.append({
                'BaseName': base_name, 'DataType': 'Local', 'Text': w_text,
                'StartTime': w_start, 'EndTime': w_end, 'Duration_ms': (w_end - w_start) * 1000,
                'Pitch_Hz': w_f0, 'Pitch_Semitone': w_f0_semi, 'Intensity_dB': w_int
            })

        df = pd.DataFrame(results)
        out_csv = os.path.join(RESULT_DIR, f"Result_Analysis_{base_name}.csv")
        df.to_csv(out_csv, index=False, encoding='utf-8-sig')
        print(f"  -> Saved: {out_csv}")

    except Exception as e:
        print(f"Error processing {base_name}: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    setup_directories()

    if len(sys.argv) >= 3:
        target_wav = sys.argv[1]
        target_tg = sys.argv[2]
        base = os.path.basename(target_tg).replace("Analysis_", "").strip()
        base = os.path.splitext(base)[0]
        process_single_pair(target_wav, target_tg, base)
    else:
        print("=== Auto Batch Acoustic Analysis ===")
        tg_files = glob.glob(os.path.join(ANALYSIS_DIR, "Analysis_*.TextGrid"))
        
        if not tg_files:
            print("No TextGrid files found in analysis folder.")
            sys.exit()

        for tg_path in tg_files:
            fname = os.path.basename(tg_path)
            base_name = fname.replace("Analysis_", "").replace(".TextGrid", "").strip()
            wav_name = f"{base_name}.wav"
            
            wav_path = os.path.join(ANALYSIS_DIR, wav_name)
            if not os.path.exists(wav_path):
                found_path = search_file_recursive(wav_name, DATA_SEARCH_ROOT)
                if found_path:
                    wav_path = found_path
                else:
                    print(f"  [Skipped] WAV file not found for {base_name}")
                    continue

            process_single_pair(wav_path, tg_path, base_name)
        print("All done.")