import pandas as pd
import numpy as np
import scipy.stats as stats
import os
import matplotlib.pyplot as plt
import seaborn as sns
import matplotlib.font_manager as fm
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats.multicomp import pairwise_tukeyhsd
import warnings
from statsmodels.tools.sm_exceptions import ConvergenceWarning

# 余計な警告を無視
warnings.simplefilter('ignore')

# ==========================================
# CONFIGURATION
# ==========================================
import matplotlib
matplotlib.use('Agg')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(BASE_DIR, "Comparison_Result", "anaTotal", "Total_File_Stats.csv")
OUTPUT_DIR = os.path.join(BASE_DIR, "Comparison_Result", "anaTest")

# Analysis Targets (CSVのカラム名と一致させる)
METRIC_BASES = {
    'Terminal Rise Slope (Hz)': 'SectionLUU_slope_hz',
    'Terminal Rise Slope (Semi)': 'SectionLUU_slope_semi',
    'Mean Pitch (Hz)': 'SectionLUU_mean_f0',
    'Std Pitch (Hz)': 'SectionLUU_std_f0',
    'Pitch Range (Hz)': 'SectionLUU_range_f0',
    'Speech Rate': 'SectionLUU_speech_rate',
    'Mean Vowel Duration': 'MeanVowelDur',
    'Backchannel Duration': 'BC_Duration',
    'Backchannel Pitch': 'BC_Pitch_Hz'
}
METRIC_SINGLE = {'VSA': 'VSA'}

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

def get_sig_char(p):
    if pd.isna(p): return "n.s."
    if p < 0.001: return "***"
    if p < 0.01: return "**"
    if p < 0.05: return "*"
    return "n.s."

def cohen_d(x, y):
    nx, ny = len(x), len(y)
    dof = nx + ny - 2
    if dof <= 0: return np.nan
    pooled_std = np.sqrt(((nx - 1) * np.var(x, ddof=1) + (ny - 1) * np.var(y, ddof=1)) / dof)
    return (np.mean(x) - np.mean(y)) / pooled_std if pooled_std > 0 else np.nan

def categorize_relation(rel_str):
    if not isinstance(rel_str, str): return "Other"
    families = ["家族", "母", "父", "娘", "息子", "妻", "夫", "兄弟", "姉妹", "孫", "祖父", "祖母", "親戚"]
    friends = ["友人", "知人", "友達", "同級生", "先輩", "後輩", "同僚", "仲間"]
    for f in families:
        if f in rel_str: return "Family"
    for f in friends:
        if f in rel_str: return "Friend"
    return "Other"

# ==========================================
# PREPARE DATASETS
# ==========================================
def prepare_data():
    print("Loading Data...")
    if not os.path.exists(INPUT_FILE):
        print(f"Input file not found: {INPUT_FILE}")
        return None
    
    df = pd.read_csv(INPUT_FILE)
    
    if 'Relation_Raw' in df.columns:
        df['Relation_Type'] = df['Relation_Raw'].apply(categorize_relation)
    else:
        df['Relation_Type'] = "Other"

    datasets = {}
    
    # --- 1. Ana1 (File-based) ---
    # 元のCSVにあるカラムをそのまま使用
    ana1_cols = METRIC_BASES.copy()
    ana1_cols.update(METRIC_SINGLE)
    
    # 欠損値を含む行を念のため確認（分析時にdropnaするが、ここではコピー）
    df_ana1 = df.copy()
    datasets['Ana1_File'] = (df_ana1, ana1_cols)
    
    # --- 2. Ana2 (Speaker-based Aggregation) ---
    # 話者ごとに「平均」をとって代表値とする
    grp_cols = ['SpeakerID', 'Condition', 'Gender', 'Relation_Type']
    
    # 集計対象のカラムリスト
    target_cols = list(METRIC_BASES.values()) + list(METRIC_SINGLE.values())
    
    # カラムが存在するかチェックしてフィルタリング
    valid_cols = [c for c in target_cols if c in df.columns]
    
    if not valid_cols:
        print("Error: No valid metric columns found in input CSV.")
        return datasets

    # 話者ごとの平均 (Mean of Files)
    # groupbyキーに含まれる欠損がある場合は除外されるため dropna等は適宜必要だが、
    # ここではgroupbyのデフォルト挙動（キーがNaNなら除外）に任せる
    # ただしGenderなどがNaNだと消えるので、fillnaしておくと安全
    df['Gender'] = df['Gender'].fillna('Unknown')
    df['Relation_Type'] = df['Relation_Type'].fillna('Other')
    
    df_spk_mean = df.groupby(grp_cols)[valid_cols].mean().reset_index()
    
    # マッピングは Ana1 と同じものを使用（カラム名は変わっていないため）
    datasets['Ana2_Speaker_Mean'] = (df_spk_mean, ana1_cols)
    
    return datasets

