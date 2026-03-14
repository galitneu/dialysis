# ECHO Project — Stage 4D4: Hospitalization Multivariable Analysis
# Generated from notebook echo_stage4d4_hospitalizations.ipynb
# ======================================================================
# ECHO Project — Stage 4D4: Hospitalization Multivariable Analysis
# ======================================================================
# ======================================================================
# ---
# ======================================================================
import subprocess, sys
for pkg in ['statsmodels']:
    try: __import__(pkg)
    except ImportError:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg, '-q'])
import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')
import statsmodels.api as sm
import statsmodels.formula.api as smf
from statsmodels.stats.outliers_influence import variance_inflation_factor
from scipy.stats import kruskal, mannwhitneyu
pd.set_option('display.max_columns', 25)
pd.set_option('display.float_format', '{:.4f}'.format)
# ── Solution ──────────────────────────────────────────────────
PRIMARY_ALGO = 'kmeans'
PRIMARY_K    = 3
PRIMARY_KEY  = f'{PRIMARY_ALGO}_K{PRIMARY_K}'
N_EXPECTED   = 645
# ── Column names ──────────────────────────────────────────────
COL_ID        = 'patient_id'
COL_HOSP      = 'hospitalization-count'
COL_TIME_DAYS = 'time_to_event_days'
COL_TIME_YRS  = 'time_to_event_years'
COL_EVENT     = 'event'
# ── Core covariates ───────────────────────────────────────────
# Pre-specified a priori; same rationale as Stage 4D3.
CORE_COVARS = [
    'AgeAtFirstHFDate',
    'LV_EF',
    'albumin-numeric result',
    'hb-numeric result',
    'AFIB_binary',
    'sbp-numeric result',
]
# Renal proxies — tested separately to avoid collinearity
RENAL_GFR  = 'GFR'
RENAL_CREAT = 'creatinine-numeric result'
# ── Extended covariates (Model 3) ─────────────────────────────
# ischemic_burden computed in load cell; HD/PD one-hot encoded
EXTENDED_VARS = ['ischemic_burden', 'HD/PD']
# ── Minimum follow-up to include in model ─────────────────────
MIN_FU_YEARS = 1 / 365  # ~1 day
# ── QA helper ────────────────────────────────────────────────
QA_LOG = []
def qa(condition, label, expected=None, actual=None):
    detail = f' (expected {expected}, got {actual})' if expected is not None else ''
    msg = ('OK    ' if condition else 'WARN  ') + label + detail
    QA_LOG.append(msg)
    print(msg)
    return condition
print('Setup complete.')
# ======================================================================
# ---
# ======================================================================
def resolve(candidates):
    for p in candidates:
        if os.path.exists(p): return p
    return candidates[0]
def read_auto(path, sheet=0):
    if path.lower().endswith(('.xlsx', '.xls')):
        return pd.read_excel(path, sheet_name=sheet)
    for enc in ['utf-8-sig', 'utf-8', 'latin-1']:
        try: return pd.read_csv(path, low_memory=False, encoding=enc)
        except UnicodeDecodeError: pass
    raise RuntimeError(f'Cannot read: {path}')
try:
    from google.colab import files
    print('Upload: base_analysis_dataset + cluster_assignments_all_solutions')
    files.upload()
except Exception:
    print('Running locally.')
# ── Base dataset ──────────────────────────────────────────────
base_path = resolve(['base_analysis_dataset.csv', 'base_analysis_dataset.xlsx'])
sheet     = 'base_analysis_dataset' if base_path.endswith(('.xlsx','.xls')) else 0
df_base   = read_auto(base_path, sheet=sheet).reset_index(drop=True)
qa(len(df_base) == N_EXPECTED, 'base dataset rows', N_EXPECTED, len(df_base))
# ── Cluster assignments ───────────────────────────────────────
assigns_df = read_auto(resolve([
    'cluster_assignments_all_solutions.csv',
    'cluster_assignments_all_solutions.xlsx']))
# ── Extract kmeans K=3 labels ─────────────────────────────────
label_col = None
for pattern in [f'{PRIMARY_ALGO}_K{PRIMARY_K}_label',
                f'{PRIMARY_ALGO}_K{PRIMARY_K}',
                f'cluster_{PRIMARY_ALGO}_K{PRIMARY_K}',
                PRIMARY_KEY]:
    if pattern in assigns_df.columns:
        label_col = pattern
        break
