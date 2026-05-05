# ============================================================
# 1. Setup
# ============================================================
from pathlib import Path
import json
from datetime import datetime
import numpy as np
import pandas as pd

pd.set_option('display.max_columns', 200)
pd.set_option('display.width', 200)

# Colab-friendly paths. Put input files in the same folder as this notebook,
# or edit BASE_DIR to your Google Drive project folder.
BASE_DIR = Path('.')
OUT_DIR = Path('analysis_outputs/stage1')
OUT_DIR.mkdir(parents=True, exist_ok=True)

INPUT_DATA = BASE_DIR / 'stage0_updated_clean_flat.csv'
DECISION_LOG_FILE = BASE_DIR / 'stage0_decision_log_FINAL_DEC038_DEC043.csv'
CATEGORY_MAPPING_FILE = BASE_DIR / 'stage1_clinician_category_mapping_DEC037.csv'

# Optional Stage 0 final variable-list files. The notebook will run even if these are absent,
# but the exports are best when they are available.
MAIN_LIST_CANDIDATES = [
    BASE_DIR / 'stage0_stage1_eligible_main_FINAL.csv',
    BASE_DIR / 'stage0_final_after_review/stage0_stage1_eligible_main_FINAL.csv',
    BASE_DIR / 'stage0_updated_stage1_eligible_main.csv',
    BASE_DIR / 'inventory_main.csv',
]
SENS_LIST_CANDIDATES = [
    BASE_DIR / 'stage0_sensitivity_exploratory_FINAL.csv',
    BASE_DIR / 'stage0_final_after_review/stage0_sensitivity_exploratory_FINAL.csv',
    BASE_DIR / 'stage0_updated_sensitivity_exploratory.csv',
    BASE_DIR / 'inventory_sensitivity.csv',
]
EXCL_LIST_CANDIDATES = [
    BASE_DIR / 'stage0_descriptive_excluded_FINAL.csv',
    BASE_DIR / 'stage0_final_after_review/stage0_descriptive_excluded_FINAL.csv',
    BASE_DIR / 'stage0_updated_descriptive_excluded.csv',
    BASE_DIR / 'inventory_excluded.csv',
]
QA_FILE_CANDIDATES = [
    BASE_DIR / 'stage0_updated_QA_flags.csv',
    BASE_DIR / '04_qa_outliers.csv',
]

REQUIRED_INPUTS = [INPUT_DATA]
missing_required = [str(p) for p in REQUIRED_INPUTS if not p.exists()]
if missing_required:
    raise FileNotFoundError(
        'Missing required input file(s): ' + ', '.join(missing_required) +
        '\nUpload stage0_updated_clean_flat.csv to the notebook folder or update BASE_DIR.'
    )

run_metadata = {
    'run_datetime': datetime.now().isoformat(timespec='seconds'),
    'input_data': str(INPUT_DATA),
    'output_dir': str(OUT_DIR),
    'notebook': 'stage1_prepare_analytic_datasets.ipynb',
    'decision_scope': 'DEC-038 through DEC-043 plus prior Stage 0 decisions',
}

print('Output directory:', OUT_DIR)

# ============================================================
# 2. Load inputs and validate source dataset
# ============================================================
df_raw = pd.read_csv(INPUT_DATA)
df = df_raw.copy()

print('Input shape:', df.shape)
assert 'patient_id' in df.columns, 'patient_id column is required.'
assert df['patient_id'].is_unique, 'patient_id must be unique.'
assert len(df) == 645, f'Expected 645 rows before exclusions; found {len(df)}.'

# Helper: load optional variable list files.
def first_existing(paths):
    for p in paths:
        if p.exists():
            return p
    return None

def load_var_list(paths, label):
    p = first_existing(paths)
    if p is None:
        print(f'Optional {label} variable list not found; continuing with empty list.')
        return pd.DataFrame(), []
    tmp = pd.read_csv(p)
    if 'column' in tmp.columns:
        cols = tmp['column'].dropna().astype(str).tolist()
    elif 'variable' in tmp.columns:
        cols = tmp['variable'].dropna().astype(str).tolist()
    else:
        cols = tmp.iloc[:,0].dropna().astype(str).tolist()
    print(f'Loaded {label}: {p.name} ({len(cols)} variables)')
    return tmp, cols

main_list_df, main_vars_stage0 = load_var_list(MAIN_LIST_CANDIDATES, 'main')
sens_list_df, sens_vars_stage0 = load_var_list(SENS_LIST_CANDIDATES, 'sensitivity/exploratory')
excl_list_df, excl_vars_stage0 = load_var_list(EXCL_LIST_CANDIDATES, 'descriptive/excluded')