# ==========================================
# TEST RUNNERS
# ==========================================

def run_step1_welch(ds_name, df, metrics_map):
    print(f"[{ds_name}] Step 1: Welch t-test")
    subsets = [('All', df)]
    for g in ['Male', 'Female']: subsets.append((f'Gender_{g}', df[df['Gender']==g]))
    # RelationTypeがデータに含まれていれば追加分析
    if 'Relation_Type' in df.columns and df['Relation_Type'].nunique() > 1:
        for r in ['Family', 'Friend', 'Other']: subsets.append((f'Rel_{r}', df[df['Relation_Type']==r]))
    
    results = []
    for sub_name, sub_df in subsets:
        if sub_df.empty: continue
        g1 = sub_df[sub_df['Condition'] == "[Non-Elderly]"]
        g2 = sub_df[sub_df['Condition'] == "[Elderly]"]
        g3 = sub_df[sub_df['Condition'] == "[Late Elderly]"]
        
        pairs = [('[Non]vs[Eld]', g1, g2), ('[Non]vs[Late]', g1, g3)]
        
        for pair_name, d1, d2 in pairs:
            for label, col in metrics_map.items():
                if col not in sub_df.columns: continue
                v1, v2 = d1[col].dropna(), d2[col].dropna()
                if len(v1) < 2 or len(v2) < 2: continue
                
                try:
                    t, p = stats.ttest_ind(v2, v1, equal_var=False)
                    d_val = cohen_d(v2, v1)
                    sig = get_sig_char(p)
                    
                    if p < 0.05:
                        results.append({'Data': ds_name, 'Subset': sub_name, 'Pair': pair_name, 'Metric': label, 'p': p, 'd': d_val, 'Sig': sig})
                        
                        plt.figure(figsize=(5, 4))
                        comb = pd.concat([d1, d2])
                        # 順序を維持
                        order = [c for c in CONDITION_ORDER if c in comb['Condition'].unique()]
                        sns.barplot(data=comb, x='Condition', y=col, order=order, palette=PALETTE, capsize=0.1, hue='Condition', legend=False)
                        plt.title(f"{label} ({sub_name}) {pair_name}\nWelch: {sig}")
                        plt.tight_layout()
                        safe_name = f"S1_{ds_name}_{sub_name}_{pair_name}_{label.replace(' ','')}.png".replace('[','').replace(']','')
                        plt.savefig(os.path.join(OUTPUT_DIR, safe_name))
                        plt.close()
                except Exception as e:
                    pass

    if results: pd.DataFrame(results).to_csv(os.path.join(OUTPUT_DIR, f"Step1_Welch_{ds_name}.csv"), index=False)

