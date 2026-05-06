"""
Stage 3 — Build pre-processed matrix for phenotyping clustering.

Implements DEC-PHENO-004 and DEC-PHENO-005:
- Source: base_analysis_dataset.xlsx → 'base_analysis_dataset' sheet (raw values)
- Variables: 18 core variables per Stage 2 doc
- Imputation: kNN(k=5) for variables 5-25% missing; drop patients with >5% missing on <5%-missing vars
- Scaling: z-score for continuous; binary kept as 0/1
- Categorical collapses: LACavitySize and TR → Mod/Severe vs Normal/Mild

Outputs:
- outputs/phenotyping/stage3_preprocessed_matrix_core.csv  (18 vars × n patients)
- outputs/phenotyping/stage3_preprocessed_matrix_extended.csv  (24 vars)
- outputs/phenotyping/stage3_preprocessing_diagnostics.csv  (imputation rates, n retained)
- outputs/phenotyping/stage3_imputation_flags.csv  (per-patient flags for imputed cells)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.impute import KNNImputer
from sklearn.preprocessing import StandardScaler

INPUT = Path('/home/user/dialysis/base_analysis_dataset.xlsx')
OUTDIR = Path('/home/user/dialysis/outputs/phenotyping')
OUTDIR.mkdir(parents=True, exist_ok=True)

# ----------------------------------------------------------------
# Variable definitions per DEC-PHENO-005
# ----------------------------------------------------------------

CORE_CONTINUOUS = [
    'AgeAtFirstHFDate',
    'LV_EF',
    'LeftVentricleEndDiastolicDiameter',
    'LeftVentriclePosteriorWallThickness',
    'LeftVentricleEstimatedMass',
    'MitralInflowPeakEWave',
    'TissueDopplerEERatioSeptal',
    'EstimatedSysPAPressure',
    'albumin-numeric result',
    'creatinine-numeric result',
    'crp-numeric result',
    'hb-numeric result',
]

CORE_BINARY_DIRECT = [
    'AFIB_binary',
    'Diabetes mellitus_binary',
]

# These need derivation from raw categorical/string columns
CORE_DERIVED = [
    'sex_male',                # 1 if m/f == 'm'
    'HD_binary',               # 1 if HD/PD == 'HD'
    'LACavity_dilated',        # 1 if LACavitySize in {Mildly, Moderately, Severely dilated}
    'TR_moderate_or_severe',   # 1 if TricuspidRegurgitation in moderate/severe levels
]

# Sensitivity set adds these
SENS_ADD_CONTINUOUS = [
    'BMI',
    'Weight',
    'LeftVentricleScoreIndex',
    'LeftVentricleEstimatedMassIndex',
    'TissueDopplerEVelositySeptal',
    'urea-numeric result',
]

# ----------------------------------------------------------------
# Load raw
# ----------------------------------------------------------------

print('Loading raw data...')
raw = pd.read_excel(INPUT, sheet_name='base_analysis_dataset')
print(f'  raw shape: {raw.shape}')

# Sanity: patient_id is unique
assert raw['patient_id'].is_unique, 'patient_id not unique'

# ----------------------------------------------------------------
# Build derived binaries
# ----------------------------------------------------------------

derived = pd.DataFrame({'patient_id': raw['patient_id']})
derived['sex_male'] = (raw['m/f'].astype(str).str.lower() == 'm').astype('Int64')
derived.loc[raw['m/f'].isna(), 'sex_male'] = pd.NA

derived['HD_binary'] = (raw['HD/PD'].astype(str).str.upper() == 'HD').astype('Int64')
derived.loc[raw['HD/PD'].isna(), 'HD_binary'] = pd.NA

# LACavitySize: collapse
def la_collapse(x):
    if pd.isna(x): return np.nan
    s = str(x).lower().strip()
    if any(t in s for t in ['mildly dilated', 'moderately dilated', 'severely dilated']):
        return 1
    if 'normal' in s:
        return 0
    return np.nan

derived['LACavity_dilated'] = raw['LACavitySize'].map(la_collapse).astype('Float64')

# TR: collapse to moderate or severe
def tr_collapse(x):
    if pd.isna(x): return np.nan
    s = str(x).lower().strip()
    if any(t in s for t in ['moderate', 'severe', 'iii', 'iv']):
        return 1
    if any(t in s for t in ['none', 'trace', 'trivial', 'mild', 'i ', '(i)']):
        return 0
    return np.nan

derived['TR_moderate_or_severe'] = raw['TricuspidRegurgitation'].map(tr_collapse).astype('Float64')

# ----------------------------------------------------------------
# Pull continuous + direct binaries
# ----------------------------------------------------------------

cont = raw[['patient_id'] + CORE_CONTINUOUS].copy()
binary_direct = raw[['patient_id'] + CORE_BINARY_DIRECT].copy()

# Merge into a single matrix (long-name → short-name later if needed)
core = (cont
        .merge(binary_direct, on='patient_id')
        .merge(derived, on='patient_id'))

print(f'\nCore matrix shape (pre-imputation): {core.shape}')
print(f'Variables: {[c for c in core.columns if c != "patient_id"]}')

# ----------------------------------------------------------------
# Pre-imputation diagnostics
# ----------------------------------------------------------------

diag_rows = []
for col in core.columns:
    if col == 'patient_id': continue
    n_miss = core[col].isna().sum()
    pct_miss = 100 * n_miss / len(core)
    diag_rows.append({
        'variable': col,
        'n_total': len(core),
        'n_missing_pre': n_miss,
        'pct_missing_pre': pct_miss,
        'imputation_method': 'kNN(k=5)' if pct_miss > 5 else 'drop_patients_with_missing',
    })
diag_pre = pd.DataFrame(diag_rows)
print('\nPre-imputation missingness:')
print(diag_pre.to_string(index=False))

# ----------------------------------------------------------------
# Per DEC-PHENO-004:
# - For variables with <5% missing: drop patients with any missing
# - For variables with 5-25% missing: kNN-impute
# ----------------------------------------------------------------

low_miss_vars = diag_pre.loc[diag_pre['pct_missing_pre'] < 5, 'variable'].tolist()
mid_miss_vars = diag_pre.loc[(diag_pre['pct_missing_pre'] >= 5) & (diag_pre['pct_missing_pre'] < 25), 'variable'].tolist()

print(f'\nLow-missing (<5%, drop patients): {low_miss_vars}')
print(f'\nMid-missing (5-25%, kNN-impute): {mid_miss_vars}')

# Drop patients missing on low-miss vars
n_before = len(core)
core_dropped = core.dropna(subset=low_miss_vars).copy()
n_dropped = n_before - len(core_dropped)
print(f'\nDropped {n_dropped} patients with missing low-missingness vars; remaining: {len(core_dropped)}')

# ----------------------------------------------------------------
# Build imputation-flag matrix BEFORE imputing (so we can audit later)
# ----------------------------------------------------------------

imp_flags = pd.DataFrame({'patient_id': core_dropped['patient_id'].values})
for col in mid_miss_vars:
    imp_flags[f'imputed__{col}'] = core_dropped[col].isna().astype(int).values
imp_flags.to_csv(OUTDIR / 'stage3_imputation_flags.csv', index=False)
print(f'\nImputation flag matrix saved (per-patient, per-variable indicator).')

# ----------------------------------------------------------------
# kNN imputation
# Note: kNN imputer needs all-numeric input; binaries (0/1/NA) work fine.
# Run on the SCALED data so distance metric is fair across vars (so we scale, then impute, then scaled is the matrix).
# Workflow: scale (skipping NaN) → kNN-impute → final z-scored matrix
# ----------------------------------------------------------------

feature_cols = [c for c in core_dropped.columns if c != 'patient_id']
X = core_dropped[feature_cols].astype(float).values

# Track which are continuous vs binary (binaries don't need to be scaled in the final output, but kNN needs comparable scale)
binary_cols = ['sex_male', 'HD_binary', 'AFIB_binary', 'Diabetes mellitus_binary',
               'LACavity_dilated', 'TR_moderate_or_severe']
continuous_cols = [c for c in feature_cols if c not in binary_cols]
print(f'\nContinuous vars: {continuous_cols}')
print(f'Binary vars: {binary_cols}')

# Scale continuous columns
scaler_pre = StandardScaler()
X_scaled = X.copy()
cont_idx = [feature_cols.index(c) for c in continuous_cols]
bin_idx = [feature_cols.index(c) for c in binary_cols]

# Fit scaler on observed (non-NaN) values
cont_block = X[:, cont_idx]
scaler_pre.fit(np.where(np.isnan(cont_block), 0, cont_block))  # ignore NaN by zero-filling for fitting (KNN handles NaNs anyway)
# Better: use nan-safe scaler
mu = np.nanmean(cont_block, axis=0)
sig = np.nanstd(cont_block, axis=0, ddof=0)
sig[sig == 0] = 1.0
X_scaled[:, cont_idx] = (cont_block - mu) / sig

# Run kNN on scaled data
print('\nRunning kNN imputation (k=5)...')
imputer = KNNImputer(n_neighbors=5, weights='distance')
X_imp = imputer.fit_transform(X_scaled)

# Verify no NaN remain
assert not np.isnan(X_imp).any(), 'NaN remaining after imputation'
print(f'  imputed matrix shape: {X_imp.shape}; no NaNs remaining')

# Round binaries back to 0/1 (kNN may produce values like 0.27)
for i in bin_idx:
    X_imp[:, i] = (X_imp[:, i] >= 0.5).astype(float)

# ----------------------------------------------------------------
# Save final core matrix
# ----------------------------------------------------------------

final = pd.DataFrame(X_imp, columns=feature_cols)
final.insert(0, 'patient_id', core_dropped['patient_id'].values)
final.to_csv(OUTDIR / 'stage3_preprocessed_matrix_core.csv', index=False)
print(f'\nCore preprocessed matrix saved: {final.shape}')

# ----------------------------------------------------------------
# Diagnostic report
# ----------------------------------------------------------------

post_diag = []
for col in feature_cols:
    pre = diag_pre.loc[diag_pre['variable'] == col].iloc[0]
    post_diag.append({
        'variable': col,
        'n_pre_drop': len(core),
        'n_post_drop': len(core_dropped),
        'n_missing_pre_drop': int(pre['n_missing_pre']),
        'pct_missing_pre_drop': pre['pct_missing_pre'],
        'imputation_method': pre['imputation_method'],
        'in_final_matrix': True,
    })
post_diag_df = pd.DataFrame(post_diag)
post_diag_df.to_csv(OUTDIR / 'stage3_preprocessing_diagnostics.csv', index=False)

print('\n=== STAGE 3 SUMMARY ===')
print(f'Patients pre-drop:  {len(core)}')
print(f'Patients post-drop: {len(core_dropped)}  (dropped {n_dropped} with low-missing-var missingness)')
print(f'Variables in core matrix: {len(feature_cols)}')
print(f'Variables imputed (kNN k=5): {len(mid_miss_vars)}')
print(f'  → {mid_miss_vars}')
print(f'Outputs in: {OUTDIR}')
