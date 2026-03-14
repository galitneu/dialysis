# ECHO Project — Stage 4D4: Hospitalization Analysis
# Generated from notebook echo_stage4d4_hospitalizations.ipynb
# ======================================================================
# ECHO Project — Stage 4D4: Hospitalization Analysis
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
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
hc = df[COL_HOSP].dropna()
# ── Summary statistics ────────────────────────────────────────
desc = pd.DataFrame([{
    'N'           : int(hc.count()),
    'mean'        : round(hc.mean(), 3),
    'variance'    : round(hc.var(), 3),
    'median'      : int(hc.median()),
    'max'         : int(hc.max()),
    'pct_zeros'   : round((hc == 0).mean() * 100, 1),
    'p95'         : round(hc.quantile(0.95), 1),
    'p99'         : round(hc.quantile(0.99), 1),
}])
print('── Hospitalization count summary ──')
print(desc.to_string())
# ── Count table (0, 1, 2, 3, 4, 5+) ─────────────────────────
bins = [0, 1, 2, 3, 4, 5, int(hc.max()) + 1]
labels = ['0', '1', '2', '3', '4', '5+']
hc_cat = pd.cut(hc, bins=bins, labels=labels, right=False)
count_tbl = (
    hc_cat.value_counts().reindex(labels).reset_index()
    .rename(columns={'index': 'hosp_count', 'count': 'hosp_count'})
)
count_tbl.columns = ['hosp_count_group', 'n_patients']
count_tbl['pct'] = (count_tbl['n_patients'] / len(hc) * 100).round(1)
print('\n── Patients by hospitalisation count ──')
print(count_tbl.to_string())
# ── Histogram + boxplot ──────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(11, 4))
# Histogram
max_val = int(hc.max())
axes[0].hist(hc, bins=range(0, max_val + 2), color='steelblue',
             edgecolor='black', alpha=0.85)
axes[0].set_xlabel('Hospitalisations', fontsize=10)
axes[0].set_ylabel('N patients', fontsize=10)
axes[0].set_title(
    f'Hospitalisation count distribution\n'
    f'N={len(hc)}  mean={hc.mean():.2f}  '
    f'zeros={int((hc==0).sum())} ({(hc==0).mean()*100:.1f}%)',
    fontsize=10)
axes[0].set_xticks(range(0, max_val + 1))
# Boxplot
bp = axes[1].boxplot(hc, vert=True, patch_artist=True,
                     notch=False, widths=0.5)
bp['boxes'][0].set_facecolor('steelblue')
bp['boxes'][0].set_alpha(0.7)
axes[1].set_ylabel('Hospitalisations', fontsize=10)
axes[1].set_xticklabels(['All patients'])
axes[1].set_title(
    f'Boxplot\n'
    f'median={int(hc.median())}  '
    f'p95={hc.quantile(0.95):.1f}  '
    f'p99={hc.quantile(0.99):.1f}',
    fontsize=10)
plt.suptitle('hospitalization-count', fontsize=12, y=1.01)
plt.tight_layout()
plt.savefig('hosp_count_distribution.png', dpi=150, bbox_inches='tight')
plt.close()
print('\nSaved: hosp_count_distribution.png')
# ── Save tables ───────────────────────────────────────────────
desc.to_csv('hosp_count_summary.csv', index=False, encoding='utf-8-sig')
count_tbl.to_csv('hosp_count_table.csv', index=False, encoding='utf-8-sig')
print('Saved: hosp_count_summary.csv, hosp_count_table.csv')
try:
    from google.colab import files
    files.download('hosp_count_distribution.png')
    files.download('hosp_count_summary.csv')
    files.download('hosp_count_table.csv')
except ImportError:
    pass
# ======================================================================
# ---
# ======================================================================
from scipy.stats import spearmanr
# ── Comorbidity vars (for type-aware imputation) ──────────────
COMORBIDITY_VARS = [
    'IHD_binary', 'AFIB_binary', 'HTN_binary',
    'Diabetes mellitus_binary', 'DYSLIPIDEMIA_binary',
    'MI_binary', 'CABG_binary', 'COPD_binary',
]
BINARY_VARS_SET = set(COMORBIDITY_VARS + ['HD_binary'])
# ── Imputation helper ─────────────────────────────────────────
def _impute_var(series, varname):
    s = pd.to_numeric(series, errors='coerce')
    if varname in BINARY_VARS_SET or set(s.dropna().unique()).issubset({0,1}):
        fill_val = s.mode().iloc[0] if len(s.mode()) > 0 else 0
        method   = 'mode'
    else:
        fill_val = s.median()
        method   = 'median'
    return s.fillna(fill_val), method, fill_val
