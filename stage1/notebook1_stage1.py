"""
Notebook 1 (Stage 1) - Build analytic datasets.

This script implements the full Stage 1 workplan signed off by the user:
  - Sources from stage0_updated_clean_flat.csv (canonical)
  - Applies decisions DEC-037..DEC-043
  - Produces 18 deliverable files in stage1/
  - No models, no feature selection, no clustering.

INPUTS:
  /home/user/dialysis/stage0_updated_clean_flat.csv
  /home/user/dialysis/stage0_final_review_updated_files.xlsx (Main FINAL,
                                                              Sensitivity FINAL,
                                                              Excluded FINAL)
OUTPUTS (in /home/user/dialysis/stage1/):
  stage1_run_metadata.json
  stage1_input_validation.csv
  stage1_comorbidity_binary_check.csv
  stage1_echo_effective_missingness.csv
  stage1_missingness_report.csv
  stage1_exclusions_log.csv
  stage1_oneyear_mortality.csv
  stage1_survival_analysis.csv
  stage1_hospitalization_analysis.csv
  stage1_echo_to_dialysis_timing_summary.csv
  stage1_echo_to_dialysis_timing_categories.csv
  stage1_echo_to_dialysis_extreme_gaps.csv
  stage1_outlier_action_log.csv
  stage1_clinician_category_mapping_applied.csv
  stage1_categorical_counts_before_after.csv
  stage1_variable_processing_log.csv
  stage1_main_analysis.csv
  stage1_sensitivity_analysis.csv
  stage1_exploratory_analysis.csv
  stage1_summary_report.md
"""
import warnings; warnings.filterwarnings('ignore')
import json
import hashlib
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path('/home/user/dialysis')
SOURCE_CSV = ROOT / 'stage0_updated_clean_flat.csv'
META_XLSX = ROOT / 'stage0_final_review_updated_files.xlsx'
OUT = ROOT / 'stage1'
OUT.mkdir(parents=True, exist_ok=True)

# ============================================================
# STEP 1 — Setup, load, validate, save metadata
# ============================================================
print('='*80)
print('Notebook 1 (Stage 1) — Build analytic datasets')
print('='*80)

src_hash = hashlib.md5(SOURCE_CSV.read_bytes()).hexdigest()
df = pd.read_csv(SOURCE_CSV)
N0 = len(df)
print(f'\nSource: {SOURCE_CSV.name}')
print(f'  shape: {df.shape}, md5: {src_hash}')

assert df.patient_id.nunique() == len(df), 'patient_id not unique!'
assert df.patient_id.is_unique
print('  ✓ patient_id unique, n=', N0)

# Load Stage 0 inventory final from xlsx
xls = pd.ExcelFile(META_XLSX)
main_final = pd.read_excel(xls, 'Main FINAL')['column'].tolist()
sens_final = pd.read_excel(xls, 'Sensitivity FINAL')['column'].tolist()
excl_final = pd.read_excel(xls, 'Excluded FINAL')['column'].tolist()
print(f'  Main FINAL: {len(main_final)}, Sensitivity FINAL: {len(sens_final)}, Excluded FINAL: {len(excl_final)}')

# Save run metadata
meta = {
    'run_datetime_utc': datetime.utcnow().isoformat(),
    'source_csv': str(SOURCE_CSV.name),
    'source_md5': src_hash,
    'source_n_rows': int(N0),
    'source_n_cols': int(df.shape[1]),
    'main_n': len(main_final),
    'sensitivity_n': len(sens_final),
    'excluded_n': len(excl_final),
    'decisions_applied': ['DEC-029','DEC-030','DEC-031','DEC-032','DEC-033','DEC-034',
                          'DEC-035','DEC-036','DEC-037','DEC-038','DEC-039','DEC-040',
                          'DEC-041','DEC-042','DEC-043'],
}
(OUT/'stage1_run_metadata.json').write_text(json.dumps(meta, indent=2))

