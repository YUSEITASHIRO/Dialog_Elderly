import pandas as pd
import re
import os
import wave
import contextlib
import shutil
import subprocess
import argparse
import sys
import glob
import traceback
import time
import random

# --- 必須ライブラリチェック ---
try:
    import textgrid
    import MeCab
    import unidic_lite
    import soundfile as sf
    import librosa
except ImportError:
    print("【重要】以下のライブラリが必要です: pip install textgrid mecab-python3 unidic-lite soundfile librosa")
    sys.exit(1)

# --- 設定 ---
DATA_SEARCH_ROOT = r"D:\CEJC\data"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MFA_INPUT_BASE = os.path.join(BASE_DIR, "mfa_input")
MFA_OUTPUT_BASE = os.path.join(BASE_DIR, "mfa_output")
ANALYSIS_DIR = os.path.join(BASE_DIR, "analysis")
SESSION_CSV_PATH = os.path.join(BASE_DIR, "data_session.csv")

# MFA設定
MFA_ACOUSTIC_MODEL = "japanese_mfa"
MFA_DICTIONARY = "japanese_mfa"
MIN_UTTERANCE_DURATION = 0.3

# ==========================================
# ユーティリティ
# ==========================================
def search_file_recursive(filename, search_root):
    """Dドライブ内を再帰検索"""
    for root, dirs, files in os.walk(search_root):
        if filename in files:
            return os.path.join(root, filename)
    return None

def setup_directories():
    """必要な親ディレクトリのみ作成"""
    for d in [MFA_INPUT_BASE, MFA_OUTPUT_BASE, ANALYSIS_DIR]:
        os.makedirs(d, exist_ok=True)

def clean_mfa_text(text):
    text = str(text)
    text = re.sub(r'\([^)]*\)', '', text)
    text = re.sub(r'[ :%?。、？「」]', '', text)
    return text.strip()

def get_csv_columns(df):
    cols_norm = {c.strip().lower(): c for c in df.columns}
    s_col, e_col, t_col, spk_col = None, None, None, None
    for c in ['starttime', 'start', '開始時間']: 
        if c in cols_norm: s_col = cols_norm[c]; break
    for c in ['endtime', 'end', '終了時間']: 
        if c in cols_norm: e_col = cols_norm[c]; break
    for c in ['text', 'content', 'luu', '発話内容']: 
        if c in cols_norm: t_col = cols_norm[c]; break
    for c in ['speakerid', 'speaker', '話者']:
        if c in cols_norm: spk_col = cols_norm[c]; break
    if not (s_col and e_col and t_col):
        if len(df.columns) >= 3:
            s_col, e_col, t_col = df.columns[0], df.columns[1], df.columns[2]
    return s_col, e_col, t_col, spk_col

