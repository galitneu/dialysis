#!/usr/bin/env python3
"""Restructure the dialysis notebook according to the approved plan."""
import json
import copy

NB_PATH = '/home/user/dialysis/date_eda_echo_dialysis_(2).ipynb'

with open(NB_PATH) as f:
    nb = json.load(f)

cells = nb['cells']

def make_md_cell(cell_id, source):
    return {
        'cell_type': 'markdown',
        'id': cell_id,
        'metadata': {},
        'source': [line + '\n' for line in source.split('\n')][:-1] + [source.split('\n')[-1]]
    }

def make_code_cell(cell_id, source):
    lines = source.split('\n')
    src_list = [line + '\n' for line in lines[:-1]] + [lines[-1]]
    return {
        'cell_type': 'code',
        'id': cell_id,
        'metadata': {},
        'source': src_list,
        'outputs': [],
        'execution_count': None,
    }

# ═══════════════════════════════════════════════════════════════════════════════
# Step 1: Replace Cell 8 (config) with parametric CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
cells[8] = make_code_cell('cell-config', r'''# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE CONFIGURATION — edit this cell to change anchor mode, windows, etc.
# ═══════════════════════════════════════════════════════════════════════════════
CONFIG = {
    # ── Anchor mode ──
    "ANCHOR_MODE": "dialysis",            # "echo" | "dialysis"

    # ── File paths ──
    "FILE_PATH": "/content/drive/MyDrive/dialysis/data/echo_project_update_cleaned_2202.xlsx",
    "SHEET_NAME": 0,
    "DRIVE_BASE": "/content/drive/MyDrive/dialysis/data",
    "OUTPUT_DIR": "/content/drive/MyDrive/dialysis/outputs",

    # ── Column names ──
    "COL_PATIENT": "patient number",
    "COL_DEATH":   "DeathDate",
    "COL_ECHO":    "Echo_Date",
    "COL_DIAL":    "Dialysis_Start_Date",
    "COL_LAST_FU": None,          # e.g. "LastFollowUpDate"

    # ── Cohort filters ──
    "ECHO_BEFORE_DIALYSIS_ONLY": True,
    "ECHO_TO_DIALYSIS_WINDOW_DAYS": 180,  # primary; use 365 for sensitivity
    "EXCLUDE_EARLY_DEATH_DAYS": None,     # set to 30 for sensitivity

    # ── Target ──
    "HORIZON_DAYS": 365,
    "FOLLOWUP_MODE": "proxy_dataset_end",  # "strict_drop_unknown" | "proxy_dataset_end"
    "DATASET_END_DATE": None,              # computed at runtime from max(all dates)

    # ── Modeling ──
    "BOOTSTRAP_N": 200,
    "N_SPLITS": 5,
    "RANDOM_STATE": 42,
}

# ── Backward-compatible aliases (so EDA cells 9-36 work unchanged) ──
FILE_PATH        = CONFIG["FILE_PATH"]
SHEET_NAME       = CONFIG["SHEET_NAME"]
DRIVE_BASE       = CONFIG["DRIVE_BASE"]
COL_PATIENT      = CONFIG["COL_PATIENT"]
COL_DEATH        = CONFIG["COL_DEATH"]
COL_ECHO         = CONFIG["COL_ECHO"]
COL_DIAL         = CONFIG["COL_DIAL"]
COL_LAST_FU      = CONFIG["COL_LAST_FU"]
EXTRA_DATE_COLS  = []
WINDOWS_MONTHS   = [3, 6, 12]
KEEP_WINDOW_MONTHS = int(CONFIG["ECHO_TO_DIALYSIS_WINDOW_DAYS"] / 30.44)

print(f"Anchor mode:  {CONFIG['ANCHOR_MODE']}")
print(f"Echo window:  {CONFIG['ECHO_TO_DIALYSIS_WINDOW_DAYS']}d")
print(f"Follow-up:    {CONFIG['FOLLOWUP_MODE']}")
print(f"Early death:  {CONFIG['EXCLUDE_EARLY_DEATH_DAYS']}")''')

# ═══════════════════════════════════════════════════════════════════════════════
# Step 2: Replace Cell 17 (derived times) with anchor-aware version
# ═══════════════════════════════════════════════════════════════════════════════
cells[17] = make_code_cell('cell-derived', r'''# ── Derived time variables (anchor-aware) ──────────────────────────────────────

# Core gaps (always computed regardless of anchor mode)
df["gap_echo_to_dial_days"]   = (df[COL_DIAL]  - df[COL_ECHO]).dt.days
df["time_dial_to_death_days"] = (df[COL_DEATH] - df[COL_DIAL]).dt.days
df["time_echo_to_death_days"] = (df[COL_DEATH] - df[COL_ECHO]).dt.days

# Censor date
if COL_LAST_FU and COL_LAST_FU in df.columns:
    df[COL_LAST_FU] = parse_date_series(df[COL_LAST_FU])
    df["censor_date"] = df[COL_LAST_FU]
    print(f"Using explicit censor column: {COL_LAST_FU}")
else:
    max_date = pd.concat([df[COL_DIAL], df[COL_ECHO], df[COL_DEATH]], axis=0).dropna().max()
    df["censor_date"] = max_date
    CONFIG["DATASET_END_DATE"] = max_date
    print(f"No COL_LAST_FU set. Using dataset max date as proxy censor: {max_date.date()}")

# Anchor-relative columns
if CONFIG["ANCHOR_MODE"] == "echo":
    df["anchor_date"] = df[COL_ECHO]
    df["gap_anchor_to_death_days"] = df["time_echo_to_death_days"]
    print(f"Anchor = Echo_Date")
else:
    df["anchor_date"] = df[COL_DIAL]
    df["gap_anchor_to_death_days"] = df["time_dial_to_death_days"]
    print(f"Anchor = Dialysis_Start_Date")

df["death_event"] = df[COL_DEATH].notna().astype(int)
df["time_anchor_to_censor_days"] = (df["censor_date"] - df["anchor_date"]).dt.days

# Backward-compat: time_to_event_or_censor_days is now anchor-relative
df["time_dial_to_censor_days"] = (df["censor_date"] - df[COL_DIAL]).dt.days
df["time_to_event_or_censor_days"] = np.where(
    df["death_event"].eq(1),
    df["gap_anchor_to_death_days"],
    df["time_anchor_to_censor_days"]
)

print(f"\nDerived columns created ({len(df)} rows)")
display(df[[COL_DIAL, COL_ECHO, COL_DEATH,
            "gap_echo_to_dial_days", "death_event",
            "time_to_event_or_censor_days"]].head(3))''')