# Decision log and mapping are strongly recommended but not required for basic validation.
decision_log = pd.read_csv(DECISION_LOG_FILE) if DECISION_LOG_FILE.exists() else pd.DataFrame()
cat_map = pd.read_csv(CATEGORY_MAPPING_FILE) if CATEGORY_MAPPING_FILE.exists() else pd.DataFrame()

validation_rows = []
for item, ok, detail in [
    ('n_rows_645', len(df) == 645, len(df)),
    ('patient_id_present', 'patient_id' in df.columns, 'patient_id' in df.columns),
    ('patient_id_unique', df['patient_id'].is_unique, df['patient_id'].duplicated().sum()),
    ('decision_log_loaded', not decision_log.empty, DECISION_LOG_FILE.name if DECISION_LOG_FILE.exists() else 'missing'),
    ('category_mapping_loaded', not cat_map.empty, CATEGORY_MAPPING_FILE.name if CATEGORY_MAPPING_FILE.exists() else 'missing'),
]:
    validation_rows.append({'check': item, 'passed': bool(ok), 'detail': detail})

validation = pd.DataFrame(validation_rows)
validation.to_csv(OUT_DIR / 'stage1_input_validation.csv', index=False)
validation

# ============================================================
# 3. Standard helpers: dates, effective missingness, numeric coercion
# ============================================================
ECHO_MISSING_TOKENS = {
    '', ' ', 'nan', 'NaN', 'None', 'NO VALUE', 'No Value', 'no value',
    'SEE BELOW', 'See below', 'see below', 'N/A', 'NA', 'Not available',
    'Not Available', 'not available', 'Not well seen', 'not well seen'
}

def clean_string_cell(x):
    if pd.isna(x):
        return np.nan
    if isinstance(x, str):
        y = x.strip()
        return np.nan if y in ECHO_MISSING_TOKENS else y
    return x

def effective_missing_mask(series):
    return series.isna() | series.astype(str).str.strip().isin(ECHO_MISSING_TOKENS)

def to_numeric(series):
    return pd.to_numeric(series, errors='coerce')

def parse_date(series):
    return pd.to_datetime(series, errors='coerce')

# Parse key dates.
for col in ['Dialysis_Start_Date', 'Echo_Date', 'DeathDate', 'data_cutoff_date', 'censor_or_event_date']:
    if col in df.columns:
        df[col + '_dt'] = parse_date(df[col])

# Numeric fields frequently needed downstream.
for col in ['time_to_event_days', 'followup_days', 'days_echo_to_dialysis', 'hosp_total', 'hospitalization-count', 'died_1year', 'event', 'event_1y']:
    if col in df.columns:
        df[col] = to_numeric(df[col])

# ============================================================
# 4. DEC-038: Comorbidity missingness means disease absence for binary covariates
# ============================================================
COMORBIDITY_DATE_COLS = [
    'MI', 'CABG', 'IHD', 'AFIB', 'HTN', 'Diabetes mellitus',
    'DYSLIPIDEMIA', 'COPD', 'OncologicalDiagnosis'
]

comorbidity_check_rows = []
for base in COMORBIDITY_DATE_COLS:
    bin_col = f'{base}_binary'
    if base in df.columns:
        expected = (~df[base].isna()).astype(int)
        if bin_col not in df.columns:
            df[bin_col] = expected
            action = 'created_from_nonmissing_source'
        else:
            # Keep existing variable but verify it is consistent enough to audit.
            existing = to_numeric(df[bin_col]).fillna(0).astype(int)
            mismatch = int((existing != expected).sum())
            action = 'verified_existing_binary'
            df[bin_col] = existing
        comorbidity_check_rows.append({
            'source_column': base,
            'binary_column': bin_col,
            'source_present': True,
            'binary_present_after_processing': bin_col in df.columns,
            'n_positive_binary': int(df[bin_col].sum()) if bin_col in df.columns else np.nan,
            'n_missing_source_interpreted_as_absence': int(df[base].isna().sum()),
            'action': action,
            'note': 'DEC-038: missing comorbidity documentation interpreted as absence for binary covariates.'
        })
    elif bin_col in df.columns:
        df[bin_col] = to_numeric(df[bin_col]).fillna(0).astype(int)
        comorbidity_check_rows.append({
            'source_column': base,
            'binary_column': bin_col,
            'source_present': False,
            'binary_present_after_processing': True,
            'n_positive_binary': int(df[bin_col].sum()),
            'n_missing_source_interpreted_as_absence': np.nan,
            'action': 'binary_available_no_source_column',
            'note': 'Binary variable retained; source column not available.'
        })