if label_col:
    cluster_labels = assigns_df[label_col].values
    print(f'Wide format — column: {label_col}')
elif 'algorithm' in assigns_df.columns:
    sub = assigns_df[
        (assigns_df['algorithm'] == PRIMARY_ALGO) &
        (assigns_df['K'].astype(int) == PRIMARY_K)
    ].reset_index(drop=True)
    qa(len(sub) == N_EXPECTED, 'long-format rows', N_EXPECTED, len(sub))
    cluster_labels = sub['cluster_label'].values
else:
    raise KeyError(f'Cannot find {PRIMARY_KEY}. Columns: {list(assigns_df.columns)}')
# ── Merge strategy ────────────────────────────────────────────
# Preferred: explicit key-based merge on patient_id.
# Positional mapping is used only as a documented fallback when
# no shared key column exists in the cluster assignments file.
shared_id = next(
    (c for c in ['patient_id', 'patient_index']
     if c in assigns_df.columns and c in df_base.columns), None)
if shared_id and label_col:
    merge_src = assigns_df[[shared_id, label_col]].rename(
        columns={label_col: 'cluster_label'})
    # Semantic key check: ranges must match
    b_ids = set(df_base[shared_id].dropna().astype(int))
    a_ids = set(assigns_df[shared_id].dropna().astype(int))
    qa(b_ids == a_ids,
       f'patient_id sets identical in both files '
       f'(base {len(b_ids)}, assigns {len(a_ids)})')
    df = df_base.merge(merge_src, on=shared_id, how='left')
    merge_type = f'key-based ({shared_id})'
else:
    # ── DOCUMENTED FALLBACK ──────────────────────────────────
    # No shared key column found. Positional mapping is used,
    # which assumes that row order in cluster_assignments matches
    # row order in base_analysis_dataset. This is a limitation:
    # if either file was sorted or filtered differently, the
    # assignment will be silently wrong.
    # Mitigation: row count QA below verifies N=645.
    qa(len(cluster_labels) == len(df_base),
       'positional join length match (FALLBACK — see note)',
       len(df_base), len(cluster_labels))
    print('  MERGE LIMITATION: using positional join — no shared key column.')
    print('  Verify that both files have identical row order before trusting results.')
    df = df_base.copy().reset_index(drop=True)
    df['cluster_label'] = cluster_labels
    merge_type = 'positional (FALLBACK — document as limitation)'
df['cluster_label'] = df['cluster_label'].astype(int)
# ── Derived variables ─────────────────────────────────────────
if COL_TIME_YRS not in df.columns:
    df[COL_TIME_YRS] = df[COL_TIME_DAYS] / 365.25
# Ischemic burden composite (0–3)
df['ischemic_burden'] = (
    df['IHD_binary'].fillna(0) +
    df['MI_binary'].fillna(0) +
    df['CABG_binary'].fillna(0)
).astype(int)
# HD/PD binary (HD=1, PD=0)
df['HD_binary'] = (df['HD/PD'].astype(str).str.upper() == 'HD').astype(int)
CLUSTERS = sorted(df['cluster_label'].unique())
# ── Merge QA ──────────────────────────────────────────────────
qa(len(df) == N_EXPECTED,           'rows after merge', N_EXPECTED, len(df))
qa(df['cluster_label'].isna().sum() == 0, 'no missing cluster labels',
   0, df['cluster_label'].isna().sum())
qa(df.duplicated(COL_ID).sum() == 0, 'no duplicate patient_ids',
   0, df.duplicated(COL_ID).sum())
print(f'Merge type: {merge_type}')
print(f'Cluster sizes: {df["cluster_label"].value_counts().sort_index().to_dict()}')
# ======================================================================
# ---
# ======================================================================
# ── Missingness report ────────────────────────────────────────
all_model_vars = (
    CORE_COVARS + [RENAL_GFR, RENAL_CREAT] +
    ['ischemic_burden', 'HD_binary', COL_HOSP, COL_TIME_YRS]
)
print('Missingness report:')
print(f'  {"Variable":<40} {"N non-miss":>10} {"N miss":>8} {"Miss%":>7}')
print('  ' + '-'*68)
for v in all_model_vars:
    if v not in df.columns:
        print(f'  {v:<40} NOT IN DATASET')
        continue
    n_miss  = df[v].isna().sum()
    n_valid = len(df) - n_miss
    pct     = n_miss / len(df) * 100
    flag    = '  ← HIGH' if pct > 30 else ('  ← mod' if pct > 15 else '')
    print(f'  {v:<40} {n_valid:>10} {n_miss:>8} {pct:>6.1f}%{flag}')