# ═══════════════════════════════════════════════════════════════════════════════
# Step 3: Replace cells 40-45 with the new modular pipeline
# ═══════════════════════════════════════════════════════════════════════════════
# Keep cells 0-39 as-is, replace 40-45 with new cells, keep 46-48

new_pipeline_cells = []

# -- pip install cell --
new_pipeline_cells.append(make_code_cell('cell-pip-install', r'''## ── Install extra libraries ───────────────────────────────────────────────────
!pip install -q xgboost lightgbm shap'''))

# -- build_cohort --
new_pipeline_cells.append(make_md_cell('cell-md-cohort',
    '## Step 4. Cohort Building — `build_cohort(df, config)`\n'
    'Parametric cohort construction. Anchor mode determines inclusion logic.'))

new_pipeline_cells.append(make_code_cell('cell-build-cohort', r'''import json, os

def build_cohort(df, config):
    """
    Filter df to analytic cohort based on config['ANCHOR_MODE'].

    Returns (df_cohort, cohort_report_dict).
    """
    report = {"anchor_mode": config["ANCHOR_MODE"], "n_input": len(df), "exclusions": {}}
    cdf = df.copy()

    if config["ANCHOR_MODE"] == "echo":
        # Requires Echo_Date
        mask = cdf[config["COL_ECHO"]].isna()
        report["exclusions"]["missing_echo_date"] = int(mask.sum())
        cdf = cdf[~mask].copy()

        # Drop death before echo
        mask = (cdf["death_event"] == 1) & (cdf["time_echo_to_death_days"] < 0)
        report["exclusions"]["death_before_echo"] = int(mask.sum())
        cdf = cdf[~mask].copy()

    else:  # dialysis
        # Requires both dates
        mask_dial = cdf[config["COL_DIAL"]].isna()
        mask_echo = cdf[config["COL_ECHO"]].isna()
        report["exclusions"]["missing_dialysis_date"] = int(mask_dial.sum())
        report["exclusions"]["missing_echo_date"] = int(mask_echo.sum())
        cdf = cdf[~mask_dial & ~mask_echo].copy()

        # Echo before dialysis
        if config["ECHO_BEFORE_DIALYSIS_ONLY"]:
            mask = cdf["gap_echo_to_dial_days"] < 0
            report["exclusions"]["echo_after_dialysis"] = int(mask.sum())
            cdf = cdf[~mask].copy()

        # Window filter
        window = config["ECHO_TO_DIALYSIS_WINDOW_DAYS"]
        mask = cdf["gap_echo_to_dial_days"] > window
        report["exclusions"][f"echo_outside_{window}d_window"] = int(mask.sum())
        cdf = cdf[~mask].copy()

        # Drop death before dialysis
        mask = (cdf["death_event"] == 1) & (cdf["time_dial_to_death_days"] < 0)
        report["exclusions"]["death_before_dialysis"] = int(mask.sum())
        cdf = cdf[~mask].copy()

    # Optional: exclude early deaths
    ed = config.get("EXCLUDE_EARLY_DEATH_DAYS")
    if ed is not None:
        mask = (cdf["death_event"] == 1) & (cdf["gap_anchor_to_death_days"].between(0, ed))
        report["exclusions"][f"early_death_le_{ed}d"] = int(mask.sum())
        cdf = cdf[~mask].copy()

    report["n_output"] = len(cdf)
    return cdf, report

# ── Execute ──
df_cohort, cohort_report = build_cohort(df, CONFIG)
print(json.dumps(cohort_report, indent=2, ensure_ascii=False))'''))

# -- make_target --
new_pipeline_cells.append(make_md_cell('cell-md-target',
    '## Step 5. Target Creation — `make_target(df_cohort, config)`'))