comorbidity_check = pd.DataFrame(comorbidity_check_rows)
comorbidity_check.to_csv(OUT_DIR / 'stage1_comorbidity_binary_check.csv', index=False)
comorbidity_check

# ============================================================
# 5. DEC-039: Echo effective missingness report
# ============================================================
ECHO_CATEGORICAL_COLS = [
    'LeftVentricleCavitySize', 'LeftVentricleWallThickness', 'LeftVentricleSystolicFunction',
    'RVSize', 'RVSystolicFunction', 'LACavitySize', 'AorticValveStructure',
    'AorticValveRegurgitation', 'MitralValveStructure', 'MitralRegurgitation',
    'TricuspidValveStructure', 'TricuspidRegurgitation', 'ECHO_SPAP'
]
ECHO_NUMERIC_COLS = [
    'LV_EF', 'LeftVentricleEndDiastolicDiameter', 'LeftVentricleEndSystolicDiameter',
    'LeftVentricleInterventricularSeptumThickness', 'LeftVentriclePosteriorWallThickness',
    'LeftVentricleEstimatedMass', 'LeftVentricleEstimatedMassIndex', 'LeftVentricleScoreIndex',
    'EstimatedSysPAPressure', 'MitralInflowPeakEWave',
    'TissueDopplerSVelocitySeptal', 'TissueDopplerEVelositySeptal', 'TissueDopplerEERatioSeptal',
    'TissueDopplerSVelocityLateral', 'TissueDopplerEVelosityLateral', 'TissueDopplerEERatioLateral'
]

# Clean only analysis-ready copies of categorical echo columns; original columns are retained in df_raw.
for col in ECHO_CATEGORICAL_COLS:
    if col in df.columns:
        df[col] = df[col].apply(clean_string_cell)

for col in ECHO_NUMERIC_COLS:
    if col in df.columns:
        df[col] = to_numeric(df[col])

echo_missing_rows = []
for col in [c for c in ECHO_CATEGORICAL_COLS + ECHO_NUMERIC_COLS if c in df.columns]:
    eff_mask_raw = effective_missing_mask(df_raw[col]) if col in df_raw.columns else df[col].isna()
    echo_missing_rows.append({
        'variable': col,
        'n': len(df),
        'n_missing_standard_after_processing': int(df[col].isna().sum()),
        'pct_missing_standard_after_processing': round(float(df[col].isna().mean()*100), 2),
        'n_effective_missing_from_raw': int(eff_mask_raw.sum()),
        'pct_effective_missing_from_raw': round(float(eff_mask_raw.mean()*100), 2),
        'decision': 'DEC-039: unusable echo values treated as missing, not normal.'
    })

echo_eff_missing = pd.DataFrame(echo_missing_rows)
echo_eff_missing.to_csv(OUT_DIR / 'stage1_echo_effective_missingness.csv', index=False)
echo_eff_missing.head(20)

# ============================================================
# 6. DEC-040: Exclusion flags for same-day echo/death or echo after death
# ============================================================
if {'Echo_Date_dt', 'DeathDate_dt'}.issubset(df.columns):
    echo_date = df['Echo_Date_dt']
    death_date = df['DeathDate_dt']
    df['flag_echo_after_death_stage1'] = ((~echo_date.isna()) & (~death_date.isna()) & (echo_date.dt.date > death_date.dt.date)).astype(int)
    df['flag_echo_same_day_as_death_stage1'] = ((~echo_date.isna()) & (~death_date.isna()) & (echo_date.dt.date == death_date.dt.date)).astype(int)
else:
    df['flag_echo_after_death_stage1'] = 0
    df['flag_echo_same_day_as_death_stage1'] = 0

df['exclude_same_day_or_after_death_stage1'] = ((df['flag_echo_after_death_stage1'] == 1) | (df['flag_echo_same_day_as_death_stage1'] == 1)).astype(int)

exclusion_rows = []
for _, row in df.loc[df['exclude_same_day_or_after_death_stage1'] == 1].iterrows():
    reason = 'echo_after_death' if row['flag_echo_after_death_stage1'] == 1 else 'echo_same_calendar_date_as_death'
    exclusion_rows.append({
        'patient_id': row['patient_id'],
        'exclusion_reason': reason,
        'stage': 'Stage 1',
        'applies_to_analysis': 'main, one-year mortality, survival, hospitalization',
        'excluded_from_main': True,
        'excluded_from_oneyear_mortality': True,
        'excluded_from_survival': True,
        'excluded_from_hospitalization': True,
        'Echo_Date': row.get('Echo_Date'),
        'DeathDate': row.get('DeathDate'),
        'decision': 'DEC-040'
    })