# ── Base modelling dataframe builder ──────────────────────────
def make_model_df(df, extra_vars, drop_high_miss_pct=40):
    """
    Subset to needed columns, impute, return (df_m, used_cols, miss_log).
    Outcome: hosp_count (int). Offset: log_fu. Cluster: cluster_cat.
    """
    needed = [COL_HOSP, COL_TIME_YRS, 'cluster_label'] + [
        v for v in extra_vars if v in df.columns]
    df_m = df[needed].copy()
    df_m = df_m.dropna(subset=[COL_HOSP, COL_TIME_YRS])
    df_m = df_m[df_m[COL_TIME_YRS] > 0].copy()
    df_m['log_fu']     = np.log(df_m[COL_TIME_YRS])
    df_m['hosp_count'] = df_m[COL_HOSP].astype(int)
    df_m['cluster_cat'] = pd.Categorical(
        df_m['cluster_label'].astype(str),
        categories=[str(c) for c in sorted(df_m['cluster_label'].unique())])
    used, miss_log = [], []
    for v in extra_vars:
        if v not in df.columns: continue
        pct = df_m[v].isna().mean() * 100
        if pct >= drop_high_miss_pct:
            print(f'  DROP {v}: {pct:.0f}% missing')
            continue
        imputed, method, fill = _impute_var(df_m[v], v)
        sv = v.replace('-','_').replace(' ','_').replace('/','_')
        df_m[sv] = imputed
        if sv != v:
            df_m = df_m.drop(columns=[v], errors='ignore')
        used.append(sv)
        if df_m[sv].isna().any():
            miss_log.append(f'{v}: {pct:.1f}% imputed ({method}={fill:.3f})')
        elif pct > 0:
            miss_log.append(f'{v}: {pct:.1f}% imputed ({method}={fill:.3f})')
    return df_m, used, miss_log
# ── NB2 fitter (MLE) ─────────────────────────────────────────
import statsmodels.formula.api as smf
def fit_nb2(df_m, covar_safe, step_label):
    """
    NB2 MLE (smf.negativebinomial with exposure offset).
    Falls back to GLM NB if NB2 fails.
    Returns (mod, irr_df, fit_dict) or (None, None, None).
    """
    pred    = ' + '.join(['cluster_cat'] + covar_safe)
    formula = f'hosp_count ~ {pred}'
    method_used = 'NB2_MLE'
    try:
        mod = smf.negativebinomial(
            formula, data=df_m,
            exposure=np.exp(df_m['log_fu'])
        ).fit(method='newton', disp=False, maxiter=200)
        alpha = float(mod.params.get('alpha', np.nan))
    except Exception as e:
        print(f'  NB2 failed ({e}); trying GLM NB ...')
        method_used = 'GLM_NB'
        try:
            mod = smf.glm(
                formula, data=df_m,
                family=sm.families.NegativeBinomial(),
                offset=df_m['log_fu']
            ).fit(disp=False)
            alpha = np.nan
        except Exception as e2:
            print(f'  GLM NB also failed: {e2}')
            return None, None, None
    coef, ci, pv = mod.params, mod.conf_int(), mod.pvalues
    rows = []
    for term in coef.index:
        if term == 'alpha': continue
        irr = np.exp(coef[term])
        lo  = np.exp(ci.loc[term, 0])
        hi  = np.exp(ci.loc[term, 1])
        p   = pv[term]
        lbl = ('Intercept' if term == 'Intercept'
               else term.replace('cluster_cat[T.','C').replace(']',''))
        rows.append(dict(
            step=step_label, method=method_used, term=term, label=lbl,
            IRR=round(irr,3), CI_lo=round(lo,3), CI_hi=round(hi,3),
            p_value=round(p,4),
            sig='***' if p<0.001 else '**' if p<0.01 else '*' if p<0.05 else '',
        ))
    irr_df = pd.DataFrame(rows)
    fit_d  = dict(
        step=step_label, method=method_used,
        N=len(df_m), total_hosp=int(df_m['hosp_count'].sum()),
        n_covars=len(covar_safe),
        LL=round(float(getattr(mod,'llf',np.nan)), 3),
        AIC=round(float(getattr(mod,'aic',np.nan)), 3),
        alpha=round(alpha, 4) if not np.isnan(alpha) else 'NA',
    )
    return mod, irr_df, fit_d
