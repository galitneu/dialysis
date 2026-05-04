"""
Stage -1 - Raw data audit & flat-file construction.
Source: base_analysis_dataset.xlsx (14 sheets)
Purpose:
  1. Inventory the RAW dataset (all 83 columns)
  2. Compare raw vs stage2_analysis_ready.csv (what was kept/dropped/transformed)
  3. Extract metadata sheets (Feature_Catalog, Main_Features, etc.)
  4. Investigate NULL semantics per variable type
  5. Levels of all categorical variables
  6. Search for Aortic Valve Structure / AR (clinician-listed but absent from stage2)
NO MODELS. NO OUTCOME ANALYSIS.
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd
from pathlib import Path

OUT = Path('/home/user/dialysis/analysis_outputs/stage_minus1')
OUT.mkdir(parents=True, exist_ok=True)
RAW = '/home/user/dialysis/base_analysis_dataset.xlsx'
S2 = '/home/user/dialysis/stage2_analysis_ready.csv'

xls = pd.ExcelFile(RAW)
print(f'Sheets in raw file ({len(xls.sheet_names)}):')
for sn in xls.sheet_names:
    print(f'  - {sn}')

# === A) Read main raw sheet ===
raw = pd.read_excel(xls, sheet_name='base_analysis_dataset')
N_RAW = len(raw)
print(f'\n=== RAW base_analysis_dataset ===')
print(f'Shape: {raw.shape}  (n={N_RAW} patients, {raw.shape[1]} cols)')
print(f'Unique patient_id: {raw.patient_id.nunique()}  (duplicates: {raw.patient_id.duplicated().sum()})')

# === B) Read stage2 ===
s2 = pd.read_csv(S2)
N_S2 = len(s2)
print(f'\n=== STAGE2 stage2_analysis_ready.csv ===')
print(f'Shape: {s2.shape}')
print(f'Unique patient_id: {s2.patient_id.nunique()}')
extra_in_s2_rows = N_S2 - N_RAW
print(f'Patient overlap with raw: '
      f'in_both={raw.patient_id.isin(s2.patient_id).sum()}, '
      f'only_raw={(~raw.patient_id.isin(s2.patient_id)).sum()}, '
      f'only_s2={(~s2.patient_id.isin(raw.patient_id)).sum()}')

# === C) Read metadata sheets ===
meta = {}
for sheet in ['Feature_Catalog','Main_Features','Sensitivity_Features',
              'Excluded_Features','Imputation_Log','Encoding_Map',
              'Feature_Processing_Map','Descriptive_Stats',
              'High_Correlations','QA_Summary_Stage2','QA_Summary_Stage3']:
    try:
        meta[sheet] = pd.read_excel(xls, sheet_name=sheet)
    except Exception as e:
        print(f'WARN: failed to read {sheet}: {e}')

print(f'\nLoaded metadata sheets: {list(meta.keys())}')

# === D) Compare raw columns vs stage2 columns ===
raw_cols = set(raw.columns); s2_cols = set(s2.columns)
only_in_raw = sorted(raw_cols - s2_cols)
only_in_s2  = sorted(s2_cols - raw_cols)
in_both     = sorted(raw_cols & s2_cols)
print(f'\n=== COLUMN COMPARISON ===')
print(f'  in both:       {len(in_both)}')
print(f'  only in raw:   {len(only_in_raw)}')
print(f'  only in stage2:{len(only_in_s2)}')

print(f'\n--- Columns ONLY in RAW (not carried into stage2) ---')
for c in only_in_raw:
    n_present = raw[c].notna().sum()
    pct_present = 100*n_present/N_RAW
    sample = raw[c].dropna().head(3).tolist()
    print(f'  {c}  (n_present={n_present} = {pct_present:.1f}%)  sample={sample}')

print(f'\n--- Columns ONLY in STAGE2 (created/derived) ---')
for c in only_in_s2:
    print(f'  {c}')

# === E) Inventory of ALL raw columns ===
inv_rows = []
for c in raw.columns:
    s = raw[c]
    n_miss = int(s.isna().sum())
    pct_miss = 100*n_miss/N_RAW
    nu = s.nunique(dropna=True)
    if pd.api.types.is_numeric_dtype(s):
        vt = 'binary' if nu<=2 else ('continuous' if nu>10 else 'discrete')
        sample_or_levels = f'min={s.min()}, max={s.max()}, median={s.median()}'
    else:
        vt = 'categorical/string/date'
        top = s.value_counts(dropna=False).head(10)
        sample_or_levels = '; '.join(f'{k}: {v} ({100*v/N_RAW:.1f}%)' for k,v in top.items())
    inv_rows.append({
        'column': c, 'dtype': str(s.dtype), 'vtype': vt,
        'n_missing': n_miss, 'pct_missing': round(pct_miss,1),
        'n_unique': nu, 'in_stage2': c in s2_cols,
        'sample_or_levels': sample_or_levels
    })
inv = pd.DataFrame(inv_rows)
inv.to_csv(OUT/'raw_variable_inventory.csv', index=False)

# === F) Search for Aortic Valve Structure / Aortic Regurgitation ===
print(f'\n=== SEARCH for AV Structure & AR in RAW ===')
hits = [c for c in raw.columns if 'aort' in c.lower() or 'AR_' in c or c.endswith('AR')
        or 'aortic' in c.lower() or 'regurg' in c.lower() or 'valve' in c.lower()]
if hits:
    for c in hits:
        print(f'  ✓ FOUND in raw: {c}')
        print(f'    - n_present={raw[c].notna().sum()}  ({100*raw[c].notna().mean():.1f}%)')
        print(f'    - in stage2? {c in s2_cols}')
        if not pd.api.types.is_numeric_dtype(raw[c]):
            print(f'    - levels: {raw[c].value_counts(dropna=False).head(15).to_dict()}')
else:
    print('  ✗ No aort/AR/valve/regurg columns found in raw either')

# === G) Categorical levels report — all categorical/string columns ===
print(f'\n=== CATEGORICAL LEVELS (all string/categorical columns) ===')
cat_levels_rows = []
for c in raw.columns:
    if pd.api.types.is_numeric_dtype(raw[c]) or pd.api.types.is_datetime64_any_dtype(raw[c]):
        continue
    vc = raw[c].value_counts(dropna=False)
    for lvl, n in vc.items():
        pct = 100*n/N_RAW
        cat_levels_rows.append({'column':c, 'level': str(lvl), 'n':n, 'pct': round(pct,2)})
cats_df = pd.DataFrame(cat_levels_rows)
cats_df.to_csv(OUT/'categorical_levels_report.csv', index=False)

# === H) NULL semantics — try to infer ===
print(f'\n=== NULL semantics inference ===')
print('  (heuristic: comorbidity-like binaries with NaN may mean "no disease")')
binary_like = [c for c in raw.columns if raw[c].dropna().isin([0,1,True,False,'0','1','Yes','No']).all()
               and raw[c].notna().sum() > 0]
print(f'  Binary-like columns ({len(binary_like)}):')
for c in binary_like[:25]:
    n_miss = raw[c].isna().sum()
    n_one = (raw[c]==1).sum() if pd.api.types.is_numeric_dtype(raw[c]) else (raw[c]=='1').sum()
    print(f'    {c}: missing={n_miss} ({100*n_miss/N_RAW:.1f}%), n_pos={n_one}')

# === I) Examine Feature_Catalog and Main/Sensitivity/Excluded ===
fc = meta['Feature_Catalog']
print(f'\n=== Feature_Catalog ({len(fc)} entries) ===')
print(f'Domains: {fc.domain.value_counts().to_dict()}')
print(f'Statuses: {fc.feature_status.value_counts().to_dict()}')
fc.to_csv(OUT/'feature_catalog.csv', index=False)

# Save Main / Sensitivity / Excluded for reference
meta['Main_Features'].to_csv(OUT/'main_features.csv', index=False)
meta['Sensitivity_Features'].to_csv(OUT/'sensitivity_features.csv', index=False)
meta['Excluded_Features'].to_csv(OUT/'excluded_features.csv', index=False)
meta['Imputation_Log'].to_csv(OUT/'imputation_log.csv', index=False)
meta['Encoding_Map'].to_csv(OUT/'encoding_map.csv', index=False)
meta['Descriptive_Stats'].to_csv(OUT/'descriptive_stats_from_raw.csv', index=False)

# === J) Build a true RAW->FLAT version (simply save the raw sheet as a CSV for transparency) ===
raw.to_csv(OUT/'raw_flat.csv', index=False)
print(f'\nSaved raw flat as raw_flat.csv ({raw.shape})')

# === K) Missingness summary by domain (using Feature_Catalog) ===
print(f'\n=== MISSINGNESS SUMMARY by domain (per Feature_Catalog) ===')
fc_with_miss = fc.copy()
fc_with_miss['miss_in_raw'] = fc_with_miss.variable_name.map(lambda v: raw[v].isna().mean()*100 if v in raw.columns else None)
print(fc_with_miss.groupby('domain').agg(
    n_vars=('variable_name','count'),
    median_miss=('miss_in_raw','median'),
    max_miss=('miss_in_raw','max')
).round(1).to_string())
fc_with_miss.to_csv(OUT/'missingness_report.csv', index=False)

# === L) Final raw-vs-stage2 column comparison ===
comp = []
for c in sorted(raw_cols | s2_cols):
    comp.append({
        'column': c, 'in_raw': c in raw_cols, 'in_stage2': c in s2_cols,
        'raw_pct_missing': round(100*raw[c].isna().mean(),1) if c in raw_cols else None,
        's2_pct_missing': round(100*s2[c].isna().mean(),1) if c in s2_cols else None,
    })
pd.DataFrame(comp).to_csv(OUT/'raw_vs_stage2_column_comparison.csv', index=False)

print(f'\n=== Stage -1 OUTPUTS ({OUT}) ===')
for p in sorted(OUT.glob('*')):
    print(f'  {p.name}  ({p.stat().st_size//1024} KB)')
print('\nStage -1 audit complete.')