# ── Outcome distribution ──────────────────────────────────────
print('\nHospitalisation count distribution:')
hc = df[COL_HOSP]
print(f'  min={hc.min():.0f}  max={hc.max():.0f}  '
      f'mean={hc.mean():.2f}  median={hc.median():.0f}  '
      f'missing={hc.isna().sum()}')
print(f'  count=0: {(hc==0).sum()}  '
      f'count>=5: {(hc>=5).sum()}  '
      f'count>=10: {(hc>=10).sum()}')
# Per-cluster raw counts
print('\nRaw hospitalisation count by cluster:')
for c in CLUSTERS:
    sub = df.loc[df['cluster_label']==c, COL_HOSP]
    fu  = df.loc[df['cluster_label']==c, COL_TIME_YRS]
    rate = (sub / fu.replace(0, np.nan)).median()
    print(f'  C{c}: n={len(sub)}  '
          f'mean={sub.mean():.2f}  median={sub.median():.0f}  '
          f'rate/yr(median)={rate:.3f}')
# ── Overdispersion check ──────────────────────────────────────
mean_h = hc.mean()
var_h  = hc.var()
print(f'\nOverdispersion: mean={mean_h:.3f}  variance={var_h:.3f}  '
      f'ratio={var_h/mean_h:.2f}')
print('→ Negative Binomial justified.' if var_h/mean_h > 1.5
      else '→ Variance close to mean; Poisson may also be adequate.')
# Guard: patients with follow-up <= 0
n_zero_fu = (df[COL_TIME_YRS] <= 0).sum()
qa(n_zero_fu == 0, 'no patients with follow_up_years <= 0', 0, n_zero_fu)
# ======================================================================
# ---
# ======================================================================
# ── Comorbidity vars for mode imputation ─────────────────────
COMORBIDITY_VARS = [
    'IHD_binary', 'AFIB_binary', 'HTN_binary',
    'Diabetes mellitus_binary', 'DYSLIPIDEMIA_binary',
    'MI_binary', 'CABG_binary', 'COPD_binary',
]
# ── Binary variables (0/1): mode imputation; continuous: median
BINARY_VARS_SET = set(COMORBIDITY_VARS + ['AFIB_binary', 'HD_binary'])
def _impute_var(series, varname):
    """Impute by type: binary -> mode, continuous -> median."""
    sv = varname.replace('-','_').replace(' ','_').replace('/','_')
    s  = pd.to_numeric(series, errors='coerce')
    if varname in BINARY_VARS_SET or set(s.dropna().unique()).issubset({0,1}):
        fill_val = s.mode().iloc[0] if len(s.mode()) > 0 else 0
        method   = 'mode'
    else:
        fill_val = s.median()
        method   = 'median'
    return s.fillna(fill_val), method, fill_val
def build_nb_df(df, covar_raw, drop_high_miss_pct=40):
    """
    Build a clean modelling dataframe for NB regression.
    """
    need_cols = ([COL_HOSP, COL_TIME_YRS, 'cluster_label'] +
                 [v for v in covar_raw if v in df.columns])
    df_m = df[need_cols].copy()
    df_m = df_m.dropna(subset=[COL_HOSP, COL_TIME_YRS]).copy()
    df_m = df_m[df_m[COL_TIME_YRS] > 0].copy()
    df_m['log_fu'] = np.log(df_m[COL_TIME_YRS])
    used, dropped, miss_report = [], [], []
    for v in covar_raw:
        if v not in df.columns:
            dropped.append((v, 'not in dataset'))
            continue
        n_miss  = df_m[v].isna().sum()
        pct_miss = n_miss / len(df_m) * 100
        if pct_miss >= drop_high_miss_pct:
            dropped.append((v, f'{pct_miss:.0f}% missing — dropped'))
            continue
        imputed, method, fill_val = _impute_var(df_m[v], v)
        sv = v.replace('-','_').replace(' ','_').replace('/','_')
        df_m[sv] = imputed
        if sv != v:
            df_m = df_m.drop(columns=[v], errors='ignore')
        used.append(sv)
        miss_report.append({
            'variable': v, 'safe_name': sv,
            'n_missing': n_miss, 'pct_missing': round(pct_miss,1),
            'imputation_method': method, 'fill_value': round(float(fill_val),4),
        })
    df_m['hosp_count'] = df_m[COL_HOSP].astype(int)
    df_m['cluster_cat'] = pd.Categorical(
        df_m['cluster_label'].astype(str),
        categories=[str(c) for c in sorted(df_m['cluster_label'].unique())])
    return df_m, used, dropped, miss_report
