import streamlit as st
import pandas as pd
import io
import re
import numpy as np
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from concurrent.futures import ThreadPoolExecutor
import json

# Try importing rapidfuzz for speed, fallback to difflib if missing
try:
    from rapidfuzz import fuzz
    USE_RAPIDFUZZ = True
except ImportError:
    import difflib
    USE_RAPIDFUZZ = False

# ==========================================
# PAGE CONFIGURATION
# ==========================================
st.set_page_config(
    page_title="GST Reconciliation Pro",
    layout="wide",
    page_icon="📊",
    initial_sidebar_state="expanded"
)

# Custom CSS for better UI
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .success-box {
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .error-box {
        background-color: #f8d7da;
        border-left: 5px solid #dc3545;
        padding: 1rem;
        border-radius: 5px;
        margin: 1rem 0;
    }
    .stDownloadButton button {
        width: 100%;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# SESSION STATE INITIALIZATION
# ==========================================
if 'reconciliation_done' not in st.session_state:
    st.session_state.reconciliation_done = False
if 'cis_result' not in st.session_state:
    st.session_state.cis_result = None
if 'g2b_result' not in st.session_state:
    st.session_state.g2b_result = None
if 'match_stats' not in st.session_state:
    st.session_state.match_stats = {}
if 'audit_log' not in st.session_state:
    st.session_state.audit_log = []

# ==========================================
# HELPER FUNCTIONS - OPTIMIZED
# ==========================================

# Translation table for fast string cleaning
import string
TRANS_TABLE = str.maketrans('', '', string.punctuation + ' ')

@st.cache_data
def find_column(df, candidates):
    """Find column name from list of candidates - cached for performance"""
    existing_cols = {
        str(c).strip().lower().replace(' ', '').replace('\n', '').replace('_', '').replace('(₹)', '').replace('₹', ''): c 
        for c in df.columns
    }
    for cand in candidates:
        clean_cand = cand.strip().lower().replace(' ', '').replace('_', '').replace('(₹)', '').replace('₹', '')
        if clean_cand in existing_cols:
            return existing_cols[clean_cand]
    return None

def clean_currency(val):
    """Vectorized currency cleaning"""
    if pd.isna(val) or str(val).strip() == '': 
        return 0.0
    if isinstance(val, (int, float)): 
        return float(val)
    try:
        clean_str = str(val).replace(',', '').replace(' ', '').replace('₹', '')
        return float(clean_str)
    except ValueError:
        return 0.0

def normalize_gstin(gstin):
    """Fast GSTIN normalization"""
    if pd.isna(gstin): 
        return ""
    return str(gstin).strip().upper().replace(" ", "")

def get_pan_from_gstin(gstin):
    """Extract PAN from GSTIN"""
    norm = normalize_gstin(gstin)
    if len(norm) >= 10:
        return norm[:10]
    return norm

def get_similarity_score(s1, s2):
    """Returns similarity 0-100"""
    if USE_RAPIDFUZZ:
        return fuzz.ratio(str(s1), str(s2))
    else:
        return difflib.SequenceMatcher(None, str(s1), str(s2)).ratio() * 100

def normalize_inv_basic_fast(inv):
    """Optimized invoice normalization using translate table"""
    if pd.isna(inv): 
        return ""
    s = str(inv).upper().translate(TRANS_TABLE)
    return s.lstrip('0') if s else ""

def normalize_inv_numeric(inv):
    """Extract only numeric characters"""
    if pd.isna(inv): 
        return ""
    s = re.sub(r'[^0-9]', '', str(inv))
    return s.lstrip('0') if s else ""

def get_last_4(inv):
    """Get last 4 digits"""
    if pd.isna(inv): 
        return ""
    s = re.sub(r'[^0-9]', '', str(inv))
    if len(s) > 4: 
        return s[-4:]
    return s.lstrip('0') if s else ""

# ==========================================
# ROBUST DATA LOADER WITH HEADER STITCHING
# ==========================================
@st.cache_data
def load_gstr2b_with_stitching(file_bytes, sheet_name):
    """
    Reads first 8 rows to find headers. Stitches split headers if found.
    Cached for performance.
    """
    file_obj = io.BytesIO(file_bytes)
    
    try:
        df_raw = pd.read_excel(file_obj, sheet_name=sheet_name, header=None, nrows=8, engine='openpyxl')
    except:
        xl = pd.ExcelFile(file_obj, engine='openpyxl')
        df_raw = pd.read_excel(file_obj, sheet_name=xl.sheet_names[0], header=None, nrows=8, engine='openpyxl')
    
    idx_gstin = -1
    idx_inv = -1
    
    def row_contains(row_idx, keyword):
        row_vals = df_raw.iloc[row_idx].astype(str).str.lower().values
        return any(keyword.lower() in val for val in row_vals)

    for i in range(len(df_raw)):
        if row_contains(i, 'gstin'): 
            idx_gstin = i
        if row_contains(i, 'invoice number') or row_contains(i, 'invoice no'): 
            idx_inv = i
            
    if idx_gstin == -1: 
        idx_gstin = 0
    if idx_inv == -1: 
        idx_inv = 0
    
    header_end_row = max(idx_gstin, idx_inv)
    final_headers = []
    num_cols = df_raw.shape[1]
    
    for c in range(num_cols):
        val_gstin = str(df_raw.iloc[idx_gstin, c]).strip()
        val_inv = str(df_raw.iloc[idx_inv, c]).strip()
        
        if val_gstin.lower() == 'nan': 
            val_gstin = ""
        if val_inv.lower() == 'nan': 
            val_inv = ""
        
        if val_inv and not val_inv.startswith("Unnamed"):
            final_headers.append(val_inv)
        elif val_gstin and not val_gstin.startswith("Unnamed"):
            final_headers.append(val_gstin)
        else:
            final_headers.append(f"Column_{c}")

    file_obj.seek(0)
    try:
        df_final = pd.read_excel(file_obj, sheet_name=sheet_name, header=header_end_row + 1, engine='openpyxl')
    except:
        df_final = pd.read_excel(file_obj, sheet_name=0, header=header_end_row + 1, engine='openpyxl')
    
    current_cols = len(df_final.columns)
    if len(final_headers) >= current_cols:
        df_final.columns = final_headers[:current_cols]
    else:
        df_final.columns = final_headers + [f"Col_{i}" for i in range(current_cols - len(final_headers))]
        
    return df_final

@st.cache_data
def load_cis_file(file_bytes):
    """Load and cache CIS file"""
    return pd.read_excel(io.BytesIO(file_bytes), engine='openpyxl')

# ==========================================
# FILE VALIDATION
# ==========================================
def validate_file(df, file_type, required_columns):
    """Validate uploaded file structure"""
    issues = []
    
    if df.empty:
        issues.append(f"❌ {file_type} file is empty")
    
    if len(df.columns) < 5:
        issues.append(f"⚠️ {file_type} file has very few columns ({len(df.columns)})")
    
    missing_cols = []
    for col_key, col_candidates in required_columns.items():
        found = find_column(df, col_candidates)
        if not found:
            missing_cols.append(col_candidates[0])
    
    if missing_cols:
        issues.append(f"❌ Missing columns in {file_type}: {', '.join(missing_cols)}")
    
    return issues

# ==========================================
# COLUMN MAPPING WITH SMART SUGGESTIONS
# ==========================================
def suggest_column_mapping(df, expected_columns):
    """Use fuzzy matching to auto-suggest column mappings"""
    suggestions = {}
    confidence_scores = {}
    
    for expected_key, candidates in expected_columns.items():
        scores = {}
        for candidate in candidates:
            for col in df.columns:
                score = get_similarity_score(candidate.lower(), str(col).lower())
                if col not in scores or score > scores[col]:
                    scores[col] = score
        
        if scores:
            best_match = max(scores, key=scores.get)
            best_score = scores[best_match]
            
            if best_score > 60:  # 60% threshold
                suggestions[expected_key] = best_match
                confidence_scores[expected_key] = best_score
    
    return suggestions, confidence_scores

# ==========================================
# MISMATCH ANALYSIS
# ==========================================
def analyze_mismatches(cis_unmatched, col_map):
    """Provide insights on why records didn't match"""
    analysis = {
        'total_unmatched': len(cis_unmatched),
        'invoice_format_issues': 0,
        'amount_issues': 0,
        'gstin_issues': 0,
        'date_issues': 0,
        'time_barred': 0
    }
    
    for idx, row in cis_unmatched.iterrows():
        # Check invoice format
        inv = row.get('Inv_Basic', '')
        if not inv or len(str(inv)) < 2:
            analysis['invoice_format_issues'] += 1
        
        # Check GSTIN
        gstin = row.get('Norm_GSTIN', '')
        if not gstin or len(str(gstin)) != 15:
            analysis['gstin_issues'] += 1
        
        # Check amounts
        if row.get('Grand_Total', 0) == 0:
            analysis['amount_issues'] += 1
        
        # Check time barred
        if 'Time Barred' in str(row.get('Short Remark', '')):
            analysis['time_barred'] += 1
    
    return analysis

# ==========================================
# CORE RECONCILIATION ENGINE - OPTIMIZED
# ==========================================
def run_8_layer_reconciliation(cis_df, gstr2b_df, col_map_cis, col_map_g2b, 
                                tol_std, tol_high, progress_callback=None):
    """
    Enhanced 8-layer reconciliation with performance optimizations
    """
    
    def update_progress(message, percent):
        if progress_callback:
            progress_callback(message, percent)
    
    # --- A. PREPROCESSING ---
    update_progress("Preprocessing data...", 10)
    
    cis_proc = cis_df.copy()
    g2b_proc = gstr2b_df.copy()

    # Drop temp columns if they exist (SAFETY FIX)
    temp_cols = ['Norm_GSTIN', 'Norm_PAN', 'Inv_Basic', 'Inv_Num', 'Inv_Last4', 
                 'Taxable', 'Tax', 'Grand_Total']
    cis_proc.drop(columns=[c for c in temp_cols if c in cis_proc.columns], inplace=True)
    g2b_proc.drop(columns=[c for c in temp_cols if c in g2b_proc.columns], inplace=True)

    # IDs
    if 'Index CIS' not in cis_proc.columns: 
        cis_proc['Index CIS'] = range(1, len(cis_proc) + 1)
    if 'INDEX' not in g2b_proc.columns: 
        g2b_proc['INDEX'] = g2b_proc.index + 100000 

    # Keys: GSTIN & PAN (Vectorized)
    cis_proc['Norm_GSTIN'] = cis_proc[col_map_cis['GSTIN']].apply(normalize_gstin)
    cis_proc['Norm_PAN'] = cis_proc[col_map_cis['GSTIN']].apply(get_pan_from_gstin)
    
    g2b_proc['Norm_GSTIN'] = g2b_proc[col_map_g2b['GSTIN']].apply(normalize_gstin)
    g2b_proc['Norm_PAN'] = g2b_proc[col_map_g2b['GSTIN']].apply(get_pan_from_gstin)

    # Keys: Invoices (Optimized)
    cis_proc['Inv_Basic'] = cis_proc[col_map_cis['INVOICE']].apply(normalize_inv_basic_fast)
    cis_proc['Inv_Num'] = cis_proc[col_map_cis['INVOICE']].apply(normalize_inv_numeric)
    cis_proc['Inv_Last4'] = cis_proc[col_map_cis['INVOICE']].apply(get_last_4)

    g2b_proc['Inv_Basic'] = g2b_proc[col_map_g2b['INVOICE']].apply(normalize_inv_basic_fast)
    g2b_proc['Inv_Num'] = g2b_proc[col_map_g2b['INVOICE']].apply(normalize_inv_numeric)
    g2b_proc['Inv_Last4'] = g2b_proc[col_map_g2b['INVOICE']].apply(get_last_4)

    # Financials (Vectorized)
    cis_proc['Taxable'] = cis_proc[col_map_cis['TAXABLE']].apply(clean_currency)
    cis_proc['Tax'] = (cis_proc[col_map_cis['IGST']].apply(clean_currency) + 
                       cis_proc[col_map_cis['CGST']].apply(clean_currency) + 
                       cis_proc[col_map_cis['SGST']].apply(clean_currency))
    cis_proc['Grand_Total'] = cis_proc['Taxable'] + cis_proc['Tax']

    g2b_proc['Taxable'] = g2b_proc[col_map_g2b['TAXABLE']].apply(clean_currency)
    g2b_proc['Tax'] = (g2b_proc[col_map_g2b['IGST']].apply(clean_currency) + 
                       g2b_proc[col_map_g2b['CGST']].apply(clean_currency) + 
                       g2b_proc[col_map_g2b['SGST']].apply(clean_currency))
    g2b_proc['Grand_Total'] = g2b_proc['Taxable'] + g2b_proc['Tax']

    # Initialize Output Columns
    cis_proc['Matching Status'] = "Unmatched"
    cis_proc['Match Category'] = ""
    cis_proc['Detailed Remark'] = ""
    cis_proc['GSTR 2B Key'] = ""
    cis_proc['Short Remark'] = ""
    cis_proc['Comments&Remarks'] = ""
    
    g2b_proc['Matching Status'] = "Unmatched"
    g2b_proc['CIS Key'] = ""

    # --- B. GROUPING (Standard Clubbing) ---
    update_progress("Grouping CIS records...", 20)
    
    cis_grouped = cis_proc.groupby(['Norm_GSTIN', 'Norm_PAN', 'Inv_Basic']).agg({
        'Taxable': 'sum', 
        'Tax': 'sum', 
        'Grand_Total': 'sum',
        'Inv_Num': 'first', 
        'Inv_Last4': 'first',
        col_map_cis['INVOICE']: 'first', 
        col_map_cis['DATE']: 'first',
        'Index CIS': list
    }).reset_index()
    cis_grouped['Matched_Flag'] = False

    match_stats = {}
    audit_log = []

    # --- C. HELPER: COMMIT MATCH WITH AUDIT ---
    def commit_match(layer_name, row_cis, row_g2b, diff_grand, detail_str, 
                     is_reverse=False, g2b_ids=None):
        
        if is_reverse:
            cis_indices = row_cis['Index CIS']
            g2b_indices = g2b_ids
        else:
            cis_indices = row_cis['Index CIS']
            g2b_indices = [row_g2b['INDEX']]
            cis_grouped.at[row_cis.name, 'Matched_Flag'] = True

        # Audit logging
        audit_log.append({
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'layer': layer_name,
            'cis_ids': str(cis_indices),
            'g2b_ids': str(g2b_indices),
            'difference': round(diff_grand, 2),
            'detail': detail_str
        })

        # Update GSTR-2B
        for g_idx in g2b_indices:
            g2b_proc.loc[g2b_proc['INDEX'] == g_idx, 'Matching Status'] = "Matched"
            g2b_proc.loc[g2b_proc['INDEX'] == g_idx, 'CIS Key'] = ", ".join(map(str, cis_indices))

        # Update CIS Lines
        for cis_id in cis_indices:
            cis_proc.loc[cis_proc['Index CIS'] == cis_id, 'Matching Status'] = "Matched"
            cis_proc.loc[cis_proc['Index CIS'] == cis_id, 'Match Category'] = layer_name
            cis_proc.loc[cis_proc['Index CIS'] == cis_id, 'GSTR 2B Key'] = ", ".join(map(str, g2b_indices))
            cis_proc.loc[cis_proc['Index CIS'] == cis_id, 'Short Remark'] = "Matched"
            cis_proc.loc[cis_proc['Index CIS'] == cis_id, 'Detailed Remark'] = detail_str
            
            existing = str(cis_proc.loc[cis_proc['Index CIS'] == cis_id, 'Comments&Remarks'].values[0])
            if existing == 'nan': 
                existing = ""
            new_rem = f"{existing} | {layer_name}".strip(" |")
            cis_proc.loc[cis_proc['Index CIS'] == cis_id, 'Comments&Remarks'] = new_rem

    # --- D. STANDARD LAYERS (1-6) - OPTIMIZED ---
    def run_standard_layer(layer_name, join_col_cis, join_col_g2b, tolerance, 
                           strict_tax_split=False, use_pan=False, progress_pct=0):
        count = 0
        update_progress(f"Running {layer_name}...", progress_pct)
        
        for idx, row_cis in cis_grouped.iterrows():
            if row_cis['Matched_Flag']: 
                continue
            
            gstin = row_cis['Norm_GSTIN']
            pan = row_cis['Norm_PAN']
            inv_val = row_cis[join_col_cis]
            
            if not inv_val or len(str(inv_val)) < 2: 
                continue

            # Filter G2B (Vectorized where possible)
            mask = (g2b_proc['Matching Status'] == "Unmatched") & (g2b_proc[join_col_g2b] == inv_val)
            if use_pan:
                mask = mask & (g2b_proc['Norm_PAN'] == pan) 
            else:
                mask = mask & (g2b_proc['Norm_GSTIN'] == gstin)
            
            candidates = g2b_proc[mask]
            if candidates.empty: 
                continue

            for g2b_idx, row_g2b in candidates.iterrows():
                # Compare
                diff_grand = abs(row_cis['Grand_Total'] - row_g2b['Grand_Total'])
                diff_taxable = abs(row_cis['Taxable'] - row_g2b['Taxable'])
                diff_tax = abs(row_cis['Tax'] - row_g2b['Tax'])
                
                is_match = False
                if strict_tax_split:
                    if diff_taxable <= tolerance and diff_tax <= tolerance: 
                        is_match = True
                else:
                    if diff_grand <= tolerance: 
                        is_match = True

                if is_match:
                    # Build Remark
                    matched_parts = ["GSTIN" if not use_pan else "PAN"]
                    if join_col_cis == "Inv_Basic": 
                        matched_parts.append("Invoice Number")
                    elif join_col_cis == "Inv_Num": 
                        matched_parts.append(f"Numeric Invoice ({row_cis[col_map_cis['INVOICE']]} vs {row_g2b[col_map_g2b['INVOICE']]})")
                    elif join_col_cis == "Inv_Last4": 
                        matched_parts.append(f"Last 4 Digits ({row_cis[col_map_cis['INVOICE']]} vs {row_g2b[col_map_g2b['INVOICE']]})")

                    if strict_tax_split:
                        matched_parts.extend(["Taxable Value", "Tax Amount"])
                    else:
                        matched_parts.append(f"Grand Total (Diff: ₹{diff_grand:.2f})")

                    # Date check
                    cis_date = pd.to_datetime(row_cis[col_map_cis['DATE']], dayfirst=True, errors='coerce')
                    g2b_date = pd.to_datetime(row_g2b[col_map_g2b['DATE']], dayfirst=True, errors='coerce')
                    if pd.notna(cis_date) and pd.notna(g2b_date) and cis_date == g2b_date:
                        matched_parts.append("Date")

                    detail_str = "Matched: " + ", ".join(matched_parts)
                    if use_pan and row_cis['Norm_GSTIN'] != row_g2b['Norm_GSTIN']:
                        detail_str += f" | Note: Matched under different GSTIN {row_g2b['Norm_GSTIN']}"

                    commit_match(layer_name, row_cis, row_g2b, diff_grand, detail_str)
                    count += 1
                    break
        
        match_stats[layer_name] = count

    # --- RUN STANDARD LAYERS ---
    run_standard_layer("Layer 1: Strict Match", "Inv_Basic", "Inv_Basic", tol_std, 
                       strict_tax_split=True, progress_pct=30)
    run_standard_layer("Layer 2: Grand Total Match", "Inv_Basic", "Inv_Basic", tol_std, 
                       progress_pct=40)
    run_standard_layer("Layer 3: High Tolerance", "Inv_Basic", "Inv_Basic", tol_high, 
                       progress_pct=50)
    run_standard_layer("Layer 4: Numeric Only", "Inv_Num", "Inv_Num", tol_std, 
                       progress_pct=60)
    run_standard_layer("Layer 5: Last 4 Digits", "Inv_Last4", "Inv_Last4", tol_std, 
                       progress_pct=65)
    run_standard_layer("Layer 6: PAN Level", "Inv_Basic", "Inv_Basic", tol_std, 
                       use_pan=True, progress_pct=70)

    # --- LAYER 7: FUZZY (LEVENSHTEIN) - OPTIMIZED ---
    def run_fuzzy_layer():
        count = 0
        layer_name = "Layer 7: Fuzzy Match"
        update_progress(f"Running {layer_name}...", 75)
        
        for idx, row_cis in cis_grouped.iterrows():
            if row_cis['Matched_Flag']: 
                continue
            
            gstin = row_cis['Norm_GSTIN']
            cis_inv = str(row_cis['Inv_Basic'])
            if len(cis_inv) < 3: 
                continue

            # Optimization: Filter G2B by GSTIN first
            g2b_candidates = g2b_proc[
                (g2b_proc['Matching Status'] == "Unmatched") & 
                (g2b_proc['Norm_GSTIN'] == gstin)
            ]
            
            if g2b_candidates.empty: 
                continue
            
            best_match = None
            best_score = 0.0

            for g_idx, row_g2b in g2b_candidates.iterrows():
                # STRICT Amount Check
                diff_grand = abs(row_cis['Grand_Total'] - row_g2b['Grand_Total'])
                if diff_grand > tol_std: 
                    continue
                
                # String Similarity
                g2b_inv = str(row_g2b['Inv_Basic'])
                score = get_similarity_score(cis_inv, g2b_inv)
                
                if score > 85 and score > best_score:
                    best_score = score
                    best_match = row_g2b

            if best_match is not None:
                diff_grand = abs(row_cis['Grand_Total'] - best_match['Grand_Total'])
                detail = f"Matched: GSTIN, Grand Total | Fuzzy Invoice: '{cis_inv}' vs '{best_match['Inv_Basic']}' (Similarity: {int(best_score)}%)"
                commit_match(layer_name, row_cis, best_match, diff_grand, detail)
                count += 1
        
        match_stats[layer_name] = count

    run_fuzzy_layer()

    # --- LAYER 8: REVERSE CLUBBING ---
    def run_reverse_clubbing():
        count = 0
        layer_name = "Layer 8: Reverse Clubbing"
        update_progress(f"Running {layer_name}...", 85)
        
        # Group Unmatched G2B
        g2b_unmatched = g2b_proc[g2b_proc['Matching Status'] == "Unmatched"]
        g2b_grouped = g2b_unmatched.groupby(['Norm_GSTIN', 'Inv_Basic']).agg({
            'Grand_Total': 'sum',
            'INDEX': list,
            'Inv_Basic': 'first'
        }).reset_index()
        
        for idx, row_cis in cis_grouped.iterrows():
            if row_cis['Matched_Flag']: 
                continue
            
            gstin = row_cis['Norm_GSTIN']
            inv = row_cis['Inv_Basic']
            
            match_row = g2b_grouped[
                (g2b_grouped['Norm_GSTIN'] == gstin) & 
                (g2b_grouped['Inv_Basic'] == inv)
            ]
            
            if match_row.empty: 
                continue
            
            row_g2b_group = match_row.iloc[0]
            diff_grand = abs(row_cis['Grand_Total'] - row_g2b_group['Grand_Total'])
            
            if diff_grand <= tol_std:
                g2b_indices = row_g2b_group['INDEX']
                detail = f"Matched: GSTIN, Invoice Number | Reverse Clubbing: 1 CIS vs {len(g2b_indices)} G2B Records (Total Diff: ₹{diff_grand:.2f})"
                cis_grouped.at[idx, 'Matched_Flag'] = True
                commit_match(layer_name, row_cis, None, diff_grand, detail, 
                           is_reverse=True, g2b_ids=g2b_indices)
                count += 1
                
        match_stats[layer_name] = count

    run_reverse_clubbing()

    # --- CLEANUP & TIME BARRED ---
    update_progress("Finalizing results...", 90)
    
    unmatched_mask = cis_proc['Matching Status'] == "Unmatched"
    if unmatched_mask.any():
        cis_proc.loc[unmatched_mask, 'Detailed Remark'] = "Mismatch: Invoice Number not found in GSTR-2B"
        cis_proc.loc[unmatched_mask, 'Short Remark'] = "Not Found"

    # Time barred check
    cutoff = pd.Timestamp("2024-03-31")
    cis_proc['D_Obj'] = pd.to_datetime(cis_proc[col_map_cis['DATE']], dayfirst=True, errors='coerce')
    mask = (cis_proc['D_Obj'] < cutoff) & (cis_proc['D_Obj'].notna())
    
    cis_proc.loc[mask, 'Short Remark'] = cis_proc.loc[mask, 'Short Remark'].astype(str) + " + Time Barred"
    cis_proc.loc[mask, 'Detailed Remark'] = cis_proc.loc[mask, 'Detailed Remark'].astype(str) + " [Warning: Date < 31 Mar 2024]"

    # Drop temporary columns
    drop_cols = ['Norm_GSTIN', 'Norm_PAN', 'Inv_Basic', 'Inv_Num', 'Inv_Last4', 
                 'Taxable', 'Tax', 'Grand_Total', 'D_Obj']
    cis_final = cis_proc.drop(columns=[c for c in drop_cols if c in cis_proc.columns])
    g2b_final = g2b_proc.drop(columns=[c for c in drop_cols if c in g2b_proc.columns])

    update_progress("Reconciliation complete!", 100)
    
    return cis_final, g2b_final, match_stats, audit_log

# ==========================================
# VISUALIZATION FUNCTIONS
# ==========================================
def create_match_pie_chart(cis_result):
    """Create pie chart for matched vs unmatched"""
    matched = len(cis_result[cis_result['Matching Status'] == 'Matched'])
    unmatched = len(cis_result[cis_result['Matching Status'] == 'Unmatched'])
    
    fig = go.Figure(data=[go.Pie(
        labels=['Matched', 'Unmatched'],
        values=[matched, unmatched],
        hole=0.4,
        marker=dict(colors=['#28a745', '#dc3545']),
        textinfo='label+percent+value',
        textfont=dict(size=14)
    )])
    
    fig.update_layout(
        title="Overall Reconciliation Status",
        height=400,
        showlegend=True
    )
    
    return fig

def create_layer_bar_chart(match_stats):
    """Create bar chart for layer-wise matches"""
    df_stats = pd.DataFrame(list(match_stats.items()), columns=['Layer', 'Matches'])
    
    fig = px.bar(
        df_stats,
        x='Layer',
        y='Matches',
        color='Matches',
        color_continuous_scale='Blues',
        text='Matches',
        title='Layer-wise Match Statistics'
    )
    
    fig.update_traces(textposition='outside')
    fig.update_layout(
        xaxis_tickangle=-45,
        height=500,
        showlegend=False
    )
    
    return fig

def create_amount_distribution(cis_result):
    """Create histogram of amount distribution"""
    matched = cis_result[cis_result['Matching Status'] == 'Matched']
    unmatched = cis_result[cis_result['Matching Status'] == 'Unmatched']
    
    # Get grand totals
    matched_amounts = []
    unmatched_amounts = []
    
    for idx, row in matched.iterrows():
        # Sum up taxable + taxes for display
        try:
            total = pd.to_numeric(row.get('Grand_Total', 0), errors='coerce')
            if pd.notna(total) and total > 0:
                matched_amounts.append(total)
        except:
            pass
    
    for idx, row in unmatched.iterrows():
        try:
            total = pd.to_numeric(row.get('Grand_Total', 0), errors='coerce')
            if pd.notna(total) and total > 0:
                unmatched_amounts.append(total)
        except:
            pass
    
    fig = go.Figure()
    
    fig.add_trace(go.Histogram(
        x=matched_amounts,
        name='Matched',
        marker_color='#28a745',
        opacity=0.7
    ))
    
    fig.add_trace(go.Histogram(
        x=unmatched_amounts,
        name='Unmatched',
        marker_color='#dc3545',
        opacity=0.7
    ))
    
    fig.update_layout(
        title='Amount Distribution: Matched vs Unmatched',
        xaxis_title='Amount (₹)',
        yaxis_title='Count',
        barmode='overlay',
        height=400
    )
    
    return fig

def highlight_status(row):
    """Apply row-wise styling based on status"""
    if row['Matching Status'] == 'Matched':
        return ['background-color: #d4edda'] * len(row)
    elif 'Time Barred' in str(row.get('Short Remark', '')):
        return ['background-color: #fff3cd'] * len(row)
    else:
        return ['background-color: #f8d7da'] * len(row)

# ==========================================
# MAIN APP UI
# ==========================================
st.markdown('<h1 class="main-header">📊 GST Reconciliation Pro</h1>', unsafe_allow_html=True)

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/tax.png", width=80)
    st.title("Settings")
    
    st.markdown("---")
    st.subheader("Tolerance Settings")
    tol_std = st.number_input(
        "Standard Tolerance (₹)",
        min_value=0.0,
        max_value=100.0,
        value=2.0,
        step=0.5,
        help="Used in Layers 1, 2, 4, 5, 6, 7, 8"
    )
    
    tol_high = st.number_input(
        "High Tolerance (₹)",
        min_value=0.0,
        max_value=500.0,
        value=50.0,
        step=5.0,
        help="Used in Layer 3 for high-variance matches"
    )
    
    st.markdown("---")
    st.subheader("Advanced Options")
    
    enable_fuzzy = st.checkbox("Enable Fuzzy Matching", value=True, help="Layer 7")
    enable_reverse = st.checkbox("Enable Reverse Clubbing", value=True, help="Layer 8")
    show_audit_log = st.checkbox("Generate Audit Log", value=True)
    
    st.markdown("---")
    st.info("💡 **Tip:** Start with default settings for best results")

# Main content tabs
tab1, tab2, tab3, tab4 = st.tabs(["🚀 Reconcile", "📈 Analytics", "📋 Audit Trail", "❓ Help"])

# ==========================================
# TAB 1: RECONCILIATION
# ==========================================
with tab1:
    st.subheader("Upload Your Files")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📄 CIS File")
        cis_file = st.file_uploader(
            "Upload your Credit Information Statement (CIS) Excel file",
            type=['xlsx'],
            key="cis",
            help="Excel file from your accounting system"
        )
        
        if cis_file:
            try:
                cis_bytes = cis_file.read()
                df_cis = load_cis_file(cis_bytes)
                st.success(f"✅ Loaded: {len(df_cis)} records, {len(df_cis.columns)} columns")
                
                # Validate
                cis_required = {
                    'GSTIN': ['SupplierGSTIN', 'GSTIN', 'Supplier GSTIN'],
                    'INVOICE': ['DocumentNumber', 'Invoice Number', 'Invoice No'],
                    'DATE': ['DocumentDate', 'Invoice Date', 'Date'],
                    'TAXABLE': ['TaxableValue', 'Taxable Value'],
                    'IGST': ['IntegratedTaxAmount', 'Integrated Tax', 'IGST'],
                    'CGST': ['CentralTaxAmount', 'Central Tax', 'CGST'],
                    'SGST': ['StateUT TaxAmount', 'State/UT Tax', 'SGST']
                }
                
                issues = validate_file(df_cis, "CIS", cis_required)
                if issues:
                    for issue in issues:
                        st.warning(issue)
                
                with st.expander("👀 Preview CIS Data"):
                    st.dataframe(df_cis.head(10), use_container_width=True)
                    
            except Exception as e:
                st.error(f"❌ Error loading CIS file: {str(e)}")
    
    with col2:
        st.markdown("#### 📊 GSTR-2B File")
        g2b_file = st.file_uploader(
            "Upload your GSTR-2B Excel file",
            type=['xlsx'],
            key="g2b",
            help="Download from GST Portal"
        )
        
        if g2b_file:
            try:
                g2b_bytes = g2b_file.read()
                xl = pd.ExcelFile(io.BytesIO(g2b_bytes), engine='openpyxl')
                sheet_name = 'B2B' if 'B2B' in xl.sheet_names else xl.sheet_names[0]
                df_g2b = load_gstr2b_with_stitching(g2b_bytes, sheet_name)
                st.success(f"✅ Loaded: {len(df_g2b)} records, {len(df_g2b.columns)} columns")
                
                # Validate
                g2b_required = {
                    'GSTIN': ['GSTIN of supplier', 'Supplier GSTIN', 'GSTIN'],
                    'INVOICE': ['Invoice number', 'Invoice No', 'Invoice Number'],
                    'DATE': ['Invoice Date', 'Date', 'Invoice date'],
                    'TAXABLE': ['Taxable Value (₹)', 'Taxable Value', 'Taxable'],
                    'IGST': ['Integrated Tax(₹)', 'Integrated Tax', 'IGST'],
                    'CGST': ['Central Tax(₹)', 'Central Tax', 'CGST'],
                    'SGST': ['State/UT Tax(₹)', 'State/UT Tax', 'SGST']
                }
                
                issues = validate_file(df_g2b, "GSTR-2B", g2b_required)
                if issues:
                    for issue in issues:
                        st.warning(issue)
                
                with st.expander("👀 Preview GSTR-2B Data"):
                    st.dataframe(df_g2b.head(10), use_container_width=True)
                    
            except Exception as e:
                st.error(f"❌ Error loading GSTR-2B file: {str(e)}")
    
    st.markdown("---")
    
    # Run reconciliation button
    if cis_file and g2b_file:
        col_btn1, col_btn2, col_btn3 = st.columns([2, 1, 2])
        with col_btn2:
            run_button = st.button("🚀 Run Reconciliation", type="primary", use_container_width=True)
        
        if run_button:
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            def update_progress(message, percent):
                status_text.text(message)
                progress_bar.progress(percent / 100)
            
            try:
                # Load files
                cis_bytes = cis_file.read() if hasattr(cis_file, 'read') else cis_file.getvalue()
                g2b_bytes = g2b_file.read() if hasattr(g2b_file, 'read') else g2b_file.getvalue()
                
                df_cis = load_cis_file(cis_bytes)
                xl = pd.ExcelFile(io.BytesIO(g2b_bytes), engine='openpyxl')
                sheet_name = 'B2B' if 'B2B' in xl.sheet_names else xl.sheet_names[0]
                df_g2b = load_gstr2b_with_stitching(g2b_bytes, sheet_name)
                
                # Column mapping
                cis_map = {
                    'GSTIN': ['SupplierGSTIN', 'GSTIN', 'Supplier GSTIN'],
                    'INVOICE': ['DocumentNumber', 'Invoice Number', 'Invoice No'],
                    'DATE': ['DocumentDate', 'Invoice Date', 'Date'],
                    'TAXABLE': ['TaxableValue', 'Taxable Value'],
                    'IGST': ['IntegratedTaxAmount', 'Integrated Tax', 'IGST'],
                    'CGST': ['CentralTaxAmount', 'Central Tax', 'CGST'],
                    'SGST': ['StateUT TaxAmount', 'State/UT Tax', 'SGST']
                }
                
                g2b_map = {
                    'GSTIN': ['GSTIN of supplier', 'Supplier GSTIN', 'GSTIN'],
                    'INVOICE': ['Invoice number', 'Invoice No', 'Invoice Number'],
                    'DATE': ['Invoice Date', 'Date', 'Invoice date'],
                    'TAXABLE': ['Taxable Value (₹)', 'Taxable Value', 'Taxable'],
                    'IGST': ['Integrated Tax(₹)', 'Integrated Tax', 'IGST'],
                    'CGST': ['Central Tax(₹)', 'Central Tax', 'CGST'],
                    'SGST': ['State/UT Tax(₹)', 'State/UT Tax', 'SGST']
                }
                
                final_cis_map = {}
                final_g2b_map = {}
                
                for k, v in cis_map.items():
                    found = find_column(df_cis, v)
                    if found:
                        final_cis_map[k] = found
                    else:
                        st.error(f"❌ Missing required CIS column: {v[0]}")
                        st.stop()
                
                for k, v in g2b_map.items():
                    found = find_column(df_g2b, v)
                    if found:
                        final_g2b_map[k] = found
                    else:
                        st.error(f"❌ Missing required GSTR-2B column: {v[0]}")
                        st.stop()
                
                # Run reconciliation
                cis_res, g2b_res, stats, audit = run_8_layer_reconciliation(
                    df_cis, df_g2b, final_cis_map, final_g2b_map,
                    tol_std, tol_high, update_progress
                )
                
                # Store in session state
                st.session_state.reconciliation_done = True
                st.session_state.cis_result = cis_res
                st.session_state.g2b_result = g2b_res
                st.session_state.match_stats = stats
                st.session_state.audit_log = audit
                
                progress_bar.empty()
                status_text.empty()
                
                # Success message
                st.balloons()
                st.markdown('<div class="success-box"><h3>✅ Reconciliation Complete!</h3></div>', 
                           unsafe_allow_html=True)
                
                # Quick stats
                matched_count = len(cis_res[cis_res['Matching Status'] == 'Matched'])
                total_count = len(cis_res)
                match_pct = (matched_count / total_count * 100) if total_count > 0 else 0
                
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Total Records", total_count)
                with col2:
                    st.metric("Matched", matched_count, delta=f"{match_pct:.1f}%")
                with col3:
                    st.metric("Unmatched", total_count - matched_count)
                with col4:
                    st.metric("Layers Used", len(stats))
                
                # Layer statistics
                st.subheader("Layer-wise Match Summary")
                stats_df = pd.DataFrame(list(stats.items()), columns=['Layer', 'Matches'])
                st.dataframe(stats_df, use_container_width=True)
                
                # Display results
                st.subheader("Reconciled CIS Data")
                
                # Color-coded display
                display_df = cis_res.copy()
                st.dataframe(
                    display_df.style.apply(highlight_status, axis=1),
                    use_container_width=True,
                    height=400
                )
                
                # Download section
                st.markdown("---")
                st.subheader("📥 Download Results")
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    # Excel download
                    output = io.BytesIO()
                    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                        cis_res.to_excel(writer, sheet_name='CIS_Reconciled', index=False)
                        g2b_res.to_excel(writer, sheet_name='GSTR2B_Mapped', index=False)
                        stats_df.to_excel(writer, sheet_name='Statistics', index=False)
                        if show_audit_log and audit:
                            pd.DataFrame(audit).to_excel(writer, sheet_name='Audit_Log', index=False)
                    
                    st.download_button(
                        "📊 Download Excel",
                        output.getvalue(),
                        f"GST_Reconciliation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                
                with col2:
                    # CSV download
                    csv_output = cis_res.to_csv(index=False)
                    st.download_button(
                        "📄 Download CSV",
                        csv_output,
                        f"CIS_Reconciled_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                with col3:
                    # JSON download (for audit)
                    if show_audit_log and audit:
                        json_output = json.dumps(audit, indent=2)
                        st.download_button(
                            "📋 Download Audit Log",
                            json_output,
                            f"Audit_Log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json",
                            use_container_width=True
                        )
                
            except Exception as e:
                progress_bar.empty()
                status_text.empty()
                st.error(f"❌ Error during reconciliation: {str(e)}")
                st.exception(e)
    
    else:
        st.info("👆 Please upload both CIS and GSTR-2B files to begin reconciliation")

# ==========================================
# TAB 2: ANALYTICS
# ==========================================
with tab2:
    if st.session_state.reconciliation_done:
        st.subheader("📊 Detailed Analytics")
        
        cis_res = st.session_state.cis_result
        stats = st.session_state.match_stats
        
        # Overall metrics
        st.markdown("### Key Metrics")
        matched_count = len(cis_res[cis_res['Matching Status'] == 'Matched'])
        unmatched_count = len(cis_res[cis_res['Matching Status'] == 'Unmatched'])
        total_count = len(cis_res)
        match_pct = (matched_count / total_count * 100) if total_count > 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        
        col1.metric("Total Records", f"{total_count:,}")
        col2.metric("Matched Records", f"{matched_count:,}", delta=f"{match_pct:.1f}%", delta_color="normal")
        col3.metric("Unmatched Records", f"{unmatched_count:,}", delta=f"{100-match_pct:.1f}%", delta_color="inverse")
        col4.metric("Match Rate", f"{match_pct:.1f}%")
        
        st.markdown("---")
        
        # Charts
        col1, col2 = st.columns(2)
        
        with col1:
            st.plotly_chart(create_match_pie_chart(cis_res), use_container_width=True)
        
        with col2:
            st.plotly_chart(create_layer_bar_chart(stats), use_container_width=True)
        
        # Amount distribution
        st.plotly_chart(create_amount_distribution(cis_res), use_container_width=True)
        
        # Mismatch analysis
        st.markdown("---")
        st.subheader("🔍 Mismatch Analysis")
        
        unmatched_df = cis_res[cis_res['Matching Status'] == 'Unmatched']
        
        if len(unmatched_df) > 0:
            # Get column map (approximate)
            col_map_approx = {
                'GSTIN': 'SupplierGSTIN',
                'INVOICE': 'DocumentNumber',
                'DATE': 'DocumentDate'
            }
            
            analysis = analyze_mismatches(unmatched_df, col_map_approx)
            
            col1, col2, col3 = st.columns(3)
            
            col1.metric("Invoice Format Issues", analysis['invoice_format_issues'])
            col2.metric("GSTIN Issues", analysis['gstin_issues'])
            col3.metric("Time Barred", analysis['time_barred'])
            
            # Show sample unmatched records
            st.markdown("#### Sample Unmatched Records")
            st.dataframe(unmatched_df.head(20), use_container_width=True)
        else:
            st.success("🎉 All records matched successfully!")
        
    else:
        st.info("Run reconciliation first to view analytics")

# ==========================================
# TAB 3: AUDIT TRAIL
# ==========================================
with tab3:
    if st.session_state.reconciliation_done and show_audit_log:
        st.subheader("📋 Audit Trail")
        
        if st.session_state.audit_log:
            audit_df = pd.DataFrame(st.session_state.audit_log)
            
            st.markdown(f"**Total Audit Entries:** {len(audit_df)}")
            
            # Filter by layer
            layers = audit_df['layer'].unique().tolist()
            selected_layer = st.selectbox("Filter by Layer", ['All'] + layers)
            
            if selected_layer != 'All':
                display_audit = audit_df[audit_df['layer'] == selected_layer]
            else:
                display_audit = audit_df
            
            st.dataframe(display_audit, use_container_width=True, height=500)
            
            # Download audit log
            csv_audit = display_audit.to_csv(index=False)
            st.download_button(
                "📥 Download Audit Trail",
                csv_audit,
                f"Audit_Trail_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.info("No audit entries generated")
    else:
        st.info("Enable 'Generate Audit Log' in settings and run reconciliation to view audit trail")

# ==========================================
# TAB 4: HELP
# ==========================================
with tab4:
    st.subheader("❓ Help & Documentation")
    
    st.markdown("""
    ## 📚 User Guide
    
    ### How to Use This Tool
    
    1. **Upload Files**
       - Upload your CIS (Credit Information Statement) Excel file
       - Upload your GSTR-2B Excel file from GST Portal
    
    2. **Configure Settings**
       - Adjust tolerance levels in the sidebar
       - Standard tolerance: For most matches (default: ₹2)
       - High tolerance: For Layer 3 matches with larger variance (default: ₹50)
    
    3. **Run Reconciliation**
       - Click "Run Reconciliation" button
       - Watch real-time progress
       - View results instantly
    
    4. **Review Results**
       - Check analytics dashboard
       - Review matched and unmatched records
       - Download results in multiple formats
    
    ---
    
    ### 🔄 8-Layer Reconciliation Algorithm
    
    #### **Layer 1: Strict Match**
    - Matches: GSTIN + Invoice Number + Taxable Value + Tax Amount
    - Tolerance: Standard (₹2)
    - Best for: Exact matches without any variance
    
    #### **Layer 2: Grand Total Match**
    - Matches: GSTIN + Invoice Number + Grand Total
    - Tolerance: Standard (₹2)
    - Best for: Cases where tax split differs but total matches
    
    #### **Layer 3: High Tolerance**
    - Matches: GSTIN + Invoice Number + Grand Total
    - Tolerance: High (₹50)
    - Best for: Rounding differences, minor calculation variances
    
    #### **Layer 4: Numeric Only**
    - Matches: GSTIN + Numeric part of invoice + Amount
    - Example: `GST/01` becomes `01`
    - Best for: Different invoice prefixes
    
    #### **Layer 5: Last 4 Digits**
    - Matches: GSTIN + Last 4 digits of invoice + Amount
    - Example: `WB-0995` becomes `0995`
    - Best for: Different invoice formats with same number
    
    #### **Layer 6: PAN Level**
    - Matches: PAN (first 10 chars) + Invoice + Amount
    - Ignores: State code in GSTIN
    - Best for: Head office vs branch office invoices
    
    #### **Layer 7: Fuzzy Match**
    - Matches: GSTIN + Similar invoice (85%+) + Amount
    - Example: `9855` matches `9885`
    - Best for: Typos, OCR errors
    
    #### **Layer 8: Reverse Clubbing**
    - Matches: 1 CIS entry vs Multiple G2B entries
    - Compares: Sum of G2B amounts
    - Best for: Split invoices in GSTR-2B
    
    ---
    
    ### 💡 Tips for Best Results
    
    1. **File Format**
       - Ensure Excel files are properly formatted
       - No merged cells in data area
       - Column headers should be in first few rows
    
    2. **Data Quality**
       - Verify GSTIN format (15 characters)
       - Check invoice numbers are not blank
       - Ensure amounts are numeric
    
    3. **Tolerance Settings**
       - Start with default values
       - Increase high tolerance for rounding issues
       - Lower tolerance for stricter matching
    
    4. **Review Unmatched**
       - Check mismatch analysis for patterns
       - Look for data quality issues
       - Verify invoice number formats
    
    ---
    
    ### 🐛 Troubleshooting
    
    **Problem:** File upload fails
    - **Solution:** Ensure file is .xlsx format, not .xls or .csv
    
    **Problem:** Missing column errors
    - **Solution:** Check your file has required columns (GSTIN, Invoice Number, Date, Amounts)
    
    **Problem:** Low match rate
    - **Solution:** 
      - Increase high tolerance
      - Check data quality (blank fields, formatting)
      - Review invoice number formats
    
    **Problem:** Slow performance
    - **Solution:** 
      - Process files in batches if very large (>10,000 records)
      - Close other browser tabs
      - Use smaller tolerance for Layer 3
    
    ---
    
    ### 📞 Support
    
    For technical support or feature requests, please contact your system administrator.
    
    **Version:** 2.0  
    **Last Updated:** February 2026
    """)
    
    # Sample file templates
    st.markdown("---")
    st.subheader("📝 Sample File Templates")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**CIS Template Columns:**")
        st.code("""
- SupplierGSTIN
- DocumentNumber
- DocumentDate
- TaxableValue
- IntegratedTaxAmount (IGST)
- CentralTaxAmount (CGST)
- StateUT TaxAmount (SGST)
        """)
    
    with col2:
        st.markdown("**GSTR-2B Template Columns:**")
        st.code("""
- GSTIN of supplier
- Invoice number
- Invoice Date
- Taxable Value (₹)
- Integrated Tax(₹)
- Central Tax(₹)
- State/UT Tax(₹)
        """)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 20px;'>
    <p>GST Reconciliation Pro v2.0 | Powered by Streamlit</p>
    <p>© 2026 - Built for NLC India Limited</p>
</div>
""", unsafe_allow_html=True)