new_pipeline_cells.append(make_code_cell('cell-make-target', r'''def make_target(df_cohort, config):
    """
    Create 1-year mortality target from anchor_date.
    Returns (df_target, target_report_dict).
    """
    H = config["HORIZON_DAYS"]
    mdf = df_cohort.copy()

    def assign_target(row):
        t = row["time_to_event_or_censor_days"]
        died = row["death_event"]
        if pd.isna(t):
            return np.nan
        if died == 1 and t <= H:
            return 1
        elif died == 1 and t > H:
            return 0
        elif died == 0 and t >= H:
            return 0
        else:
            return np.nan  # censored before horizon

    mdf["target_1yr_death"] = mdf.apply(assign_target, axis=1)
    n_unknown = int(mdf["target_1yr_death"].isna().sum())
    mdf = mdf.dropna(subset=["target_1yr_death"]).copy()
    mdf["target_1yr_death"] = mdf["target_1yr_death"].astype(int)

    report = {
        "followup_mode": config["FOLLOWUP_MODE"],
        "n_excluded_unknown": n_unknown,
        "n_final": len(mdf),
        "n_deaths": int(mdf["target_1yr_death"].sum()),
        "n_survived": int((mdf["target_1yr_death"] == 0).sum()),
        "mortality_rate": round(float(mdf["target_1yr_death"].mean()), 4),
    }
    return mdf, report

# ── Execute ──
df_target, target_report = make_target(df_cohort, CONFIG)
print(json.dumps(target_report, indent=2, ensure_ascii=False))'''))

# -- build_preprocessor --
new_pipeline_cells.append(make_md_cell('cell-md-preprocess',
    '## Step 6. Preprocessing — ordinal encoding, binary flags, engineered features'))