# ==========================================
# STEP 1: データ準備 (変換・配置)
# ==========================================
def prepare_data(wav_path, csv_path, speaker_id, target_folder_id=None, suffix="", force_speaker_id=None):
    # 出力先フォルダの決定
    dest_speaker_id = target_folder_id if target_folder_id else speaker_id
    speaker_dir = os.path.join(MFA_INPUT_BASE, dest_speaker_id)
    os.makedirs(speaker_dir, exist_ok=True)

    wav_base = os.path.basename(wav_path)
    if suffix:
        root, ext = os.path.splitext(wav_base)
        wav_out_name = f"{root}{suffix}{ext}"
    else:
        wav_out_name = wav_base

    target_wav = os.path.join(speaker_dir, wav_out_name)
    target_tg = os.path.splitext(target_wav)[0] + ".TextGrid"

    # WAV準備 (変換処理)
    # 単なるコピーではなく、MFAが読める形式(16kHz, PCM_16)に強制変換する
    if not os.path.exists(target_wav):
        try:
            # librosaで読み込み (sr=16000, mono=True でリサンプリング・モノラル化)
            y, sr = librosa.load(wav_path, sr=16000, mono=True)
            # soundfileで書き出し (subtype='PCM_16' で16bit整数化)
            sf.write(target_wav, y, sr, subtype='PCM_16')
        except Exception as e:
            print(f"  [Error] WAV Conversion failed: {wav_base} ({e})")
            return False

    # TextGrid生成
    try:
        try: df = pd.read_csv(csv_path, encoding='utf-8')
        except: df = pd.read_csv(csv_path, encoding='cp932')
        
        s_col, e_col, t_col, spk_col = get_csv_columns(df)
        
        if force_speaker_id is None:
            if spk_col:
                df = df[df[spk_col].astype(str).str.contains(speaker_id, na=False)].copy()
        
        intervals = []
        max_time = 0.0
        for _, row in df.iterrows():
            try:
                s = float(str(row[s_col]).replace('s',''))
                e = float(str(row[e_col]).replace('s',''))
                txt = clean_mfa_text(row[t_col])
                if e > max_time: max_time = e
                if not txt: continue
                if (e - s) < MIN_UTTERANCE_DURATION: continue
                intervals.append({'xmin': s, 'xmax': e, 'text': txt})
            except: continue
            
        if not intervals: return False
        
        # WAV長さを確認 (生成したファイルの長さを見る)
        try:
            with contextlib.closing(wave.open(target_wav, 'r')) as f:
                frames = f.getnframes()
                rate = f.getframerate()
                dur = frames / float(rate)
                if dur > max_time: max_time = dur
        except: pass
        
        tg = textgrid.TextGrid(maxTime=max_time)
        tier = textgrid.IntervalTier(name="words", maxTime=max_time)
        for i in intervals:
            try: tier.add(i['xmin'], i['xmax'], i['text'].replace('"', '""'))
            except: pass
        tg.append(tier)
        
        with open(target_tg, 'w', encoding='utf-8') as f: tg.write(f)
        return True
    except Exception as e:
        print(f"  [Error] TextGrid generation failed: {e}")
        return False

def remove_data(wav_path, speaker_id, suffix=""):
    """指定されたファイル(およびダミー)を入力フォルダから削除"""
    speaker_dir = os.path.join(MFA_INPUT_BASE, speaker_id)
    wav_base = os.path.basename(wav_path)
    if suffix:
        root, ext = os.path.splitext(wav_base)
        target_name = f"{root}{suffix}"
    else:
        target_name = os.path.splitext(wav_base)[0]
    
    for f in glob.glob(os.path.join(speaker_dir, f"{target_name}*")):
        try: os.remove(f)
        except: pass

# ==========================================
# STEP 2: MFA実行
# ==========================================
def run_mfa(speaker_id):
    input_dir = os.path.join(MFA_INPUT_BASE, speaker_id)
    output_dir = os.path.join(MFA_OUTPUT_BASE, speaker_id)
    os.makedirs(output_dir, exist_ok=True)

    if not hasattr(run_mfa, "downloaded"):
        subprocess.run(["mfa", "models", "download", "acoustic", MFA_ACOUSTIC_MODEL], check=False, capture_output=True)
        subprocess.run(["mfa", "models", "download", "dictionary", MFA_DICTIONARY], check=False, capture_output=True)
        run_mfa.downloaded = True

    cmd = [
        "mfa", "align", 
        input_dir, 
        MFA_DICTIONARY, 
        MFA_ACOUSTIC_MODEL, 
        output_dir,
        "--clean", "--overwrite",
        "-j", "4", 
        "--beam", "100", "--retry_beam", "400",
        "--one-pass",  # fMLLR有効
        "--verbose"
    ]

    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