def fit_nb(df_m, covar_safe, label=''):
    """
    Fit Negative Binomial regression (NB2, MLE).
    """
    pred    = ' + '.join(['cluster_cat'] + covar_safe)
    formula = f'hosp_count ~ {pred}'
    n       = len(df_m)
    total_h = int(df_m['hosp_count'].sum())
    method_used = 'NB2_MLE'
    try:
        mod = smf.negativebinomial(
            formula, data=df_m,
            exposure=np.exp(df_m['log_fu'])
        ).fit(method='newton', disp=False, maxiter=200)
        alpha = mod.params.get('alpha', np.nan)
    except Exception as e_nb2:
        print(f'  NB2 failed ({e_nb2}); falling back to GLM NB ...')
        method_used = 'GLM_NB_fallback'
        try:
            mod = smf.glm(
                formula, data=df_m,
                family=sm.families.NegativeBinomial(),
                offset=df_m['log_fu']
            ).fit(disp=False)
            alpha = np.nan
        except Exception as e_glm:
            print(f'  {label} GLM also failed: {e_glm}')
            return None, None, None
    coef, ci, pv = mod.params, mod.conf_int(), mod.pvalues
    rows = []
    for term in coef.index:
        if term == 'alpha': continue
        irr = np.exp(coef[term])
        lo  = np.exp(ci.loc[term, 0])
        hi  = np.exp(ci.loc[term, 1])
        p   = pv[term]
        lbl = ('reference' if term == 'Intercept'
               else term.replace('cluster_cat[T.','C').replace(']',''))
        rows.append(dict(
            model=label, term=term, label=lbl,
            IRR=round(irr,3), CI_lo=round(lo,3), CI_hi=round(hi,3),
            p_value=round(p,4),
            sig='***' if p<0.001 else '**' if p<0.01 else '*' if p<0.05 else '',
        ))
    irr_df = pd.DataFrame(rows)
    ll  = getattr(mod, 'llf', np.nan)
    aic = getattr(mod, 'aic', np.nan)
    fit_stats = {
        'model': label, 'method': method_used,
        'N': n, 'total_hosp': total_h,
        'log_likelihood': round(float(ll), 3) if not np.isnan(ll) else np.nan,
        'AIC': round(float(aic), 3) if not np.isnan(aic) else np.nan,
        'alpha_dispersion': round(float(alpha), 4) if not np.isnan(alpha) else 'NA',
        'n_params': len([t for t in coef.index if t != 'alpha']),
    }
    print(f'  [{method_used}]  N={n}  hosp={total_h}  '
          f'LL={fit_stats["log_likelihood"]}  AIC={fit_stats["AIC"]}  '
          f'alpha={fit_stats["alpha_dispersion"]}')
    print(irr_df[['label','IRR','CI_lo','CI_hi','p_value','sig']].to_string())
    return mod, irr_df, fit_stats
# ── Model 0: cluster only ─────────────────────────────────────
print('\n── Model 0: Unadjusted (cluster only) ──')
df_m0, _, dropped0, miss0 = build_nb_df(df, [])
mod0, irr0, fs0 = fit_nb(df_m0, [], label='Model0_unadjusted')
ALL_IRR      = [irr0] if irr0 is not None else []
ALL_FIT_STATS = [fs0]  if fs0  is not None else []
# ======================================================================
# ---
# ======================================================================
print('── Model 1: Core covariates + GFR ──')
M1_VARS = CORE_COVARS + [RENAL_GFR]
df_m1, used1, dropped1, miss1 = build_nb_df(df, M1_VARS)
if dropped1:
    print(f'  Dropped: {dropped1}')
