import matplotlib
# 【重要】GUIバックエンドを使わず、画像保存専用のAggを使うことでクラッシュを防ぐ
matplotlib.use('Agg') 

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import argparse
import os
import matplotlib.font_manager as fm
import numpy as np
from matplotlib.lines import Line2D
import glob
import re

# --- 設定 ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULT_DIR = os.path.join(BASE_DIR, "Result")
COMPARISON_DIR = os.path.join(BASE_DIR, "Comparison_Result")
SESSION_CSV_PATH = os.path.join(BASE_DIR, "data_session.csv")

def set_japanese_font():
    target_fonts = ["MS Gothic", "Meiryo", "Yu Gothic", "Hiragino Sans", "TakaoGothic", "IPAGothic"]
    system_fonts = {f.name for f in fm.fontManager.ttflist}
    for font in target_fonts:
        if font in system_fonts:
            plt.rcParams['font.family'] = font
            return
    print("Warning: No Japanese font found.")

def save_csv_safe(df, path):
    try:
        df.to_csv(path)
        print(f"Saved CSV: {path}")
    except PermissionError:
        print(f"\n【Error】保存失敗: {path} (ファイルが開かれています)")

def save_plot_safe(fig, path):
    try:
        fig.savefig(path, bbox_inches='tight')
        plt.close(fig)
        print(f"Saved plot: {path}")
    except Exception as e:
        plt.close(fig)
        print(f"【Error】画像保存失敗: {path} ({e})")

def get_session_info():
    """data_session.csv から会話IDごとの属性情報を取得"""
    if not os.path.exists(SESSION_CSV_PATH):
        return {}
    
    try:
        try: df = pd.read_csv(SESSION_CSV_PATH, encoding='utf-8')
        except: df = pd.read_csv(SESSION_CSV_PATH, encoding='cp932')
        
        info_map = {}
        for _, row in df.iterrows():
            cid = str(row['会話ID']).strip()
            # フラグの取得
            is_elderly_only = row.get('対高齢者のみ', 0) == 1
            is_elderly_inc = row.get('対高齢者含む', 0) == 1
            is_late_elderly = row.get('対後期高齢者のみ', 0) == 1
            
            # 辞書として格納
            info_map[cid] = {
                'elderly_only': is_elderly_only,
                'elderly_inc': is_elderly_inc,
                'late_elderly': is_late_elderly
            }
        return info_map
    except Exception as e:
        print(f"Error reading session csv: {e}")
        return {}