# Input validation report
val_rows = []
for must in ['patient_id','Dialysis_Start_Date','Echo_Date','DeathDate',
             'days_echo_to_dialysis','event','event_1y','died_1year',
             'death_event','time_to_event_days','followup_days',
             'hosp_total','LV_EF','AgeAtFirstHFDate']:
    val_rows.append({
        'column': must,
        'present': must in df.columns,
        'n_missing': int(df[must].isna().sum()) if must in df.columns else None,
        'pct_missing': round(100*df[must].isna().mean(),2) if must in df.columns else None,
    })
val_df = pd.DataFrame(val_rows)
val_df.to_csv(OUT/'stage1_input_validation.csv', index=False)
print('  ✓ input validation written')

# ============================================================
# STEP 2 — Comorbidity binaries (DEC-038)
# ============================================================
print('\nSTEP 2: comorbidity binary check (DEC-038)')
COMORB = ['MI','CABG','IHD','AFIB','HTN','Diabetes mellitus',
          'DYSLIPIDEMIA','COPD','OncologicalDiagnosis']
co_rows = []
for c in COMORB:
    bin_col = f'{c}_binary'
    if bin_col in df.columns:
        # Verify against raw notna
        expected = df[c].notna().astype(int) if c in df.columns else None
        observed = df[bin_col].astype(int)
        match = (expected.equals(observed)) if expected is not None else None
        co_rows.append({
            'comorbidity': c, 'binary_column': bin_col,
            'present': True, 'n_pos': int(observed.sum()),
            'pct_pos': round(100*observed.mean(),2),
            'matches_raw_notna': bool(match) if match is not None else None,
            'unique_vals': sorted(observed.unique().tolist()),
        })
co_df = pd.DataFrame(co_rows)
co_df.to_csv(OUT/'stage1_comorbidity_binary_check.csv', index=False)
print(co_df[['comorbidity','n_pos','pct_pos','matches_raw_notna']].to_string(index=False))

# ============================================================
# STEP 3 — Echo missingness (DEC-039)
# ============================================================
print('\nSTEP 3: echo effective missingness (DEC-039)')
ECHO_CAT = ['LeftVentricleCavitySize','LeftVentricleWallThickness',
            'LeftVentricleSystolicFunction','RVSize','RVSystolicFunction',
            'LACavitySize','AorticValveStructure','AorticValveRegurgitation',
            'MitralValveStructure','MitralRegurgitation',
            'TricuspidValveStructure','TricuspidRegurgitation','ECHO_SPAP']
emiss_rows = []
for c in ECHO_CAT:
    if c not in df.columns: continue
    s = df[c]
    n_nan = int(s.isna().sum())
    n_no_value = int((s == 'No Value').sum())
    n_see_below = int(s.fillna('').astype(str).str.lower().str.startswith('see below').sum())
    n_eff_miss = n_nan + n_no_value + n_see_below
    emiss_rows.append({
        'column': c,
        'n_total': N0,
        'n_nan': n_nan,
        'n_no_value': n_no_value,
        'n_see_below': n_see_below,
        'n_effective_missing': n_eff_miss,
        'pct_effective_missing': round(100*n_eff_miss/N0, 1),
        'n_effective_present': N0 - n_eff_miss,
        'pct_effective_present': round(100*(N0 - n_eff_miss)/N0, 1),
    })
emiss = pd.DataFrame(emiss_rows).sort_values('pct_effective_missing', ascending=False)
emiss.to_csv(OUT/'stage1_echo_effective_missingness.csv', index=False)
print(emiss.to_string(index=False))

# ============================================================
# STEP 4 — Exclusions (DEC-040): same-day or after-death echo
# ============================================================
print('\nSTEP 4: exclusions (DEC-040)')
df['DeathDate'] = pd.to_datetime(df['DeathDate'], errors='coerce')
df['Echo_Date'] = pd.to_datetime(df['Echo_Date'], errors='coerce')
df['Dialysis_Start_Date'] = pd.to_datetime(df['Dialysis_Start_Date'], errors='coerce')