def run_step2_paired(ds_name, df, metrics_map):
    # Ana2 (Speaker-based) のみ実施
    if "Ana2" not in ds_name: return
    print(f"[{ds_name}] Step 2: Paired Analysis")
    
    subsets = [('All', df)]
    for g in ['Male', 'Female']: subsets.append((f'Gender_{g}', df[df['Gender']==g]))

    results = []
    for sub_name, sub_df in subsets:
        if sub_df.empty: continue
        
        # SpeakerID と Condition で一意になっているはずだが念のため再集計は不要（Ana2ですでに集計済）
        
        for label, col in metrics_map.items():
            if col not in sub_df.columns: continue
            
            # Pivot table to align subjects
            try:
                pivoted = sub_df.pivot(index='SpeakerID', columns='Condition', values=col)
                pairs = [('[Non]vs[Eld]', "[Non-Elderly]", "[Elderly]"), 
                         ('[Non]vs[Late]', "[Non-Elderly]", "[Late Elderly]")]
                
                for pair_name, c1, c2 in pairs:
                    if c1 not in pivoted.columns or c2 not in pivoted.columns: continue
                    valid = pivoted[[c1, c2]].dropna()
                    if len(valid) < 3: continue
                    
                    v1, v2 = valid[c1], valid[c2]
                    t, p_t = stats.ttest_rel(v2, v1)
                    sig_t = get_sig_char(p_t)
                    
                    diff = v2 - v1
                    inc = (diff > 0).sum()
                    dec = (diff < 0).sum()
                    tie = (diff == 0).sum()
                    p_bin = stats.binomtest(inc, len(diff)-tie, p=0.5).pvalue
                    sig_b = get_sig_char(p_bin)
                    
                    if p_t < 0.05 or p_bin < 0.05:
                        results.append({'Data': ds_name, 'Subset': sub_name, 'Pair': pair_name, 'Metric': label, 'p_ttest': p_t, 'Sig_t': sig_t, 'p_binom': p_bin, 'Sig_b': sig_b})
                        
                        plt.figure(figsize=(6, 2))
                        total = inc+dec+tie
                        if total > 0:
                            plt.barh([0], [dec/total*100], color='tab:blue', label='Dec')
                            plt.barh([0], [tie/total*100], left=[dec/total*100], color='lightgray')
                            plt.barh([0], [inc/total*100], left=[(dec+tie)/total*100], color='tab:red', label='Inc')
                            plt.title(f"{label} ({sub_name}) {pair_name}\nPaired:{sig_t} Binom:{sig_b}")
                            plt.tight_layout()
                            safe_name = f"S2_{ds_name}_{sub_name}_{pair_name}_{label.replace(' ','')}.png".replace('[','').replace(']','')
                            plt.savefig(os.path.join(OUTPUT_DIR, safe_name))
                            plt.close()
            except Exception as e:
                # Pivot失敗時などはスキップ
                pass
                    
    if results: pd.DataFrame(results).to_csv(os.path.join(OUTPUT_DIR, f"Step2_Paired_{ds_name}.csv"), index=False)

def run_step3_anova(ds_name, df, metrics_map):
    print(f"[{ds_name}] Step 3: ANOVA 3-Group")
    subsets = [('All', df)]
    for g in ['Male', 'Female']: subsets.append((f'Gender_{g}', df[df['Gender']==g]))
    
    results = []
    plot_data = []
    
    for sub_name, sub_df in subsets:
        if sub_df.empty: continue
        d_3 = sub_df[sub_df['Condition'].isin(CONDITION_ORDER)]
        
        for label, col in metrics_map.items():
            if col not in d_3.columns: continue
            clean = d_3.dropna(subset=[col, 'Condition'])
            
            # 各群のデータリストを作成
            grps = []
            for c in CONDITION_ORDER:
                if c in clean['Condition'].unique():
                    grps.append(clean[clean['Condition']==c][col])
            
            if len(grps) < 3: continue
            
            try:
                f, p = stats.f_oneway(*grps)
                if p < 0.05:
                    tukey = pairwise_tukeyhsd(clean[col], clean['Condition'])
                    # Tukey結果の整理
                    res_data = pd.DataFrame(data=tukey._results_table.data[1:], columns=tukey._results_table.data[0])
                    sig_pairs = []
                    for _, r in res_data.iterrows():
                        if r['reject']: sig_pairs.append(f"{r['group1']}vs{r['group2']}")
                    
                    results.append({'Data': ds_name, 'Subset': sub_name, 'Metric': label, 'p': p, 'Pairs': ",".join(sig_pairs)})
                    plot_data.append((sub_name, label, col, clean, sig_pairs))
            except:
                pass

    # Mega Plot (サマリ画像)
    from collections import defaultdict
    plots_by_sub = defaultdict(list)
    for p in plot_data: plots_by_sub[p[0]].append(p)
    
    for sub_name, items in plots_by_sub.items():
        if not items: continue
        n = len(items)
        cols = 4
        rows = (n + cols - 1) // cols
        
        fig, axes = plt.subplots(rows, cols, figsize=(5*cols, 4*rows), squeeze=False)
        axes = axes.flatten()
        
        for i, (sname, lbl, c, d, pairs) in enumerate(items):
            ax = axes[i]
            order = [cond for cond in CONDITION_ORDER if cond in d['Condition'].unique()]
            sns.boxplot(data=d, x='Condition', y=c, order=order, palette=PALETTE, ax=ax, hue='Condition', legend=False)
            ax.set_title(f"{lbl}\nSig: {','.join(pairs)}", fontsize=8)
            ax.set_xlabel("")
        
        for j in range(i+1, len(axes)): axes[j].axis('off')
            
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, f"S3_Mega_{ds_name}_{sub_name}.png"))
        plt.close()
        
    if results: pd.DataFrame(results).to_csv(os.path.join(OUTPUT_DIR, f"Step3_ANOVA_{ds_name}.csv"), index=False)

