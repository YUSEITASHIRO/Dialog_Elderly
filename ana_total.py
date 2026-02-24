import parselmouth
import textgrid
import pandas as pd
import numpy as np
import os
import glob
import re
import math
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.font_manager as fm

# ==========================================
# CONFIGURATION
# ==========================================
DATA_SEARCH_ROOT = r"E:\CEJC\data"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ANALYSIS_DIR = os.path.join(BASE_DIR, "analysis")
OUTPUT_DIR = os.path.join(BASE_DIR, "Comparison_Result", "anaTotal")
SESSION_CSV = os.path.join(BASE_DIR, "data_session.csv")
PARTICIPANT_CSV = os.path.join(BASE_DIR, "data_participant.csv")

# Constants
MORA_PHONES = {'a', 'i', 'u', 'e', 'o', 'N', 'q', 'A', 'I', 'U', 'E', 'O', 'Q', 'n', 'm', 'ng', 'ɴ'} 
VOWELS = {'a', 'i', 'u', 'e', 'o'}
VOWEL_MAP = {
    'a': 'a', 'A': 'a', 'ɐ': 'a', 'ɑ': 'a', 'aː': 'a',
    'i': 'i', 'I': 'i', 'ɪ': 'i', 'iː': 'i',
    'u': 'u', 'U': 'u', 'ɯ': 'u', 'ɨ': 'u', 'ʊ': 'u', 'uː': 'u',
    'e': 'e', 'E': 'e', 'ɛ': 'e', 'eː': 'e',
    'o': 'o', 'O': 'o', 'ɔ': 'o', 'oː': 'o'
}
SILENCE_LABELS = {"", "<eps>", "sil", "sp", "silent", "pause", "spn"}
BACKCHANNEL_TEXTS = ["うん", "はい"]
CONDITION_ORDER = ["[Non-Elderly]", "[Elderly]", "[Late Elderly]"]
PALETTE = {"[Non-Elderly]": "tab:blue", "[Elderly]": "tab:red", "[Late Elderly]": "tab:green"}

# ==========================================
# UTILS
# ==========================================
def setup_dirs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

def set_japanese_font():
    target_fonts = ["MS Gothic", "Meiryo", "Yu Gothic", "Hiragino Sans", "TakaoGothic", "IPAGothic"]
    system_fonts = {f.name for f in fm.fontManager.ttflist}
    for font in target_fonts:
        if font in system_fonts:
            plt.rcParams['font.family'] = font
            return

def search_file_recursive(filename, search_root):
    for root, dirs, files in os.walk(search_root):
        if filename in files:
            return os.path.join(root, filename)
    return None

def find_tier(tg, name_candidates):
    if isinstance(name_candidates, str): name_candidates = [name_candidates]
    for t in tg.tiers:
        if t.name in name_candidates: return t
    return None

def clean_phone(ph):
    return re.sub(r'[ːˑ̥ˌˈ̄́̀̆̂̌_0-9]', '', ph).strip()

def get_base_vowel(ph):
    cleaned = clean_phone(ph)
    return VOWEL_MAP.get(cleaned)

def hz_to_semi(hz):
    return 12 * np.log2(hz / 100.0) if hz > 0 else np.nan

def get_5point_slope(pitch_obj, start, end):
    if end <= start: return np.nan, np.nan
    times = np.linspace(start, end, 5)
    vals_hz = []
    vals_semi = []
    valid_t = []
    for t in times:
        v = pitch_obj.get_value_at_time(t)
        if not np.isnan(v) and v > 0:
            vals_hz.append(v)
            vals_semi.append(hz_to_semi(v))
            valid_t.append(t)
    if len(valid_t) >= 2:
        slope_hz = np.polyfit(valid_t, vals_hz, 1)[0]
        slope_semi = np.polyfit(valid_t, vals_semi, 1)[0]
        return slope_hz, slope_semi
    return np.nan, np.nan

def count_moras_in_interval(tg_phones, start, end):
    count = 0
    for p in tg_phones:
        if p.minTime >= end: break
        if p.maxTime > start:
            mark = p.mark.strip()
            if get_base_vowel(mark) or clean_phone(mark) in MORA_PHONES:
                count += 1
    return count