new_pipeline_cells.append(make_code_cell('cell-build-preprocessor', r'''def build_preprocessor(df_in, config):
    """
    Apply ordinal encoding, binary flags, and engineered features.
    Returns (df_processed, ordinal_maps_dict).
    """
    mdf = df_in.copy()

    # ── Binary encodings ──
    mdf['is_male'] = (mdf['m/f'].astype(str).str.strip().str.lower()
                       .map({'m': 1, 'male': 1, 'f': 0, 'female': 0, 'זכר': 1, 'נקבה': 0}))
    mdf['is_hd'] = (mdf['HD/PD'].astype(str).str.strip().str.upper()
                     .map({'HD': 1, 'PD': 0}))

    # ── Ordinal mappings (existing + RV) ──
    ORDINAL_MAPS = {
        'LeftVentricleCavitySize': {
            'תקין': 0, 'normal': 0,
            'מורחב במידה קלה': 1, 'mildly dilated': 1,
            'מורחב במידה בינונית': 2, 'moderately dilated': 2,
            'מורחב במידה קשה': 3, 'severely dilated': 3,
            'מורחב': 2,
        },
        'LeftVentricleWallThickness': {
            'תקין': 0, 'normal': 0,
            'מעובה במידה קלה': 1,
            'מעובה במידה בינונית': 2, 'היפרטרופי': 2,
            'מעובה במידה קשה': 3, 'מעובה': 2,
        },
        'LeftVentricleSystolicFunction': {
            'תקין': 0, 'normal': 0, 'שמור': 0,
            'ירוד במידה קלה': 1, 'mildly reduced': 1,
            'ירוד במידה קלה עד בינונית': 1.5,
            'ירוד במידה בינונית': 2, 'moderately reduced': 2,
            'ירוד במידה בינונית עד קשה': 2.5,
            'ירוד במידה קשה': 3, 'severely reduced': 3,
        },
        'LACavitySize': {
            'תקין': 0, 'normal': 0,
            'מורחב במידה קלה': 1, 'מוגדל במידה קלה': 1,
            'מורחב במידה בינונית': 2, 'מוגדל במידה בינונית': 2,
            'מורחב במידה קשה': 3, 'מוגדל במידה קשה': 3,
            'מורחב': 2, 'מוגדל': 2,
        },
        'MitralRegurgitation': {
            'ללא': 0, 'none': 0, 'אין': 0,
            'מינימלי': 0.5, 'מינימלית': 0.5, 'minimal': 0.5, 'זניח': 0.5,
            'קל': 1, 'קלה': 1, 'mild': 1,
            'קל עד בינוני': 1.5, 'קלה עד בינונית': 1.5,
            'בינוני': 2, 'בינונית': 2, 'moderate': 2,
            'בינוני עד קשה': 2.5, 'בינונית עד קשה': 2.5,
            'קשה': 3, 'חמור': 3, 'severe': 3,
        },
        'TricuspidRegurgitation': {
            'ללא': 0, 'none': 0, 'אין': 0,
            'מינימלי': 0.5, 'מינימלית': 0.5, 'minimal': 0.5,
            'קל': 1, 'קלה': 1, 'mild': 1,
            'קל עד בינוני': 1.5, 'קלה עד בינונית': 1.5,
            'בינוני': 2, 'בינונית': 2, 'moderate': 2,
            'בינוני עד קשה': 2.5, 'בינונית עד קשה': 2.5,
            'קשה': 3, 'חמור': 3, 'severe': 3,
        },
        'AorticValveRegurgitation': {
            'ללא': 0, 'none': 0, 'אין': 0,
            'מינימלי': 0.5, 'מינימלית': 0.5, 'minimal': 0.5,
            'קל': 1, 'קלה': 1, 'mild': 1,
            'קל עד בינוני': 1.5, 'קלה עד בינונית': 1.5,
            'בינוני': 2, 'בינונית': 2, 'moderate': 2,
            'קשה': 3, 'חמור': 3, 'severe': 3,
        },
        # ── NEW: Right Ventricle ──
        'RVSize': {
            'תקין': 0, 'normal': 0,
            'מורחב במידה קלה': 1, 'mildly dilated': 1, 'mild': 1,
            'מורחב במידה בינונית': 2, 'moderately dilated': 2, 'moderate': 2,
            'מורחב במידה קשה': 3, 'severely dilated': 3, 'severe': 3,
            'מורחב': 2, 'מוגדל': 2, 'enlarged': 2,
        },
        'RVSystolicFunction': {
            'תקין': 0, 'normal': 0,
            'ירוד במידה קלה': 1, 'mildly_reduced': 1, 'mildly reduced': 1, 'mild': 1,
            'ירוד במידה בינונית': 2, 'moderately_reduced': 2, 'moderately reduced': 2,
            'moderate': 2, 'היפוקינטי': 2,
            'ירוד במידה קשה': 3, 'severely_reduced': 3, 'severely reduced': 3,
            'severe': 3,
            'ירוד': 2, 'reduced': 2,
        },
    }

    def map_ordinal(series, mapping):
        result = pd.Series(np.nan, index=series.index)
        for idx, val in series.items():
            if pd.isna(val):
                continue
            val_clean = str(val).strip()
            if val_clean in mapping:
                result[idx] = mapping[val_clean]
                continue
            val_lower = val_clean.lower()
            for k, v in mapping.items():
                if k.lower() == val_lower:
                    result[idx] = v
                    break
            else:
                for k, v in sorted(mapping.items(), key=lambda x: -len(x[0])):
                    if k in val_clean or val_clean in k:
                        result[idx] = v
                        break
        return result

    for col, mapping in ORDINAL_MAPS.items():
        if col in mdf.columns:
            mdf[f"{col}_ord"] = map_ordinal(mdf[col], mapping)
            pct = mdf[f"{col}_ord"].notna().mean()
            print(f"  {col} -> {col}_ord: {pct:.0%} mapped")

    # ── Comorbidities ──
    COMORBIDITY_COLS = ['MI', 'CABG', 'IHD', 'AFIB', 'HTN',
                        'Diabetes mellitus', 'DYSLIPIDEMIA', 'COPD',
                        'OncologicalDiagnosis']
    for col in COMORBIDITY_COLS:
        if col in mdf.columns:
            mdf[f'has_{col}'] = mdf[col].notna().astype(int)

    # ── Engineered features ──
    if 'urea-numeric result' in mdf.columns and 'creatinine-numeric result' in mdf.columns:
        mdf['bun_creatinine_ratio'] = mdf['urea-numeric result'] / mdf['creatinine-numeric result'].replace(0, np.nan)
    if 'ca-numeric result' in mdf.columns and 'p-numeric result' in mdf.columns:
        mdf['ca_p_product'] = mdf['ca-numeric result'] * mdf['p-numeric result']
    if 'albumin-numeric result' in mdf.columns and 'crp-numeric result' in mdf.columns:
        mdf['albumin_crp_ratio'] = mdf['albumin-numeric result'] / mdf['crp-numeric result'].replace(0, np.nan)
    if 'sbp-numeric result' in mdf.columns and 'dbp-numeric result' in mdf.columns:
        mdf['pulse_pressure'] = mdf['sbp-numeric result'] - mdf['dbp-numeric result']
        mdf['map_pressure'] = mdf['dbp-numeric result'] + mdf['pulse_pressure'] / 3
    if 'LeftVentricleEndDiastolicDiameter' in mdf.columns and 'LeftVentricleEndSystolicDiameter' in mdf.columns:
        mdf['lv_fractional_shortening'] = (
            (mdf['LeftVentricleEndDiastolicDiameter'] - mdf['LeftVentricleEndSystolicDiameter'])
            / mdf['LeftVentricleEndDiastolicDiameter'].replace(0, np.nan))
    if 'LeftVentricleInterventricularSeptumThickness' in mdf.columns and 'LeftVentriclePosteriorWallThickness' in mdf.columns:
        mdf['relative_wall_thickness'] = (
            2 * mdf['LeftVentriclePosteriorWallThickness']
            / mdf['LeftVentricleEndDiastolicDiameter'].replace(0, np.nan))
    if 'TissueDopplerEERatioSeptal' in mdf.columns and 'TissueDopplerEERatioLateral' in mdf.columns:
        mdf['avg_E_e_ratio'] = (mdf['TissueDopplerEERatioSeptal'] + mdf['TissueDopplerEERatioLateral']) / 2
    if 'TissueDopplerEVelositySeptal' in mdf.columns and 'TissueDopplerEVelosityLateral' in mdf.columns:
        mdf['avg_e_prime'] = (mdf['TissueDopplerEVelositySeptal'] + mdf['TissueDopplerEVelosityLateral']) / 2
    if 'LV_EF' in mdf.columns:
        mdf['ef_category'] = pd.cut(mdf['LV_EF'], bins=[0, 40, 50, 100], labels=[2, 1, 0]).astype(float)
    if 'albumin-numeric result' in mdf.columns:
        mdf['low_albumin'] = (mdf['albumin-numeric result'] < 3.5).astype(int)
    if 'hb-numeric result' in mdf.columns:
        mdf['anemia'] = (mdf['hb-numeric result'] < 10).astype(int)
    if 'crp-numeric result' in mdf.columns:
        mdf['high_crp'] = (mdf['crp-numeric result'] > 10).astype(int)
    if 'EstimatedSysPAPressure' in mdf.columns:
        mdf['pulm_htn'] = (mdf['EstimatedSysPAPressure'] > 40).astype(int)
    if 'AgeAtFirstHFDate' in mdf.columns:
        mdf['age_over_75'] = (mdf['AgeAtFirstHFDate'] > 75).astype(int)
    comorbidity_features = [f'has_{c}' for c in COMORBIDITY_COLS if c in mdf.columns]
    if comorbidity_features:
        mdf['n_comorbidities'] = mdf[comorbidity_features].sum(axis=1)

    # Save category mapping
    try:
        os.makedirs(config.get("OUTPUT_DIR", "."), exist_ok=True)
        mapping_path = f"{config['OUTPUT_DIR']}/category_mapping.json"
        with open(mapping_path, "w") as f:
            json.dump({k: {str(kk): vv for kk, vv in v.items()}
                       for k, v in ORDINAL_MAPS.items()}, f, indent=2, ensure_ascii=False)
        print(f"\nSaved: {mapping_path}")
    except Exception:
        pass

    return mdf, ORDINAL_MAPS

# ── Execute ──
df_model, ordinal_maps = build_preprocessor(df_target, CONFIG)
print(f"Processed: {len(df_model)} rows")'''))

