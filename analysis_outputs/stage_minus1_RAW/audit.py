"""
Stage -1 — TRUE raw audit on echo_project_update.xlsx (645 rows × 66 cols).
Purpose:
  1. Inventory every column with type, missingness, NULL semantics
  2. Categorical levels per variable
  3. Free-text vs categorical vs continuous identification
  4. Comorbidity columns: date-encoded → NaN means "no condition"
  5. Identify "No Value" string entries vs true NaN
  6. Date integrity checks (no models — only QC)
  7. Cross-check vs clinician category-merging table
NO MODELS. NO OUTCOME CORRELATIONS.
"""
import warnings; warnings.filterwarnings('ignore')
import json
import numpy as np
import pandas as pd
from pathlib import Path

OUT = Path('/home/user/dialysis/analysis_outputs/stage_minus1_RAW')
OUT.mkdir(parents=True, exist_ok=True)
SRC = '/home/user/dialysis/echo_project_update.xlsx'

xl = pd.ExcelFile(SRC, engine='openpyxl')
print(f'Source file: {SRC}')
print(f'Sheets: {xl.sheet_names}')
df = pd.read_excel(xl, sheet_name=0, engine='openpyxl')
N = len(df)
print(f'Shape: {df.shape}  (n={N} patients × {df.shape[1]} cols)')
print(f'Unique patient_id: {df["patient number"].nunique()}  (duplicates: {df["patient number"].duplicated().sum()})')

# === Variable type inference ===
TEXT_SUMMARY = ['LeftVentricleSummary','AorticValveSummary','MitralValveSummary','ProcedureSummary']
DATE_COMORBID = ['CABG','IHD','AFIB','HTN','Diabetes mellitus','DYSLIPIDEMIA','COPD']
SPECIAL_MI = ['MI']  # mixed (object) — investigate
SPECIAL_ONCO = ['OncologicalDiagnosis']
DATE_OUTCOME = ['DeathDate','Dialysis_Start_Date','Echo_Date']

inv_rows = []
for col in df.columns:
    s = df[col]
    n_miss = int(s.isna().sum())
    pct_miss = round(100*n_miss/N, 1)
    nu = s.nunique(dropna=True)
    dtype = str(s.dtype)

    # Detect "No Value" string entries (treated as missing in clinical data)
    if pd.api.types.is_object_dtype(s) or pd.api.types.is_string_dtype(s):
        n_no_value = int((s.astype(str).str.strip().str.lower() == 'no value').sum())
    else:
        n_no_value = 0
    n_effective_miss = n_miss + n_no_value
    pct_effective_miss = round(100*n_effective_miss/N, 1)

    # NULL semantics inference
    if col in TEXT_SUMMARY:
        sem = 'NULL = no narrative entered (descriptive only; high missingness expected)'
        var_role = 'Echo text (descriptive only)'
    elif col in DATE_COMORBID:
        sem = 'Date-encoded comorbidity → NaN = NO condition (NOT missing)'
        var_role = 'Comorbidity date — derive binary as notna()'
    elif col in SPECIAL_MI:
        sem = 'MIXED dtype object: some dates, some strings → INVESTIGATE'
        var_role = 'Comorbidity (atypical encoding)'
    elif col in SPECIAL_ONCO:
        sem = "String marker: NaN vs 'Oncological diagnosis' → derive binary"
        var_role = 'Comorbidity flag'
    elif col in DATE_OUTCOME:
        sem = 'NaN in DeathDate = censored / alive at last FU; otherwise NaN = data error'
        var_role = 'Outcome / time origin'
    elif col == 'patient number':
        sem = 'Identifier — no missing expected'; var_role = 'ID'
    elif col == 'hospitalization-count':
        sem = 'Always populated (0 or N) — no NaN expected'; var_role = 'Outcome (hosp count)'
    elif pd.api.types.is_numeric_dtype(s) and not col in ['patient number']:
        sem = 'NaN = not measured (true missing)'
        var_role = 'Continuous (echo or lab)'
    elif pd.api.types.is_object_dtype(s):
        sem = "NaN = not entered; 'No Value' string = explicitly recorded as missing"
        var_role = 'Categorical (echo qualitative)'
    else:
        sem = 'unclear'
        var_role = 'unknown'

    if pd.api.types.is_numeric_dtype(s):
        sample_or_levels = f'min={s.min()}, max={s.max()}, median={s.median()}'
    elif pd.api.types.is_datetime64_any_dtype(s):
        sample_or_levels = f'min={s.min()}, max={s.max()}'
    else:
        top = s.value_counts(dropna=False).head(15)
        sample_or_levels = '; '.join(f'{k}: {v} ({100*v/N:.1f}%)' for k, v in top.items())

    inv_rows.append({
        'idx': len(inv_rows), 'column': col, 'dtype': dtype,
        'n_missing_raw_NaN': n_miss, 'pct_missing_raw_NaN': pct_miss,
        'n_NoValue_string': n_no_value,
        'n_effective_missing': n_effective_miss, 'pct_effective_missing': pct_effective_miss,
        'n_unique_nonNaN': nu, 'NULL_semantics': sem, 'role_inference': var_role,
        'sample_or_top_levels': sample_or_levels,
    })