exclusions_log = pd.DataFrame(exclusion_rows)
if exclusions_log.empty:
    exclusions_log = pd.DataFrame(columns=['patient_id','exclusion_reason','stage','applies_to_analysis','excluded_from_main','excluded_from_oneyear_mortality','excluded_from_survival','excluded_from_hospitalization','Echo_Date','DeathDate','decision'])
exclusions_log.to_csv(OUT_DIR / 'stage1_exclusions_log.csv', index=False)

exclusions_summary = pd.DataFrame({
    'metric': ['n_echo_after_death', 'n_echo_same_day_as_death', 'n_excluded_same_day_or_after_death'],
    'n': [
        int(df['flag_echo_after_death_stage1'].sum()),
        int(df['flag_echo_same_day_as_death_stage1'].sum()),
        int(df['exclude_same_day_or_after_death_stage1'].sum())
    ],
})
exclusions_summary['pct_of_645'] = round(exclusions_summary['n'] / len(df) * 100, 2)
exclusions_summary.to_csv(OUT_DIR / 'stage1_exclusions_summary.csv', index=False)
exclusions_summary

# ============================================================
# 7. DEC-041: Echo-to-dialysis timing distribution
# ============================================================
if 'days_echo_to_dialysis' not in df.columns and 'gap_echo_to_dial_days' in df.columns:
    df['days_echo_to_dialysis'] = to_numeric(df['gap_echo_to_dial_days']) * -1  # only if needed; verify externally

if 'days_echo_to_dialysis' in df.columns:
    df['days_echo_to_dialysis'] = to_numeric(df['days_echo_to_dialysis'])
    d = df['days_echo_to_dialysis']
    timing_summary = pd.DataFrame([{
        'n_nonmissing': int(d.notna().sum()),
        'mean_days': d.mean(),
        'median_days': d.median(),
        'sd_days': d.std(),
        'min_days': d.min(),
        'q25_days': d.quantile(0.25),
        'q75_days': d.quantile(0.75),
        'max_days': d.max(),
        'n_after_dialysis': int((d > 0).sum()),
        'n_same_day': int((d == 0).sum()),
        'n_before_dialysis': int((d < 0).sum()),
        'decision': 'DEC-041: no maximum gap cutoff at Stage 1; summarize and present distribution.'
    }])

    bins = [-np.inf, -365, -180, -90, -30, -1, 0, np.inf]
    labels = ['before_gt_365d', 'before_181_365d', 'before_91_180d', 'before_31_90d', 'before_0_30d', 'same_day', 'after_dialysis']
    df['echo_to_dialysis_timing_category'] = pd.cut(d, bins=bins, labels=labels, include_lowest=True, right=True)
    # pd.cut assigns 0 to same_day because bin [-1,0]; relabel exact zero to same_day, positive to after.
    df.loc[d == 0, 'echo_to_dialysis_timing_category'] = 'same_day'
    df.loc[d > 0, 'echo_to_dialysis_timing_category'] = 'after_dialysis'

    timing_categories = (df['echo_to_dialysis_timing_category']
                         .value_counts(dropna=False)
                         .rename_axis('timing_category')
                         .reset_index(name='n'))
    timing_categories['pct'] = round(timing_categories['n'] / len(df) * 100, 2)

    extreme_gaps = df.loc[d.abs() > 365, ['patient_id','Echo_Date','Dialysis_Start_Date','days_echo_to_dialysis','echo_to_dialysis_timing_category']].copy()
else:
    timing_summary = pd.DataFrame()
    timing_categories = pd.DataFrame()
    extreme_gaps = pd.DataFrame()

timing_summary.to_csv(OUT_DIR / 'stage1_echo_to_dialysis_timing_summary.csv', index=False)
timing_categories.to_csv(OUT_DIR / 'stage1_echo_to_dialysis_timing_categories.csv', index=False)
extreme_gaps.to_csv(OUT_DIR / 'stage1_echo_to_dialysis_extreme_gaps.csv', index=False)

timing_summary

# ============================================================
# 8. DEC-030: Continuous outlier handling for Stage 1 datasets
# ============================================================
# Conservative clinical plausibility thresholds. These are action rules for analytic copies, not deletion rules.
OUTLIER_RULES = {
    'BMI': {'low': 12, 'high': 70},
    'Weight': {'low': 30, 'high': 250},
    'LeftVentricleInterventricularSeptumThickness': {'low': 0.4, 'high': 2.5},
    'LeftVentriclePosteriorWallThickness': {'low': 0.4, 'high': 2.0},
    'LeftVentricleEstimatedMass': {'low': 30, 'high': 600},
    'LeftVentricleEstimatedMassIndex': {'low': 20, 'high': 300},
}