# ==========================================
# STEP 3: 後処理
# ==========================================
def postprocess(wav_base_name, final_output_file, csv_path, speaker_id):
    if os.path.exists(final_output_file): return True

    mfa_out_dir = os.path.join(MFA_OUTPUT_BASE, speaker_id)
    target_tg_name = os.path.splitext(wav_base_name)[0] + ".TextGrid"
    mfa_tg_path = os.path.join(mfa_out_dir, target_tg_name)
    
    if not os.path.exists(mfa_tg_path): return False
    
    IGNORE = {"うん", "はい", "ええ", "あ", "えっと", "うーん", "<eps>", "sp", "sil"} 
    
    try:
        tagger = MeCab.Tagger()
        mfa_tg = textgrid.TextGrid.fromFile(mfa_tg_path)
        final_tg = textgrid.TextGrid(minTime=0, maxTime=mfa_tg.maxTime)
        
        luu_tier = textgrid.IntervalTier(name='luu', minTime=0, maxTime=mfa_tg.maxTime)
        bun_tier = textgrid.IntervalTier(name='bunsetsu', minTime=0, maxTime=mfa_tg.maxTime)
        
        words_src = None
        for t in mfa_tg:
            if t.name == "words": words_src = t; break
        if not words_src: words_src = mfa_tg[0]

        try: df = pd.read_csv(csv_path, encoding='utf-8')
        except: df = pd.read_csv(csv_path, encoding='cp932')
        s_col, e_col, t_col, spk_col = get_csv_columns(df)
        if spk_col: df = df[df[spk_col].astype(str).str.contains(speaker_id, na=False)].copy()
        df['clean'] = df[t_col].apply(clean_mfa_text)
        
        for _, row in df.sort_values(s_col).iterrows():
            if not row['clean']: continue
            s = float(str(row[s_col]).replace('s',''))
            e = float(str(row[e_col]).replace('s',''))
            
            targets = [w for w in words_src if w.mark and w.minTime >= s - 0.2 and w.minTime < e + 0.1 and w.mark not in IGNORE]
            if not targets: continue
            
            r_s, r_e = targets[0].minTime, targets[-1].maxTime
            if len(luu_tier) > 0 and r_s < luu_tier[-1].maxTime: r_s = luu_tier[-1].maxTime
            if r_s < r_e: luu_tier.add(r_s, r_e, row['clean'])
            
            full_txt = "".join([w.mark for w in targets])
            node = tagger.parseToNode(full_txt)
            chunks, curr, first = [], "", True
            while node:
                w = node.surface
                if w:
                    feats = node.feature.split(',')
                    if (feats[0] not in ['助詞', '助動詞', '接尾辞']) and not first:
                        chunks.append(curr); curr = w
                    else: curr += w
                    first = False
                node = node.next
            if curr: chunks.append(curr)
            
            w_i, c_acc = 0, 0
            for chk in chunks:
                b_len, got, b_s, b_e = len(chk), 0, None, None
                while got < b_len and w_i < len(targets):
                    w = targets[w_i]
                    if b_s is None: b_s = w.minTime
                    rem = len(w.mark) - c_acc
                    need = b_len - got
                    if rem <= need:
                        got += rem; b_e = w.maxTime; w_i += 1; c_acc = 0
                    else:
                        got += need; b_e = w.maxTime; c_acc += need
                if b_s is not None and b_e is not None:
                    if len(bun_tier) > 0 and b_s < bun_tier[-1].maxTime: b_s = bun_tier[-1].maxTime
                    if b_s < b_e: bun_tier.add(b_s, b_e, chk)

        final_tg.append(luu_tier)
        final_tg.append(bun_tier)
        for n in ['words', 'phones']:
            for t in mfa_tg:
                if n in t.name:
                    nt = textgrid.IntervalTier(name=n, minTime=0, maxTime=mfa_tg.maxTime)
                    for i in t: nt.addInterval(i)
                    final_tg.append(nt); break
        
        final_tg.write(final_output_file)
        return True
    except: return False