print(f'  Predictors: {used1}')
mod1, irr1, fs1 = fit_nb(df_m1, used1, label='Model1_GFR')
if irr1 is not None: ALL_IRR.append(irr1)
if fs1  is not None: ALL_FIT_STATS.append(fs1)
# ── VIF for Model 1 ───────────────────────────────────────────
print('\nVIF — Model 1:')
cont1 = [v for v in used1 if df_m1[v].nunique() > 5]
if len(cont1) > 1:
    X_vif = sm.add_constant(df_m1[cont1].astype(float))
    for i, col in enumerate(X_vif.columns):
        if col == 'const': continue
        vif = variance_inflation_factor(X_vif.values, i)
        flag = '  ← HIGH' if vif > 10 else ('  ← mod' if vif > 5 else '')
        print(f'  {col:<40} VIF={vif:.2f}{flag}')
# ======================================================================
# ---
# ======================================================================
print('── Model 2: Core covariates + Creatinine ──')
M2_VARS = CORE_COVARS + [RENAL_CREAT]
df_m2, used2, dropped2, miss2 = build_nb_df(df, M2_VARS)
if dropped2:
    print(f'  Dropped: {dropped2}')
print(f'  Predictors: {used2}')
mod2, irr2, fs2 = fit_nb(df_m2, used2, label='Model2_creatinine')
if irr2 is not None: ALL_IRR.append(irr2)
if fs2  is not None: ALL_FIT_STATS.append(fs2)
# ── Compare cluster IRRs: GFR vs creatinine ───────────────────
print('\nCluster IRR comparison — GFR vs Creatinine models:')
print(f'  {"Cluster term":<30} {"Model1_GFR IRR":>14} {"Model2_creat IRR":>16}')
for df_irr, label in [(irr1,'M1'), (irr2,'M2')]:
    pass
if irr1 is not None and irr2 is not None:
    cl_terms = [t for t in irr1['term'] if 'cluster_cat' in t]
    for t in cl_terms:
        r1 = irr1.loc[irr1['term']==t, ['IRR','p_value']].values
        r2 = irr2.loc[irr2['term']==t, ['IRR','p_value']].values
        irr1_v = f"{r1[0][0]} (p={r1[0][1]})" if len(r1) else 'NA'
        irr2_v = f"{r2[0][0]} (p={r2[0][1]})" if len(r2) else 'NA'
        lbl = t.replace('cluster_cat[T.','C').replace(']','')
        print(f'  {lbl:<30} {irr1_v:>14}   {irr2_v:>16}')
# ======================================================================
# ---
# ======================================================================
print('── Model 3: Core + GFR + ischemic_burden + HD_binary ──')
print('NOTE: HD/PD encoded as HD_binary (HD=1, PD=0) to avoid one-hot issues.')
for v in ['ischemic_burden', 'HD_binary']:
    n_miss = df[v].isna().sum() if v in df.columns else -1
    print(f'  {v}: {n_miss} missing')
M3_VARS = CORE_COVARS + [RENAL_GFR, 'ischemic_burden', 'HD_binary']
df_m3, used3, dropped3, miss3 = build_nb_df(df, M3_VARS)
if dropped3:
    print(f'  Dropped: {dropped3}')
print(f'  Predictors: {used3}')
mod3, irr3, fs3 = fit_nb(df_m3, used3, label='Model3_extended')
if irr3 is not None: ALL_IRR.append(irr3)
if fs3  is not None: ALL_FIT_STATS.append(fs3)
# VIF for Model 3
print('\nVIF — Model 3:')
cont3 = [v for v in used3 if df_m3[v].nunique() > 5]
if len(cont3) > 1:
    X_vif3 = sm.add_constant(df_m3[cont3].astype(float))
    for i, col in enumerate(X_vif3.columns):
        if col == 'const': continue
        vif = variance_inflation_factor(X_vif3.values, i)
        flag = '  ← HIGH' if vif > 10 else ('  ← mod' if vif > 5 else '')
        print(f'  {col:<40} VIF={vif:.2f}{flag}')