outlier_action_rows = []
for col, rule in OUTLIER_RULES.items():
    if col not in df.columns:
        continue
    df[col] = to_numeric(df[col])
    low, high = rule.get('low'), rule.get('high')
    mask = pd.Series(False, index=df.index)
    if low is not None:
        mask |= df[col] < low
    if high is not None:
        mask |= df[col] > high
    for idx, row in df.loc[mask, ['patient_id', col]].iterrows():
        outlier_action_rows.append({
            'patient_id': row['patient_id'],
            'variable': col,
            'original_value': row[col],
            'action': 'set_to_missing_in_stage1_analytic_copy',
            'corrected_value': np.nan,
            'reason': f'Implausible continuous value outside [{low}, {high}] and no approved unit-conversion rule.',
            'requires_clinical_review': True,
            'decision': 'DEC-030'
        })
    df.loc[mask, col] = np.nan

outlier_action_log = pd.DataFrame(outlier_action_rows)
if outlier_action_log.empty:
    outlier_action_log = pd.DataFrame(columns=['patient_id','variable','original_value','action','corrected_value','reason','requires_clinical_review','decision'])
outlier_action_log.to_csv(OUT_DIR / 'stage1_outlier_action_log.csv', index=False)
outlier_action_log.head(30)

# ============================================================
# 9. DEC-037 / DEC-043: Clinician-approved category harmonization
# ============================================================
category_counts_before_after_rows = []
variable_processing_rows = []

if not cat_map.empty:
    required_map_cols = {'original_variable','grouped_variable','original_category','grouped_category'}
    missing_cols = required_map_cols - set(cat_map.columns)
    if missing_cols:
        raise ValueError(f'Category mapping file missing required columns: {missing_cols}')

    for orig_var, sub in cat_map.groupby('original_variable'):
        if orig_var not in df.columns:
            variable_processing_rows.append({
                'variable': orig_var,
                'new_variable': None,
                'action': 'mapping_not_applied_variable_missing',
                'decision': 'DEC-037/DEC-043',
                'note': 'Original variable not found in dataset.'
            })
            continue
        grouped_var = sub['grouped_variable'].iloc[0]
        mapping = dict(zip(sub['original_category'].astype(str), sub['grouped_category'].astype(str)))

        before_counts = df[orig_var].value_counts(dropna=False).reset_index()
        before_counts.columns = ['category', 'n_before']
        before_counts['variable'] = orig_var

        # Apply mapping to string-stripped categories. Unmapped nonmissing categories are retained as-is and flagged.
        source = df[orig_var].apply(clean_string_cell)
        df[grouped_var] = source.map(lambda x: np.nan if pd.isna(x) else mapping.get(str(x), str(x)))

        after_counts = df[grouped_var].value_counts(dropna=False).reset_index()
        after_counts.columns = ['category', 'n_after']
        after_counts['variable'] = grouped_var

        # Long-form before/after counts.
        for _, r in before_counts.iterrows():
            category_counts_before_after_rows.append({
                'original_variable': orig_var,
                'grouped_variable': grouped_var,
                'stage': 'before',
                'category': r['category'],
                'n': int(r['n_before'])
            })
        for _, r in after_counts.iterrows():
            category_counts_before_after_rows.append({
                'original_variable': orig_var,
                'grouped_variable': grouped_var,
                'stage': 'after',
                'category': r['category'],
                'n': int(r['n_after'])
            })

        unmapped = sorted(set(source.dropna().astype(str).unique()) - set(mapping.keys()))
        variable_processing_rows.append({
            'variable': orig_var,
            'new_variable': grouped_var,
            'action': 'clinician_category_mapping_applied',
            'decision': 'DEC-037/DEC-043',
            'note': f'Unmapped categories retained as original labels: {unmapped}' if unmapped else 'All observed mapped categories were covered.'
        })

cat_counts = pd.DataFrame(category_counts_before_after_rows)
processing_log = pd.DataFrame(variable_processing_rows)

cat_map.to_csv(OUT_DIR / 'stage1_clinician_category_mapping_applied.csv', index=False)
cat_counts.to_csv(OUT_DIR / 'stage1_categorical_counts_before_after.csv', index=False)
processing_log.to_csv(OUT_DIR / 'stage1_variable_processing_log.csv', index=False)

processing_log.head(20)

# ============================================================
# 10. DEC-042: Retain free-text echo summaries, but do not model them now
# ============================================================
TEXT_COLS = [
    'LeftVentricleSummary', 'AorticValveSummary', 'MitralValveSummary', 'ProcedureSummary'
]
text_retention = []
for col in TEXT_COLS:
    if col in df.columns:
        text_retention.append({
            'variable': col,
            'n_nonmissing': int(df[col].notna().sum()),
            'n_unique_nonmissing': int(df[col].nunique(dropna=True)),
            'stage1_role': 'retained_for_future_text_or_NLP_review_not_modeled',
            'decision': 'DEC-042'
        })