def run_step4_lmm(ds_name, df, metrics_map):
    # Ana1 (File-based) で行うのが一般的（サンプル数確保のため）
    if "Ana1" not in ds_name: return
    print(f"[{ds_name}] Step 4: LMM")
    
    results = []
    targets = [("[Elderly]", "Eld"), ("[Late Elderly]", "Late")]
    
    for label, col in metrics_map.items():
        if col not in df.columns: continue
        
        for t_cond, t_name in targets:
            sub = df[df['Condition'].isin(["[Non-Elderly]", t_cond])].copy()
            clean = sub.dropna(subset=[col, 'Condition', 'SpeakerID'])
            # 収束のために最低限のデータ数をチェック
            if len(clean) < 10 or clean['SpeakerID'].nunique() < 2: continue
            
            try:
                # 警告抑制コンテキスト
                with warnings.catch_warnings():
                    warnings.filterwarnings("ignore")
                    # Conditionの参照レベルをNon-Elderlyに設定
                    model = smf.mixedlm(f"{col} ~ C(Condition, Treatment('[Non-Elderly]'))", clean, groups=clean["SpeakerID"])
                    fit = model.fit(reml=False) # REML=Falseの方が収束しやすい場合がある
                    
                    # 結果取得 (Interceptが0番目, Conditionが1番目)
                    p_val = fit.pvalues.iloc[1]
                    coef = fit.params.iloc[1]
                    
                    if p_val < 0.05:
                        sig = get_sig_char(p_val)
                        results.append({'Data': ds_name, 'Target': t_name, 'Metric': label, 'p': p_val, 'Coef': coef, 'Sig': sig})
            except Exception as e:
                # 収束しなかった場合などはスキップ
                pass
            
    if results: pd.DataFrame(results).to_csv(os.path.join(OUTPUT_DIR, f"Step4_LMM_{ds_name}.csv"), index=False)

def run_step5_interaction(ds_name, df, metrics_map):
    print(f"[{ds_name}] Step 5: Interaction")
    
    results = []
    targets = [("[Elderly]", "Eld"), ("[Late Elderly]", "Late")]
    
    for label, col in metrics_map.items():
        if col not in df.columns: continue
        
        for t_cond, t_name in targets:
            sub = df[df['Condition'].isin(["[Non-Elderly]", t_cond])].copy()
            clean = sub.dropna(subset=[col, 'Condition', 'Gender'])
            if len(clean) < 10: continue
            
            try:
                # 単純なOLSで交互作用を見る (LMMだと収束しにくいので傾向把握用)
                model = smf.ols(f"{col} ~ C(Condition) * C(Gender)", data=clean).fit()
                anova = sm.stats.anova_lm(model, typ=2)
                
                # 交互作用項を探す (通常は最後あるいは : を含む項)
                int_rows = [idx for idx in anova.index if ':' in idx]
                if not int_rows: continue
                idx = int_rows[0]
                
                p = anova.loc[idx, 'PR(>F)']
                
                if p < 0.05:
                    results.append({'Data': ds_name, 'Target': t_name, 'Metric': label, 'p_inter': p})
                    plt.figure(figsize=(5, 4))
                    sns.pointplot(data=clean, x='Condition', y=col, hue='Gender', order=["[Non-Elderly]", t_cond], capsize=0.1)
                    plt.title(f"Interaction: {label} ({t_name})\np={p:.4f}")
                    plt.tight_layout()
                    safe_name = f"S5_Int_{ds_name}_{t_name}_{label.replace(' ','')}.png".replace('[','').replace(']','')
                    plt.savefig(os.path.join(OUTPUT_DIR, safe_name))
                    plt.close()
            except: pass

    if results: pd.DataFrame(results).to_csv(os.path.join(OUTPUT_DIR, f"Step5_Interaction_{ds_name}.csv"), index=False)

# ==========================================
# MAIN
# ==========================================
def main():
    setup_dirs()
    set_japanese_font()
    
    datasets = prepare_data()
    if not datasets:
        print("No datasets prepared. Exiting.")
        return
    
    for name, (data, metrics) in datasets.items():
        run_step1_welch(name, data, metrics)
        run_step2_paired(name, data, metrics)
        run_step3_anova(name, data, metrics)
        run_step4_lmm(name, data, metrics)
        run_step5_interaction(name, data, metrics)
    
    print("All Comprehensive Tests Completed.")

if __name__ == "__main__":
    main()