# ======================================================================
# ---
# ======================================================================
from scipy.stats import spearmanr
gfr_vals   = pd.to_numeric(df[RENAL_GFR],   errors='coerce')
creat_vals = pd.to_numeric(df[RENAL_CREAT],  errors='coerce')
both_valid = gfr_vals.notna() & creat_vals.notna()
r_pearson  = gfr_vals[both_valid].corr(creat_vals[both_valid])
r_spearman, p_sp = spearmanr(gfr_vals[both_valid], creat_vals[both_valid])
print('GFR vs Creatinine collinearity:')
print(f'  N pairs        : {both_valid.sum()}')
print(f'  Pearson r      : {r_pearson:.3f}')
print(f'  Spearman r     : {r_spearman:.3f}  p={p_sp:.4f}')
if abs(r_pearson) > 0.70:
    print('  → COLLINEAR (|r| > 0.70): do NOT include both in the same model.')
    print('    Model 1 (GFR) and Model 2 (Creatinine) are correctly run as separate sensitivities.')
else:
    print(f'  → Moderate correlation; could include together, but separate models preferred.')
coll_df = pd.DataFrame([{
    'var1': RENAL_GFR, 'var2': RENAL_CREAT,
    'n_pairs': int(both_valid.sum()),
    'pearson_r': round(r_pearson,3),
    'spearman_r': round(r_spearman,3),
    'spearman_p': round(float(p_sp),4),
    'collinear': abs(r_pearson) > 0.70,
}])
coll_df.to_csv('collinearity_gfr_creatinine.csv', index=False, encoding='utf-8-sig')
print('Saved: collinearity_gfr_creatinine.csv')
# ======================================================================
# ---
# ======================================================================
MODEL_ORDER = [
    'Model0_unadjusted',
    'Model1_GFR',
    'Model2_creatinine',
    'Model3_extended',
]
print('── Cluster IRR across models ──')
compare_rows = []
for irr_df in ALL_IRR:
    if irr_df is None: continue
    model_name = irr_df['model'].iloc[0]
    cl_rows = irr_df[irr_df['term'].str.contains('cluster_cat', regex=False)].copy()
    for _, r in cl_rows.iterrows():
        compare_rows.append({
            'model'  : model_name,
            'cluster': r['label'],
            'IRR'    : r['IRR'],
            'CI_lo'  : r['CI_lo'],
            'CI_hi'  : r['CI_hi'],
            'p_value': r['p_value'],
            'sig'    : r['sig'],
        })
comp_df = pd.DataFrame(compare_rows)
if len(comp_df) > 0:
    pivot = comp_df.pivot_table(
        index='cluster', columns='model',
        values=['IRR','p_value'], aggfunc='first')
    print(pivot.to_string())
# ── Full IRR table (all terms, all models) ─────────────────────
all_irr_df = pd.concat([x for x in ALL_IRR if x is not None])
model_meta = {}
for mod_obj, irr_df_item, df_m in [
    (mod0, irr0, df_m0),
    (mod1, irr1, df_m1),
    (mod2, irr2, df_m2),
    (mod3, irr3, df_m3),
]:
    if irr_df_item is None: continue
    name = irr_df_item['model'].iloc[0]
    model_meta[name] = {
        'N': len(df_m),
        'total_hosp': int(df_m['hosp_count'].sum())
    }
all_irr_df['N'] = all_irr_df['model'].map(
    {k: v['N'] for k,v in model_meta.items()})
all_irr_df['total_hosp'] = all_irr_df['model'].map(
    {k: v['total_hosp'] for k,v in model_meta.items()})
all_irr_df.to_csv(
    'hospitalization_nb_multivariable_kmeans_K3.csv',
    index=False, encoding='utf-8-sig')
comp_df.to_csv(
    'hospitalization_cluster_irr_comparison.csv',
    index=False, encoding='utf-8-sig')
print('\nSaved: hospitalization_nb_multivariable_kmeans_K3.csv')
print('Saved: hospitalization_cluster_irr_comparison.csv')
# ── Model fit comparison table ────────────────────────────────
print('\n── Model fit comparison ──')
fit_df = pd.DataFrame([fs for fs in ALL_FIT_STATS if fs is not None])
display_cols = ['model','method','N','total_hosp',
                'log_likelihood','AIC','alpha_dispersion','n_params']