text_retention = pd.DataFrame(text_retention)
text_retention.to_csv(OUT_DIR / 'stage1_text_fields_retention_log.csv', index=False)
text_retention

# ============================================================
# 11. Build predictor lists for Stage 1 exports
# ============================================================
OUTCOME_ADMIN_FOLLOWUP = {
    'DeathDate','Dialysis_Start_Date','Echo_Date','data_cutoff_date','censor_or_event_date',
    'event','event_1y','death_event','died_1year','time_to_event_days','time_to_event_years',
    'followup_days','followup_years','log_followup_years','hosp_total','hospitalization-count',
    'flag_echo_after_death','flag_echo_after_death_stage1','flag_echo_same_day_as_death_stage1',
    'exclude_same_day_or_after_death_stage1'
}
DATE_DT_COLS = {c for c in df.columns if c.endswith('_dt')}
TEXT_COL_SET = set(TEXT_COLS)
TIMING_DUPLICATES = {'months_echo_to_dialysis', 'months_dialysis_to_echo', 'gap_echo_to_dial_days'}
ALLOWED_TIMING = {'days_echo_to_dialysis', 'echo_to_dialysis_timing_category'}

# Original -> grouped variable map.
orig_to_grouped = {}
if not cat_map.empty:
    for orig_var, sub in cat_map.groupby('original_variable'):
        if orig_var in df.columns:
            orig_to_grouped[orig_var] = sub['grouped_variable'].iloc[0]

def convert_to_stage1_predictors(vars_in, label):
    out = []
    exclusions = []
    for v in vars_in:
        if v not in df.columns and v not in orig_to_grouped:
            exclusions.append({'source_list': label, 'variable': v, 'reason': 'not_found_in_dataset'})
            continue
        # Replace original categorical variable with clinician-grouped version when available.
        v2 = orig_to_grouped.get(v, v)
        if v2 in OUTCOME_ADMIN_FOLLOWUP or v2 in DATE_DT_COLS or v2 in TEXT_COL_SET or v2 in TIMING_DUPLICATES:
            exclusions.append({'source_list': label, 'variable': v, 'stage1_variable': v2, 'reason': 'not_predictor_or_duplicate'})
            continue
        if v2 not in df.columns:
            exclusions.append({'source_list': label, 'variable': v, 'stage1_variable': v2, 'reason': 'mapped_variable_missing'})
            continue
        if v2 not in out:
            out.append(v2)
    return out, pd.DataFrame(exclusions)

# Fallback main list if Stage 0 list is missing.
if not main_vars_stage0:
    # Minimal conservative fallback: core clinical + selected echo variables.
    main_vars_stage0 = [
        'm/f','AgeAtFirstHFDate','creatinine-numeric result','albumin-numeric result','hb-numeric result',
        'HD/PD','MI_binary','CABG_binary','IHD_binary','AFIB_binary','HTN_binary','Diabetes mellitus_binary','COPD_binary',
        'days_echo_to_dialysis','LV_EF','LeftVentricleSystolicFunction','LACavitySize','TricuspidRegurgitation',
        'MitralRegurgitation','EstimatedSysPAPressure','LeftVentricleEstimatedMassIndex','MitralInflowPeakEWave','TissueDopplerEERatioSeptal'
    ]

main_predictors, main_excl = convert_to_stage1_predictors(main_vars_stage0, 'main')
sens_predictors, sens_excl = convert_to_stage1_predictors(sens_vars_stage0, 'sensitivity_exploratory')

# Enforce DEC-034: do not include GFR and creatinine together in main; keep creatinine in main if both are present.
if 'GFR' in main_predictors and 'creatinine-numeric result' in main_predictors:
    main_predictors.remove('GFR')
    if 'GFR' not in sens_predictors and 'GFR' in df.columns:
        sens_predictors.append('GFR')

predictor_exclusions = pd.concat([main_excl, sens_excl], ignore_index=True) if not main_excl.empty or not sens_excl.empty else pd.DataFrame(columns=['source_list','variable','stage1_variable','reason'])
predictor_exclusions.to_csv(OUT_DIR / 'stage1_predictor_list_exclusions.csv', index=False)

pd.DataFrame({'stage1_main_predictor': main_predictors}).to_csv(OUT_DIR / 'stage1_main_predictor_list.csv', index=False)
pd.DataFrame({'stage1_sensitivity_exploratory_predictor': sens_predictors}).to_csv(OUT_DIR / 'stage1_sensitivity_exploratory_predictor_list.csv', index=False)