def get_vowel_data(tg_phones, snd, start, end):
    data = []
    total_dur = snd.get_total_duration()
    for p in tg_phones:
        if p.minTime >= end: break
        if p.maxTime > start:
            v = get_base_vowel(p.mark.strip())
            if v:
                p_start = max(start, p.minTime)
                p_end = min(end, p.maxTime)
                dur = p_end - p_start
                mid = p_start + dur/2
                try:
                    part_start = max(0, mid - 0.025)
                    part_end = min(total_dur, mid + 0.025)
                    part = snd.extract_part(part_start, part_end)
                    formant = part.to_formant_burg(maximum_formant=5500)
                    f1 = formant.get_value_at_time(1, mid - part_start)
                    f2 = formant.get_value_at_time(2, mid - part_start)
                    data.append({'vowel': v, 'dur': dur*1000, 'f1': f1, 'f2': f2})
                except: pass
    return data

# ==========================================
# CORE PROCESSING
# ==========================================
def process_files():
    print("Starting processing...")
    try:
        df_ses = pd.read_csv(SESSION_CSV, encoding='cp932')
        df_par = pd.read_csv(PARTICIPANT_CSV, encoding='cp932')
    except:
        df_ses = pd.read_csv(SESSION_CSV, encoding='utf-8')
        df_par = pd.read_csv(PARTICIPANT_CSV, encoding='utf-8')

    df_ses.columns = [c.strip() for c in df_ses.columns]
    df_par.columns = [c.strip() for c in df_par.columns]
    
    file_data_list = []
    tg_files = glob.glob(os.path.join(ANALYSIS_DIR, "Analysis_*.TextGrid"))
    
    if not tg_files:
        print("No TextGrid files found.")
        return pd.DataFrame()

    print(f"Found {len(tg_files)} files.")

    for tg_path in tg_files:
        base_name = os.path.basename(tg_path).replace("Analysis_", "").replace(".TextGrid", "").strip()
        wav_name = f"{base_name}.wav"
        wav_path = os.path.join(ANALYSIS_DIR, wav_name)
        if not os.path.exists(wav_path):
            wav_path = search_file_recursive(wav_name, DATA_SEARCH_ROOT)
        
        if not wav_path or not os.path.exists(wav_path):
            print(f"Skipping {base_name}: Wav not found.")
            continue
            
        print(f"Processing {base_name}...")
        try:
            snd = parselmouth.Sound(wav_path)
            pitch_obj = snd.to_pitch()
            tg = textgrid.TextGrid.fromFile(tg_path)
        except Exception as e:
            print(f"Error loading {base_name}: {e}")
            continue
            
        parts = base_name.split('_')
        match = re.match(r'(.+)_(IC\d+|Z\d+[A-Z]?|[A-Z]+\d+)', base_name)
        if match:
            conv_id = match.group(1)
            speaker_id = match.group(2)
        else:
            conv_id = parts[0]
            speaker_id = parts[-1] if len(parts) > 1 else "Unknown"
        
        conditions = []
        ses_row = df_ses[df_ses['会話ID'] == conv_id]
        if ses_row.empty:
            short_id = conv_id.split('_')[0]
            ses_row = df_ses[df_ses['会話ID'] == short_id]
            
        if not ses_row.empty:
            r = ses_row.iloc[0]
            # 非対高齢者
            if r.get('対高齢者含む') == 0:
                conditions.append("[Non-Elderly]")
            # 対高齢者 (65歳〜)
            if r.get('対高齢者のみ') == 1:
                conditions.append("[Elderly]")
            # 対後期高齢者 (75歳〜)
            if r.get('対後期高齢者のみ') == 1:
                conditions.append("[Late Elderly]")
        else:
            conditions.append("Unknown")

        gender = "Unknown"
        par_row = df_par[(df_par['会話ID'] == conv_id) & (df_par['話者IC'] == speaker_id)]
        if par_row.empty and '_' in conv_id:
             par_row = df_par[(df_par['会話ID'] == conv_id.split('_')[0]) & (df_par['話者IC'] == speaker_id)]

        if not par_row.empty:
            g = par_row.iloc[0].get('性別', 'Unknown')
            if g == '男性': gender = 'Male'
            elif g == '女性': gender = 'Female'
            else: gender = g
            
        tg_phones = find_tier(tg, ["phones", "phone"]) or tg.tiers[0]
        tg_bun = find_tier(tg, ["Bunsetsu", "bunsetsu"])
        tg_luu = find_tier(tg, ["LUU", "luu"]) or (tg.tiers[3] if len(tg.tiers)>3 else None)
        
        sec_luus = []
        if tg_luu:
            curr = []
            curr_start = 0
            for intv in tg_luu:
                txt = intv.mark.strip()
                if txt and txt not in SILENCE_LABELS:
                    if not curr: curr_start = intv.minTime
                    curr_end = intv.maxTime
                    curr.append(txt)
                else:
                    if curr and (intv.maxTime - intv.minTime >= 1.0):
                        sec_luus.append({'start': curr_start, 'end': curr_end})
                        curr = []
                    elif curr: curr_end = intv.maxTime
            if curr: sec_luus.append({'start': curr_start, 'end': curr_end})

        tier_data = {k: {'slope_hz':[], 'slope_semi':[], 
                         'mean_f0':[], 'std_f0':[], 'range_f0':[], 
                         'mean_f0_semi':[], 'std_f0_semi':[], 'range_f0_semi':[], 
                         'speech_rate':[]} 
                     for k in ['Section LUU', 'LUU', 'Bunsetsu']}
        
        pitch_times = pitch_obj.xs()
        pitch_vals = pitch_obj.selected_array['frequency']
        
        def analyze_interval(start, end, tier_name):
            dur = end - start
            if dur <= 0: return
            mask = (pitch_times >= start) & (pitch_times <= end)
            p_hz = pitch_vals[mask]
            p_hz = p_hz[p_hz > 0]
            if len(p_hz) > 0:
                tier_data[tier_name]['mean_f0'].append(np.mean(p_hz))
                tier_data[tier_name]['std_f0'].append(np.std(p_hz))
                tier_data[tier_name]['range_f0'].append(np.max(p_hz) - np.min(p_hz))
                p_semi = 12 * np.log2(p_hz / 100.0)
                tier_data[tier_name]['mean_f0_semi'].append(np.mean(p_semi))
                tier_data[tier_name]['std_f0_semi'].append(np.std(p_semi))
                tier_data[tier_name]['range_f0_semi'].append(np.max(p_semi) - np.min(p_semi))
            moras = count_moras_in_interval(tg_phones, start, end)
            tier_data[tier_name]['speech_rate'].append(moras / dur)
            target_start, target_end = None, None
            phones_in_range = [p for p in tg_phones if p.maxTime > start and p.minTime < end]
            if phones_in_range:
                for p in reversed(phones_in_range):
                    m = p.mark.strip()
                    if get_base_vowel(m) or clean_phone(m) in {'N', 'n', 'm', 'ng', 'ɴ'}:
                        target_start = max(start, p.minTime)
                        target_end = min(end, p.maxTime)
                        break
            if target_start:
                s_hz, s_s = get_5point_slope(pitch_obj, target_start, target_end)
                if not np.isnan(s_hz):
                    tier_data[tier_name]['slope_hz'].append(s_hz)
                    tier_data[tier_name]['slope_semi'].append(s_s)

        for i in sec_luus: analyze_interval(i['start'], i['end'], 'Section LUU')
        if tg_luu: 
            for i in tg_luu: 
                if i.mark.strip() not in SILENCE_LABELS: analyze_interval(i.minTime, i.maxTime, 'LUU')
        if tg_bun:
            for i in tg_bun:
                if i.mark.strip() not in SILENCE_LABELS: analyze_interval(i.minTime, i.maxTime, 'Bunsetsu')

        vowel_items = get_vowel_data(tg_phones, snd, 0, snd.get_total_duration())
        v_durs = [x['dur'] for x in vowel_items]
        file_v_means = {}
        for v in VOWELS:
            f1s = [x['f1'] for x in vowel_items if x['vowel']==v and not np.isnan(x['f1'])]
            f2s = [x['f2'] for x in vowel_items if x['vowel']==v and not np.isnan(x['f2'])]
            file_v_means[f'F1_{v}'] = np.mean(f1s) if f1s else np.nan
            file_v_means[f'F2_{v}'] = np.mean(f2s) if f2s else np.nan
        pts = []
        for v in ['i', 'e', 'a', 'o', 'u']:
            if not np.isnan(file_v_means[f'F1_{v}']): pts.append((file_v_means[f'F1_{v}'], file_v_means[f'F2_{v}']))
        vsa_area = 0.5 * np.abs(np.dot([p[0] for p in pts], np.roll([p[1] for p in pts], 1)) - np.dot([p[1] for p in pts], np.roll([p[0] for p in pts], 1))) if len(pts)>=3 else np.nan

        bc_durs, bc_pitch, bc_pitch_semi = [], [], []
        if tg_bun:
            for i in tg_bun:
                if i.mark.strip() in BACKCHANNEL_TEXTS:
                    dur = i.maxTime - i.minTime
                    bc_durs.append(dur * 1000)
                    mask = (pitch_times >= i.minTime) & (pitch_times <= i.maxTime)
                    p_vals = pitch_vals[mask]
                    p_vals = p_vals[p_vals > 0]
                    if len(p_vals) > 0:
                        bc_pitch.append(np.mean(p_vals))
                        bc_pitch_semi.append(np.mean(12 * np.log2(p_vals / 100.0)))

        # 【修正】カラム名を'SpeakerID'に統一して、groupby時のKeyErrorを防ぐ
        base_row = {
            'FileName': base_name, 'Gender': gender, 'SpeakerID': speaker_id, 'ConvID': conv_id,
            'MeanVowelDur': np.mean(v_durs) if v_durs else np.nan, 'VSA': vsa_area,
            'BC_Duration': np.mean(bc_durs) if bc_durs else np.nan,
            'BC_Pitch_Hz': np.mean(bc_pitch) if bc_pitch else np.nan,
            'BC_Pitch_Semi': np.mean(bc_pitch_semi) if bc_pitch_semi else np.nan
        }
        for k, v in file_v_means.items(): base_row[k] = v
        for tier in ['Section LUU', 'LUU', 'Bunsetsu']:
            prefix = tier.replace(' ', '')
            for m in ['slope_hz', 'slope_semi', 'mean_f0', 'std_f0', 'range_f0', 'mean_f0_semi', 'std_f0_semi', 'range_f0_semi', 'speech_rate']:
                vals = tier_data[tier][m]
                base_row[f'{prefix}_{m}'] = np.mean(vals) if vals else np.nan
        
        for c in conditions:
            row = base_row.copy()
            row['Condition'] = c
            file_data_list.append(row)

    df_files = pd.DataFrame(file_data_list)
    df_files.to_csv(os.path.join(OUTPUT_DIR, "Total_File_Stats.csv"), index=False)
    print(f"Data aggregation complete. Saved to Total_File_Stats.csv")
    return df_files