# Echo after death (date-only comparison)
flag_after = df.DeathDate.notna() & df.Echo_Date.notna() & (df.Echo_Date.dt.date > df.DeathDate.dt.date)
# Echo same calendar day as death
flag_same = df.DeathDate.notna() & df.Echo_Date.notna() & (df.Echo_Date.dt.date == df.DeathDate.dt.date)

df['flag_echo_after_death_d1'] = flag_after.astype(int)
df['flag_echo_same_day_as_death'] = flag_same.astype(int)
df['exclude_same_day_or_after_death'] = (flag_after | flag_same).astype(int)

n_after = int(flag_after.sum())
n_same = int(flag_same.sum())
n_excluded = int((flag_after | flag_same).sum())
print(f'  echo after death: {n_after}')
print(f'  echo same day as death: {n_same}')
print(f'  total excluded by DEC-040: {n_excluded}')

excl_log_rows = []
for _, r in df.loc[flag_after | flag_same, ['patient_id','Echo_Date','DeathDate',
                                              'flag_echo_after_death_d1',
                                              'flag_echo_same_day_as_death']].iterrows():
    excl_log_rows.append({
        'patient_id': int(r.patient_id),
        'Echo_Date': str(r.Echo_Date),
        'DeathDate': str(r.DeathDate),
        'reason': 'echo_after_death' if r.flag_echo_after_death_d1==1 else 'echo_same_day_as_death',
        'decision_id': 'DEC-040',
        'applies_to': 'all_three_outcomes',
    })
excl_df = pd.DataFrame(excl_log_rows)
excl_df.to_csv(OUT/'stage1_exclusions_log.csv', index=False)
print(f'  exclusion log: {len(excl_df)} rows')

# ============================================================
# STEP 5 — Time origin and three outcome cohorts
# ============================================================
print('\nSTEP 5: outcome cohorts (DEC-040 applied)')

# Pre-exclusion totals
N_pre = N0
not_excluded = df.exclude_same_day_or_after_death == 0
print(f'  Pre-exclusion N = {N_pre}; post-exclusion N = {int(not_excluded.sum())}')

# 1y mortality cohort
mask_1y = not_excluded & df.died_1year.notna()
print(f'  1-year mortality cohort: n={int(mask_1y.sum())} (events={int(df.loc[mask_1y,"died_1year"].sum())})')

# Survival cohort
mask_surv = not_excluded & df.event.notna() & df.time_to_event_days.notna() & (df.time_to_event_days >= 0)
print(f'  Survival cohort:         n={int(mask_surv.sum())} (events={int(df.loc[mask_surv,"event"].sum())})')

# Hospitalization cohort
mask_hosp = not_excluded & df.hosp_total.notna() & df.followup_days.notna() & (df.followup_days > 0)
print(f'  Hospitalization cohort:  n={int(mask_hosp.sum())} (total hosp={int(df.loc[mask_hosp,"hosp_total"].sum())})')

# Helper to build cohort dataset (lazy column selection for now: keep all)
def cohort_df(d, mask):
    return d.loc[mask].copy().reset_index(drop=True)

# We'll save the cohort *files* later (after all transformations done in steps 6-8)

# ============================================================
# STEP 6 — Echo-to-dialysis timing (DEC-041)
# ============================================================
print('\nSTEP 6: echo-to-dialysis timing (DEC-041)')
g = df.days_echo_to_dialysis  # negative = echo before dialysis (per DEC-032)
timing_summary = pd.DataFrame({
    'metric': ['n','mean','median','sd','min','q25','q75','max'],
    'value': [int(g.notna().sum()), round(g.mean(),2), round(g.median(),2),
              round(g.std(),2), int(g.min()), int(g.quantile(0.25)),
              int(g.quantile(0.75)), int(g.max())]
})
timing_summary.to_csv(OUT/'stage1_echo_to_dialysis_timing_summary.csv', index=False)
print(timing_summary.to_string(index=False))

