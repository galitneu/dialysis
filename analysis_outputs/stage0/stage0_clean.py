"""
Stage 0 - Apply data-cleaning decisions DEC-011..020 to raw and produce clean flat file + inventory.

INPUT: echo_project_update.xlsx (66 columns, 645 rows, raw)
OUTPUT:
  - 01_clean_flat.csv             (cleaned, one row per patient, NO clinical merging yet)
  - 02_variable_inventory.csv     (with axis + proposed status)
  - 02_inventory_report.md        (human readable)
  - 03_cleaning_provenance.md     (record of every transformation applied)

NO outcome models. NO clinical category merging (Stage 1).
NO cohort filtering by echo timing (Stage 2).
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd
from pathlib import Path

OUT = Path('/home/user/dialysis/analysis_outputs/stage0')
OUT.mkdir(parents=True, exist_ok=True)
RAW = '/home/user/dialysis/echo_project_update.xlsx'

# Load
raw = pd.read_excel(RAW, sheet_name=0)
N0 = len(raw)
print(f'RAW: shape={raw.shape}, columns={raw.shape[1]}')
df = raw.copy()
prov = []  # provenance log

def log(action, detail):
    prov.append({'step': len(prov)+1, 'action': action, 'detail': detail})
    print(f'  [{len(prov)}] {action}: {detail}')

# ============================================================
# DEC-011 — strip whitespace + collapse duplicates that differ only by spaces
# ============================================================
print('\n=== DEC-011: whitespace strip + collapse duplicates ===')
str_cols = df.select_dtypes(include=['object']).columns.tolist()
for c in str_cols:
    if df[c].isna().all(): continue
    before_levels = set(df[c].dropna().unique())
    df[c] = df[c].astype(str).str.strip()
    df.loc[df[c].isin(['nan','NaT','None','']), c] = np.nan
    after_levels = set(df[c].dropna().unique())
    removed = before_levels - after_levels
    if removed:
        log('whitespace_strip', f'{c}: removed {len(removed)} whitespace-variant levels: {sorted(removed)[:5]}')

# ============================================================
# DEC-012 — "No Value" string -> NaN  (echo categoricals)
# ============================================================
print('\n=== DEC-012: "No Value" -> NaN ===')
for c in str_cols:
    if c not in df.columns: continue
    n_nv = (df[c]=='No Value').sum() if pd.api.types.is_string_dtype(df[c]) else 0
    if n_nv > 0:
        df.loc[df[c]=='No Value', c] = np.nan
        log('no_value_to_nan', f'{c}: {n_nv} "No Value" -> NaN')

# ============================================================
# DEC-014 — "See below" -> NaN  (echo qualitative referrals)
# ============================================================
print('\n=== DEC-014: "See below" -> NaN ===')
for c in str_cols:
    if c not in df.columns: continue
    if pd.api.types.is_string_dtype(df[c]):
        mask = df[c].fillna('').str.lower().str.startswith('see below')
        n_sb = mask.sum()
        if n_sb > 0:
            df.loc[mask, c] = np.nan
            log('see_below_to_nan', f'{c}: {n_sb} "See below" -> NaN')

# ============================================================
# DEC-018 — "Preserved" -> "Normal"  (LV systolic function only)
# ============================================================
print('\n=== DEC-018: Preserved -> Normal in LV Systolic Function ===')
col = 'LeftVentricleSystolicFunction'
n_pres = (df[col]=='Preserved').sum()
if n_pres > 0:
    df.loc[df[col]=='Preserved', col] = 'Normal'
    log('preserved_to_normal', f'{col}: {n_pres} "Preserved" -> "Normal"')
else:
    log('preserved_to_normal', f'{col}: 0 "Preserved" found (already harmonized by whitespace strip if present as "Preserved ")')

# ============================================================
# DEC-019 — MR English -> Roman numeral mapping
# ============================================================
print('\n=== DEC-019: MR English -> Roman numerals ===')
mr_map = {
    'Trace':    'Trivial',
    'Mild':     'Mild (I)',
    'Moderate': 'Moderate (II)',
    'Severe':   'Severe (IV)',
}
for english, roman in mr_map.items():
    n = (df['MitralRegurgitation']==english).sum()
    if n > 0:
        df.loc[df['MitralRegurgitation']==english, 'MitralRegurgitation'] = roman
        log('mr_english_to_roman', f'MR: {n}× "{english}" -> "{roman}"')

# ============================================================
# DEC-013 — comorbidities: NaN = no condition; create binary
# Use original column notna() (works for both date and text storage).
# Then for date-stored columns, also coerce to datetime for reference.
# ============================================================
print('\n=== DEC-013: comorbidity NULL=no condition -> binary indicators ===')
COMORB_COLS = ['MI','CABG','IHD','AFIB','HTN','Diabetes mellitus',
               'DYSLIPIDEMIA','COPD','OncologicalDiagnosis']
for c in COMORB_COLS:
    if c not in df.columns: continue
    bin_col = f'{c}_binary'
    df[bin_col] = df[c].notna().astype(int)  # binary derived from "has any value"
    n_pos = df[bin_col].sum()
    log('comorb_null_to_binary', f'{c} -> {bin_col} (n_pos={n_pos}, {100*n_pos/N0:.1f}%)')
    # If stored as date, coerce for reference; else leave as-is
    parsed = pd.to_datetime(df[c], errors='coerce')
    if parsed.notna().sum() > 0:
        df[c] = parsed

# ============================================================
# DEC-020 — censor date 2025-08-16 (working)
# ============================================================
print('\n=== DEC-020: working censor date = 2025-08-16 ===')
WORKING_CENSOR = pd.Timestamp('2025-08-16')
log('working_censor_date', f'set to {WORKING_CENSOR.date()} (provisional, pending source confirmation)')

# Parse the three core dates
for c in ['DeathDate','Dialysis_Start_Date','Echo_Date']:
    df[c] = pd.to_datetime(df[c], errors='coerce')

# ============================================================
# DEC-016 — flag Echo_Date > DeathDate cases
# ============================================================
print('\n=== DEC-016: flag Echo_Date > DeathDate ===')
mask_invalid = df.DeathDate.notna() & df.Echo_Date.notna() & (df.Echo_Date > df.DeathDate)
n_invalid = int(mask_invalid.sum())
df['flag_echo_after_death'] = mask_invalid.astype(int)
if n_invalid > 0:
    log('echo_after_death_flag', f'{n_invalid} patient(s) with Echo_Date > DeathDate, flagged for exclusion')
    bad = df.loc[mask_invalid, ['patient number','Echo_Date','DeathDate']].copy()
    print(bad.to_string(index=False))

# ============================================================
# DERIVED time variables (using working censor)
# ============================================================
print('\n=== Derived time variables (using working censor) ===')
df['gap_echo_to_dial_days'] = (df.Dialysis_Start_Date - df.Echo_Date).dt.days  # +ve = echo BEFORE dialysis
df['death_event'] = df.DeathDate.notna().astype(int)
df['censor_or_event_date'] = df.DeathDate.where(df.death_event==1, WORKING_CENSOR)
df['time_to_event_days'] = (df.censor_or_event_date - df.Dialysis_Start_Date).dt.days
df['followup_days'] = (df.censor_or_event_date - df.Dialysis_Start_Date).dt.days
df['died_1year'] = ((df.death_event==1) & (df.time_to_event_days <= 365)).astype(int)
df.loc[(df.death_event==0) & (df.time_to_event_days < 365), 'died_1year'] = np.nan  # insufficient FU
log('derived_time_vars', 'gap_echo_to_dial_days, death_event, time_to_event_days, followup_days, died_1year')

# Hospitalization rename for consistency
if 'hospitalization-count' in df.columns:
    df['hosp_total'] = df['hospitalization-count']
    log('hosp_rename', '"hospitalization-count" mirrored to "hosp_total"')

# ============================================================
# WRITE clean flat file
# ============================================================
print('\n=== Writing clean flat file ===')
df.to_csv(OUT/'01_clean_flat.csv', index=False)
print(f'  shape: {df.shape}')
print(f'  saved: 01_clean_flat.csv')

# ============================================================
# VARIABLE INVENTORY with axis + proposed status
# ============================================================
print('\n=== Building variable inventory ===')

# Axis classification (extends Stage -1 mapping; NEW variables now visible)
AXIS_MAP = {
    # admin / id
    'patient number': ('Admin','Excluded'),
    'Dialysis_Start_Date': ('Admin','Excluded — date kept for derivations'),
    'Echo_Date': ('Admin','Excluded — date kept for derivations'),
    'DeathDate': ('Admin','Excluded — date kept for derivations'),
    'censor_or_event_date': ('Admin','Excluded — derived'),

    # outcomes
    'death_event': ('Outcome','Outcome — secondary (Cox)'),
    'time_to_event_days': ('Outcome','Outcome — secondary (Cox)'),
    'followup_days': ('Outcome','Outcome — denominator for hosp rate'),
    'died_1year': ('Outcome','Outcome — primary (1y mortality)'),
    'hosp_total': ('Outcome','Outcome — primary (hosp rate)'),
    'hospitalization-count': ('Outcome','Excluded — duplicate of hosp_total'),
    'flag_echo_after_death': ('Outcome QC','Used to define cohort exclusion'),

    # timing
    'gap_echo_to_dial_days': ('Timing','Core clinical (covariate)'),

    # demographics
    'AgeAtFirstHFDate': ('Clinical','Core clinical'),
    'm/f': ('Clinical','Core clinical'),
    'HD/PD': ('Clinical','Candidate covariate (full base)'),

    # comorbidities (dates)
    'MI': ('Clinical (date)','Excluded — date kept; binary used'),
    'CABG': ('Clinical (date)','Excluded — date kept; binary used'),
    'IHD': ('Clinical (date)','Excluded — date kept; binary used'),
    'AFIB': ('Clinical (date)','Excluded — date kept; binary used'),
    'HTN': ('Clinical (date)','Excluded — date kept; binary used'),
    'Diabetes mellitus': ('Clinical (date)','Excluded — date kept; binary used'),
    'DYSLIPIDEMIA': ('Clinical (date)','Excluded — date kept; binary used'),
    'COPD': ('Clinical (date)','Excluded — date kept; binary used'),
    'OncologicalDiagnosis': ('Clinical (date)','Excluded — date kept; binary used'),

    # comorbidities (binary)
    'MI_binary': ('Clinical','Candidate covariate (full base)'),
    'CABG_binary': ('Clinical','Candidate covariate (full base)'),
    'IHD_binary': ('Clinical','Candidate covariate (full base)'),
    'AFIB_binary': ('Clinical','Candidate covariate (full base)'),
    'HTN_binary': ('Clinical','Candidate covariate (full base)'),
    'Diabetes mellitus_binary': ('Clinical','Candidate covariate (full base)'),
    'DYSLIPIDEMIA_binary': ('Clinical','Descriptive only (held for Stage 4 per DEC-017)'),
    'COPD_binary': ('Clinical','Candidate covariate (full base)'),
    'OncologicalDiagnosis_binary': ('Clinical','Descriptive only (held for Stage 4 per DEC-017)'),

    # vitals
    'sbp-numeric result': ('Lab','Sensitivity (>20% missing)'),
    'dbp-numeric result': ('Lab','Sensitivity (>20% missing)'),
    'Weight': ('Clinical','Descriptive only (held for Stage 4 per DEC-017)'),
    'BMI': ('Clinical','Descriptive only (held for Stage 4 per DEC-017)'),

    # labs
    'GFR': ('Lab','Candidate covariate (alternative to creatinine)'),
    'creatinine-numeric result': ('Lab','Core clinical (parsimonious base)'),
    'albumin-numeric result': ('Lab','Candidate covariate (full base)'),
    'hb-numeric result': ('Lab','Candidate covariate (full base)'),
    'crp-numeric result': ('Lab','Candidate covariate (full base)'),
    'urea-numeric result': ('Lab','Sensitivity (held for Stage 4)'),
    'na-numeric result': ('Lab','Sensitivity (held for Stage 4)'),
    'k-numeric result': ('Lab','Sensitivity (held for Stage 4)'),
    'ca-numeric result': ('Lab','Sensitivity (held for Stage 4)'),
    'p-numeric result': ('Lab','Sensitivity (held for Stage 4)'),
    'ua-numeric result': ('Lab','Sensitivity (held for Stage 4)'),
    'hba1c-numeric result': ('Lab','Sensitivity (held for Stage 4)'),

    # echo benchmark
    'LV_EF': ('Echo: Benchmark','Benchmark — fixed in all models'),

    # echo LV systolic (other)
    'LeftVentricleSystolicFunction': ('Echo: LV systolic (other)','Candidate (categorical)'),
    'TissueDopplerSVelocitySeptal': ('Echo: LV systolic (other)','Sensitivity (>30% effective miss)'),
    'TissueDopplerSVelocityLateral': ('Echo: LV systolic (other)','Sensitivity (~20% miss)'),
    'LeftVentricleScoreIndex': ('Echo: LV systolic (other)','Sensitivity (overlap with EF)'),

    # echo LV diastolic / filling
    'MitralInflowPeakEWave': ('Echo: LV diastolic / filling','Candidate'),
    'TissueDopplerEVelositySeptal': ('Echo: LV diastolic / filling','Candidate (was previously OMITTED)'),
    'TissueDopplerEVelosityLateral': ('Echo: LV diastolic / filling','Candidate (was previously OMITTED)'),
    'TissueDopplerEERatioSeptal': ('Echo: LV diastolic / filling','Candidate'),
    'TissueDopplerEERatioLateral': ('Echo: LV diastolic / filling','Candidate'),

    # echo LV structure / mass
    'LeftVentricleEstimatedMass': ('Echo: LV structure / mass','Sensitivity (use LVMI instead)'),
    'LeftVentricleEstimatedMassIndex': ('Echo: LV structure / mass','Candidate (LVMI)'),
    'LeftVentricleInterventricularSeptumThickness': ('Echo: LV structure / mass','Sensitivity'),
    'LeftVentriclePosteriorWallThickness': ('Echo: LV structure / mass','Sensitivity'),
    'LeftVentricleEndDiastolicDiameter': ('Echo: LV structure / mass','Sensitivity'),
    'LeftVentricleEndSystolicDiameter': ('Echo: LV structure / mass','Sensitivity'),
    'LeftVentricleCavitySize': ('Echo: LV structure / mass','Sensitivity (categorical)'),
    'LeftVentricleWallThickness': ('Echo: LV structure / mass','Sensitivity (categorical)'),

    # echo LA / atrial
    'LACavitySize': ('Echo: LA / atrial','Candidate (categorical)'),

    # echo right-heart / congestion (TR moved here per DEC-004)
    'TricuspidRegurgitation': ('Echo: Right-heart / congestion','Candidate (categorical)'),
    'EstimatedSysPAPressure': ('Echo: Right-heart / congestion','Candidate (numeric SPAP)'),
    'ECHO_SPAP': ('Echo: Right-heart / congestion','Candidate (categorical)'),
    'RVSize': ('Echo: Right-heart / congestion','Candidate (categorical)'),
    'RVSystolicFunction': ('Echo: Right-heart / congestion','Candidate (categorical)'),

    # echo valves (other than TR which moved)
    'MitralRegurgitation': ('Echo: Valves','Candidate (categorical)'),
    'AorticValveRegurgitation': ('Echo: Valves','Candidate (categorical, was OMITTED from stage2)'),
    'AorticValveStructure': ('Echo: Valves','Sensitivity (categorical)'),
    'MitralValveStructure': ('Echo: Valves','Excluded (>60% effective miss after No Value→NaN)'),
    'TricuspidValveStructure': ('Echo: Valves','Excluded (>85% effective miss)'),

    # echo text (Hebrew)
    'LeftVentricleSummary': ('Echo: Text','Descriptive only — Hebrew free text'),
    'AorticValveSummary': ('Echo: Text','Descriptive only — Hebrew free text'),
    'MitralValveSummary': ('Echo: Text','Descriptive only — Hebrew free text'),
    'ProcedureSummary': ('Echo: Text','Descriptive only — Hebrew free text'),
}

inv_rows = []
for col in df.columns:
    s = df[col]
    n_miss = int(s.isna().sum())
    pct_miss = round(100*n_miss/len(df), 1)
    nu = s.nunique(dropna=True)
    if pd.api.types.is_numeric_dtype(s):
        vt = 'binary' if nu<=2 else ('continuous' if nu>10 else 'discrete')
        if nu > 0:
            sample = f'min={s.min()}, max={s.max()}, median={s.median()}'
        else: sample = 'all NaN'
    elif pd.api.types.is_datetime64_any_dtype(s):
        vt = 'date'
        sample = f'min={s.min()}, max={s.max()}'
    else:
        vt = 'categorical'
        top = s.value_counts(dropna=False).head(8)
        sample = '; '.join(f'{k}: {v} ({100*v/len(df):.1f}%)' for k,v in top.items())
    axis, status = AXIS_MAP.get(col, ('UNCLASSIFIED','NEEDS REVIEW'))
    # missingness threshold check
    if pct_miss > 60 and 'Excluded' not in status and 'Outcome' not in axis and 'Admin' not in axis and 'date' not in vt and 'Text' not in axis:
        status = status + ' [⚠️ effective miss > 60%]'
    inv_rows.append({
        'column': col, 'dtype': str(s.dtype), 'vtype': vt,
        'n_missing': n_miss, 'pct_missing': pct_miss,
        'n_unique': nu, 'clinical_axis': axis,
        'proposed_status': status, 'sample_or_top_levels': sample,
    })
inv = pd.DataFrame(inv_rows)
inv.to_csv(OUT/'02_variable_inventory.csv', index=False)

# Print inventory grouped by axis
print('\n' + '='*80)
print('VARIABLE INVENTORY — grouped by clinical axis')
print('='*80)
for axis, grp in inv.groupby('clinical_axis', sort=False):
    print(f'\n--- {axis} ({len(grp)} columns) ---')
    for _, r in grp.iterrows():
        marker = '⚠' if r.pct_missing > 25 else ' '
        print(f'  {marker} {r.column:<48s}  miss={r.pct_missing:>5.1f}%  unique={r.n_unique:>4d}  [{r.proposed_status}]')

# ============================================================
# Save provenance
# ============================================================
print('\n' + '='*80)
print('CLEANING PROVENANCE')
print('='*80)
with open(OUT/'03_cleaning_provenance.md', 'w', encoding='utf-8') as f:
    f.write('# Stage 0 — Cleaning Provenance\n\n')
    f.write('Every transformation applied to the raw file `echo_project_update.xlsx` '
            'in producing `01_clean_flat.csv`. Each step references the decision-log entry that authorized it.\n\n')
    f.write('| # | Decision | Action | Detail |\n|---|---|---|---|\n')
    dec_map = {
        'whitespace_strip': 'DEC-011',
        'no_value_to_nan': 'DEC-012',
        'see_below_to_nan': 'DEC-014',
        'preserved_to_normal': 'DEC-018',
        'mr_english_to_roman': 'DEC-019',
        'comorb_date_to_binary': 'DEC-013',
        'working_censor_date': 'DEC-020',
        'echo_after_death_flag': 'DEC-016',
        'derived_time_vars': '(derived from DEC-020)',
        'hosp_rename': '(naming consistency)',
    }
    for p in prov:
        dec = dec_map.get(p['action'], '—')
        f.write(f"| {p['step']} | {dec} | {p['action']} | {p['detail']} |\n")

# Save inventory report markdown
with open(OUT/'02_inventory_report.md', 'w', encoding='utf-8') as f:
    f.write('# Stage 0 — Variable Inventory\n\n')
    f.write(f'Source: `01_clean_flat.csv` (n={len(df)} patients, {df.shape[1]} columns)\n\n')
    f.write('Cleaning applied per DEC-011..020 (see `03_cleaning_provenance.md`).\n\n')
    f.write('Status legend:\n')
    f.write('- **Core clinical**: pre-specified by clinicians, in every model\n')
    f.write('- **Benchmark**: LV_EF, fixed in all models\n')
    f.write('- **Candidate**: fits a clinical axis and may be selected at Stage 4\n')
    f.write('- **Sensitivity**: relevant but missingness/overlap concerns\n')
    f.write('- **Descriptive only**: reported but not modeled\n')
    f.write('- **Excluded**: not used (date columns kept for derivations, free text, redundant, very high missing)\n\n')
    for axis, grp in inv.groupby('clinical_axis', sort=False):
        f.write(f'\n## {axis} ({len(grp)})\n\n')
        f.write('| Column | dtype | type | %miss | unique | Status |\n|---|---|---|---|---|---|\n')
        for _, r in grp.iterrows():
            f.write(f'| `{r.column}` | {r.dtype} | {r.vtype} | {r.pct_missing}% | {r.n_unique} | {r.proposed_status} |\n')

print('\nFiles produced:')
for p in sorted(OUT.glob('*')):
    print(f'  {p.name}  ({p.stat().st_size//1024} KB)')
print(f'\nClean flat file: n={len(df)} rows, {df.shape[1]} columns')
print(f'  - patients: {df["patient number"].nunique()}')
print(f'  - flag_echo_after_death=1: {int(df.flag_echo_after_death.sum())} (will be excluded at cohort definition)')
print(f'  - died_1year=NaN (insufficient FU): {int(df.died_1year.isna().sum())}')
print(f'  - died_1year=1: {int((df.died_1year==1).sum())}')
print(f'  - death_event=1 (any time): {int(df.death_event.sum())}')
print('\nStage 0 complete. STOP-2 reached. No clinical category merging or modeling performed.')