# ==========================================
# PLOTTING
# ==========================================
def generate_stats_and_plots(df):
    print("Generating Stats and Plots...")
    
    target_conds = [c for c in CONDITION_ORDER if c in df['Condition'].unique()]
    if not target_conds: return

    metrics_base = [
        ('slope_hz', 'Terminal Rise Slope (Hz_s)'), ('slope_semi', 'Terminal Rise Slope (Semi_s)'),
        ('mean_f0', 'Mean Pitch (Hz)'), ('mean_f0_semi', 'Mean Pitch (Semi)'),
        ('std_f0', 'Std Pitch (Hz)'), ('std_f0_semi', 'Std Pitch (Semi)'),
        ('range_f0', 'Pitch Range (Hz)'), ('range_f0_semi', 'Pitch Range (Semi)'),
        ('speech_rate', 'Speech Rate (mora_s)')
    ]
    tier_metrics = []
    for tier in ['SectionLUU', 'LUU', 'Bunsetsu']:
        for m, lbl in metrics_base:
            tier_metrics.append((f'{tier}_{m}', f'{tier} {lbl}'))
    
    other_metrics = [
        ('MeanVowelDur', 'Mean Vowel Duration (ms)'), ('VSA', 'VSA (Hz^2)'),
        ('BC_Duration', 'Backchannel Duration (ms)'), 
        ('BC_Pitch_Hz', 'Backchannel Pitch (Hz)'), ('BC_Pitch_Semi', 'Backchannel Pitch (Semi)')
    ]
    all_metrics = tier_metrics + other_metrics

    # 【確認】SpeakerIDカラムがあることを前提に集計
    num_cols = df.select_dtypes(include=[np.number]).columns
    df_spk = df.groupby(['ConvID', 'SpeakerID', 'Condition', 'Gender'])[num_cols].mean().reset_index()
    
    stats_rows = []

    def process_metric(data, col, label, ana_type):
        plot_data_mean = []
        plot_data_median = []
        
        for cond in target_conds:
            d_cond = data[data['Condition'] == cond]
            for gen in ['Male', 'Female', 'All']:
                d_target = d_cond if gen == 'All' else d_cond[d_cond['Gender'] == gen]
                vals = d_target[col].dropna()
                
                val_mean = vals.mean() if not vals.empty else np.nan
                val_med = vals.median() if not vals.empty else np.nan
                
                stats_rows.append({
                    'AnalysisType': ana_type, 'Metric': label, 
                    'Condition': cond, 'Gender': gen, 
                    'Mean': val_mean, 'Median': val_med
                })
                
                plot_data_mean.append({'Condition': cond, 'Gender': gen, 'Value': val_mean})
                plot_data_median.append({'Condition': cond, 'Gender': gen, 'Value': val_med})

        for stat_type, p_data in [('Mean', plot_data_mean), ('Median', plot_data_median)]:
            df_plot = pd.DataFrame(p_data)
            if df_plot.empty or df_plot['Value'].isna().all(): continue
            plt.figure(figsize=(8, 6))
            sns.barplot(data=df_plot, x='Condition', y='Value', hue='Gender', 
                        hue_order=['Male', 'Female', 'All'], palette='muted')
            plt.title(f"[{ana_type}] {label} ({stat_type})")
            plt.ylabel(label)
            plt.tight_layout()
            safe_col = col.replace(" ", "")
            plt.savefig(os.path.join(OUTPUT_DIR, f"{ana_type}_{safe_col}_{stat_type}.png"))
            plt.close()

    for col, label in all_metrics:
        if col in df.columns:
            process_metric(df, col, label, 'ana1')
            process_metric(df_spk, col, label, 'ana2')

    pd.DataFrame(stats_rows).to_csv(os.path.join(OUTPUT_DIR, "Total_Aggregated_Stats.csv"), index=False)

    v_order = ['i', 'e', 'a', 'o', 'u']
    for gen_filter in ['Male', 'Female', 'All']:
        plt.figure(figsize=(6, 6))
        d_gen = df if gen_filter == 'All' else df[df['Gender'] == gen_filter]
        
        plotted = False
        for cond in target_conds:
            d_c = d_gen[d_gen['Condition'] == cond]
            if d_c.empty: continue
            
            pts_x, pts_y = [], []
            valid_poly = True
            for v in v_order:
                f1 = d_c[f'F1_{v}'].mean()
                f2 = d_c[f'F2_{v}'].mean()
                if np.isnan(f1) or np.isnan(f2): valid_poly = False; break
                pts_x.append(f2) # X=F2
                pts_y.append(f1) # Y=F1
            
            if valid_poly:
                pts_x.append(pts_x[0]); pts_y.append(pts_y[0])
                color = PALETTE.get(cond, 'black')
                plt.plot(pts_x, pts_y, marker='o', label=cond, color=color, linewidth=2)
                for i, v in enumerate(v_order):
                    if i < len(pts_x)-1: plt.text(pts_x[i], pts_y[i], v, fontsize=12, fontweight='bold', color=color)
                plotted = True
        
        if plotted:
            plt.title(f"VSA Polygon ({gen_filter})")
            plt.xlabel("F2 (Hz)"); plt.ylabel("F1 (Hz)")
            plt.gca().invert_xaxis(); plt.gca().invert_yaxis()
            plt.legend(); plt.grid(True, linestyle='--', alpha=0.5); plt.tight_layout()
            plt.savefig(os.path.join(OUTPUT_DIR, f"VSA_Polygon_{gen_filter}.png"))
        plt.close()

if __name__ == "__main__":
    setup_dirs()
    set_japanese_font()
    df_results = process_files()
    if not df_results.empty:
        generate_stats_and_plots(df_results)
        print("Analysis Complete.")
    else:
        print("No data processed.")