inv = pd.DataFrame(inv_rows)
inv.to_csv(OUT / 'raw_variable_inventory.csv', index=False)

# Print compact summary table grouped by inferred role
print('\n' + '='*80)
print('FULL INVENTORY (66 columns) — grouped by role inference')
print('='*80)
for role in inv.role_inference.unique():
    sub = inv[inv.role_inference == role]
    print(f'\n--- {role}  ({len(sub)} cols) ---')
    for _, r in sub.iterrows():
        marker = ' ⚠' if r.pct_effective_missing > 30 else ''
        nv_note = f' (+{r.n_NoValue_string} "No Value")' if r.n_NoValue_string else ''
        print(f"  [{r.idx:2d}] {r.column:<48s} miss_raw={r.pct_missing_raw_NaN:5.1f}%{nv_note}  "
              f"unique={r.n_unique_nonNaN:>4d}{marker}")

# ====== INVESTIGATE the MI mixed-type column ======
print('\n' + '='*80)
print('INVESTIGATING `MI` (object dtype with 175 unique values, 70.1% missing)')
print('='*80)
s = df['MI']
print(f'Distinct values (sample of first 20):')
for v in list(s.dropna().unique())[:20]:
    print(f'  {repr(v)}')
print(f'Are any non-null entries dates? Try parse:')
parsed = pd.to_datetime(s, errors='coerce')
print(f'  parse-able as date: {parsed.notna().sum()} of {s.notna().sum()} non-null')
print(f'  unparseable strings: {(s.notna() & parsed.isna()).sum()}')
unparsed = s[s.notna() & parsed.isna()]
if len(unparsed) > 0:
    print(f'  unparseable examples: {list(unparsed.unique())[:10]}')

# Save MI investigation
mi_invest = pd.DataFrame({'value': s.value_counts(dropna=False).index.astype(str),
                          'count': s.value_counts(dropna=False).values})
mi_invest.to_csv(OUT / 'MI_column_investigation.csv', index=False)

# ====== DATE QC ======
print('\n' + '='*80)
print('DATE QC')
print('='*80)
for c in ['DeathDate','Dialysis_Start_Date','Echo_Date']:
    s = df[c]
    print(f'  {c}: dtype={s.dtype}, miss={s.isna().sum()} ({100*s.isna().mean():.1f}%), '
          f'min={s.min()}, max={s.max()}')
# Ordering checks
print(f"\nSanity: rows where echo > dialysis (echo AFTER dialysis):  "
      f"{((df.Echo_Date > df.Dialysis_Start_Date)).sum()}")
print(f"Sanity: rows where dialysis > death (dialysis AFTER death): "
      f"{((df.DeathDate.notna()) & (df.Dialysis_Start_Date > df.DeathDate)).sum()}")
print(f"Sanity: rows where echo > death (echo AFTER death): "
      f"{((df.DeathDate.notna()) & (df.Echo_Date > df.DeathDate)).sum()}")

# ====== HD/PD typo check (notebook flagged 3 unique vals) ======
print('\n' + '='*80)
print('HD/PD value cleanup check')
print('='*80)
print(df['HD/PD'].value_counts(dropna=False).to_string())
print(f"  unique stripped: {df['HD/PD'].astype(str).str.strip().value_counts().to_dict()}")
print('  → trailing whitespace likely; will be stripped in Stage 0.')

# m/f
print('\nm/f:')
print(df['m/f'].value_counts(dropna=False).to_string())

# ====== CATEGORICAL LEVELS ======
print('\n' + '='*80)
print('CATEGORICAL LEVELS for echo qualitative variables (raw, n=645)')
print('='*80)
ECHO_CATS = ['LeftVentricleCavitySize','LeftVentricleWallThickness','LeftVentricleSystolicFunction',
             'RVSize','RVSystolicFunction','LACavitySize',
             'AorticValveStructure','AorticValveRegurgitation',
             'MitralValveStructure','MitralRegurgitation',
             'TricuspidValveStructure','TricuspidRegurgitation','ECHO_SPAP']
cat_levels_rows = []
for c in ECHO_CATS:
    print(f'\n--- {c} (unique={df[c].nunique(dropna=True)}, miss={df[c].isna().sum()}) ---')
    vc = df[c].value_counts(dropna=False)
    for k, n in vc.items():
        pct = 100*n/N
        flag = ' ⚠ <5%' if pct < 5 and pd.notna(k) else ''
        nv_flag = ' (No Value string)' if str(k).strip().lower() == 'no value' else ''
        print(f'  {str(k):<35s}  n={n:>4d}  ({pct:5.1f}%){flag}{nv_flag}')
        cat_levels_rows.append({'column': c, 'level': str(k), 'n': n, 'pct': round(pct, 2)})