# ── Define sequential steps ───────────────────────────────────
STEPS = [
    ('Step1_cluster_only',   []),
    ('Step2_age_ef',         ['AgeAtFirstHFDate', 'LV_EF']),
    ('Step3_albumin',        ['AgeAtFirstHFDate', 'LV_EF',
                              'albumin-numeric result']),
    ('Step4_sbp',            ['AgeAtFirstHFDate', 'LV_EF',
                              'albumin-numeric result',
                              'sbp-numeric result']),
    ('Step5a_creatinine',    ['AgeAtFirstHFDate', 'LV_EF',
                              'albumin-numeric result',
                              'sbp-numeric result',
                              'creatinine-numeric result']),
    ('Step5b_GFR',           ['AgeAtFirstHFDate', 'LV_EF',
                              'albumin-numeric result',
                              'sbp-numeric result',
                              'GFR']),
    ('Step6_AFIB',           ['AgeAtFirstHFDate', 'LV_EF',
                              'albumin-numeric result',
                              'sbp-numeric result',
                              'creatinine-numeric result',
                              'AFIB_binary']),
]
# ── Run all steps ─────────────────────────────────────────────
ALL_IRR, ALL_FIT, ALL_MODS, ALL_DFS = [], [], {}, {}
for step_name, extra_vars in STEPS:
    print(f'\n── {step_name} ──')
    df_m, used, miss_log = make_model_df(df, extra_vars)
    if miss_log:
        for m in miss_log: print(f'  imputed: {m}')
    mod, irr_df, fit_d = fit_nb2(df_m, used, step_name)
    if mod is None: continue
    # Print cluster IRRs only (not all covariates)
    cl_rows = irr_df[irr_df['term'].str.contains('cluster_cat', regex=False)]
    print(cl_rows[['label','IRR','CI_lo','CI_hi','p_value','sig']].to_string(index=False))
    print(f'  N={fit_d["N"]}  AIC={fit_d["AIC"]}  alpha={fit_d["alpha"]}')
    ALL_IRR.append(irr_df)
    ALL_FIT.append(fit_d)
    ALL_MODS[step_name] = mod
    ALL_DFS[step_name]  = df_m
# ── Collinearity: creatinine vs GFR ──────────────────────────
gfr_v   = pd.to_numeric(df['GFR'], errors='coerce')
creat_v = pd.to_numeric(df['creatinine-numeric result'], errors='coerce')
both    = gfr_v.notna() & creat_v.notna()
r_pear  = gfr_v[both].corr(creat_v[both])
r_sp, p_sp = spearmanr(gfr_v[both], creat_v[both])
print(f'\nCollinearity GFR vs Creatinine: '
      f'Pearson r={r_pear:.3f}  Spearman r={r_sp:.3f}  p={p_sp:.4f}')
print('→ Step 5a (creatinine) and Step 5b (GFR) are run as separate'
      ' sensitivity models for this reason.')
# ======================================================================
# ---
# ======================================================================
# Poisson + robust SE on the same vars as Step 6
REF_STEP = 'Step6_AFIB'
print(f'Sanity check: Poisson + robust SE  (mirroring {REF_STEP})')
if REF_STEP in ALL_DFS:
    df_ps = ALL_DFS[REF_STEP].copy()
    # get the covariates used in Step 6
    ref_irr = next(r for r in ALL_IRR if r['step'].iloc[0] == REF_STEP)
    ref_used = [t for t in ref_irr['term']
                if t not in ('Intercept','alpha')
                and 'cluster_cat' not in t]
    pred    = ' + '.join(['cluster_cat'] + ref_used)
    formula = f'hosp_count ~ {pred}'
    try:
        pois_mod = smf.glm(
            formula, data=df_ps,
            family=sm.families.Poisson(),
            offset=df_ps['log_fu']
        ).fit(cov_type='HC3', disp=False)
        coef_p, ci_p, pv_p = pois_mod.params, pois_mod.conf_int(), pois_mod.pvalues
        poisson_rows = []
        for term in coef_p.index:
            if 'cluster_cat' not in term: continue
            irr = np.exp(coef_p[term])
            lo  = np.exp(ci_p.loc[term, 0])
            hi  = np.exp(ci_p.loc[term, 1])
            p   = pv_p[term]
            lbl = term.replace('cluster_cat[T.','C').replace(']','')
            poisson_rows.append(dict(
                model='Poisson_robust_SE', term=term, label=lbl,
                IRR=round(irr,3), CI_lo=round(lo,3), CI_hi=round(hi,3),
                p_value=round(p,4),
                sig='***' if p<0.001 else '**' if p<0.01 else '*' if p<0.05 else '',
            ))
        poisson_irr = pd.DataFrame(poisson_rows)
        print('Cluster IRRs — Poisson robust SE:')
        print(poisson_irr[['label','IRR','CI_lo','CI_hi','p_value','sig']].to_string(index=False))
        # ── Direction agreement with NB ───────────────────────
        nb_step6 = next((r for r in ALL_IRR if r['step'].iloc[0] == REF_STEP), None)
        if nb_step6 is not None:
            nb_cl = nb_step6[nb_step6['term'].str.contains('cluster_cat', regex=False)]
            print('\nDirection agreement (NB vs Poisson):')
            for _, row_p in poisson_irr.iterrows():
                nb_row = nb_cl[nb_cl['label'] == row_p['label']]
                if nb_row.empty: continue
                nb_irr = float(nb_row['IRR'].values[0])
                p_irr  = float(row_p['IRR'])
                agree  = ('AGREE' if (nb_irr > 1) == (p_irr > 1)
                          else 'DISAGREE')
                print(f'  {row_p["label"]}: '
                      f'NB={nb_irr:.3f}{nb_row["sig"].values[0]}  '
                      f'Poisson={p_irr:.3f}{row_p["sig"]}  '
                      f'→ {agree}')
    except Exception as e:
        print(f'Poisson fit failed: {e}')
        poisson_irr = pd.DataFrame()
