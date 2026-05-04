"""
Stage 0 - Data audit and variable inventory.
Purpose: full transparent listing of every column in the source dataset.
Outputs: 00_audit.csv (machine-readable), 00_audit.md (human-readable).
NO MODELS. NO OUTCOME ANALYSIS. PURELY DESCRIPTIVE.
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd

# Use the FULL n=645 dataset to match the clinician's table percentages exactly
df = pd.read_csv('/home/user/dialysis/stage2_analysis_ready.csv')
N_TOTAL = len(df)
print(f'Source file: stage2_analysis_ready.csv')
print(f'Total rows (n): {N_TOTAL}')
print(f'Total columns: {len(df.columns)}')
print()

# --- proposed axis classification (pre-outcome, clinical reasoning) ---
AXIS_MAP = {
    # Identifiers / admin
    'patient_id': ('Admin', 'Excluded'),
    'Dialysis_Start_Date': ('Admin', 'Excluded'),
    'selected_Echo_Date': ('Admin', 'Excluded'),

    # Outcomes
    'event': ('Outcome', 'Outcome — secondary (Cox)'),
    'time_to_event_days': ('Outcome', 'Outcome — secondary (Cox)'),
    'time_to_event_years': ('Outcome', 'Outcome — secondary (Cox, redundant)'),
    'followup_days': ('Outcome', 'Outcome — denominator for hosp rate'),
    'died_1year': ('Outcome', 'Outcome — primary (1y mortality)'),
    'hosp_total': ('Outcome', 'Outcome — primary (hosp rate)'),

    # Echo timing
    'echo_to_dialysis_days': ('Timing', 'Core clinical (covariate)'),
    'echo_timing_class': ('Timing', 'Descriptive only — used to define cohort'),
    'echo_before_dialysis': ('Timing', 'Descriptive only — redundant with class'),

    # Demographics / clinical
    'AgeAtFirstHFDate': ('Clinical', 'Core clinical'),
    'Age_z': ('Clinical', 'Excluded — pre-z-scored, redundant'),
    'sex_male': ('Clinical', 'Core clinical'),
    'HD_binary': ('Clinical', 'Candidate covariate (full base)'),
    'IHD_binary': ('Clinical', 'Candidate covariate (full base)'),
    'AFIB_binary': ('Clinical', 'Candidate covariate (full base)'),
    'Diabetes mellitus_binary': ('Clinical', 'Candidate covariate (full base)'),
    'MI_binary': ('Clinical', 'Candidate covariate (full base)'),
    'CABG_binary': ('Clinical', 'Candidate covariate (full base)'),
    'HTN_binary': ('Clinical', 'Candidate covariate (full base)'),
    'COPD_binary': ('Clinical', 'Candidate covariate (full base)'),

    # Labs
    'albumin-numeric result': ('Lab', 'Candidate covariate (full base)'),
    'albumin_z': ('Lab', 'Excluded — pre-z-scored'),
    'creatinine-numeric result': ('Lab', 'Core clinical (parsimonious base)'),
    'creatinine_z': ('Lab', 'Excluded — pre-z-scored'),
    'GFR': ('Lab', 'Candidate covariate (alternative to creatinine)'),
    'GFR_z': ('Lab', 'Excluded — pre-z-scored'),
    'hb-numeric result': ('Lab', 'Candidate covariate (full base)'),
    'crp-numeric result': ('Lab', 'Candidate covariate (full base)'),
    'sbp-numeric result': ('Lab', 'Sensitivity (>20% missing)'),
    'dbp-numeric result': ('Lab', 'Sensitivity (>20% missing)'),

    # ---- ECHO: Benchmark ----
    'LV_EF': ('Echo: Benchmark', 'Benchmark — fixed in all models'),
    'LV_EF_z': ('Echo: Benchmark', 'Excluded — pre-z-scored'),

    # ---- ECHO: LV systolic (other than EF) ----
    'TissueDopplerSVelocitySeptal': ('Echo: LV systolic (other)', 'Candidate'),
    'TissueDopplerSVelocityLateral': ('Echo: LV systolic (other)', 'Candidate'),
    'LeftVentricleSystolicFunction': ('Echo: LV systolic (other)', 'Candidate (categorical)'),
    'LeftVentricleSystolicFunction_ord': ('Echo: LV systolic (other)', 'Excluded — superseded by categorical'),
    'LeftVentricleScoreIndex': ('Echo: LV systolic (other)', 'Sensitivity (overlap with EF)'),

    # ---- ECHO: LV diastolic / filling ----
    'MitralInflowPeakEWave': ('Echo: LV diastolic / filling', 'Candidate'),
    'TissueDopplerEVelositySeptal': ('Echo: LV diastolic / filling', 'Candidate (was previously OMITTED)'),
    'TissueDopplerEVelosityLateral': ('Echo: LV diastolic / filling', 'Candidate (was previously OMITTED)'),
    'TissueDopplerEERatioSeptal': ('Echo: LV diastolic / filling', 'Candidate'),
    'TissueDopplerEERatioLateral': ('Echo: LV diastolic / filling', 'Candidate'),
    'EeRatio_avg': ('Echo: LV diastolic / filling', 'Candidate (derived)'),
    'Ewave_z': ('Echo: LV diastolic / filling', 'Excluded — pre-z-scored'),
    'EeRatioSep_z': ('Echo: LV diastolic / filling', 'Excluded — pre-z-scored'),

    # ---- ECHO: LV structure / mass ----
    'LeftVentricleEstimatedMass': ('Echo: LV structure / mass', 'Sensitivity (use LVMI instead)'),
    'LeftVentricleEstimatedMassIndex': ('Echo: LV structure / mass', 'Candidate (LVMI)'),
    'LeftVentricleInterventricularSeptumThickness': ('Echo: LV structure / mass', 'Sensitivity'),
    'LeftVentriclePosteriorWallThickness': ('Echo: LV structure / mass', 'Sensitivity'),
    'LeftVentricleEndDiastolicDiameter': ('Echo: LV structure / mass', 'Sensitivity'),
    'LeftVentricleEndSystolicDiameter': ('Echo: LV structure / mass', 'Sensitivity'),
    'LeftVentricleCavitySize': ('Echo: LV structure / mass', 'Sensitivity (categorical)'),
    'LeftVentricleWallThickness': ('Echo: LV structure / mass', 'Sensitivity (categorical)'),
    'LVMI_z': ('Echo: LV structure / mass', 'Excluded — pre-z-scored'),
    'IVS_z': ('Echo: LV structure / mass', 'Excluded — pre-z-scored'),
    'LVEDD_z': ('Echo: LV structure / mass', 'Excluded — pre-z-scored'),

    # ---- ECHO: LA / atrial ----
    'LACavitySize': ('Echo: LA / atrial', 'Candidate (categorical)'),

    # ---- ECHO: Right-heart / congestion (TR moved here) ----
    'TricuspidRegurgitation': ('Echo: Right-heart / congestion', 'Candidate (categorical, merged)'),
    'EstimatedSysPAPressure': ('Echo: Right-heart / congestion', 'Candidate (numeric SPAP)'),
    'SPAP_z': ('Echo: Right-heart / congestion', 'Excluded — pre-z-scored'),
    'ECHO_SPAP': ('Echo: Right-heart / congestion', 'Candidate (categorical)'),
    'RVSize': ('Echo: Right-heart / congestion', 'Candidate (categorical, RVH dropped)'),
    'RVSystolicFunction': ('Echo: Right-heart / congestion', 'Candidate (categorical)'),

    # ---- ECHO: Valves (other than TR which moved) ----
    'MitralRegurgitation': ('Echo: Valves', 'Candidate (categorical, merged)'),

    # QC flags
    'flag_missing_dialysis_date': ('QC flag', 'Excluded'),
    'flag_missing_echo_date': ('QC flag', 'Excluded'),
    'flag_no_patient_level_followup_date': ('QC flag', 'Excluded'),
    'flag_death_before_dialysis': ('QC flag', 'Excluded'),
    'flag_negative_followup': ('QC flag', 'Excluded'),
    'flag_echo_after_dialysis': ('QC flag', 'Used to define cohort'),
    'flag_echo_same_day': ('QC flag', 'Used to define cohort'),
    'flag_echo_more_than_365d_before_dialysis': ('QC flag', 'Used to define cohort'),
    'flag_short_followup_for_1y_outcome': ('QC flag', 'Used to define cohort'),
    'flag_multiple_echo_records': ('QC flag', 'Excluded'),
    'flag_hosp_1y_not_computable': ('QC flag', 'Excluded'),
    'flag_manual_review_needed': ('QC flag', 'Excluded'),
    'flag_primary_analysis_exclusion_candidate': ('QC flag', 'Used to define cohort'),
}

# Build audit table
rows = []
for col in df.columns:
    s = df[col]
    n_miss = int(s.isna().sum())
    pct_miss = 100 * n_miss / N_TOTAL
    nunique = s.nunique(dropna=True)
    if pd.api.types.is_numeric_dtype(s):
        vtype = 'binary' if nunique <= 2 else ('continuous' if nunique > 10 else 'discrete-numeric')
        sample = f'min={s.min()}, max={s.max()}, median={s.median()}'
    else:
        vtype = 'categorical / string / date'
        # show top 5 levels
        top = s.value_counts(dropna=False).head(8)
        sample = '; '.join(f'{k}: {v} ({100*v/N_TOTAL:.1f}%)' for k,v in top.items())
    axis, status = AXIS_MAP.get(col, ('UNCLASSIFIED', 'NEEDS REVIEW'))
    rows.append({
        'column': col, 'dtype': str(s.dtype), 'vtype': vtype,
        'n_missing': n_miss, 'pct_missing': round(pct_miss, 1),
        'n_unique': nunique, 'sample_or_top_levels': sample,
        'clinical_axis': axis, 'proposed_status': status,
    })

audit = pd.DataFrame(rows)
audit.to_csv('/home/user/dialysis/analysis_outputs/00_audit.csv', index=False)

# --- Cross-checks ---
print('=' * 80)
print('CROSS-CHECK 1: variables in dataset vs clinician table')
print('=' * 80)
clin_table_vars = {
    'LeftVentricleCavitySize': 'LV Cavity Size',
    'LeftVentricleWallThickness': 'LV Wall Thickness',
    'LeftVentricleSystolicFunction': 'LV Systolic Function',
    'RVSize': 'RV Size',
    'AorticValveStructure': 'Aortic Valve Structure (CLINICIAN listed)',
    'AorticRegurgitation': 'Aortic Regurgitation (CLINICIAN listed)',
    'MitralRegurgitation': 'Mitral Regurgitation',
    'TricuspidRegurgitation': 'Tricuspid Regurgitation',
    'LACavitySize': 'LA Cavity Size',
    'RVSystolicFunction': 'RV Systolic Function',
    'ECHO_SPAP': 'ECHO SPAP',
}
for v, label in clin_table_vars.items():
    if v in df.columns:
        n_present = df[v].notna().sum()
        print(f'  ✓ {label:<55s}  found  (n_present={n_present})')
    else:
        print(f'  ✗ {label:<55s}  MISSING from dataset')

# --- Print top-level summary table ---
print()
print('=' * 80)
print('SUMMARY BY CLINICAL AXIS')
print('=' * 80)
summary = audit.groupby('clinical_axis').agg(
    n_columns=('column','count'),
    median_pct_missing=('pct_missing','median')
).round(1)
print(summary)

# --- Print full inventory grouped ---
print()
print('=' * 80)
print('FULL INVENTORY (grouped by axis)')
print('=' * 80)
for axis in audit.clinical_axis.unique():
    sub = audit[audit.clinical_axis == axis]
    print(f'\n--- {axis} ({len(sub)} columns) ---')
    for _, r in sub.iterrows():
        marker = '⚠' if r.pct_missing > 25 else ' '
        print(f"  {marker} {r.column:<50s}  miss={r.pct_missing:5.1f}%  unique={r.n_unique:>4d}  "
              f"[{r.proposed_status}]")

# --- Categorical level distributions for echo categoricals ---
print()
print('=' * 80)
print('CATEGORICAL LEVELS (raw, n=645) for echo categorical variables')
print('=' * 80)
echo_cats = ['LACavitySize','MitralRegurgitation','TricuspidRegurgitation','RVSize',
            'RVSystolicFunction','LeftVentricleSystolicFunction',
            'LeftVentricleCavitySize','LeftVentricleWallThickness','ECHO_SPAP']
for v in echo_cats:
    if v not in df.columns: continue
    print(f'\n--- {v} ---')
    vc = df[v].value_counts(dropna=False)
    for k, n in vc.items():
        pct = 100*n/N_TOTAL
        marker = ' ⚠ <5%' if pct < 5 and pd.notna(k) else ''
        print(f'    {str(k):<35s}  n={n:>4d}  ({pct:5.1f}%){marker}')

# --- Check if Aortic Valve Structure / AR exist under any other column name ---
print()
print('=' * 80)
print('SEARCH: any column with "aort" or "AR" in name?')
print('=' * 80)
hits = [c for c in df.columns if 'aort' in c.lower() or c.lower().startswith('ar') or '_ar_' in c.lower()]
if hits:
    for h in hits:
        print(f'  found: {h}')
else:
    print('  no columns matching "aort" / "AR" found in this dataset')
print('  ⇒ Aortic Valve Structure and Aortic Regurgitation are NOT in this dataset.')
print('  ⇒ The clinician table lists them but they were not included in the source CSV.')
print('  ⇒ Action: documented as a limitation; cannot be analyzed.')

# --- Save markdown report ---
with open('/home/user/dialysis/analysis_outputs/00_audit.md', 'w', encoding='utf-8') as f:
    f.write('# Stage 0 — Variable Audit Report\n\n')
    f.write(f'**Source**: stage2_analysis_ready.csv | n={N_TOTAL} rows | {len(df.columns)} columns\n\n')
    f.write('## Cross-check vs clinician table\n\n')
    f.write('| Clinician variable | In dataset? | n with value |\n|---|---|---|\n')
    for v, label in clin_table_vars.items():
        if v in df.columns:
            f.write(f'| {label} | ✓ | {df[v].notna().sum()} |\n')
        else:
            f.write(f'| {label} | ✗ MISSING | — |\n')
    f.write('\n## Full inventory (grouped by axis)\n\n')
    for axis in audit.clinical_axis.unique():
        sub = audit[audit.clinical_axis == axis]
        f.write(f'\n### {axis} (n={len(sub)})\n\n')
        f.write('| Column | dtype | type | %miss | unique | proposed status |\n|---|---|---|---|---|---|\n')
        for _, r in sub.iterrows():
            f.write(f'| `{r.column}` | {r.dtype} | {r.vtype} | {r.pct_missing}% | {r.n_unique} | {r.proposed_status} |\n')

print()
print('=' * 80)
print('OUTPUTS WRITTEN:')
print('  /home/user/dialysis/analysis_outputs/00_audit.csv')
print('  /home/user/dialysis/analysis_outputs/00_audit.md')
print('=' * 80)
print('Stage 0 audit complete. STOP-1 reached. Awaiting approval.')
