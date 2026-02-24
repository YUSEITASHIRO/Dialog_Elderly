import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os
import glob
import numpy as np
import matplotlib.font_manager as fm
import re

# ==========================================
# 設定
# ==========================================
import matplotlib
matplotlib.use('Agg')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COMPARISON_DIR = os.path.join(BASE_DIR, "Comparison_Result")
SESSION_CSV_PATH = os.path.join(BASE_DIR, "data_session.csv")
PARTICIPANT_CSV_PATH = os.path.join(BASE_DIR, "data_participant.csv")

OUTPUT_DIR = os.path.join(COMPARISON_DIR, "total")

# 【拡張】分析対象の指標を28項目にフル解禁 (Sec_ は SecLUU_ に変更)
TARGET_METRICS = {
    'SecLUU_SpeechRate': 'Speech Rate - SecLUU (mora/s)',
    'LUU_SpeechRate': 'Speech Rate - LUU (mora/s)',
    'Bun_SpeechRate': 'Speech Rate - Bunsetsu (mora/s)',
    'SecLUU_MeanF0_Hz': 'Mean F0 - SecLUU (Hz)',
    'SecLUU_StdF0_Hz': 'Intonation (Std F0) - SecLUU (Hz)',
    'SecLUU_RangeF0_Hz': 'Pitch Range - SecLUU (Hz)',
    'Bun_MeanF0_Hz': 'Mean F0 - Bunsetsu (Hz)',
    'Bun_StdF0_Hz': 'Intonation (Std F0) - Bunsetsu (Hz)',
    'SecLUU_MeanF0_Semi': 'Mean F0 (Semitone)',
    'SecLUU_StdF0_Semi': 'Intonation (Semitone)',
    'SecLUU_Rise_Mean_Hz': 'Terminal Rise - SecLUU (Hz/s)',
    'Bun_Rise_Mean_Hz': 'Terminal Rise - Bunsetsu (Hz/s)',
    'SecLUU_Rise_Mean_Semi': 'Terminal Rise - SecLUU (ST/s)',
    'Bun_Rise_Mean_Semi': 'Terminal Rise - Bunsetsu (ST/s)',
    'SecLUU_Intensity': 'Mean Intensity - SecLUU (dB)',
    'LUU_Intensity': 'Mean Intensity - LUU (dB)',
    'Bun_Intensity': 'Mean Intensity - Bunsetsu (dB)',
    'SecLUU_MeanVowelDur': 'Mean Vowel Duration (ms)',
    'SecLUU_VSA': 'Vowel Space Area (Hz^2)',
    'Loc_Un_Count': 'Backchannel Count',
    'Loc_Un_Dur_ms': 'Backchannel Duration (ms)',
    'Loc_Un_Pitch_Hz': 'Backchannel Pitch (Hz)',
    'Loc_Un_Intensity_dB': 'Backchannel Intensity (dB)'
}

CONDITION_ORDER = ["[Non-Elderly]", "[Elderly]", "[Late Elderly]", "[Mix]"]
PALETTE = {
    "[Non-Elderly]": "tab:blue",
    "[Elderly]": "tab:red",
    "[Late Elderly]": "tab:green",
    "[Mix]": "tab:purple",
    "[Unknown]": "gray"
}

# ==========================================
# ユーティリティ関数（元ファイルのまま完全維持）
# ==========================================
def set_japanese_font():
    target_fonts = ["MS Gothic", "Meiryo", "Yu Gothic", "Hiragino Sans", "TakaoGothic", "IPAGothic"]
    system_fonts = {f.name for f in fm.fontManager.ttflist}
    for font in target_fonts:
        if font in system_fonts:
            plt.rcParams['font.family'] = font
            return

def parse_age(age_str):
    if pd.isna(age_str): return np.nan
    age_str = str(age_str).replace("歳", "")
    if "以上" in age_str: return int(re.findall(r'\d+', age_str)[0]) + 5 if re.findall(r'\d+', age_str) else np.nan
    if "-" in age_str:
        try: l, h = map(int, age_str.split('-')); return (l + h) / 2
        except: pass
    try: return float(age_str)
    except: return np.nan

def categorize_relation_simple(rel_str):
    if not isinstance(rel_str, str) or '・' in rel_str or ',' in rel_str: return np.nan
    if '家族' in rel_str: return 'Family'
    if '友人' in rel_str or '知人' in rel_str: return 'Friend'
    if '同僚' in rel_str or '仕事' in rel_str: return 'Colleague'
    return 'Other'