# -- get_feature_sets --
new_pipeline_cells.append(make_md_cell('cell-md-features',
    '## Step 7. Feature Sets — echo-only, echo+adjustments, full clinical'))

new_pipeline_cells.append(make_code_cell('cell-get-feature-sets', r'''def get_feature_sets(df):
    """Return dict of feature set name -> list of column names (validated)."""
    echo_numeric = [
        'LV_EF', 'LeftVentricleEndDiastolicDiameter', 'LeftVentricleEndSystolicDiameter',
        'LeftVentricleInterventricularSeptumThickness', 'LeftVentriclePosteriorWallThickness',
        'LeftVentricleEstimatedMass', 'LeftVentricleEstimatedMassIndex', 'LeftVentricleScoreIndex',
        'TissueDopplerSVelocitySeptal', 'TissueDopplerEVelositySeptal', 'TissueDopplerEERatioSeptal',
        'TissueDopplerSVelocityLateral', 'TissueDopplerEVelosityLateral', 'TissueDopplerEERatioLateral',
        'MitralInflowPeakEWave', 'EstimatedSysPAPressure',
    ]
    echo_ordinal = [
        'LeftVentricleCavitySize_ord', 'LeftVentricleWallThickness_ord',
        'LeftVentricleSystolicFunction_ord', 'LACavitySize_ord',
        'MitralRegurgitation_ord', 'TricuspidRegurgitation_ord', 'AorticValveRegurgitation_ord',
        'RVSize_ord', 'RVSystolicFunction_ord',
    ]
    echo_engineered = [
        'lv_fractional_shortening', 'relative_wall_thickness',
        'avg_E_e_ratio', 'avg_e_prime', 'ef_category', 'pulm_htn',
    ]
    set1 = [c for c in echo_numeric + echo_ordinal + echo_engineered if c in df.columns]

    adjustments = ['AgeAtFirstHFDate', 'is_male', 'is_hd', 'gap_echo_to_dial_days']
    set2 = set1 + [c for c in adjustments if c in df.columns]

    labs = [
        'Weight', 'BMI', 'GFR',
        'creatinine-numeric result', 'urea-numeric result',
        'na-numeric result', 'k-numeric result',
        'ca-numeric result', 'p-numeric result',
        'hb-numeric result', 'albumin-numeric result',
        'hba1c-numeric result', 'crp-numeric result',
        'sbp-numeric result', 'dbp-numeric result',
        'hospitalization-count',
    ]
    comorbidity_flags = [c for c in df.columns if c.startswith('has_')]
    lab_engineered = [
        'bun_creatinine_ratio', 'ca_p_product', 'albumin_crp_ratio',
        'pulse_pressure', 'map_pressure',
        'n_comorbidities', 'low_albumin', 'anemia', 'high_crp', 'age_over_75',
    ]
    set3 = set2 + [c for c in labs + comorbidity_flags + lab_engineered if c in df.columns]
    set3 = list(dict.fromkeys(set3))

    result = {"echo_only": set1, "echo_adjustments": set2, "full_clinical": set3}
    for name, feats in result.items():
        print(f"  {name}: {len(feats)} features")
    return result

# ── Execute ──
feature_sets = get_feature_sets(df_model)

# Generate features_report
features_report = []
for set_name, feats in feature_sets.items():
    for f in feats:
        if f in df_model.columns:
            features_report.append({
                'feature_set': set_name, 'feature': f,
                'dtype': str(df_model[f].dtype),
                'pct_missing': round(float(df_model[f].isna().mean()), 3),
                'n_unique': int(df_model[f].nunique()),
            })
try:
    fr = pd.DataFrame(features_report)
    fr.to_csv(f"{CONFIG['OUTPUT_DIR']}/features_report.csv", index=False)
    print(f"\nSaved features_report.csv ({len(fr)} rows)")
except Exception:
    pass'''))

# -- Elastic Net --
new_pipeline_cells.append(make_md_cell('cell-md-elastic',
    '## Step 8a. Primary Model — Elastic Net Logistic with Bootstrap Stability'))