def process_group(group_id, files, session_info):
    """1つのグループ（C001など）に対する比較分析と出力"""
    print(f"\n>>> Processing Group: {group_id} ({len(files)} files)")
    
    out_dir = os.path.join(COMPARISON_DIR, group_id)
    os.makedirs(out_dir, exist_ok=True)
    
    data_list = []
    
    for f in files:
        fname = os.path.basename(f)
        base = fname.replace("Result_Analysis_", "").replace(".csv", "")
        
        parts = base.split('_')
        if len(parts) >= 2 and parts[-1].startswith("IC"):
            conv_id = "_".join(parts[:-1])
        else:
            conv_id = base
            
        flags = session_info.get(conv_id)
        
        # タグの決定ロジックの修正
        tags_to_add = []
        if flags is None:
            tags_to_add.append("[Unknown]")
        else:
            # 1. 非対高齢者 (0-64歳のみ)
            if flags['elderly_inc'] == 0:
                tags_to_add.append("[Non-Elderly]")
            
            # 2. 対高齢者 (65歳以上を含む)
            if flags['elderly_only'] == 1:
                tags_to_add.append("[Elderly]")
                
            # 3. 対後期高齢者 (75歳以上を含む)
            if flags['late_elderly'] == 1:
                tags_to_add.append("[Late Elderly]")
                
        try:
            df_origin = pd.read_csv(f)
            # F0 Rangeの計算
            if 'MaxF0_Hz' in df_origin.columns and 'MinF0_Hz' in df_origin.columns:
                df_origin['F0_Range_Hz'] = df_origin['MaxF0_Hz'] - df_origin['MinF0_Hz']
            
            # 各タグごとにデータを登録
            for tag in tags_to_add:
                df = df_origin.copy()
                label = f"{base}\n{tag}"
                df['Source'] = label
                df['Condition'] = tag
                data_list.append(df)
                
        except Exception as e:
            print(f"Error reading {fname}: {e}")

    if not data_list: return

    df_all = pd.concat(data_list, ignore_index=True)
    unique_sources = df_all['Source'].unique()
    
    # 色設定
    conditions = df_all[['Source', 'Condition']].drop_duplicates().set_index('Source')['Condition'].to_dict()
    palette = {}
    
    cond_palette = {
        "[Non-Elderly]": "tab:blue",
        "[Elderly]": "tab:red",
        "[Late Elderly]": "tab:green",
        "[Mix]": "tab:purple",
        "[Unknown]": "gray"
    }
    
    n_non = len([c for c in conditions.values() if c=="[Non-Elderly]"])
    c_non = sns.color_palette("Blues", n_colors=n_non + 2)[2:]
    n_eld = len([c for c in conditions.values() if c=="[Elderly]"])
    c_elderly = sns.color_palette("Reds", n_colors=n_eld + 2)[2:]
    n_late = len([c for c in conditions.values() if c=="[Late Elderly]"])
    c_late = sns.color_palette("Greens", n_colors=n_late + 2)[2:] 
    n_other = len([c for c in conditions.values() if c not in ["[Elderly]", "[Non-Elderly]", "[Late Elderly]"]])
    c_other = sns.color_palette("Purples", n_colors=n_other + 2)[2:]
    
    ie, inon, ilate, ioth = 0, 0, 0, 0
    for src in unique_sources:
        cond = conditions[src]
        if cond == "[Elderly]":
            palette[src] = c_elderly[ie % len(c_elderly)]
            ie += 1
        elif cond == "[Late Elderly]":
            palette[src] = c_late[ilate % len(c_late)]
            ilate += 1
        elif cond == "[Non-Elderly]":
            palette[src] = c_non[inon % len(c_non)]
            inon += 1
        else:
            palette[src] = c_other[ioth % len(c_other)]
            ioth += 1

    condition_order = ["[Non-Elderly]", "[Elderly]", "[Late Elderly]", "[Mix]"]
    existing_conditions = [c for c in condition_order if c in conditions.values()]

    # ==========================================
    # 1. 平均値の集計 (Aggregation)
    # ==========================================
    
    summary_rows = []
    vowels = ['a', 'i', 'u', 'e', 'o'] # For VSA Formants

    for src in unique_sources:
        d = df_all[df_all['Source'] == src]
        
        def get_stats(data, prefix):
            stats = {}
            if data.empty: return stats
            
            # Terminal Rise Slope
            if 'TerminalRise_Slope_Hz' in data.columns:
                stats[f'{prefix}_Rise_Mean_Hz'] = data['TerminalRise_Slope_Hz'].mean()
            elif 'TerminalRise_Hz' in data.columns:
                stats[f'{prefix}_Rise_Mean_Hz'] = data['TerminalRise_Hz'].mean()
                
            if 'TerminalRise_Slope_Semi' in data.columns:
                stats[f'{prefix}_Rise_Mean_Semi'] = data['TerminalRise_Slope_Semi'].mean()
            
            # Basic Pitch Stats
            stats[f'{prefix}_MeanF0_Hz'] = data['MeanF0_Hz'].mean()
            
            # Intonation (Std) & Range
            if 'StdF0_Hz' in data.columns:
                stats[f'{prefix}_StdF0_Hz'] = data['StdF0_Hz'].mean()
            if 'F0_Range_Hz' in data.columns:
                stats[f'{prefix}_RangeF0_Hz'] = data['F0_Range_Hz'].mean()

            # Temporal & VSA
            stats[f'{prefix}_SpeechRate'] = data['SpeechRate'].mean()
            stats[f'{prefix}_VSA'] = data['VSA_Area'].mean()
            
            for v in vowels:
                f1_col = f"F1_{v}"
                f2_col = f"F2_{v}"
                if f1_col in data.columns:
                    stats[f'{prefix}_F1_{v}'] = data[f1_col].mean()
                if f2_col in data.columns:
                    stats[f'{prefix}_F2_{v}'] = data[f2_col].mean()

            # Intensity & Vowel Duration
            stats[f'{prefix}_Intensity'] = data['MeanIntensity_dB'].mean()
            if 'MeanVowelDuration_ms' in data.columns:
                stats[f'{prefix}_MeanVowelDur'] = data['MeanVowelDuration_ms'].mean()
                
            return stats

        row = {'ID': src, 'Condition': conditions[src]}
        # 【変更】 Section_LUU (発話全体) でのStatsを取得。プレフィックスは SecLUU
        row.update(get_stats(d[d['DataType']=='Section_LUU'], 'SecLUU'))
        row.update(get_stats(d[d['DataType']=='LUU'], 'LUU'))
        row.update(get_stats(d[d['DataType']=='Bunsetsu'], 'Bun'))
        
        # Backchannel (相槌) Analysis
        loc_un = d[(d['DataType']=='Local') & (d['Text']=='うん')]
        row['Loc_Un_Count'] = len(loc_un)
        if not loc_un.empty:
            row['Loc_Un_Pitch_Hz'] = loc_un['Pitch_Hz'].mean()
            row['Loc_Un_Dur_ms'] = loc_un['Duration_ms'].mean()
            if 'Intensity_dB' in loc_un.columns:
                row['Loc_Un_Intensity_dB'] = loc_un['Intensity_dB'].mean()
        
        summary_rows.append(row)
    
    df_summary_file = pd.DataFrame(summary_rows)
    save_csv_safe(df_summary_file.set_index('ID'), os.path.join(out_dir, f"Summary_By_File_{group_id}.csv"))

    # 条件ごとの平均値 (Summary_By_Condition)
    if not df_summary_file.empty and 'Condition' in df_summary_file.columns:
        numeric_cols = df_summary_file.select_dtypes(include=[np.number]).columns
        df_summary_cond = df_summary_file.groupby('Condition')[numeric_cols].agg(['mean', 'std', 'count'])
        df_summary_cond = df_summary_cond.reindex(existing_conditions)
        save_csv_safe(df_summary_cond, os.path.join(out_dir, f"Summary_By_Condition_{group_id}.csv"))

        # --- 平均値の比較グラフ (Bar Plot) ---
        target_metrics = {
            'SecLUU_MeanF0_Hz': 'Mean F0 (Hz)',
            'SecLUU_StdF0_Hz': 'Intonation/Std F0 (Hz)',
            'SecLUU_RangeF0_Hz': 'Pitch Range (Hz)',
            'SecLUU_SpeechRate': 'Speech Rate (mora/s)',
            'SecLUU_VSA': 'Vowel Space Area (Hz^2)',
            'SecLUU_Rise_Mean_Hz': 'Terminal Rise Slope (Hz/s)',
            'SecLUU_Intensity': 'Mean Intensity (dB)',
            'SecLUU_MeanVowelDur': 'Mean Vowel Duration (ms)',
            'Loc_Un_Pitch_Hz': 'Backchannel Pitch (Hz)',
            'Loc_Un_Intensity_dB': 'Backchannel Intensity (dB)'
        }
        
        valid_metrics = {k: v for k, v in target_metrics.items() if k in df_summary_file.columns}
        
        if valid_metrics:
            n_cols = 3
            n_rows = (len(valid_metrics) + n_cols - 1) // n_cols
            fig, axes = plt.subplots(n_rows, n_cols, figsize=(5 * n_cols, 5 * n_rows))
            axes = axes.flatten()
            
            for i, (col, title) in enumerate(valid_metrics.items()):
                sns.barplot(x='Condition', y=col, hue='Condition', data=df_summary_file, 
                            ax=axes[i], palette=cond_palette, capsize=.1, legend=False,
                            order=existing_conditions)
                axes[i].set_title(title)
                axes[i].set_ylabel("")
            
            for j in range(len(valid_metrics), len(axes)): axes[j].axis('off')

            plt.tight_layout()
            save_plot_safe(fig, os.path.join(out_dir, "bar_mean_comparison.png"))

    # ==========================================
    # 2. 分布の可視化 (Distribution)
    # ==========================================
    
    def plot_box(y_col, title, fname):
        plot_data = df_all[df_all['DataType'].isin(['Section_LUU', 'LUU', 'Bunsetsu'])].copy()
        if y_col not in plot_data.columns: return
        plt.figure(figsize=(max(10, len(unique_sources)*2), 6))
        sns.boxplot(x='Source', y=y_col, hue='DataType', data=plot_data, palette='Set2')
        plt.title(f'{title} Distribution - {group_id}')
        plt.xticks(rotation=45)
        plt.tight_layout()
        save_plot_safe(plt.gcf(), os.path.join(out_dir, fname))

    # Existing Boxplots
    tr_col = 'TerminalRise_Slope_Hz' if 'TerminalRise_Slope_Hz' in df_all.columns else 'TerminalRise_Hz'
    tr_title = 'Terminal Rise Slope (Hz/s)' if 'Slope' in tr_col else 'Terminal Rise (Hz)'
    plot_box(tr_col, tr_title, 'dist_box_terminal_rise.png')
    plot_box('TerminalRise_Slope_Semi', 'Terminal Rise Slope (ST/s)', 'dist_box_terminal_rise_semi.png')
    plot_box('SpeechRate', 'Speech Rate (mora/s)', 'dist_box_speed.png')
    plot_box('VSA_Area', 'Vowel Space Area (Hz^2)', 'dist_box_vsa.png')
    plot_box('MeanIntensity_dB', 'Intensity (dB)', 'dist_box_intensity.png')
    plot_box('MeanVowelDuration_ms', 'Vowel Duration (ms)', 'dist_box_vowel_dur.png')
    plot_box('StdF0_Hz', 'Intonation/Std F0 (Hz)', 'dist_box_std_f0.png')
    plot_box('F0_Range_Hz', 'Pitch Range (Hz)', 'dist_box_range_f0.png')

    # Terminal Rise Slope Detail (Sec_LUU/LUU/Bun) Barplots
    rise_cols = [c for c in df_all.columns if 'TerminalRise_Slope' in c]
    if rise_cols:
        col_hz = 'TerminalRise_Slope_Hz'
        if col_hz in df_all.columns:
            plt.figure(figsize=(max(10, len(unique_sources)*2), 6))
            plot_data = df_all[df_all['DataType'].isin(['Section_LUU', 'LUU', 'Bunsetsu'])].copy()
            sns.barplot(x='Source', y=col_hz, hue='DataType', data=plot_data, 
                        palette='Set2', capsize=.1, errorbar='se')
            plt.title(f'Terminal Rise Slope (Hz/s) by DataType - {group_id}')
            plt.xticks(rotation=45)
            plt.tight_layout()
            save_plot_safe(plt.gcf(), os.path.join(out_dir, 'bar_terminal_rise_hz_detail.png'))
        
        col_semi = 'TerminalRise_Slope_Semi'
        if col_semi in df_all.columns:
            plt.figure(figsize=(max(10, len(unique_sources)*2), 6))
            plot_data = df_all[df_all['DataType'].isin(['Section_LUU', 'LUU', 'Bunsetsu'])].copy()
            sns.barplot(x='Source', y=col_semi, hue='DataType', data=plot_data, 
                        palette='Set2', capsize=.1, errorbar='se')
            plt.title(f'Terminal Rise Slope (ST/s) by DataType - {group_id}')
            plt.xticks(rotation=45)
            plt.tight_layout()
            save_plot_safe(plt.gcf(), os.path.join(out_dir, 'bar_terminal_rise_semi_detail.png'))

    # Histograms
    sec_data = df_all[df_all['DataType'] == 'Section_LUU']
    if not sec_data.empty:
        fig, axes = plt.subplots(2, 2, figsize=(14, 10))
        cols = [('MeanF0_Semitone', 'Mean Pitch (Semi)'), ('StdF0_Semitone', 'Intonation (Semi)'),
                ('MeanF0_Hz', 'Mean Pitch (Hz)'), ('StdF0_Hz', 'Intonation (Hz)')]
        for i, (col, title) in enumerate(cols):
            ax = axes[i//2, i%2]
            if col in sec_data.columns:
                sns.histplot(data=sec_data, x=col, hue='Source', palette=palette, kde=True, element="step", fill=True, alpha=0.3, ax=ax)
                ax.set_title(title)
        plt.tight_layout()
        save_plot_safe(fig, os.path.join(out_dir, 'dist_hist_pitch.png'))
        
        if 'F0_Range_Hz' in sec_data.columns:
            plt.figure(figsize=(10, 6))
            sns.histplot(data=sec_data, x='F0_Range_Hz', hue='Source', palette=palette, kde=True, element="step", fill=True, alpha=0.3)
            plt.title('Pitch Range Distribution (Hz)')
            save_plot_safe(plt.gcf(), os.path.join(out_dir, 'dist_hist_f0_range.png'))

    # VSA Scatter/Polygon (Individual Session)
    markers = {'a': 'o', 'i': '^', 'u': 's', 'e': 'D', 'o': 'X'}
    plt.figure(figsize=(10, 10))
    for src in unique_sources:
        d = sec_data[sec_data['Source'] == src]
        c = palette[src]
        for v in vowels:
            f1, f2 = f"F1_{v}", f"F2_{v}"
            if f1 in d.columns:
                m1, m2 = d[f1].mean(), d[f2].mean()
                if not np.isnan(m1):
                    plt.scatter(m1, m2, color=c, marker=markers[v], s=150, edgecolors='black', label=f"{src}-{v}")
    src_proxies = [Line2D([0], [0], marker='o', color='w', markerfacecolor=palette[s], label=s) for s in unique_sources]
    plt.legend(handles=src_proxies, title="Source")
    plt.title(f"VSA Mean Scatter - {group_id}")
    plt.xlabel("F1"); plt.ylabel("F2")
    plt.gca().invert_xaxis(); plt.gca().invert_yaxis()
    save_plot_safe(plt.gcf(), os.path.join(out_dir, 'dist_vsa_scatter.png'))

    plt.figure(figsize=(8, 8))
    v_order = ['i', 'e', 'a', 'o', 'u']
    for src in unique_sources:
        d = sec_data[sec_data['Source'] == src]
        c = palette[src]
        pts_f1, pts_f2 = [], []
        for v in v_order:
            f1, f2 = f"F1_{v}", f"F2_{v}"
            if f1 in d.columns:
                m1, m2 = d[f1].mean(), d[f2].mean()
                if not np.isnan(m1): pts_f1.append(m1); pts_f2.append(m2)
        if len(pts_f1) >= 3:
            pts_f1.append(pts_f1[0]); pts_f2.append(pts_f2[0])
            plt.plot(pts_f1, pts_f2, color=c, linewidth=2, marker='o', label=src)
    plt.title(f"VSA Polygon - {group_id}")
    plt.xlabel("F1"); plt.ylabel("F2")
    plt.gca().invert_xaxis(); plt.gca().invert_yaxis()
    plt.legend()
    save_plot_safe(plt.gcf(), os.path.join(out_dir, 'dist_vsa_polygon.png'))

    # Local Emphasis (Backchannel) Boxplots
    loc_un = df_all[(df_all['DataType'] == 'Local') & (df_all['Text'] == 'うん')]
    if not loc_un.empty:
        fig, axes = plt.subplots(1, 3, figsize=(18, 5))
        sns.boxplot(x='Source', y='Intensity_dB', hue='Source', data=loc_un, palette=palette, ax=axes[0], legend=False)
        axes[0].set_title('Intensity')
        sns.boxplot(x='Source', y='Pitch_Semitone', hue='Source', data=loc_un, palette=palette, ax=axes[1], legend=False)
        axes[1].set_title('Pitch')
        sns.boxplot(x='Source', y='Duration_ms', hue='Source', data=loc_un, palette=palette, ax=axes[2], legend=False)
        axes[2].set_title('Duration')
        plt.tight_layout()
        save_plot_safe(fig, os.path.join(out_dir, 'dist_local_emphasis.png'))

def main():
    set_japanese_font()
    if not os.path.exists(RESULT_DIR): return
    csv_files = glob.glob(os.path.join(RESULT_DIR, "Result_Analysis_*.csv"))
    if not csv_files: return
    session_info = get_session_info()
    groups = {}
    for f in csv_files:
        fname = os.path.basename(f)
        base = fname.replace("Result_Analysis_", "")
        prefix = base.split('_')[0]
        if prefix not in groups: groups[prefix] = []
        groups[prefix].append(f)
    
    valid_groups = {}
    for gid, files in groups.items():
        has_baseline = False
        has_target = False
        for f in files:
            fname = os.path.basename(f)
            base = fname.replace("Result_Analysis_", "").replace(".csv", "")
            parts = base.split('_')
            if len(parts) >= 2 and parts[-1].startswith("IC"): conv_id = "_".join(parts[:-1])
            else: conv_id = base
            info = session_info.get(conv_id)
            if info:
                if not info['elderly_inc']: has_baseline = True
                if info['elderly_only']: has_target = True
        if has_baseline and has_target: valid_groups[gid] = files
        else: print(f"Skipping Group {gid}: Missing Baseline or Target data.")
    
    for gid, files in valid_groups.items():
        process_group(gid, files, session_info)
    print("\n=== All Analysis Comparisons Completed ===")

if __name__ == "__main__":
    main()