def timing_cat(d):
    if pd.isna(d): return 'missing'
    if d > 0: return 'after_dialysis'
    if d == 0: return 'same_day'
    if d >= -30: return 'before_0_30d'
    if d >= -90: return 'before_31_90d'
    if d >= -180: return 'before_91_180d'
    if d >= -365: return 'before_181_365d'
    return 'before_gt_365d'

df['echo_timing_cat'] = df.days_echo_to_dialysis.apply(timing_cat)
cat_counts = df.echo_timing_cat.value_counts(dropna=False).reindex(
    ['after_dialysis','same_day','before_0_30d','before_31_90d',
     'before_91_180d','before_181_365d','before_gt_365d','missing']).fillna(0).astype(int)
cat_pct = (100*cat_counts/N0).round(1)
cat_df = pd.DataFrame({'category': cat_counts.index, 'n': cat_counts.values, 'pct': cat_pct.values})
cat_df.to_csv(OUT/'stage1_echo_to_dialysis_timing_categories.csv', index=False)
print(cat_df.to_string(index=False))

extreme = df[df.days_echo_to_dialysis < -365][['patient_id','days_echo_to_dialysis',
                                                 'Echo_Date','Dialysis_Start_Date']].copy()
extreme = extreme.sort_values('days_echo_to_dialysis')
extreme.to_csv(OUT/'stage1_echo_to_dialysis_extreme_gaps.csv', index=False)
print(f'  extreme gaps (>365d before): n={len(extreme)}')

# ============================================================
# STEP 7 — Outlier handling (DEC-030)
# ============================================================
print('\nSTEP 7: outlier action log (DEC-030)')
RULES = {
    'BMI':                                          dict(low=12, high=70, unit='kg/m²'),
    'Weight':                                       dict(low=30, high=200, unit='kg'),
    'LeftVentricleInterventricularSeptumThickness': dict(high=2.5,  unit='cm'),
    'LeftVentriclePosteriorWallThickness':          dict(high=2.0,  unit='cm'),
    'LeftVentricleEstimatedMass':                   dict(high=600,  unit='g'),
    'LeftVentricleEstimatedMassIndex':              dict(high=300,  unit='g/m²'),
}
out_actions = []
for col, r in RULES.items():
    if col not in df.columns: continue
    s = df[col]
    cells = []
    if 'low' in r:
        m = s.notna() & (s < r['low'])
        for pid, v in df.loc[m, ['patient_id', col]].itertuples(index=False):
            cells.append((pid, v, 'low', r['low']))
    if 'high' in r:
        m = s.notna() & (s > r['high'])
        for pid, v in df.loc[m, ['patient_id', col]].itertuples(index=False):
            cells.append((pid, v, 'high', r['high']))
    for pid, v, side, thr in cells:
        # DEC-030: do NOT impute via mean/median; flag and (optionally) set to missing
        # For Stage 1 build, we set the cell to NaN in the analytic datasets ONLY
        # but keep the original value in the source df. Action="set_to_missing".
        out_actions.append({
            'patient_id': int(pid),
            'variable': col,
            'value_before': float(v),
            'side': side,
            'threshold': thr,
            'unit': r['unit'],
            'action': 'set_to_missing',
            'decision_id': 'DEC-030',
            'note': 'Implausible; flagged at Stage 0; in analytic datasets the value is set to missing; patient is retained.',
        })
out_log = pd.DataFrame(out_actions)
out_log.to_csv(OUT/'stage1_outlier_action_log.csv', index=False)
print(f'  outlier actions: {len(out_log)}')