pd.DataFrame(cat_levels_rows).to_csv(OUT / 'categorical_levels_report.csv', index=False)

# ====== CROSS-CHECK with clinician table ======
print('\n' + '='*80)
print('CROSS-CHECK with clinician category-merging table')
print('='*80)
expected = {
    'LeftVentricleCavitySize': ['Normal','Mildly dilated','Moderately dilated','Severely dilated','Small'],
    'LeftVentricleWallThickness': ['Normal','Mildly increased','Moderately increased','Severely increased'],
    'LeftVentricleSystolicFunction': ['Normal','Mildly reduced','Mild-moderately reduced',
        'Moderately reduced','Moderate-severely reduced','Severely reduced','Increased (hyperdynamic)'],
    'RVSize': ['Normal','Mildly dilated','Dilated','RVH'],
    'AorticValveStructure': ['Normal','Calcified','Thickened','Bioprosthesis','Prosthetic',
                             'Focal calcification','Bicuspid','Not well seen'],
    'AorticValveRegurgitation': ['Trivial','Mild (I)','Mild-to-moderate (I-II)','Moderate (II)',
                                 'Moderately-severe (III)','Severe (IV)'],
    'MitralRegurgitation': ['Trivial','Mild (I)','Mild-to-moderate (I-II)','Moderate (II)',
                            'Moderately-severe (III)','Severe (IV)'],
    'TricuspidRegurgitation': ['Trivial','Mild (I)','Mild-to-moderate (I-II)','Moderate (II)',
                               'Moderately-severe (III)','Severe (IV)'],
    'LACavitySize': ['Normal','Mildly dilated','Moderately dilated','Severely dilated'],
    'RVSystolicFunction': ['Normal','Mildly reduced','Moderately reduced','Severely reduced'],
    'ECHO_SPAP': ['Normal','Mildly increased','Moderately increased','Severely increased'],
}
mismatch_rows = []
for c, exp_lvls in expected.items():
    actual_lvls = set(df[c].dropna().unique()) - {'No Value'}
    expected_set = set(exp_lvls)
    extra = actual_lvls - expected_set
    missing_levels = expected_set - actual_lvls
    has_no_value = (df[c].astype(str).str.strip().str.lower() == 'no value').any()
    print(f"\n  {c}:")
    if not extra and not missing_levels:
        print(f'    ✓ matches clinician table  (No Value present: {has_no_value})')
    else:
        if extra: print(f'    ⚠ extra levels in data: {extra}')
        if missing_levels: print(f'    ⚠ levels in clinician table NOT in data: {missing_levels}')
    mismatch_rows.append({'column': c, 'extra_in_data': sorted(extra),
                          'missing_from_data': sorted(missing_levels), 'has_NoValue_string': has_no_value})
pd.DataFrame(mismatch_rows).to_csv(OUT / 'clinician_table_mismatches.csv', index=False)

# ====== Comorbidity NULL semantics validation ======
print('\n' + '='*80)
print('COMORBIDITY NULL semantics: NaN should mean NO condition')
print('='*80)
for c in DATE_COMORBID + ['MI','OncologicalDiagnosis']:
    s = df[c]
    n_with = s.notna().sum()
    pct_with = 100*n_with/N
    print(f'  {c}: n_with_value={n_with} ({pct_with:5.1f}%) — interpret as "patient HAS this condition"')

# ====== Save raw flat ======
df.to_csv(OUT / 'raw_flat.csv', index=False)

# ====== Save variable inventory MD ======
with open(OUT / 'AUDIT_REPORT.md', 'w', encoding='utf-8') as f:
    f.write('# Stage -1 Raw Audit — `echo_project_update.xlsx`\n\n')
    f.write(f'**Source**: {SRC}\n')
    f.write(f'**Shape**: {df.shape[0]} patients × {df.shape[1]} columns\n')
    f.write(f'**Unique patient IDs**: {df["patient number"].nunique()} (duplicates: {df["patient number"].duplicated().sum()})\n\n')
    f.write('## Variable inventory (grouped by inferred role)\n\n')
    for role in inv.role_inference.unique():
        sub = inv[inv.role_inference == role]
        f.write(f'\n### {role}  ({len(sub)} cols)\n\n')
        f.write('| # | Column | dtype | %miss(raw) | "No Value" str | unique | NULL semantics |\n')
        f.write('|---|---|---|---|---|---|---|\n')
        for _, r in sub.iterrows():
            f.write(f'| {r.idx} | `{r.column}` | {r.dtype} | {r.pct_missing_raw_NaN}% | {r.n_NoValue_string} | {r.n_unique_nonNaN} | {r.NULL_semantics} |\n')

print('\n' + '='*80)
print(f'STAGE -1 OUTPUTS ({OUT}):')
for p in sorted(OUT.glob('*')):
    print(f'  {p.name}  ({p.stat().st_size//1024} KB)')
print('='*80)
print('\nStage -1 (true raw) audit complete. STOP-1 reached.')