def categorize_speaker_count(count):
    if pd.isna(count): return np.nan
    try:
        c = int(count)
        if c == 2: return '1. 2 (Dyad)'
        elif 3 <= c <= 4: return '2. 3-4 (Small Group)'
        elif c >= 5: return '3. 5+ (Large Group)'
        else: return 'Other'
    except: return np.nan

def load_metadata():
    try: df_ses = pd.read_csv(SESSION_CSV_PATH, encoding='utf-8')
    except: df_ses = pd.read_csv(SESSION_CSV_PATH, encoding='cp932')
    df_ses.columns = [c.strip() for c in df_ses.columns]

    try: df_par = pd.read_csv(PARTICIPANT_CSV_PATH, encoding='utf-8')
    except: df_par = pd.read_csv(PARTICIPANT_CSV_PATH, encoding='cp932')
    df_par.columns = [c.strip() for c in df_par.columns]
    df_par['Age_Num'] = df_par['年齢'].apply(parse_age)
    return df_ses, df_par

def get_attributes(row_id, df_ses, df_par):
    base_id = row_id.split('\n')[0].strip()
    match = re.match(r'(.+)_(IC\d+|Z\d+[A-Z]?)', base_id)
    if not match:
        parts = base_id.split('_')
        conv_id = "_".join(parts[:-1])
        spk_ic = parts[-1]
    else:
        conv_id = match.group(1)
        spk_ic = match.group(2)

    attrs = {}
    if df_ses is not None:
        ses_row = df_ses[df_ses['会話ID'] == conv_id]
        if not ses_row.empty:
            raw_rel = ses_row.iloc[0].get('話者間の関係性', 'Unknown')
            attrs['Relation'] = raw_rel
            attrs['Relation_Simple'] = categorize_relation_simple(raw_rel)
            spk_cnt = ses_row.iloc[0].get('話者数', np.nan)
            attrs['SpeakerCount'] = spk_cnt
            attrs['SpeakerCount_Group'] = categorize_speaker_count(spk_cnt)
            attrs['Place'] = ses_row.iloc[0].get('場所', 'Unknown')
    
    if df_par is not None:
        par_row = df_par[(df_par['会話ID'] == conv_id) & (df_par['話者IC'] == spk_ic)]
        my_age = np.nan
        if not par_row.empty:
            my_age = par_row.iloc[0].get('Age_Num', np.nan)
            attrs['Gender'] = par_row.iloc[0].get('性別', 'Unknown')
            attrs['My_Age_Group'] = par_row.iloc[0].get('年齢', 'Unknown')
        
        if not np.isnan(my_age):
            others = df_par[(df_par['会話ID'] == conv_id) & (df_par['話者IC'] != spk_ic)]
            if not others.empty:
                diff = others['Age_Num'].mean() - my_age
                attrs['Age_Diff_Value'] = diff
                if diff >= 30: attrs['Age_Relation'] = '1. Older (30y+)'
                elif diff >= 20: attrs['Age_Relation'] = '2. Older (20~29y)'
                elif diff >= 10: attrs['Age_Relation'] = '3. Older (10~19y)'
                elif diff >= 0: attrs['Age_Relation'] = '4. Older/Peer (0~9y)'
                else: attrs['Age_Relation'] = '5. Younger (<0y)'
                
                if diff >= 30: attrs['Age_Diff_3Group'] = '1. Older (30y+)'
                elif diff >= 0: attrs['Age_Diff_3Group'] = '2. Older (0~29y)'
                else: attrs['Age_Diff_3Group'] = '3. Younger (<0y)'
            else:
                attrs['Age_Relation'] = 'Solo/Unknown'
                attrs['Age_Diff_3Group'] = 'Solo/Unknown'
        else:
            attrs['Age_Relation'] = 'Unknown'
            attrs['Age_Diff_3Group'] = 'Unknown'
            
    return attrs