# Apply action: set the cell to NaN ONLY in a working copy used for analytic datasets
df_work = df.copy()
for r in out_actions:
    df_work.loc[df_work.patient_id == r['patient_id'], r['variable']] = np.nan

# ============================================================
# STEP 8 — Clinician category mapping (DEC-037, DEC-043)
# ============================================================
print('\nSTEP 8: clinician category mapping (DEC-037, DEC-043)')

CLIN_MAP = {
    # var: dict of {original_level: grouped_level OR 'IGNORE' (= rare/ignored, treated as base or NaN)}
    'LeftVentricleCavitySize': {
        'Normal': 'Normal',
        'Mildly dilated': 'Mildly dilated',
        'Moderately dilated': 'Moderately-Severely dilated',
        'Severely dilated':   'Moderately-Severely dilated',
        'Small': 'IGNORE',
    },
    'LeftVentricleWallThickness': {
        'Normal': 'Normal',
        'Mildly increased': 'Mildly increased',
        'Moderately increased': 'Moderately-Severely increased',
        'Severely increased':  'Moderately-Severely increased',
    },
    'LeftVentricleSystolicFunction': {
        # No change
        'Normal': 'Normal',
        'Mildly reduced': 'Mildly reduced',
        'Mild-moderately reduced': 'Mild-moderately reduced',
        'Moderately reduced': 'Moderately reduced',
        'Moderate-severely reduced': 'Moderate-severely reduced',
        'Severely reduced': 'Severely reduced',
        'Increased (hyperdynamic)': 'Increased (hyperdynamic)',
    },
    'RVSize': {
        'Normal': 'Normal',
        'Mildly dilated': 'Mildly dilated',
        'Dilated': 'Dilated',
        'RVH': 'IGNORE',
    },
    'AorticValveStructure': {
        'Normal': 'Normal',
        'Thickened': 'Thickened',
        'Calcified': 'Calcified',
        'Bioprosthesis': 'Prosthetic_or_Bioprosthesis',
        'Prosthetic':   'Prosthetic_or_Bioprosthesis',
        'Focal calcification': 'IGNORE',
        'Bicuspid': 'IGNORE',
        'Not well seen': 'IGNORE',
    },
    'AorticValveRegurgitation': {
        'Trivial': 'Trivial',
        'Mild (I)': 'Mild_or_Mild-to-moderate',
        'Mild-to-moderate (I-II)': 'Mild_or_Mild-to-moderate',
        'Moderate (II)':           'Moderate-Severe',
        'Moderately-severe (III)': 'Moderate-Severe',
        'Severe (IV)':             'Moderate-Severe',
    },
    'MitralRegurgitation': {
        'Trivial': 'Trivial',
        'Mild (I)': 'Mild (I)',
        'Mild-to-moderate (I-II)': 'Mild-to-moderate (I-II)',
        'Moderate (II)':           'Moderate-Severe',
        'Moderately-severe (III)': 'Moderate-Severe',
        'Severe (IV)':             'Moderate-Severe',
    },
    'TricuspidRegurgitation': {
        'Trivial': 'Trivial',
        'Mild (I)': 'Mild (I)',
        'Mild-to-moderate (I-II)': 'Mild-to-moderate (I-II)',
        'Moderate (II)':           'Moderate-Severe',
        'Moderately-severe (III)': 'Moderate-Severe',
        'Severe (IV)':             'Moderate-Severe',
    },
    'LACavitySize':       None,   # no change
    'RVSystolicFunction': None,
    'ECHO_SPAP':          None,
}

# First, normalize "No Value" / "See below" to NaN per DEC-039 in df_work
for c in ECHO_CAT:
    if c not in df_work.columns: continue
    df_work.loc[df_work[c]=='No Value', c] = np.nan
    sb = df_work[c].fillna('').astype(str).str.lower().str.startswith('see below')
    df_work.loc[sb, c] = np.nan