new_pipeline_cells.append(make_code_cell('cell-elastic-net', r'''from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict, GridSearchCV
from sklearn.metrics import (roc_auc_score, average_precision_score, f1_score,
                             recall_score, precision_score, classification_report,
                             confusion_matrix, roc_curve, precision_recall_curve)
from sklearn.base import clone
import warnings
warnings.filterwarnings('ignore')

def run_elastic_net_bootstrap(X, y, config):
    """
    Elastic Net Logistic Regression with bootstrap stability.

    Returns dict with cv_auc, stability_table, y_prob, estimator.
    """
    pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", LogisticRegression(
            penalty="elasticnet", solver="saga", l1_ratio=0.5,
            max_iter=5000, random_state=config["RANDOM_STATE"],
            class_weight="balanced")),
    ])
    param_grid = {
        "model__C": [0.001, 0.01, 0.1, 0.5, 1.0, 5.0],
        "model__l1_ratio": [0.1, 0.3, 0.5, 0.7, 0.9],
    }
    cv = StratifiedKFold(n_splits=config["N_SPLITS"], shuffle=True,
                         random_state=config["RANDOM_STATE"])
    search = GridSearchCV(pipe, param_grid, cv=cv, scoring="roc_auc",
                          n_jobs=-1, refit=True)
    search.fit(X, y)
    best_pipe = search.best_estimator_

    y_prob = cross_val_predict(best_pipe, X, y, cv=cv, method="predict_proba")[:, 1]
    cv_auc = roc_auc_score(y, y_prob)
    cv_ap = average_precision_score(y, y_prob)

    # Bootstrap stability
    N = config["BOOTSTRAP_N"]
    coef_matrix = np.zeros((N, X.shape[1]))
    print(f"  Running {N} bootstrap iterations...")
    for b in range(N):
        rng = np.random.RandomState(b)
        idx = rng.choice(len(X), len(X), replace=True)
        X_b, y_b = X.iloc[idx], y.iloc[idx]
        pipe_b = clone(best_pipe)
        pipe_b.fit(X_b, y_b)
        coef_matrix[b] = pipe_b.named_steps["model"].coef_[0]

    main_coefs = best_pipe.named_steps["model"].coef_[0]
    stability = pd.DataFrame({
        "feature": list(X.columns),
        "selection_freq": (np.abs(coef_matrix) > 1e-6).mean(axis=0),
        "mean_abs_coef": np.abs(coef_matrix).mean(axis=0),
        "mean_coef": coef_matrix.mean(axis=0),
        "std_coef": coef_matrix.std(axis=0),
        "effect_direction": ["risk" if c > 0 else "protective" for c in coef_matrix.mean(axis=0)],
        "odds_ratio": np.exp(main_coefs),
        "coefficient": main_coefs,
    }).sort_values("selection_freq", ascending=False)

    return {
        "cv_auc": cv_auc, "cv_ap": cv_ap,
        "best_params": search.best_params_,
        "estimator": best_pipe, "y_prob": y_prob,
        "stability_table": stability, "coef_matrix": coef_matrix,
    }'''))

# -- GBM/XGBoost --
new_pipeline_cells.append(make_md_cell('cell-md-gbm',
    '## Step 8b. Secondary Model — XGBoost with SHAP'))

new_pipeline_cells.append(make_code_cell('cell-gbm-shap', r'''import xgboost as xgb
import shap

def run_xgboost_shap(X, y, config):
    """
    XGBoost with SHAP analysis.
    Returns dict with cv_auc, shap_values, feature_importance, y_prob.
    """
    pos_weight = (y == 0).sum() / max((y == 1).sum(), 1)
    pipe = Pipeline([
        ("imputer", SimpleImputer(strategy="median")),
        ("scaler", StandardScaler()),
        ("model", xgb.XGBClassifier(
            n_estimators=300, max_depth=4, learning_rate=0.05,
            subsample=0.8, colsample_bytree=0.8,
            eval_metric="logloss", use_label_encoder=False,
            random_state=config["RANDOM_STATE"],
            scale_pos_weight=pos_weight)),
    ])
    cv = StratifiedKFold(n_splits=config["N_SPLITS"], shuffle=True,
                         random_state=config["RANDOM_STATE"])
    y_prob = cross_val_predict(pipe, X, y, cv=cv, method="predict_proba")[:, 1]
    cv_auc = roc_auc_score(y, y_prob)

    pipe.fit(X, y)
    X_transformed = pd.DataFrame(
        pipe.named_steps["scaler"].transform(
            pipe.named_steps["imputer"].transform(X)),
        columns=X.columns)
    explainer = shap.TreeExplainer(pipe.named_steps["model"])
    shap_vals = explainer.shap_values(X_transformed)

    shap_importance = pd.DataFrame({
        "feature": list(X.columns),
        "mean_abs_shap": np.abs(shap_vals).mean(axis=0),
    }).sort_values("mean_abs_shap", ascending=False)

    return {
        "cv_auc": cv_auc, "y_prob": y_prob,
        "estimator": pipe,
        "shap_values": shap_vals,
        "shap_importance": shap_importance,
        "X_display": X_transformed,
    }'''))

# -- Pipeline orchestration --
new_pipeline_cells.append(make_md_cell('cell-md-orchestrate',
    '## Step 8c. Run Pipeline — All Feature Sets'))