# ==========================================
# メイン処理（元ファイルのグラフ化コードを完全復活）
# ==========================================
def main():
    set_japanese_font()
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df_ses, df_par = load_metadata()

    summary_files = glob.glob(os.path.join(COMPARISON_DIR, "*", "Summary_By_File_*.csv"))
    if not summary_files: return
    
    df_list = []
    for f in summary_files:
        df = pd.read_csv(f)
        df['Group_ID'] = os.path.basename(os.path.dirname(f))
        df_list.append(df)
    
    df_total = pd.concat(df_list, ignore_index=True)
    if 'ID' not in df_total.columns: df_total.rename(columns={df_total.columns[0]: 'ID'}, inplace=True)

    attr_list = [get_attributes(row['ID'], df_ses, df_par) for _, row in df_total.iterrows()]
    df_total = pd.concat([df_total.reset_index(drop=True), pd.DataFrame(attr_list).reset_index(drop=True)], axis=1)
    df_total = df_total[df_total['Condition'].isin(["[Non-Elderly]", "[Elderly]", "[Late Elderly]"])]

    # 半音データ等の列名揺れ補正
    if 'SecLUU_MeanF0_Semitone' in df_total.columns: df_total['SecLUU_MeanF0_Semi'] = df_total['SecLUU_MeanF0_Semitone']
    if 'SecLUU_StdF0_Semitone' in df_total.columns: df_total['SecLUU_StdF0_Semi'] = df_total['SecLUU_StdF0_Semitone']

    df_total.to_csv(os.path.join(OUTPUT_DIR, "Total_Raw_Data.csv"), index=False)

    numeric_cols = [c for c in TARGET_METRICS.keys() if c in df_total.columns]
    summary_overall = df_total.groupby('Condition')[numeric_cols].agg(['mean', 'std', 'count', 'median'])
    summary_overall.to_csv(os.path.join(OUTPUT_DIR, "Total_Statistics_Summary.csv"))

    # --- 1. Overall Bar Comparison (元ファイルのまま) ---
    if numeric_cols:
        n_cols = 4
        n_rows = (len(numeric_cols) + n_cols - 1) // n_cols
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(6 * n_cols, 5 * n_rows))
        axes = axes.flatten()
        for i, col in enumerate(numeric_cols):
            sns.barplot(data=df_total, x='Condition', y=col, hue='Condition', legend=False,
                        order=[c for c in CONDITION_ORDER if c in df_total['Condition'].unique()],
                        palette=PALETTE, ax=axes[i], capsize=.1, errorbar='se')
            axes[i].set_title(f"Overall: {TARGET_METRICS.get(col, col)}")
            axes[i].set_xlabel(""); axes[i].set_ylabel("")
        for j in range(len(numeric_cols), len(axes)): axes[j].axis('off')
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, "Overall_Bar_Comparison.png"))
        plt.close()

    # --- 2. Cross Analysis (Boxplots) (元ファイルのまま) ---
    analysis_factors = {
        'Gender': 'Gender (Male/Female)',
        'Age_Relation': 'Age Difference (Detailed)',
        'Age_Diff_3Group': 'Age Difference (3 Groups)',
        'Relation': 'Relationship (Detailed)',
        'Relation_Simple': 'Relationship (Simple)',
        'SpeakerCount': 'Number of Speakers (Raw)',
        'SpeakerCount_Group': 'Number of Speakers (Group)'
    }
    for factor, factor_name in analysis_factors.items():
        if factor not in df_total.columns: continue
        df_sub = df_total.dropna(subset=[factor])
        if df_sub.empty: continue
        
        cross_stats = df_sub.groupby([factor, 'Condition'])[numeric_cols].mean()
        cross_stats.to_csv(os.path.join(OUTPUT_DIR, f"Summary_By_{factor}.csv"))
        
        for col in numeric_cols:
            plt.figure(figsize=(10, 6))
            if df_sub[factor].nunique() > 0:
                sns.boxplot(data=df_sub, x=factor, y=col, hue='Condition',
                            order=sorted(df_sub[factor].unique()),
                            hue_order=[c for c in CONDITION_ORDER if c in df_sub['Condition'].unique()],
                            palette=PALETTE, showfliers=False)
                plt.title(f"{TARGET_METRICS.get(col, col)} by {factor_name}")
                plt.tight_layout()
                plt.savefig(os.path.join(OUTPUT_DIR, f"Boxplot_{factor}_{col}.png"))
                plt.close()

    # --- 3. Speaker Differences (Delta Scatter) (元ファイルのまま) ---
    diff_rows = []
    for gid in df_total['Group_ID'].unique():
        g_data = df_total[df_total['Group_ID'] == gid]
        baseline = g_data[g_data['Condition'] == "[Non-Elderly]"][numeric_cols].mean()
        if baseline.isna().all(): continue
        for cond in ["[Elderly]", "[Late Elderly]"]:
            target_data = g_data[g_data['Condition'] == cond]
            if target_data.empty: continue
            diff = target_data[numeric_cols].mean() - baseline
            row = {'Group_ID': gid, 'Target_Condition': cond}
            row.update(diff.to_dict())
            row.update(g_data.iloc[0][['Gender', 'Age_Relation']].to_dict())
            diff_rows.append(row)
    if diff_rows:
        df_diff = pd.DataFrame(diff_rows)
        df_diff.to_csv(os.path.join(OUTPUT_DIR, "Speaker_Differences_Delta.csv"), index=False)
        for col in numeric_cols:
            plt.figure(figsize=(8, 6))
            sns.stripplot(data=df_diff, x='Target_Condition', y=col, hue='Gender', dodge=True, jitter=True, size=8, alpha=0.7, palette='Set1')
            plt.axhline(0, color='black', linestyle='--')
            plt.title(f"Delta: {TARGET_METRICS.get(col, col)}")
            plt.tight_layout()
            plt.savefig(os.path.join(OUTPUT_DIR, f"Delta_Scatter_{col}.png"))
            plt.close()

    # --- 4. Detailed Comparisons (SecLUU / LUU / Bun) (元ファイルのまま、Sec_をSecLUU_に変更) ---
    comparison_targets = {
        'Rise_Mean_Hz': ('Terminal Rise Slope (Hz/s)', ['SecLUU', 'LUU', 'Bun']),
        'Rise_Mean_Semi': ('Terminal Rise Slope (ST/s)', ['SecLUU', 'LUU', 'Bun']),
        'SpeechRate': ('Speech Rate (mora/s)', ['SecLUU', 'LUU', 'Bun'])
    }
    for metric_suffix, (title_base, types) in comparison_targets.items():
        cols = [f"{t}_{metric_suffix}" for t in types]
        valid_cols = [c for c in cols if c in df_total.columns]
        if not valid_cols: continue
        df_melt = df_total.melt(id_vars=['Condition'], value_vars=valid_cols, var_name='DataType', value_name='Value')
        df_melt['DataType'] = df_melt['DataType'].apply(lambda x: x.split('_')[0].replace('SecLUU', 'Section_LUU').replace('Bun', 'Bunsetsu'))
        plt.figure(figsize=(10, 6))
        sns.barplot(data=df_melt, x='Condition', y='Value', hue='DataType', order=[c for c in CONDITION_ORDER if c in df_melt['Condition'].unique()], palette='Set2', capsize=.1, errorbar='se')
        plt.title(f"Overall {title_base} by Unit")
        plt.ylabel(title_base)
        plt.tight_layout()
        save_name = "Hz" if "Hz" in metric_suffix else ("Semi" if "Semi" in metric_suffix else "Speed")
        plt.savefig(os.path.join(OUTPUT_DIR, f"Overall_{save_name}_Detail.png"))
        plt.close()

    # --- 5. Overall VSA Polygon (SecLUU) (元ファイルのまま) ---
    vowels = ['a', 'i', 'u', 'e', 'o']
    if all(f"SecLUU_F1_{v}" in df_total.columns and f"SecLUU_F2_{v}" in df_total.columns for v in vowels):
        plt.figure(figsize=(8, 8))
        v_order = ['i', 'e', 'a', 'o', 'u']
        for cond in CONDITION_ORDER:
            d = df_total[df_total['Condition'] == cond]
            if d.empty: continue
            pts_f1 = [d[f"SecLUU_F1_{v}"].mean() for v in v_order]
            pts_f2 = [d[f"SecLUU_F2_{v}"].mean() for v in v_order]
            if len(pts_f1) >= 3 and not np.isnan(pts_f1[0]):
                pts_f1.append(pts_f1[0]); pts_f2.append(pts_f2[0])
                plt.plot(pts_f1, pts_f2, marker='o', linewidth=2, label=cond, color=PALETTE[cond])
                for idx, v_char in enumerate(v_order):
                    plt.text(pts_f1[idx], pts_f2[idx], v_char, fontsize=12, fontweight='bold', color=PALETTE[cond])
        plt.title("Overall VSA Polygon Comparison (Section LUU)")
        plt.xlabel("F1 (Hz)"); plt.ylabel("F2 (Hz)")
        plt.gca().invert_xaxis(); plt.gca().invert_yaxis()
        plt.legend()
        plt.grid(True, linestyle='--', alpha=0.5)
        plt.savefig(os.path.join(OUTPUT_DIR, "Overall_VSA_Polygon.png"))
        plt.close()

    print("=== Total Analysis Completed (All Original Visualizations Restored & Expanded) ===")

if __name__ == "__main__":
    main()