# Apply mapping → produce <var>_clin_grouped; rare categories → NaN
applied_rows = []
before_after_rows = []
for var, mapping in CLIN_MAP.items():
    if var not in df_work.columns: continue
    new_col = f'{var}_clin_grouped'
    if mapping is None:
        df_work[new_col] = df_work[var]
        applied_rows.append({'variable': var, 'new_column': new_col,
                            'mapping_action': 'no_change', 'decision_id': 'DEC-037'})
    else:
        def remap(v):
            if pd.isna(v): return v
            target = mapping.get(v, None)
            if target is None: return v   # unknown level: keep as-is to detect later
            if target == 'IGNORE': return np.nan
            return target
        df_work[new_col] = df_work[var].map(remap)
        for src, dst in mapping.items():
            applied_rows.append({'variable': var, 'new_column': new_col,
                                'original_level': src, 'mapped_to': dst,
                                'decision_id': 'DEC-037'})
    # Frequencies before / after
    before = df[var].value_counts(dropna=False) if var in df.columns else pd.Series(dtype=int)
    after = df_work[new_col].value_counts(dropna=False)
    for lvl, n in before.items():
        before_after_rows.append({'variable': var, 'phase': 'before',
                                 'level': str(lvl), 'n': int(n),
                                 'pct': round(100*n/N0, 1)})
    for lvl, n in after.items():
        before_after_rows.append({'variable': var, 'phase': 'after',
                                 'level': str(lvl), 'n': int(n),
                                 'pct': round(100*n/N0, 1)})

apply_df = pd.DataFrame(applied_rows)
ba_df = pd.DataFrame(before_after_rows)
apply_df.to_csv(OUT/'stage1_clinician_category_mapping_applied.csv', index=False)
ba_df.to_csv(OUT/'stage1_categorical_counts_before_after.csv', index=False)
print(f'  mapping applied to {apply_df.variable.nunique()} variables')

# ============================================================
# STEP 9 — Free-text retention (DEC-042)
# ============================================================
print('\nSTEP 9: free-text retention (DEC-042)')
TEXT_COLS = ['LeftVentricleSummary','AorticValveSummary',
             'MitralValveSummary','ProcedureSummary']
text_meta = []
for c in TEXT_COLS:
    if c not in df.columns: continue
    text_meta.append({'column': c, 'role': 'retained_for_future_text_or_NLP_review',
                     'use_as_predictor': False,
                     'n_present': int(df[c].notna().sum()),
                     'pct_present': round(100*df[c].notna().mean(),1)})
text_meta_df = pd.DataFrame(text_meta)
print(text_meta_df.to_string(index=False))

# ============================================================
# STEP 10 — Build final analytic datasets
# ============================================================
print('\nSTEP 10: build analytic datasets')

# Stage 0 inventory split
MAIN = main_final
SENS = sens_final
EXCL = excl_final

# Identifier and outcome columns to always include
IDS_OUTCOME = ['patient_id','Dialysis_Start_Date','Echo_Date','DeathDate',
               'data_cutoff_date','event','event_1y','death_event','died_1year',
               'time_to_event_days','time_to_event_years','followup_days',
               'hosp_total','flag_echo_after_death_d1','flag_echo_same_day_as_death',
               'exclude_same_day_or_after_death','echo_timing_cat']

def build_analytic(df_w, mask, predictor_cols):
    cols = [c for c in IDS_OUTCOME if c in df_w.columns]
    cols += [c for c in predictor_cols if c in df_w.columns and c not in cols]
    # also keep grouped versions for any categorical that was mapped
    for v in CLIN_MAP.keys():
        gc = f'{v}_clin_grouped'
        if gc in df_w.columns and gc not in cols:
            cols.append(gc)
    return df_w.loc[mask, cols].copy().reset_index(drop=True)

main_predictors = [c for c in MAIN if c in df_work.columns]
sens_predictors = [c for c in SENS if c in df_work.columns]
expl_predictors = ['years_since_MI','LeftVentricleSummary','AorticValveSummary',
                  'MitralValveSummary','ProcedureSummary']