new_pipeline_cells.append(make_code_cell('cell-orchestrate', r'''import os
os.makedirs(CONFIG["OUTPUT_DIR"], exist_ok=True)

# ── Run models on each feature set ──
pipeline_results = {}
for set_name, features in feature_sets.items():
    X = df_model[features].copy()
    y = df_model["target_1yr_death"].copy()

    print(f"\n{'='*60}")
    print(f"  Feature set: {set_name} ({len(features)} features, n={len(X)})")
    print(f"  Mortality rate: {y.mean():.1%}")
    print(f"{'='*60}")

    # Primary: Elastic Net
    print("\n  [Elastic Net]")
    en_result = run_elastic_net_bootstrap(X, y, CONFIG)
    print(f"  CV AUC: {en_result['cv_auc']:.4f} | CV AP: {en_result['cv_ap']:.4f}")

    # Secondary: XGBoost
    print("\n  [XGBoost]")
    xgb_result = run_xgboost_shap(X, y, CONFIG)
    print(f"  CV AUC: {xgb_result['cv_auc']:.4f}")

    pipeline_results[set_name] = {
        "elastic_net": en_result, "xgboost": xgb_result,
        "X": X, "y": y, "features": features,
    }

    # Save cardiac feature ranking
    en_result["stability_table"].to_csv(
        f"{CONFIG['OUTPUT_DIR']}/cardiac_feature_ranking_{set_name}.csv", index=False)

# Save reports
with open(f"{CONFIG['OUTPUT_DIR']}/cohort_report.json", "w") as f:
    json.dump(cohort_report, f, indent=2, ensure_ascii=False)
with open(f"{CONFIG['OUTPUT_DIR']}/target_report.json", "w") as f:
    json.dump(target_report, f, indent=2, ensure_ascii=False)

print(f"\n{'='*60}")
print("  SUMMARY")
print(f"{'='*60}")
for sn, pr in pipeline_results.items():
    print(f"  {sn}: EN AUC={pr['elastic_net']['cv_auc']:.4f}, "
          f"XGB AUC={pr['xgboost']['cv_auc']:.4f}, "
          f"n_features={len(pr['features'])}")'''))

# -- Results dashboard --
new_pipeline_cells.append(make_md_cell('cell-md-dashboard',
    '## Step 8d. Results Dashboard'))

new_pipeline_cells.append(make_code_cell('cell-dashboard', r'''import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.calibration import calibration_curve

for set_name, pr in pipeline_results.items():
    en = pr["elastic_net"]
    xgb_r = pr["xgboost"]
    X = pr["X"]
    y = pr["y"]

    print(f"\n\n{'#'*70}")
    print(f"  DASHBOARD: {set_name}")
    print(f"{'#'*70}")

    # ── ROC + PR curves: Elastic Net vs XGBoost ──
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    for name, y_prob, color in [
        (f"Elastic Net (AUC={en['cv_auc']:.3f})", en["y_prob"], "#2980b9"),
        (f"XGBoost (AUC={xgb_r['cv_auc']:.3f})", xgb_r["y_prob"], "#e74c3c"),
    ]:
        fpr, tpr, _ = roc_curve(y, y_prob)
        axes[0].plot(fpr, tpr, label=name, color=color, linewidth=2)
        prec, rec, _ = precision_recall_curve(y, y_prob)
        ap = average_precision_score(y, y_prob)
        axes[1].plot(rec, prec, label=name.replace("AUC", "AP").replace(
            f"{roc_auc_score(y, y_prob):.3f}", f"{ap:.3f}"), color=color, linewidth=2)
    axes[0].plot([0,1],[0,1],'k--',alpha=0.3)
    axes[0].set_title(f"ROC — {set_name}", fontsize=14)
    axes[0].set_xlabel("FPR"); axes[0].set_ylabel("TPR")
    axes[0].legend(fontsize=10); axes[0].grid(alpha=0.3)
    axes[1].set_title(f"Precision-Recall — {set_name}", fontsize=14)
    axes[1].set_xlabel("Recall"); axes[1].set_ylabel("Precision")
    axes[1].legend(fontsize=10); axes[1].grid(alpha=0.3)
    plt.tight_layout(); plt.show()

    # ── Bootstrap stability plot (top 15) ──
    stab = en["stability_table"].head(15).sort_values("selection_freq")
    fig, ax = plt.subplots(figsize=(10, 7))
    colors = ["#e74c3c" if d == "risk" else "#2980b9" for d in stab["effect_direction"]]
    ax.barh(stab["feature"], stab["selection_freq"], color=colors, edgecolor="black", linewidth=0.3)
    ax.set_xlabel("Bootstrap Selection Frequency", fontsize=12)
    ax.set_title(f"Feature Stability — Elastic Net ({set_name})\nRed=Risk, Blue=Protective", fontsize=14)
    ax.axvline(0.5, color="gray", linestyle="--", alpha=0.5)
    plt.tight_layout(); plt.show()

    # ── SHAP summary ──
    try:
        fig, ax = plt.subplots(figsize=(10, 10))
        shap.summary_plot(xgb_r["shap_values"], xgb_r["X_display"],
                          max_display=20, show=False)
        plt.title(f"SHAP — XGBoost ({set_name})", fontsize=14)
        plt.tight_layout(); plt.show()
    except Exception as e:
        print(f"  SHAP plot skipped: {e}")

    # ── Classification report (Elastic Net) ──
    thresholds = np.arange(0.2, 0.8, 0.05)
    f1s = [f1_score(y, (en["y_prob"] >= t).astype(int), zero_division=0) for t in thresholds]
    best_thr = thresholds[np.argmax(f1s)]
    y_pred = (en["y_prob"] >= best_thr).astype(int)
    print(f"\n  Elastic Net — threshold={best_thr:.2f}")
    print(classification_report(y, y_pred, target_names=["Survived 1yr", "Died within 1yr"]))

    # ── Calibration curve ──
    fig, ax = plt.subplots(figsize=(8, 6))
    prob_true, prob_pred = calibration_curve(y, en["y_prob"], n_bins=10, strategy="uniform")
    ax.plot(prob_pred, prob_true, "o-", linewidth=2, label="Elastic Net")
    ax.plot([0,1],[0,1],"k--",alpha=0.3)
    ax.set_xlabel("Mean predicted probability"); ax.set_ylabel("Fraction of positives")
    ax.set_title(f"Calibration — {set_name}", fontsize=14)
    ax.legend(); ax.grid(alpha=0.3)
    plt.tight_layout(); plt.show()'''))