else:
    print(f'{REF_STEP} not available; skipping Poisson check.')
    poisson_irr = pd.DataFrame()
# ======================================================================
# ---
# ======================================================================
# ── Fit stats table ───────────────────────────────────────────
fit_df = pd.DataFrame(ALL_FIT)
print('── Model fit progression ──')
print(fit_df[['step','N','n_covars','LL','AIC','alpha']].to_string())
# ── Cluster IRR across all steps ─────────────────────────────
all_irr_df = pd.concat(ALL_IRR, ignore_index=True)
cl_all = all_irr_df[all_irr_df['term'].str.contains('cluster_cat', regex=False)].copy()
cl_pivot = cl_all.pivot_table(
    index='step', columns='label',
    values=['IRR','p_value'], aggfunc='first'
).round(3)
print('\n── Cluster IRR by step ──')
print(cl_pivot.to_string())
# ── Zero-inflation check (Step 6) ────────────────────────────
if 'Step6_AFIB' in ALL_MODS and 'Step6_AFIB' in ALL_DFS:
    mod_zi = ALL_MODS['Step6_AFIB']
    df_zi  = ALL_DFS['Step6_AFIB']
    obs_z  = (df_zi['hosp_count'] == 0).sum()
    obs_pct = obs_z / len(df_zi) * 100
    mu_hat  = mod_zi.predict()
    alpha_v = mod_zi.params.get('alpha', None)
    if alpha_v is not None and float(alpha_v) > 0:
        a = float(alpha_v)
        pred_p0 = ((a / (a + mu_hat)) ** (1/a)).mean()
    else:
        pred_p0 = np.exp(-mu_hat).mean()
    pred_z  = pred_p0 * len(df_zi)
    zi_ratio = obs_z / pred_z if pred_z > 0 else np.nan
    print(f'\n── Zero-inflation check (Step 6) ──')
    print(f'  Observed zeros : {obs_z} ({obs_pct:.1f}%)')
    print(f'  NB predicted   : {pred_z:.1f} ({pred_p0*100:.1f}%)')
    print(f'  Ratio          : {zi_ratio:.2f}')
    print('  → Potential zero-inflation (consider ZINB sensitivity)'
          if zi_ratio > 1.5
          else '  → No substantial zero-inflation; NB adequate.')
# ── Save ──────────────────────────────────────────────────────
fit_df.to_csv('nb_sequential_fit_stats.csv', index=False, encoding='utf-8-sig')
all_irr_df.to_csv('nb_sequential_irr_all.csv', index=False, encoding='utf-8-sig')
cl_all.to_csv('nb_sequential_cluster_irr.csv', index=False, encoding='utf-8-sig')
if not poisson_irr.empty:
    poisson_irr.to_csv('poisson_sanity_irr.csv', index=False, encoding='utf-8-sig')
print('Saved: nb_sequential_fit_stats.csv, nb_sequential_irr_all.csv')
print('       nb_sequential_cluster_irr.csv, poisson_sanity_irr.csv')
# ======================================================================
# ---
# ======================================================================
print('=' * 65)
print('Stage 4D4 — QA')
print('=' * 65)
expected_files = [
    'hosp_count_summary.csv',
    'hosp_count_table.csv',
    'hosp_count_distribution.png',
    'nb_sequential_fit_stats.csv',
    'nb_sequential_irr_all.csv',
    'nb_sequential_cluster_irr.csv',
    'poisson_sanity_irr.csv',
]
qa(len(ALL_IRR) >= 5, 'At least 5 sequential models run', 5, len(ALL_IRR))
qa(len(ALL_FIT)  >= 5, 'Fit stats for >= 5 steps', 5, len(ALL_FIT))
qa('Step1_cluster_only' in ALL_MODS, 'Step 1 fitted')
qa('Step6_AFIB'         in ALL_MODS, 'Step 6 (full) fitted')
qa(not poisson_irr.empty, 'Poisson sanity check run')
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