# ==========================================
# Main Logic
# ==========================================
def main():
    setup_directories()

    # --- Mode Decision ---
    single_mode = False
    data_range = None
    phase_start, phase_end = 1, 5  # Default Phase 1 to 5

    # 引数パース
    if len(sys.argv) >= 2:
        arg1 = sys.argv[1]
        
        if re.match(r'^\d+-\d+$', arg1):
            data_range = arg1
            if len(sys.argv) >= 3 and re.match(r'^\d+-\d+$', sys.argv[2]):
                ps, pe = map(int, sys.argv[2].split('-'))
                phase_start, phase_end = ps, pe
        
        elif len(sys.argv) >= 3:
            single_mode = True
        else:
            print("Usage: \n  Single: python ana_mfa_pipeline.py <wav> <csv>\n  Batch: python ana_mfa_pipeline.py [DataRange 1-100] [PhaseRange 1-5]")
            sys.exit(1)

    # --- Single Mode ---
    if single_mode:
        target_wav = sys.argv[1]
        target_csv = sys.argv[2]
        base = os.path.splitext(target_wav)[0]
        match = re.match(r'(.+)_(IC\d{2})', base, re.IGNORECASE)
        if not match:
            print("Error: Invalid filename format.")
            sys.exit(1)
        conv_id = match.group(1)
        spk_id = match.group(2)
        print(f"=== Single Mode: {target_wav} ===")
        w_path = search_file_recursive(target_wav, DATA_SEARCH_ROOT)
        c_path = search_file_recursive(target_csv, DATA_SEARCH_ROOT)
        if w_path and c_path:
            prepare_data(w_path, c_path, spk_id)
            if run_mfa(spk_id):
                final_file = os.path.join(ANALYSIS_DIR, f"Analysis_ {base}.TextGrid")
                postprocess(base, final_file, c_path, spk_id)
        return

    # --- Batch Mode ---
    if not os.path.exists(SESSION_CSV_PATH):
        print(f"Error: {SESSION_CSV_PATH} not found.")
        sys.exit(1)

    print(f"=== Robust Batch Processing Start (Phases {phase_start}-{phase_end}) ===")
    
    # 対象リスト取得
    try:
        try: df = pd.read_csv(SESSION_CSV_PATH, encoding='utf-8')
        except: df = pd.read_csv(SESSION_CSV_PATH, encoding='cp932')
        df.columns = [c.strip() for c in df.columns]
        
        # 1. プレフィックス(C001など)の抽出
        df['Prefix'] = df['会話ID'].astype(str).apply(lambda x: x.split('_')[0])
        
        # 2. 条件揃い判定 (Validation: Group must have BOTH conditions)
        # 対高齢者のみ=1 (Elderly) AND 対高齢者含む=0 (Non-Elderly) が同一グループ内に存在するか確認
        valid_prefixes = []
        for prefix, group in df.groupby('Prefix'):
            has_elderly = (group['対高齢者のみ'] == 1).any()
            has_non_elderly = (group['対高齢者含む'] == 0).any()
            
            # 両方の条件が揃っているグループのみを対象とする
            if has_elderly and has_non_elderly:
                valid_prefixes.append(prefix)
        
        print(f"Found {len(valid_prefixes)} valid conversation groups (Comparison Pairs).")

        # 3. ターゲット抽出 (Selectable Filter)
        # まずは有効なグループのみに絞る
        df_valid = df[df['Prefix'].isin(valid_prefixes)]
        
        # ユーザー指定の条件でフィルタリング (コメントアウトで切り替え)
        # ---------------------------------------------------------
        targets = df_valid[df_valid['対高齢者のみ'] == 1]
        #targets = df_valid[df_valid['対高齢者含む'] == 0]
        # ---------------------------------------------------------
        
        print(f"Target count after filtering: {len(targets)}")

    except:
        print("Error reading CSV or filtering targets")
        traceback.print_exc()
        sys.exit(1)

    # 範囲適用
    if data_range:
        s, e = map(int, data_range.split('-'))
        s = max(1, s)
        targets = targets.iloc[s-1:e]
        print(f"Range Filter Applied: {s} to {e} (Processing {len(targets)} items)")

    # 処理キュー作成
    tasks = []
    for _, row in targets.iterrows():
        tasks.append({
            'conv_id': str(row['会話ID']).strip(),
            'speaker_id': str(row['本人IC']).strip(),
            'wav_file': f"{str(row['会話ID']).strip()}_{str(row['本人IC']).strip()}.wav",
            'csv_file': f"{str(row['会話ID']).strip()}-luu.csv"
        })

    success_list = []
    failed_list = [] 

    # --- Phase 1: Normal Scan ---
    if phase_start <= 1 <= phase_end:
        print("\n>>> Phase 1: Normal Scan")
        for task in tasks:
            s_id = task['speaker_id']
            wav_name = task['wav_file']
            
            final_out = os.path.join(ANALYSIS_DIR, f"Analysis_ {wav_name.replace('.wav', '.TextGrid')}")
            if os.path.exists(final_out):
                success_list.append(wav_name)
                continue

            w_path = search_file_recursive(wav_name, DATA_SEARCH_ROOT)
            c_path = search_file_recursive(task['csv_file'], DATA_SEARCH_ROOT)
            if not w_path or not c_path: continue

            print(f"Processing: {wav_name}")
            prepare_data(w_path, c_path, s_id)
            
            if run_mfa(s_id):
                if postprocess(wav_name, final_out, c_path, s_id):
                    print(f"  [Success] {wav_name}")
                    success_list.append(wav_name)
                else:
                    remove_data(w_path, s_id)
                    failed_list.append(task)
            else:
                print(f"  [Failed] Removing file from pool.")
                remove_data(w_path, s_id)
                failed_list.append(task)
    else:
        for task in tasks:
            wav_name = task['wav_file']
            final_out = os.path.join(ANALYSIS_DIR, f"Analysis_ {wav_name.replace('.wav', '.TextGrid')}")
            if os.path.exists(final_out):
                success_list.append(wav_name)
            else:
                failed_list.append(task)

    # --- Phase 2: Retry x3 ---
    if failed_list and (phase_start <= 2 <= phase_end):
        print(f"\n>>> Phase 2: Retry with 3x Boost ({len(failed_list)} files)")
        phase2_failed = []
        for task in failed_list:
            s_id = task['speaker_id']
            wav_name = task['wav_file']
            print(f"Retrying: {wav_name}")
            
            w_path = search_file_recursive(wav_name, DATA_SEARCH_ROOT)
            c_path = search_file_recursive(task['csv_file'], DATA_SEARCH_ROOT)
            if not w_path or not c_path: continue
            
            prepare_data(w_path, c_path, s_id)
            for i in range(2): prepare_data(w_path, c_path, s_id, suffix=f"_dummy_{i}")
            
            if run_mfa(s_id):
                final_out = os.path.join(ANALYSIS_DIR, f"Analysis_ {wav_name.replace('.wav', '.TextGrid')}")
                postprocess(wav_name, final_out, c_path, s_id)
                print(f"  [Success] {wav_name}")
                success_list.append(wav_name)
                for i in range(2): remove_data(w_path, s_id, suffix=f"_dummy_{i}")
            else:
                print(f"  [Failed]")
                remove_data(w_path, s_id)
                for i in range(2): remove_data(w_path, s_id, suffix=f"_dummy_{i}")
                phase2_failed.append(task)
        failed_list = phase2_failed

    # --- Phase 3: Retry x5 ---
    if failed_list and (phase_start <= 3 <= phase_end):
        print(f"\n>>> Phase 3: Retry with 5x Boost ({len(failed_list)} files)")
        phase3_failed = []
        for task in failed_list:
            s_id = task['speaker_id']
            wav_name = task['wav_file']
            print(f"Retrying: {wav_name}")
            
            w_path = search_file_recursive(wav_name, DATA_SEARCH_ROOT)
            c_path = search_file_recursive(task['csv_file'], DATA_SEARCH_ROOT)
            if not w_path or not c_path: continue
            
            prepare_data(w_path, c_path, s_id)
            for i in range(4): prepare_data(w_path, c_path, s_id, suffix=f"_dummy_{i}")
            
            if run_mfa(s_id):
                final_out = os.path.join(ANALYSIS_DIR, f"Analysis_ {wav_name.replace('.wav', '.TextGrid')}")
                postprocess(wav_name, final_out, c_path, s_id)
                print(f"  [Success] {wav_name}")
                success_list.append(wav_name)
                for i in range(4): remove_data(w_path, s_id, suffix=f"_dummy_{i}")
            else:
                print(f"  [Failed]")
                remove_data(w_path, s_id)
                for i in range(4): remove_data(w_path, s_id, suffix=f"_dummy_{i}")
                phase3_failed.append(task)
        failed_list = phase3_failed

    # --- Phase 4: Context Boost ---
    if failed_list and (phase_start <= 4 <= phase_end):
        print(f"\n>>> Phase 4: Retry with Context Boost ({len(failed_list)} files)")
        phase4_failed = []
        for task in failed_list:
            s_id = task['speaker_id']
            wav_name = task['wav_file']
            conv_prefix = task['conv_id'].split('_')[0]
            print(f"Retrying: {wav_name} (Context: {conv_prefix})")
            
            w_path = search_file_recursive(wav_name, DATA_SEARCH_ROOT)
            c_path = search_file_recursive(task['csv_file'], DATA_SEARCH_ROOT)
            if not w_path or not c_path: continue
            
            prepare_data(w_path, c_path, s_id)
            
            parent_dir = os.path.dirname(w_path)
            context_files = []
            for root, dirs, files in os.walk(os.path.dirname(parent_dir)):
                for f in files:
                    if f.startswith(conv_prefix) and f.endswith(".wav") and f != wav_name:
                        context_files.append(os.path.join(root, f))
                        if len(context_files) >= 5: break
                if len(context_files) >= 5: break
            
            added_context = []
            for ctx_wav in context_files:
                base = os.path.basename(ctx_wav)
                match = re.match(r'(.+)_(IC\d{2})', base)
                if match:
                    ctx_id = match.group(1)
                    ctx_csv_name = f"{ctx_id}-luu.csv"
                    ctx_csv = search_file_recursive(ctx_csv_name, DATA_SEARCH_ROOT)
                    if ctx_csv:
                        if prepare_data(ctx_wav, ctx_csv, s_id):
                            added_context.append(ctx_wav)

            if run_mfa(s_id):
                final_out = os.path.join(ANALYSIS_DIR, f"Analysis_ {wav_name.replace('.wav', '.TextGrid')}")
                postprocess(wav_name, final_out, c_path, s_id)
                print(f"  [Success] {wav_name}")
                success_list.append(wav_name)
                for ctx_wav in added_context: remove_data(ctx_wav, s_id)
            else:
                print(f"  [Failed]")
                remove_data(w_path, s_id)
                for ctx_wav in added_context: remove_data(ctx_wav, s_id)
                phase4_failed.append(task)
        failed_list = phase4_failed

    # --- Phase 5: Ultimate Rescue ---
    if failed_list and (phase_start <= 5 <= phase_end):
        print(f"\n>>> Phase 5: Ultimate Rescue ({len(failed_list)} files)")
        phase5_failed = []
        
        all_wavs_pool = []
        for root, dirs, files in os.walk(DATA_SEARCH_ROOT):
            for f in files:
                if f.endswith(".wav") and "IC" in f:
                    all_wavs_pool.append(os.path.join(root, f))
            if len(all_wavs_pool) > 300: break
        
        if len(all_wavs_pool) > 30:
            rescue_wavs = random.sample(all_wavs_pool, 30)
        else:
            rescue_wavs = all_wavs_pool

        for task in failed_list:
            s_id = task['speaker_id']
            wav_name = task['wav_file']
            print(f"Retrying: {wav_name} (Rescue with {len(rescue_wavs)} files)")
            
            w_path = search_file_recursive(wav_name, DATA_SEARCH_ROOT)
            c_path = search_file_recursive(task['csv_file'], DATA_SEARCH_ROOT)
            if not w_path or not c_path: continue
            
            prepare_data(w_path, c_path, s_id)
            
            added_rescue = []
            for r_wav in rescue_wavs:
                if os.path.basename(r_wav) == wav_name: continue
                
                base = os.path.basename(r_wav)
                match = re.match(r'(.+)_(IC\d{2})', base)
                if match:
                    r_id = match.group(1)
                    r_csv_name = f"{r_id}-luu.csv"
                    r_csv = search_file_recursive(r_csv_name, DATA_SEARCH_ROOT)
                    if r_csv:
                        suffix_id = f"_rescue_{random.randint(1000,9999)}"
                        if prepare_data(r_wav, r_csv, s_id, suffix=suffix_id):
                            added_rescue.append((r_wav, suffix_id))

            if run_mfa(s_id):
                final_out = os.path.join(ANALYSIS_DIR, f"Analysis_ {wav_name.replace('.wav', '.TextGrid')}")
                postprocess(wav_name, final_out, c_path, s_id)
                print(f"  [Success] {wav_name}")
                success_list.append(wav_name)
            else:
                print(f"  [Failed] Hopeless.")
                phase5_failed.append(task)
            
            remove_data(w_path, s_id)
            for r_wav, suff in added_rescue:
                remove_data(r_wav, s_id, suffix=suff)
                
        failed_list = phase5_failed

    print("\n=== Processing Summary ===")
    print(f"Total Tasks: {len(tasks)}")
    print(f"Success: {len(success_list)}")
    print(f"Failed: {len(tasks) - len(success_list)}")
    if len(tasks) - len(success_list) > 0:
        print("Failed files:")
        for t in failed_list: print(f" - {t['wav_file']}")

if __name__ == "__main__":
    main()