# -- Anchor comparison --
new_pipeline_cells.append(make_md_cell('cell-md-compare',
    '## Step 9. Anchor Mode Comparison'))

new_pipeline_cells.append(make_code_cell('cell-compare-anchors', r'''import copy

def compare_anchor_modes(df_raw, base_config):
    """
    Run the full pipeline for echo-anchored, dialysis-180d, dialysis-365d.
    Returns (all_results_dict, comparison_df).
    """
    configs_to_run = {
        "echo_anchored": {"ANCHOR_MODE": "echo"},
        "dialysis_180d": {"ANCHOR_MODE": "dialysis", "ECHO_TO_DIALYSIS_WINDOW_DAYS": 180},
        "dialysis_365d": {"ANCHOR_MODE": "dialysis", "ECHO_TO_DIALYSIS_WINDOW_DAYS": 365},
    }

    all_results = {}
    for label, overrides in configs_to_run.items():
        cfg = copy.deepcopy(base_config)
        cfg.update(overrides)
        print(f"\n{'='*60}")
        print(f"  Running: {label} (anchor={cfg['ANCHOR_MODE']}, window={cfg.get('ECHO_TO_DIALYSIS_WINDOW_DAYS','N/A')}d)")
        print(f"{'='*60}")

        # Re-derive times for this anchor
        df_run = df_raw.copy()
        if cfg["ANCHOR_MODE"] == "echo":
            df_run["anchor_date"] = df_run[cfg["COL_ECHO"]]
            df_run["gap_anchor_to_death_days"] = df_run["time_echo_to_death_days"]
        else:
            df_run["anchor_date"] = df_run[cfg["COL_DIAL"]]
            df_run["gap_anchor_to_death_days"] = df_run["time_dial_to_death_days"]
        df_run["time_anchor_to_censor_days"] = (df_run["censor_date"] - df_run["anchor_date"]).dt.days
        df_run["time_to_event_or_censor_days"] = np.where(
            df_run["death_event"].eq(1),
            df_run["gap_anchor_to_death_days"],
            df_run["time_anchor_to_censor_days"])

        cohort, c_report = build_cohort(df_run, cfg)
        target_df, t_report = make_target(cohort, cfg)
        processed, _ = build_preprocessor(target_df, cfg)
        fsets = get_feature_sets(processed)
        feats = fsets["full_clinical"]
        X_run = processed[feats]
        y_run = processed["target_1yr_death"]

        en = run_elastic_net_bootstrap(X_run, y_run, cfg)
        top10 = list(en["stability_table"].head(10)["feature"])

        all_results[label] = {
            "n": len(X_run), "mortality_rate": round(float(y_run.mean()), 4),
            "cv_auc": en["cv_auc"], "top10": top10,
            "stability": en["stability_table"],
        }
        print(f"  N={len(X_run)}, AUC={en['cv_auc']:.4f}, Top: {', '.join(top10[:5])}")

    # Jaccard overlap
    labels = list(all_results.keys())
    rows = []
    for i, l1 in enumerate(labels):
        for l2 in labels[i+1:]:
            s1, s2 = set(all_results[l1]["top10"]), set(all_results[l2]["top10"])
            jacc = len(s1 & s2) / len(s1 | s2) if s1 | s2 else 0
            rows.append({
                "mode_1": l1, "mode_2": l2,
                "jaccard_top10": round(jacc, 3),
                "overlap": list(s1 & s2),
                "auc_1": all_results[l1]["cv_auc"],
                "auc_2": all_results[l2]["cv_auc"],
            })

    comp_df = pd.DataFrame(rows)
    try:
        comp_df.to_csv(f"{base_config['OUTPUT_DIR']}/anchor_comparison_report.csv", index=False)
    except Exception:
        pass
    return all_results, comp_df

# ── Execute ──
anchor_results, anchor_comparison = compare_anchor_modes(df, CONFIG)
print(f"\n{'='*60}")
print("  ANCHOR COMPARISON")
print(f"{'='*60}")
for label, r in anchor_results.items():
    print(f"  {label}: N={r['n']}, mortality={r['mortality_rate']:.1%}, AUC={r['cv_auc']:.4f}")
print()
display(anchor_comparison)'''))

# ═══════════════════════════════════════════════════════════════════════════════
# Step 4: Assemble final notebook
# ═══════════════════════════════════════════════════════════════════════════════
# Keep cells 0-39, replace 40-45 with new cells, keep 46-48
final_cells = cells[:40] + new_pipeline_cells + cells[46:]

nb['cells'] = final_cells

with open(NB_PATH, 'w') as f:
    json.dump(nb, f, ensure_ascii=False, indent=1)

print(f"Notebook restructured: {len(cells)} cells -> {len(final_cells)} cells")
print(f"Removed old cells 40-45 ({cells[40].get('id')} .. {cells[45].get('id')})")
print(f"Added {len(new_pipeline_cells)} new pipeline cells")

# Verify
for i, cell in enumerate(final_cells):
    cid = cell.get('id', 'N/A')
    ctype = cell['cell_type']
    src = ''.join(cell['source'])[:55].replace('\n', ' ')
    print(f'{i:3d} [{ctype:8s}] {cid:25s} | {src}')