print('Main predictors:', len(main_predictors))
print(main_predictors)
print('Sensitivity/exploratory predictors:', len(sens_predictors))

# ============================================================
# 12. Create outcome-specific analytic cohorts
# ============================================================
analysis_base = df.loc[df['exclude_same_day_or_after_death_stage1'] == 0].copy()

# One-year mortality cohort: defined died_1year only.
one_year = analysis_base.loc[analysis_base['died_1year'].notna()].copy() if 'died_1year' in analysis_base.columns else pd.DataFrame()

# Survival cohort: event and valid nonnegative time.
survival = analysis_base.copy()
if 'event' in survival.columns and 'time_to_event_days' in survival.columns:
    survival = survival.loc[survival['event'].notna() & survival['time_to_event_days'].notna() & (survival['time_to_event_days'] >= 0)].copy()
else:
    survival = pd.DataFrame()

# Hospitalization cohort: hosp_total and positive follow-up.
hosp = analysis_base.copy()
if 'hosp_total' in hosp.columns and 'followup_days' in hosp.columns:
    hosp = hosp.loc[hosp['hosp_total'].notna() & hosp['followup_days'].notna() & (hosp['followup_days'] > 0)].copy()
    hosp['followup_years'] = hosp['followup_days'] / 365.25
    hosp['log_followup_years'] = np.log(hosp['followup_years'])
else:
    hosp = pd.DataFrame()

# Helper to select available columns in desired order.
def select_cols(data, cols):
    seen = []
    for c in cols:
        if c in data.columns and c not in seen:
            seen.append(c)
    return data[seen].copy()

ID_COLS = ['patient_id']
COMMON_FLAGS = ['days_echo_to_dialysis','echo_to_dialysis_timing_category','exclude_same_day_or_after_death_stage1']
ONE_YEAR_OUTCOME = ['died_1year']
SURVIVAL_OUTCOME = ['event','time_to_event_days']
HOSP_OUTCOME = ['hosp_total','followup_days','followup_years','log_followup_years']

stage1_main = select_cols(analysis_base, ID_COLS + main_predictors + COMMON_FLAGS + ONE_YEAR_OUTCOME + SURVIVAL_OUTCOME + HOSP_OUTCOME)
stage1_sensitivity = select_cols(analysis_base, ID_COLS + main_predictors + sens_predictors + COMMON_FLAGS + ONE_YEAR_OUTCOME + SURVIVAL_OUTCOME + HOSP_OUTCOME)
stage1_exploratory = select_cols(analysis_base, ID_COLS + main_predictors + sens_predictors + COMMON_FLAGS + ONE_YEAR_OUTCOME + SURVIVAL_OUTCOME + HOSP_OUTCOME)
stage1_oneyear = select_cols(one_year, ID_COLS + main_predictors + COMMON_FLAGS + ONE_YEAR_OUTCOME)
stage1_survival = select_cols(survival, ID_COLS + main_predictors + COMMON_FLAGS + SURVIVAL_OUTCOME)
stage1_hosp = select_cols(hosp, ID_COLS + main_predictors + COMMON_FLAGS + HOSP_OUTCOME)

stage1_main.to_csv(OUT_DIR / 'stage1_main_analysis.csv', index=False)
stage1_sensitivity.to_csv(OUT_DIR / 'stage1_sensitivity_analysis.csv', index=False)
stage1_exploratory.to_csv(OUT_DIR / 'stage1_exploratory_analysis.csv', index=False)
stage1_oneyear.to_csv(OUT_DIR / 'stage1_oneyear_mortality.csv', index=False)
stage1_survival.to_csv(OUT_DIR / 'stage1_survival_analysis.csv', index=False)
stage1_hosp.to_csv(OUT_DIR / 'stage1_hospitalization_analysis.csv', index=False)

cohort_summary = pd.DataFrame([
    {'dataset': 'input_full', 'n_rows': len(df), 'n_cols': df.shape[1]},
    {'dataset': 'analysis_base_after_DEC040_exclusion', 'n_rows': len(analysis_base), 'n_cols': analysis_base.shape[1]},
    {'dataset': 'stage1_main_analysis', 'n_rows': len(stage1_main), 'n_cols': stage1_main.shape[1]},
    {'dataset': 'stage1_oneyear_mortality', 'n_rows': len(stage1_oneyear), 'n_cols': stage1_oneyear.shape[1]},
    {'dataset': 'stage1_survival_analysis', 'n_rows': len(stage1_survival), 'n_cols': stage1_survival.shape[1]},
    {'dataset': 'stage1_hospitalization_analysis', 'n_rows': len(stage1_hosp), 'n_cols': stage1_hosp.shape[1]},
    {'dataset': 'stage1_sensitivity_analysis', 'n_rows': len(stage1_sensitivity), 'n_cols': stage1_sensitivity.shape[1]},
])
cohort_summary.to_csv(OUT_DIR / 'stage1_cohort_summary.csv', index=False)
cohort_summary