# 1y mortality (main predictors)
ds_1y = build_analytic(df_work, mask_1y, main_predictors)
ds_1y.to_csv(OUT/'stage1_oneyear_mortality.csv', index=False)
print(f'  stage1_oneyear_mortality.csv: {ds_1y.shape}')

# Survival (main predictors)
ds_surv = build_analytic(df_work, mask_surv, main_predictors)
ds_surv.to_csv(OUT/'stage1_survival_analysis.csv', index=False)
print(f'  stage1_survival_analysis.csv: {ds_surv.shape}')

# Hospitalization (main predictors)
df_work['followup_years'] = df_work.followup_days / 365.25
df_work['log_followup_years'] = np.log(df_work.followup_years.clip(lower=1e-6))
extra_hosp = ['followup_years','log_followup_years']
def build_hosp(df_w, mask, preds):
    cols = [c for c in IDS_OUTCOME if c in df_w.columns]
    cols += extra_hosp
    cols += [c for c in preds if c in df_w.columns and c not in cols]
    for v in CLIN_MAP.keys():
        gc = f'{v}_clin_grouped'
        if gc in df_w.columns and gc not in cols:
            cols.append(gc)
    return df_w.loc[mask, cols].copy().reset_index(drop=True)
ds_hosp = build_hosp(df_work, mask_hosp, main_predictors)
ds_hosp.to_csv(OUT/'stage1_hospitalization_analysis.csv', index=False)
print(f'  stage1_hospitalization_analysis.csv: {ds_hosp.shape}')

# MAIN dataset = union of three cohorts on main predictors? Per workplan: a single
# main analysis file with main predictors and outcomes, on the not_excluded base.
ds_main = build_hosp(df_work, not_excluded, main_predictors)
ds_main.to_csv(OUT/'stage1_main_analysis.csv', index=False)
print(f'  stage1_main_analysis.csv: {ds_main.shape}')

# Sensitivity dataset
ds_sens = build_hosp(df_work, not_excluded, sens_predictors)
ds_sens.to_csv(OUT/'stage1_sensitivity_analysis.csv', index=False)
print(f'  stage1_sensitivity_analysis.csv: {ds_sens.shape}')

# Exploratory dataset
ds_expl = build_hosp(df_work, not_excluded, expl_predictors + main_predictors[:0])
ds_expl.to_csv(OUT/'stage1_exploratory_analysis.csv', index=False)
print(f'  stage1_exploratory_analysis.csv: {ds_expl.shape}')

# ============================================================
# STEP 11 — Missingness reports
# ============================================================
print('\nSTEP 11: missingness reports')
miss_rows = []
def add_miss(label, dframe, cols):
    for c in cols:
        if c not in dframe.columns: continue
        miss_rows.append({
            'cohort': label,
            'variable': c,
            'n_total': len(dframe),
            'n_missing': int(dframe[c].isna().sum()),
            'pct_missing': round(100*dframe[c].isna().mean(),2),
        })
add_miss('full_cohort', df_work, MAIN+SENS+expl_predictors)
add_miss('one_year_mortality', ds_1y, MAIN)
add_miss('survival', ds_surv, MAIN)
add_miss('hospitalization', ds_hosp, MAIN)
add_miss('main_dataset', ds_main, MAIN)
add_miss('sensitivity_dataset', ds_sens, SENS)
add_miss('exploratory_dataset', ds_expl, expl_predictors)
miss_df = pd.DataFrame(miss_rows)
miss_df.to_csv(OUT/'stage1_missingness_report.csv', index=False)
print(f'  missingness rows: {len(miss_df)}')