print(fit_df[[c for c in display_cols if c in fit_df.columns]].to_string())
fit_df.to_csv('model_fit_comparison.csv', index=False, encoding='utf-8-sig')
print('Saved: model_fit_comparison.csv')
# ── Zero-inflation check ──────────────────────────────────────
print('\n── Zero-inflation check (Model 1) ──')
if mod1 is not None:
    obs_zeros = (df_m1['hosp_count'] == 0).sum()
    obs_pct   = obs_zeros / len(df_m1) * 100
    mu_hat = mod1.predict()
    alpha_val = mod1.params.get('alpha', None)
    if alpha_val is not None and float(alpha_val) > 0:
        a = float(alpha_val)
        pred_p0 = ((a / (a + mu_hat)) ** (1/a)).mean()
    else:
        pred_p0 = np.exp(-mu_hat).mean()
    pred_zeros = pred_p0 * len(df_m1)
    excess_zeros = obs_zeros - pred_zeros
    zi_ratio = obs_zeros / pred_zeros if pred_zeros > 0 else np.nan
    print(f'  Observed zeros : {obs_zeros} ({obs_pct:.1f}%)')
    print(f'  NB predicted   : {pred_zeros:.1f} ({pred_p0*100:.1f}%)')
    print(f'  Excess zeros   : {excess_zeros:.1f}  ratio={zi_ratio:.2f}')
    if zi_ratio > 1.5:
        print('  → Potential zero-inflation (ratio > 1.5).')
        print('    Consider zero-inflated NB (ZINB) for a sensitivity run.')
    else:
        print('  → No substantial zero-inflation detected.')
        print('    NB model is appropriate for this data.')
    zi_df = pd.DataFrame([{
        'model': 'Model1_GFR', 'obs_zeros': obs_zeros,
        'obs_zeros_pct': round(obs_pct,1),
        'nb_predicted_zeros': round(pred_zeros,1),
        'nb_predicted_pct': round(pred_p0*100,1),
        'excess_zeros': round(excess_zeros,1),
        'zi_ratio': round(float(zi_ratio),3) if not np.isnan(zi_ratio) else np.nan,
        'zi_concern': zi_ratio > 1.5 if not np.isnan(zi_ratio) else None,
    }])
    zi_df.to_csv('zero_inflation_check.csv', index=False, encoding='utf-8-sig')
    print('Saved: zero_inflation_check.csv')
else:
    print('  Model 1 not available; skipping zero-inflation check.')
# ======================================================================
# ---
# ======================================================================
print('=' * 65)
print('Stage 4D4 — QA')
print('=' * 65)
expected_files = [
    'hospitalization_nb_multivariable_kmeans_K3.csv',
    'hospitalization_cluster_irr_comparison.csv',
    'collinearity_gfr_creatinine.csv',
    'model_fit_comparison.csv',
    'zero_inflation_check.csv',
]
qa(mod0 is not None,  'Model 0 fitted')
qa(mod1 is not None,  'Model 1 fitted (GFR)')
qa(mod2 is not None,  'Model 2 fitted (Creatinine)')
qa(mod3 is not None,  'Model 3 fitted (Extended)')
qa(len(ALL_IRR) >= 3, 'At least 3 models in IRR table', 3, len(ALL_IRR))
qa('ALL_FIT_STATS' in dir() and len(ALL_FIT_STATS) >= 3,
   'Fit stats collected for >= 3 models')
qa(os.path.exists('model_fit_comparison.csv'), 'model_fit_comparison.csv saved')
qa(os.path.exists('zero_inflation_check.csv'), 'zero_inflation_check.csv saved')
for f in expected_files:
    qa(os.path.exists(f), f'File saved: {f}')
print()
print('── QA log ──')
for msg in QA_LOG:
    print(' ', msg)
n_warn = sum(1 for m in QA_LOG if m.startswith('WARN'))
print('-' * 65)
print(f'Warnings: {n_warn}/{len(QA_LOG)}')
print('=' * 65)
pd.DataFrame([{'check': m.split('  ',1)[-1],
               'status': 'OK' if m.startswith('OK') else 'WARN'}
              for m in QA_LOG]
).to_csv('qa_stage4d4_summary.csv', index=False, encoding='utf-8-sig')
print()
print('DATA LIMITATION REMINDER:')
print('  hospitalization-count = total count over follow-up only.')
print('  No admission dates, causes, or treatment data available.')
print('  Analysis limited to overall burden; time-to-first-admission')
print('  and cause-specific analysis are not possible from this data.')
try:
    from google.colab import files
    for f in expected_files + ['qa_stage4d4_summary.csv']:
        if os.path.exists(f): files.download(f)
except ImportError:
    print('Not in Colab — files saved locally.')