# ============================================================
# 13. Missingness report by cohort and variable role
# ============================================================
def missingness_table(data, dataset_name, variables, role):
    rows = []
    for v in variables:
        if v in data.columns:
            n = len(data)
            nmiss = int(data[v].isna().sum())
            rows.append({
                'dataset': dataset_name,
                'variable': v,
                'role': role,
                'n': n,
                'n_missing': nmiss,
                'pct_missing': round(nmiss / n * 100, 2) if n else np.nan,
                'n_nonmissing': int(data[v].notna().sum()),
                'n_unique_nonmissing': int(data[v].nunique(dropna=True))
            })
    return pd.DataFrame(rows)

miss_tables = []
cohorts = [
    ('full_input_processed', df),
    ('analysis_base', analysis_base),
    ('one_year_mortality', one_year),
    ('survival', survival),
    ('hospitalization', hosp),
]
for name, data in cohorts:
    miss_tables.append(missingness_table(data, name, main_predictors, 'main_predictor'))
    miss_tables.append(missingness_table(data, name, sens_predictors, 'sensitivity_exploratory_predictor'))
    miss_tables.append(missingness_table(data, name, ONE_YEAR_OUTCOME + SURVIVAL_OUTCOME + HOSP_OUTCOME, 'outcome_or_denominator'))

missingness_report = pd.concat([t for t in miss_tables if not t.empty], ignore_index=True)
missingness_report.to_csv(OUT_DIR / 'stage1_missingness_report.csv', index=False)
missingness_report.head(30)

# ============================================================
# 14. Summary report and metadata
# ============================================================
run_metadata.update({
    'input_shape_rows': int(df_raw.shape[0]),
    'input_shape_columns': int(df_raw.shape[1]),
    'processed_shape_rows': int(df.shape[0]),
    'processed_shape_columns': int(df.shape[1]),
    'n_excluded_same_day_or_after_death': int(df['exclude_same_day_or_after_death_stage1'].sum()),
    'n_main_predictors': int(len(main_predictors)),
    'n_sensitivity_exploratory_predictors': int(len(sens_predictors)),
    'n_one_year_mortality': int(len(stage1_oneyear)),
    'n_survival': int(len(stage1_survival)),
    'n_hospitalization': int(len(stage1_hosp)),
})

with open(OUT_DIR / 'stage1_run_metadata.json', 'w', encoding='utf-8') as f:
    json.dump(run_metadata, f, indent=2, ensure_ascii=False)

# Compose markdown report.
summary_lines = []
summary_lines.append('# Stage 1 Summary Report')
summary_lines.append('')
summary_lines.append(f'Generated: {run_metadata["run_datetime"]}')
summary_lines.append(f'Input: `{INPUT_DATA.name}`')
summary_lines.append(f'Input rows/columns: {df_raw.shape[0]} / {df_raw.shape[1]}')
summary_lines.append('')
summary_lines.append('## Key decisions applied')
summary_lines.append('- DEC-038: Missing comorbidity documentation interpreted as absence for binary covariates.')
summary_lines.append('- DEC-039: Unusable echo values treated as missing/effective missing, not normal.')
summary_lines.append('- DEC-040: Same-calendar-date echo/death or echo-after-death excluded from analytic cohorts and reported.')
summary_lines.append('- DEC-041: No maximum echo-to-dialysis gap cutoff at Stage 1; distribution exported for clinician review.')
summary_lines.append('- DEC-042: Echo free-text fields retained for future text/NLP review, not modeled now.')
summary_lines.append('- DEC-043: Echo category distributions before/after clinician grouping exported.')
summary_lines.append('')
summary_lines.append('## Cohort sizes')
summary_lines.append(cohort_summary.to_markdown(index=False))
summary_lines.append('')
summary_lines.append('## Exclusion summary')
summary_lines.append(exclusions_summary.to_markdown(index=False))
summary_lines.append('')
summary_lines.append('## Outputs')
for f in sorted(OUT_DIR.glob('*')):
    summary_lines.append(f'- `{f.name}`')

report = chr(10).join(summary_lines)
with open(OUT_DIR / 'stage1_summary_report.md', 'w', encoding='utf-8') as f:
    f.write(report)

print(report[:3000])