# ============================================================
# Variable processing log
# ============================================================
proc_rows = []
for c in df_work.columns:
    src = 'derived' if c not in df.columns else 'source'
    role = 'main' if c in MAIN else ('sensitivity' if c in SENS else
                                     ('text' if c in TEXT_COLS else
                                      ('outcome' if c in IDS_OUTCOME else
                                       ('grouped' if c.endswith('_clin_grouped') else 'other'))))
    proc_rows.append({'column': c, 'source_or_derived': src, 'final_role': role})
pd.DataFrame(proc_rows).to_csv(OUT/'stage1_variable_processing_log.csv', index=False)

# ============================================================
# STEP 12 — Summary report
# ============================================================
print('\nSTEP 12: summary report')
summary = f"""# Stage 1 (Notebook 1) — Summary report

**Run**: {meta['run_datetime_utc']}
**Source**: `{SOURCE_CSV.name}` (md5 `{src_hash}`)

## Cohort flow

| Step | n |
|---|---|
| Source patients | {N0} |
| Excluded by DEC-040 (echo same-day or after death) | {n_excluded} (echo_after_death={n_after}, echo_same_day={n_same}) |
| Eligible base (not excluded) | {int(not_excluded.sum())} |
| 1-year mortality cohort (`died_1year` ∈ {{0,1}}) | {int(mask_1y.sum())} (events = {int(df.loc[mask_1y, "died_1year"].sum())}) |
| Survival cohort | {int(mask_surv.sum())} (events = {int(df.loc[mask_surv,"event"].sum())}) |
| Hospitalization cohort | {int(mask_hosp.sum())} (total hosp = {int(df.loc[mask_hosp,"hosp_total"].sum())}) |

## Decisions applied
- **DEC-029**: source-of-truth = `stage0_updated_clean_flat.csv`
- **DEC-030**: outliers flagged, not central-imputed; in analytic data the implausible cell → NaN; patient retained
- **DEC-031**: outcome / admin / follow-up columns are not predictors
- **DEC-032**: `days_echo_to_dialysis` is the single canonical timing covariate
- **DEC-033**: `RVSize`, `RVSystolicFunction`, `AorticValveRegurgitation` → exploratory/sensitivity only
- **DEC-034**: GFR not used together with creatinine (creatinine kept; GFR moved to sensitivity)
- **DEC-035**: SBP, DBP → sensitivity/descriptive only
- **DEC-036**: `years_since_MI` → exploratory only
- **DEC-037**: clinician-approved category mapping applied to 11 echo categorical vars (3 unchanged, 8 collapsed)
- **DEC-038**: comorbidity NaN = no condition (binary indicators created upstream; verified)
- **DEC-039**: "No Value" / "See below" → missing, not Normal
- **DEC-040**: same-day or after-death echo excluded from analytic cohort
- **DEC-041**: no maximum echo→dialysis cutoff; distribution and predefined categories produced
- **DEC-042**: free-text echo summaries retained but not used as predictors
- **DEC-043**: original variables preserved; `<var>_clin_grouped` parallel; counts before/after reported

## Outlier actions (DEC-030)
{out_log[['variable','side','value_before','threshold']].to_string(index=False) if len(out_log) else 'no outliers flagged'}

## Echo-to-dialysis timing distribution

```
{cat_df.to_string(index=False)}
```

## Variables and roles

| Group | n | source |
|---|---|---|
| Main predictors  | {len(MAIN)} | Stage 0 final |
| Sensitivity      | {len(SENS)} | Stage 0 final |
| Excluded         | {len(EXCL)} | Stage 0 final |
| Free-text retained (DEC-042) | {len(TEXT_COLS)} | n/a (descriptive) |

## Open items still requiring confirmation
- **OPEN-002**: confirm 2025-08-16 as the official administrative censor date (currently provisional). Does not block analytic computations.

## Files produced
"""
files = sorted(p.name for p in OUT.glob('*'))
for f in files:
    summary += f'- `{f}`\n'
(OUT/'stage1_summary_report.md').write_text(summary)
print('\n' + summary)
print('Stage 1 complete.')
