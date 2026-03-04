#!/usr/bin/env python3
"""
Restructure notebook to match the full 11-issue spec.
Replaces cells 40-58 (old pipeline) with new modular cells.
Keeps cells 0-39 (EDA) and 59-61 (viz/notes).
"""
import json, copy, textwrap

NB_PATH = "date_eda_echo_dialysis_(2).ipynb"

def make_code_cell(cell_id, source):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {"id": cell_id},
        "outputs": [],
        "source": [source],
    }

def make_md_cell(cell_id, source):
    return {
        "cell_type": "markdown",
        "metadata": {"id": cell_id},
        "source": [source],
    }

# ═══════════════════════════════════════════════════════════════════
# NEW CONFIG cell (replaces cell 8)
# ═══════════════════════════════════════════════════════════════════
CONFIG_SOURCE = textwrap.dedent(r'''
# ═══════════════════════════════════════════════════════════════════════════════
# PIPELINE CONFIGURATION — edit this cell to change anchor mode, windows, etc.
# ═══════════════════════════════════════════════════════════════════════════════
CONFIG = {
    # ── Anchor mode ──
    "ANCHOR_MODE": "echo",                # "echo" | "dialysis"

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
print(f"Early death:  {CONFIG['EXCLUDE_EARLY_DEATH_DAYS']}")
''').strip()

# ═══════════════════════════════════════════════════════════════════
# NEW cells 40+ (pipeline)
# ═══════════════════════════════════════════════════════════════════
NEW_CELLS = []

# ── 0: pip install ──────────────────────────────────────────────
NEW_CELLS.append(make_code_cell("cell-pip-install", textwrap.dedent(r'''
## ── Install extra libraries ───────────────────────────────────────
!pip install -q xgboost shap scikit-learn pyyaml
''').strip()))

# ── 1: markdown Issue 1 ──────────────────────────────────────────
NEW_CELLS.append(make_md_cell("cell-md-issue1",
    "## Issue 1 — Data Cleaning & Binary Variables"))

# ── 2: Issue 1 code — data cleaning + is_male, is_hd, n_comorbidities ─
NEW_CELLS.append(make_code_cell("cell-data-clean", textwrap.dedent(r'''
import json, os, warnings
import numpy as np, pandas as pd
warnings.filterwarnings('ignore')

os.makedirs(CONFIG["OUTPUT_DIR"], exist_ok=True)

# ── Binary variables ──────────────────────────────────────────────
df['is_male'] = (df['m/f'].astype(str).str.strip().str.lower()
                  .map({'m': 1, 'male': 1, 'f': 0, 'female': 0,
                        'זכר': 1, 'נקבה': 0}))
df['is_hd'] = (df['HD/PD'].astype(str).str.strip().str.upper()
                .map({'HD': 1, 'PD': 0}))

# ── Comorbidities ─────────────────────────────────────────────────
COMORBIDITY_COLS = [
    'MI_binary', 'CABG_binary', 'IHD_binary', 'AFIB_binary',
    'HTN_binary', 'Diabetes mellitus_binary', 'DYSLIPIDEMIA_binary',
    'COPD_binary', 'OncologicalDiagnosis',
]
for col in COMORBIDITY_COLS:
    if col in df.columns:
        # Ensure binary: if not already 0/1, convert
        if df[col].dtype == object:
            df[col] = df[col].notna().astype(int)
        else:
            df[col] = df[col].fillna(0).clip(0, 1).astype(int)

avail_comorbidities = [c for c in COMORBIDITY_COLS if c in df.columns]
df['n_comorbidities'] = df[avail_comorbidities].sum(axis=1)
print(f"n_comorbidities built from {len(avail_comorbidities)} columns: {avail_comorbidities}")

# ── Remove rows without patient number ────────────────────────────
n_before = len(df)
df = df.dropna(subset=[CONFIG["COL_PATIENT"]]).copy()
n_no_id = n_before - len(df)

# ── Remove duplicate patients (keep first) ────────────────────────
n_before2 = len(df)
df = df.drop_duplicates(subset=[CONFIG["COL_PATIENT"]], keep='first').copy()
n_dupes = n_before2 - len(df)

# ── Report ────────────────────────────────────────────────────────
load_report = {
    "n_raw": n_before + n_no_id,
    "n_removed_no_id": n_no_id,
    "n_removed_duplicates": n_dupes,
    "n_clean": len(df),
    "is_male_pct": round(float(df['is_male'].mean()), 3),
    "is_hd_pct": round(float(df['is_hd'].mean()), 3),
    "n_comorbidities_mean": round(float(df['n_comorbidities'].mean()), 2),
    "comorbidity_columns_used": avail_comorbidities,
}
with open(f"{CONFIG['OUTPUT_DIR']}/data_loaded_report.json", "w") as f:
    json.dump(load_report, f, indent=2, ensure_ascii=False)
print(json.dumps(load_report, indent=2))
''').strip()))

# ── 3: markdown Issue 2 ──────────────────────────────────────────
NEW_CELLS.append(make_md_cell("cell-md-issue2",
    "## Issue 2 — Cohort Building & Anchor\n\n`build_cohort(df, config)` — defines anchor_date and applies inclusion/exclusion filters."))

# ── 4: Issue 2 code — build_cohort ──────────────────────────────
NEW_CELLS.append(make_code_cell("cell-build-cohort", textwrap.dedent(r'''
def build_cohort(df, config):
    """
    Build analytic cohort based on ANCHOR_MODE.

    Echo mode:
      anchor_date = Echo_Date
      Require Echo_Date not missing
      Drop if DeathDate < Echo_Date

    Dialysis mode:
      anchor_date = Dialysis_Start_Date
      Require both dates present
      If ECHO_BEFORE_DIALYSIS_ONLY: require Echo_Date <= Dialysis_Start_Date
      Require gap_echo_to_dial_days <= ECHO_TO_DIALYSIS_WINDOW_DAYS
      Drop if DeathDate < Dialysis_Start_Date

    Returns (df_cohort, cohort_report_dict).
    """
    report = {"anchor_mode": config["ANCHOR_MODE"], "n_input": len(df), "exclusions": {}}
    cdf = df.copy()

    # Ensure gap column exists
    cdf["gap_echo_to_dial_days"] = (cdf[config["COL_DIAL"]] - cdf[config["COL_ECHO"]]).dt.days

    if config["ANCHOR_MODE"] == "echo":
        cdf["anchor_date"] = cdf[config["COL_ECHO"]]

        mask = cdf[config["COL_ECHO"]].isna()
        report["exclusions"]["missing_echo_date"] = int(mask.sum())
        cdf = cdf[~mask].copy()

        mask = cdf[config["COL_DEATH"]].notna() & (cdf[config["COL_DEATH"]] < cdf[config["COL_ECHO"]])
        report["exclusions"]["death_before_echo"] = int(mask.sum())
        cdf = cdf[~mask].copy()

    else:  # dialysis
        cdf["anchor_date"] = cdf[config["COL_DIAL"]]

        mask_dial = cdf[config["COL_DIAL"]].isna()
        mask_echo = cdf[config["COL_ECHO"]].isna()
        report["exclusions"]["missing_dialysis_date"] = int(mask_dial.sum())
        report["exclusions"]["missing_echo_date"] = int(mask_echo.sum())
        cdf = cdf[~mask_dial & ~mask_echo].copy()

        if config.get("ECHO_BEFORE_DIALYSIS_ONLY", True):
            mask = cdf["gap_echo_to_dial_days"] < 0
            report["exclusions"]["echo_after_dialysis"] = int(mask.sum())
            cdf = cdf[~mask].copy()

        window = config["ECHO_TO_DIALYSIS_WINDOW_DAYS"]
        mask = cdf["gap_echo_to_dial_days"] > window
        report["exclusions"][f"echo_outside_{window}d_window"] = int(mask.sum())
        cdf = cdf[~mask].copy()

        mask = cdf[config["COL_DEATH"]].notna() & (cdf[config["COL_DEATH"]] < cdf[config["COL_DIAL"]])
        report["exclusions"]["death_before_dialysis"] = int(mask.sum())
        cdf = cdf[~mask].copy()

    # Optional: exclude early deaths
    ed = config.get("EXCLUDE_EARLY_DEATH_DAYS")
    if ed is not None:
        time_to_death = (cdf[config["COL_DEATH"]] - cdf["anchor_date"]).dt.days
        mask = cdf[config["COL_DEATH"]].notna() & time_to_death.between(0, ed)
        report["exclusions"][f"early_death_le_{ed}d"] = int(mask.sum())
        cdf = cdf[~mask].copy()

    report["n_output"] = len(cdf)
    return cdf, report

# ── Execute ──────────────────────────────────────────────────────
df_cohort, cohort_report = build_cohort(df, CONFIG)
with open(f"{CONFIG['OUTPUT_DIR']}/cohort_report_{CONFIG['ANCHOR_MODE']}.json", "w") as f:
    json.dump(cohort_report, f, indent=2, ensure_ascii=False)
print(json.dumps(cohort_report, indent=2, ensure_ascii=False))
''').strip()))

# ── 5: markdown Issue 3 ──────────────────────────────────────────
NEW_CELLS.append(make_md_cell("cell-md-issue3",
    "## Issue 3 — Target Creation (1-year mortality)\n\n`make_target(df_cohort, config)`"))

# ── 6: Issue 3 code — make_target ────────────────────────────────
NEW_CELLS.append(make_code_cell("cell-make-target", textwrap.dedent(r'''
def make_target(df_cohort, config):
    """
    Create binary target: died within HORIZON_DAYS of anchor_date.

    If DeathDate exists:
      time_to_event = (DeathDate - anchor_date).days
      y = 1 if 0 <= time_to_event <= 365

    If no DeathDate:
      followup_days = (DATASET_END_DATE - anchor_date).days
      y = 0 if followup_days >= 365
      DROP if followup_days < 365 (insufficient follow-up)

    Returns (df_target, target_report_dict).
    """
    H = config["HORIZON_DAYS"]
    mdf = df_cohort.copy()

    # Compute dataset_end_date if not set
    dataset_end = config.get("DATASET_END_DATE")
    if dataset_end is None:
        dataset_end = pd.concat([
            mdf[config["COL_ECHO"]],
            mdf[config["COL_DIAL"]],
            mdf[config["COL_DEATH"]]
        ]).dropna().max()
        config["DATASET_END_DATE"] = dataset_end
    print(f"Dataset end date: {dataset_end}")

    def assign_target(row):
        anchor = row["anchor_date"]
        death = row[config["COL_DEATH"]]
        if pd.isna(anchor):
            return np.nan

        if pd.notna(death):
            tte = (death - anchor).days
            if tte < 0:
                return np.nan
            return 1 if tte <= H else 0
        else:
            followup = (dataset_end - anchor).days
            if followup >= H:
                return 0
            else:
                return np.nan  # insufficient follow-up

    mdf["target_1yr_death"] = mdf.apply(assign_target, axis=1)
    n_dropped = int(mdf["target_1yr_death"].isna().sum())
    mdf = mdf.dropna(subset=["target_1yr_death"]).copy()
    mdf["target_1yr_death"] = mdf["target_1yr_death"].astype(int)

    report = {
        "followup_mode": config["FOLLOWUP_MODE"],
        "dataset_end_date": str(dataset_end.date()) if hasattr(dataset_end, 'date') else str(dataset_end),
        "n_dropped_insufficient_followup": n_dropped,
        "n_final": len(mdf),
        "n_events": int(mdf["target_1yr_death"].sum()),
        "n_censored": int((mdf["target_1yr_death"] == 0).sum()),
        "event_rate": round(float(mdf["target_1yr_death"].mean()), 4),
    }
    return mdf, report

# ── Execute ──────────────────────────────────────────────────────
df_target, target_report = make_target(df_cohort, CONFIG)
with open(f"{CONFIG['OUTPUT_DIR']}/target_report_{CONFIG['ANCHOR_MODE']}.json", "w") as f:
    json.dump(target_report, f, indent=2, ensure_ascii=False)
print(json.dumps(target_report, indent=2, ensure_ascii=False))
''').strip()))

# ── 7: markdown Issue 4+5 ────────────────────────────────────────
NEW_CELLS.append(make_md_cell("cell-md-issue45",
    "## Issue 4+5 — Feature Definitions: Baseline & Echo Raw\n\nExact feature lists as specified in the protocol."))

# ── 8: Issue 4+5 code — feature definitions ──────────────────────
NEW_CELLS.append(make_code_cell("cell-feature-defs", textwrap.dedent(r'''
# ══════════════════════════════════════════════════════════════════
# FEATURE SET DEFINITIONS — hardcoded per protocol
# ══════════════════════════════════════════════════════════════════

BASELINE_SMALL = [
    "AgeAtFirstHFDate",
    "is_male",
    "is_hd",
    "hospitalization-count",
    "n_comorbidities",
    "albumin-numeric result",
    "hb-numeric result",
    "crp-numeric result",
    "creatinine-numeric result",
]

ECHO_RAW = [
    # LV
    "LV_EF",
    "LeftVentricleEndDiastolicDiameter",
    "LeftVentricleEndSystolicDiameter",
    "LeftVentricleInterventricularSeptumThickness",
    "LeftVentriclePosteriorWallThickness",
    "LeftVentricleEstimatedMassIndex",
    "LeftVentricleSystolicFunction_ord",
    "LeftVentricleCavitySize_ord",
    "LeftVentricleWallThickness_ord",
    "LeftVentricleScoreIndex",
    # Diastolic
    "MitralInflowPeakEWave",
    "TissueDopplerEVelositySeptal",
    "TissueDopplerEERatioSeptal",
    "TissueDopplerEVelosityLateral",
    "TissueDopplerEERatioLateral",
    # Derived diastolic
    "avg_E_e_ratio",
    "avg_e_prime",
    # Pulmonary pressure
    "EstimatedSysPAPressure",
    # RV (mandatory)
    "RVSize_ord",
    "RVSystolicFunction_ord",
    # Valves
    "MitralRegurgitation_ord",
    "TricuspidRegurgitation_ord",
    "AorticValveRegurgitation_ord",
    # LA
    "LACavitySize_ord",
]

CONSTRUCTS = [
    "lv_systolic_severity",
    "lvh_binary",
    "diastolic_burden",
    "phtn_severity",
    "right_heart_burden_score",
    "valve_burden_max",
]

# ── 5 model specifications ────────────────────────────────────────
MODEL_SPECS = {
    "M0": {"label": "Baseline-Small",          "features": BASELINE_SMALL},
    "M1A": {"label": "Echo-Raw",               "features": ECHO_RAW},
    "M1B": {"label": "Constructs",             "features": CONSTRUCTS},
    "M2A": {"label": "Baseline + Echo-Raw",    "features": BASELINE_SMALL + ECHO_RAW},
    "M2B": {"label": "Baseline + Constructs",  "features": BASELINE_SMALL + CONSTRUCTS},
}

for name, spec in MODEL_SPECS.items():
    print(f"  {name} ({spec['label']}): {len(spec['features'])} features defined")
''').strip()))

# ── 9: markdown Issue 5b + ordinal maps ──────────────────────────
NEW_CELLS.append(make_md_cell("cell-md-issue5b",
    "## Issue 5b — Ordinal Encoding & Preprocessing\n\n`build_preprocessor(df_in, config)` — ordinal encoding, derived variables."))

# ── 10: Issue 5b code — build_preprocessor ────────────────────────
NEW_CELLS.append(make_code_cell("cell-build-preprocessor", textwrap.dedent(r'''
def build_preprocessor(df_in, config):
    """
    Ordinal encoding for categorical echo features.
    Creates _ord columns + derived echo variables.
    Saves category_mapping.json.
    Returns (df_processed, ordinal_maps).
    """
    mdf = df_in.copy()

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

    # ── Derived echo variables ────────────────────────────────────
    if 'TissueDopplerEERatioSeptal' in mdf.columns and 'TissueDopplerEERatioLateral' in mdf.columns:
        mdf['avg_E_e_ratio'] = mdf[['TissueDopplerEERatioSeptal', 'TissueDopplerEERatioLateral']].mean(axis=1)
    if 'TissueDopplerEVelositySeptal' in mdf.columns and 'TissueDopplerEVelosityLateral' in mdf.columns:
        mdf['avg_e_prime'] = mdf[['TissueDopplerEVelositySeptal', 'TissueDopplerEVelosityLateral']].mean(axis=1)

    # Save category_mapping.json
    mapping_path = f"{config['OUTPUT_DIR']}/category_mapping.json"
    with open(mapping_path, "w") as f:
        json.dump({k: {str(kk): vv for kk, vv in v.items()}
                   for k, v in ORDINAL_MAPS.items()}, f, indent=2, ensure_ascii=False)
    print(f"\nSaved: {mapping_path}")

    return mdf, ORDINAL_MAPS

# ── Execute ──────────────────────────────────────────────────────
df_model, ordinal_maps = build_preprocessor(df_target, CONFIG)
print(f"Preprocessed: {len(df_model)} rows")
''').strip()))

# ── 11: markdown Issue 6 ─────────────────────────────────────────
NEW_CELLS.append(make_md_cell("cell-md-issue6",
    "## Issue 6 — Clinical Constructs\n\n6 composite scores derived from echo features."))

# ── 12: Issue 6 code — constructs ────────────────────────────────
NEW_CELLS.append(make_code_cell("cell-constructs", textwrap.dedent(r'''
def build_constructs(df):
    """
    Build 6 clinical constructs:
    1. lv_systolic_severity (0-3)
    2. lvh_binary (0/1)
    3. diastolic_burden (0-2)
    4. phtn_severity (0-3)
    5. right_heart_burden_score (0-5)
    6. valve_burden_max (0-3)
    """
    mdf = df.copy()

    # ── 1. lv_systolic_severity (0-3) ─────────────────────────────
    # Primary: from LV_EF; fallback: LeftVentricleSystolicFunction_ord
    if 'LV_EF' in mdf.columns:
        mdf['lv_systolic_severity'] = pd.cut(
            mdf['LV_EF'],
            bins=[-np.inf, 30, 40, 50, np.inf],
            labels=[3, 2, 1, 0]
        ).astype(float)
    if 'LeftVentricleSystolicFunction_ord' in mdf.columns:
        mask_missing = mdf['lv_systolic_severity'].isna() if 'lv_systolic_severity' in mdf.columns else pd.Series(True, index=mdf.index)
        fallback = mdf['LeftVentricleSystolicFunction_ord'].clip(0, 3).round()
        if 'lv_systolic_severity' not in mdf.columns:
            mdf['lv_systolic_severity'] = fallback
        else:
            mdf.loc[mask_missing, 'lv_systolic_severity'] = fallback[mask_missing]
    print(f"  lv_systolic_severity: {mdf['lv_systolic_severity'].notna().mean():.0%} available")

    # ── 2. lvh_binary (0/1) ───────────────────────────────────────
    # Based on LeftVentricleEstimatedMassIndex, Q4 threshold
    if 'LeftVentricleEstimatedMassIndex' in mdf.columns:
        q75 = mdf['LeftVentricleEstimatedMassIndex'].quantile(0.75)
        mdf['lvh_binary'] = (mdf['LeftVentricleEstimatedMassIndex'] >= q75).astype(float)
        mdf.loc[mdf['LeftVentricleEstimatedMassIndex'].isna(), 'lvh_binary'] = np.nan
        print(f"  lvh_binary: Q4 threshold = {q75:.1f}, prevalence = {mdf['lvh_binary'].mean():.0%}")
    else:
        mdf['lvh_binary'] = np.nan
        print("  lvh_binary: LeftVentricleEstimatedMassIndex not found, all NaN")

    # ── 3. diastolic_burden (0-2) ─────────────────────────────────
    # Based on avg_E_e_ratio and avg_e_prime
    mdf['diastolic_burden'] = np.nan
    if 'avg_E_e_ratio' in mdf.columns and 'avg_e_prime' in mdf.columns:
        # E/e' thresholds: <8 normal, 8-14 indeterminate, >14 elevated
        # e' thresholds: >10 normal, 7-10 borderline, <7 impaired
        ee_score = pd.cut(
            mdf['avg_E_e_ratio'],
            bins=[-np.inf, 8, 14, np.inf],
            labels=[0, 1, 2]
        ).astype(float)
        ep_score = pd.cut(
            mdf['avg_e_prime'],
            bins=[-np.inf, 7, 10, np.inf],
            labels=[2, 1, 0]
        ).astype(float)
        mdf['diastolic_burden'] = ((ee_score.fillna(0) + ep_score.fillna(0)) / 2).round().clip(0, 2)
        # Set back to NaN where both inputs missing
        both_missing = mdf['avg_E_e_ratio'].isna() & mdf['avg_e_prime'].isna()
        mdf.loc[both_missing, 'diastolic_burden'] = np.nan
    print(f"  diastolic_burden: {mdf['diastolic_burden'].notna().mean():.0%} available")

    # ── 4. phtn_severity (0-3) ────────────────────────────────────
    # Based on EstimatedSysPAPressure quantiles/thresholds
    if 'EstimatedSysPAPressure' in mdf.columns:
        mdf['phtn_severity'] = pd.cut(
            mdf['EstimatedSysPAPressure'],
            bins=[-np.inf, 35, 45, 60, np.inf],
            labels=[0, 1, 2, 3]
        ).astype(float)
        print(f"  phtn_severity: {mdf['phtn_severity'].notna().mean():.0%} available")
    else:
        mdf['phtn_severity'] = np.nan
        print("  phtn_severity: EstimatedSysPAPressure not found")

    # ── 5. right_heart_burden_score (0-5) ─────────────────────────
    # RVSize (0-2) + RVSystolicFunction (0-3)
    rv_size = mdf.get('RVSize_ord', pd.Series(np.nan, index=mdf.index)).clip(0, 2)
    rv_func = mdf.get('RVSystolicFunction_ord', pd.Series(np.nan, index=mdf.index)).clip(0, 3)
    mdf['right_heart_burden_score'] = rv_size.fillna(0) + rv_func.fillna(0)
    both_rv_missing = mdf.get('RVSize_ord', pd.Series(np.nan, index=mdf.index)).isna() & \
                      mdf.get('RVSystolicFunction_ord', pd.Series(np.nan, index=mdf.index)).isna()
    mdf.loc[both_rv_missing, 'right_heart_burden_score'] = np.nan
    print(f"  right_heart_burden_score: {mdf['right_heart_burden_score'].notna().mean():.0%} available")

    # ── 6. valve_burden_max (0-3) ─────────────────────────────────
    # max severity among MR, TR, AR (after rounding ordinals to 0-3)
    valve_cols = ['MitralRegurgitation_ord', 'TricuspidRegurgitation_ord', 'AorticValveRegurgitation_ord']
    avail_valves = [c for c in valve_cols if c in mdf.columns]
    if avail_valves:
        valve_df = mdf[avail_valves].clip(0, 3).round()
        mdf['valve_burden_max'] = valve_df.max(axis=1)
        all_valve_missing = valve_df.isna().all(axis=1)
        mdf.loc[all_valve_missing, 'valve_burden_max'] = np.nan
    else:
        mdf['valve_burden_max'] = np.nan
    print(f"  valve_burden_max: {mdf['valve_burden_max'].notna().mean():.0%} available")

    # ── Save constructs report ────────────────────────────────────
    construct_cols = ['lv_systolic_severity', 'lvh_binary', 'diastolic_burden',
                      'phtn_severity', 'right_heart_burden_score', 'valve_burden_max']
    report = []
    for c in construct_cols:
        report.append({
            'construct': c,
            'pct_available': round(float(mdf[c].notna().mean()), 3),
            'mean': round(float(mdf[c].mean()), 3) if mdf[c].notna().any() else None,
            'min': float(mdf[c].min()) if mdf[c].notna().any() else None,
            'max': float(mdf[c].max()) if mdf[c].notna().any() else None,
        })
    pd.DataFrame(report).to_csv(f"{CONFIG['OUTPUT_DIR']}/constructs_report.csv", index=False)
    print(f"\nSaved constructs_report.csv")

    return mdf

# ── Execute ──────────────────────────────────────────────────────
df_model = build_constructs(df_model)
print(f"\nConstructs added. Shape: {df_model.shape}")
''').strip()))

# ── 13: markdown Issue 7 ─────────────────────────────────────────
NEW_CELLS.append(make_md_cell("cell-md-issue7",
    "## Issue 7 — Preprocessing & Feature Reports\n\nMedian imputation + standardization (inside model pipeline). Feature availability report."))

# ── 14: Issue 7 code — feature validation + reports ───────────────
NEW_CELLS.append(make_code_cell("cell-preprocessing", textwrap.dedent(r'''
def validate_features(df, feature_list, name=""):
    """Validate feature list against available columns. Return available + report."""
    available = [f for f in feature_list if f in df.columns]
    missing = [f for f in feature_list if f not in df.columns]
    if missing:
        print(f"  WARNING [{name}]: {len(missing)} features not in data: {missing}")

    report_rows = []
    for f in available:
        report_rows.append({
            'feature': f,
            'dtype': str(df[f].dtype),
            'missing_rate': round(float(df[f].isna().mean()), 3),
            'n_unique': int(df[f].nunique()),
        })
    return available, pd.DataFrame(report_rows)

# ── Generate reports for each model spec ──────────────────────────
print("Feature availability per model:\n")
validated_specs = {}
all_feature_reports = []

for model_name, spec in MODEL_SPECS.items():
    avail, report_df = validate_features(df_model, spec['features'], model_name)
    validated_specs[model_name] = {**spec, 'features_valid': avail}
    report_df['model'] = model_name
    all_feature_reports.append(report_df)
    print(f"  {model_name} ({spec['label']}): {len(avail)}/{len(spec['features'])} available")

# Save combined report
combined_report = pd.concat(all_feature_reports, ignore_index=True)
combined_report.to_csv(f"{CONFIG['OUTPUT_DIR']}/preprocessing_report.csv", index=False)

# Save per-model reports
for model_name in MODEL_SPECS:
    mr = combined_report[combined_report['model'] == model_name].drop(columns=['model'])
    anchor = CONFIG['ANCHOR_MODE']
    mr.to_csv(f"{CONFIG['OUTPUT_DIR']}/features_report_{anchor}_{model_name}.csv", index=False)

print(f"\nSaved preprocessing_report.csv and per-model features_report_*.csv")

# ── Baseline features report ─────────────────────────────────────
baseline_report = combined_report[combined_report['model'] == 'M0'].drop(columns=['model'])
baseline_report.to_csv(f"{CONFIG['OUTPUT_DIR']}/baseline_features_report.csv", index=False)

# ── Echo features report ─────────────────────────────────────────
echo_report = combined_report[combined_report['model'] == 'M1A'].drop(columns=['model'])
echo_report.to_csv(f"{CONFIG['OUTPUT_DIR']}/echo_features_report.csv", index=False)

print(f"Saved baseline_features_report.csv, echo_features_report.csv")
''').strip()))

# ── 15: markdown Issue 8 ─────────────────────────────────────────
NEW_CELLS.append(make_md_cell("cell-md-issue8",
    "## Issue 8 — Elastic Net Logistic Regression + Bootstrap Stability\n\n`fit_elastic_net_logit(X, y)` with CV hyperparameter search and `bootstrap_stability(model_fn, X, y, B=200)`."))

# ── 16: Issue 8 code — Elastic Net ───────────────────────────────
NEW_CELLS.append(make_code_cell("cell-elastic-net", textwrap.dedent(r'''
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict, GridSearchCV
from sklearn.metrics import (roc_auc_score, average_precision_score, brier_score_loss,
                             f1_score, classification_report, roc_curve,
                             precision_recall_curve, confusion_matrix)
from sklearn.base import clone

def fit_elastic_net_logit(X, y, config):
    """
    Elastic Net Logistic Regression with CV for hyperparameter selection.
    Returns fitted pipeline + CV predictions.
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

    # CV predictions for unbiased evaluation
    y_prob = cross_val_predict(best_pipe, X, y, cv=cv, method="predict_proba")[:, 1]

    return best_pipe, y_prob, search.best_params_


def bootstrap_stability(model_fn, X, y, B=200, random_state=42):
    """
    Bootstrap stability analysis.
    For each bootstrap iteration:
      - Sample with replacement
      - Fit model
      - Record: whether each feature selected (beta != 0) and beta value

    Returns DataFrame with:
      feature, selection_freq, median_beta, mean_abs_beta, median_OR,
      sign_pos_rate, sign_neg_rate
    """
    n_features = X.shape[1]
    coef_matrix = np.zeros((B, n_features))
    feature_names = list(X.columns)

    for b in range(B):
        rng = np.random.RandomState(random_state + b)
        idx = rng.choice(len(X), len(X), replace=True)
        X_b, y_b = X.iloc[idx], y.iloc[idx]
        try:
            pipe_b = clone(model_fn)
            pipe_b.fit(X_b, y_b)
            coef_matrix[b] = pipe_b.named_steps["model"].coef_[0]
        except Exception:
            coef_matrix[b] = 0

    selected = np.abs(coef_matrix) > 1e-6
    pos_signs = coef_matrix > 1e-6
    neg_signs = coef_matrix < -1e-6

    stability = pd.DataFrame({
        "feature": feature_names,
        "selection_freq": selected.mean(axis=0),
        "median_beta": np.median(coef_matrix, axis=0),
        "mean_abs_beta": np.abs(coef_matrix).mean(axis=0),
        "median_OR": np.exp(np.median(coef_matrix, axis=0)),
        "sign_pos_rate": pos_signs.mean(axis=0),
        "sign_neg_rate": neg_signs.mean(axis=0),
    })
    stability = stability.sort_values("selection_freq", ascending=False).reset_index(drop=True)
    return stability

print("Elastic Net + Bootstrap functions defined.")
''').strip()))

# ── 17: markdown Issue 9 ─────────────────────────────────────────
NEW_CELLS.append(make_md_cell("cell-md-issue9",
    "## Issue 9 — XGBoost / Gradient Boosting + SHAP\n\n`fit_xgb(X, y)` with SHAP global importance."))

# ── 18: Issue 9 code — XGBoost ───────────────────────────────────
NEW_CELLS.append(make_code_cell("cell-xgboost", textwrap.dedent(r'''
import xgboost as xgb
import shap

def fit_xgb(X, y, config):
    """
    XGBoost classifier with CV evaluation.
    Returns fitted pipeline + CV predictions.
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

    # Fit on full data for SHAP
    pipe.fit(X, y)
    return pipe, y_prob


def compute_shap_importance(pipe, X):
    """Compute mean |SHAP| for each feature."""
    X_transformed = pd.DataFrame(
        pipe.named_steps["scaler"].transform(
            pipe.named_steps["imputer"].transform(X)),
        columns=X.columns)
    explainer = shap.TreeExplainer(pipe.named_steps["model"])
    shap_vals = explainer.shap_values(X_transformed)

    importance = pd.DataFrame({
        "feature": list(X.columns),
        "mean_abs_shap": np.abs(shap_vals).mean(axis=0),
    }).sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)

    return importance, shap_vals, X_transformed

print("XGBoost + SHAP functions defined.")
''').strip()))

# ── 19: markdown Issue 8+9+10 combined runner ────────────────────
NEW_CELLS.append(make_md_cell("cell-md-runner",
    "## Run All Models (M0–M2B)\n\nExecute Elastic Net + Bootstrap + XGBoost for each model specification."))

# ── 20: Runner code ──────────────────────────────────────────────
NEW_CELLS.append(make_code_cell("cell-runner", textwrap.dedent(r'''
import os
os.makedirs(CONFIG["OUTPUT_DIR"], exist_ok=True)
anchor = CONFIG["ANCHOR_MODE"]
y = df_model["target_1yr_death"]

all_results = {}
performance_rows = []

for model_name, spec in validated_specs.items():
    feats = spec['features_valid']
    if len(feats) == 0:
        print(f"\n  SKIP {model_name}: no valid features")
        continue

    X = df_model[feats].copy()
    print(f"\n{'='*60}")
    print(f"  {model_name}: {spec['label']} ({len(feats)} features, n={len(X)})")
    print(f"  Mortality rate: {y.mean():.1%}")
    print(f"{'='*60}")

    # ── Elastic Net ───────────────────────────────────────────────
    print("  [Elastic Net] fitting...")
    en_pipe, en_yprob, en_params = fit_elastic_net_logit(X, y, CONFIG)
    en_auc = roc_auc_score(y, en_yprob)
    en_brier = brier_score_loss(y, en_yprob)
    print(f"  CV AUC: {en_auc:.4f} | Brier: {en_brier:.4f} | params: {en_params}")

    # ── Bootstrap stability ───────────────────────────────────────
    print(f"  [Bootstrap] B={CONFIG['BOOTSTRAP_N']}...")
    stability = bootstrap_stability(en_pipe, X, y,
                                    B=CONFIG['BOOTSTRAP_N'],
                                    random_state=CONFIG['RANDOM_STATE'])
    stability.to_csv(
        f"{CONFIG['OUTPUT_DIR']}/feature_stability_logit_{anchor}_{model_name}.csv",
        index=False)
    print(f"  Top 5 stable: {list(stability.head(5)['feature'])}")

    # ── XGBoost ───────────────────────────────────────────────────
    print("  [XGBoost] fitting...")
    xgb_pipe, xgb_yprob = fit_xgb(X, y, CONFIG)
    xgb_auc = roc_auc_score(y, xgb_yprob)
    xgb_brier = brier_score_loss(y, xgb_yprob)
    print(f"  CV AUC: {xgb_auc:.4f} | Brier: {xgb_brier:.4f}")

    # ── SHAP ──────────────────────────────────────────────────────
    print("  [SHAP] computing...")
    shap_imp, shap_vals, X_display = compute_shap_importance(xgb_pipe, X)
    shap_imp.to_csv(
        f"{CONFIG['OUTPUT_DIR']}/feature_importance_xgb_{anchor}_{model_name}.csv",
        index=False)

    # ── Store results ─────────────────────────────────────────────
    all_results[model_name] = {
        "label": spec['label'],
        "features": feats,
        "en_pipe": en_pipe, "en_yprob": en_yprob, "en_auc": en_auc, "en_brier": en_brier,
        "stability": stability,
        "xgb_pipe": xgb_pipe, "xgb_yprob": xgb_yprob, "xgb_auc": xgb_auc, "xgb_brier": xgb_brier,
        "shap_importance": shap_imp, "shap_values": shap_vals, "X_display": X_display,
        "X": X, "y": y,
    }

    # ── Performance row ───────────────────────────────────────────
    # Bootstrap CI for AUC
    auc_boots = []
    for b in range(200):
        rng = np.random.RandomState(b)
        idx = rng.choice(len(y), len(y), replace=True)
        try:
            auc_boots.append(roc_auc_score(y.iloc[idx], en_yprob[idx]))
        except ValueError:
            pass
    auc_ci_low = np.percentile(auc_boots, 2.5) if auc_boots else np.nan
    auc_ci_high = np.percentile(auc_boots, 97.5) if auc_boots else np.nan

    performance_rows.append({
        "model_name": model_name,
        "model_type": "ElasticNet",
        "N": len(X),
        "n_features": len(feats),
        "event_rate": round(float(y.mean()), 4),
        "AUC_mean": round(en_auc, 4),
        "AUC_CI_low": round(auc_ci_low, 4),
        "AUC_CI_high": round(auc_ci_high, 4),
        "Brier": round(en_brier, 4),
    })
    performance_rows.append({
        "model_name": model_name,
        "model_type": "XGBoost",
        "N": len(X),
        "n_features": len(feats),
        "event_rate": round(float(y.mean()), 4),
        "AUC_mean": round(xgb_auc, 4),
        "AUC_CI_low": np.nan,
        "AUC_CI_high": np.nan,
        "Brier": round(xgb_brier, 4),
    })

# ── Performance table ─────────────────────────────────────────────
perf_df = pd.DataFrame(performance_rows)
perf_df.to_csv(f"{CONFIG['OUTPUT_DIR']}/performance_table_{anchor}.csv", index=False)
print(f"\n{'='*60}")
print("  PERFORMANCE SUMMARY")
print(f"{'='*60}")
display(perf_df)
''').strip()))

# ── 21: markdown Issue 10 ────────────────────────────────────────
NEW_CELLS.append(make_md_cell("cell-md-issue10",
    "## Issue 10 — Incremental Value (ΔAUC)\n\nCompute ΔAUC of M2A/M2B vs M0 (baseline)."))

# ── 22: Issue 10 code — incremental value ────────────────────────
NEW_CELLS.append(make_code_cell("cell-incremental", textwrap.dedent(r'''
# ── Incremental value: ΔAUC over M0 baseline ─────────────────────
anchor = CONFIG["ANCHOR_MODE"]
incr_rows = []

if "M0" in all_results:
    m0_auc_en = all_results["M0"]["en_auc"]
    m0_auc_xgb = all_results["M0"]["xgb_auc"]

    for compare_name in ["M2A", "M2B"]:
        if compare_name in all_results:
            r = all_results[compare_name]
            incr_rows.append({
                "comparison": f"{compare_name} vs M0",
                "model_type": "ElasticNet",
                "AUC_M0": round(m0_auc_en, 4),
                f"AUC_{compare_name}": round(r["en_auc"], 4),
                "delta_AUC": round(r["en_auc"] - m0_auc_en, 4),
            })
            incr_rows.append({
                "comparison": f"{compare_name} vs M0",
                "model_type": "XGBoost",
                "AUC_M0": round(m0_auc_xgb, 4),
                f"AUC_{compare_name}": round(r["xgb_auc"], 4),
                "delta_AUC": round(r["xgb_auc"] - m0_auc_xgb, 4),
            })

incr_df = pd.DataFrame(incr_rows)
incr_df.to_csv(f"{CONFIG['OUTPUT_DIR']}/incremental_value_{anchor}.csv", index=False)
print("Incremental value (ΔAUC):")
display(incr_df)
''').strip()))

# ── 23: markdown Dashboard ───────────────────────────────────────
NEW_CELLS.append(make_md_cell("cell-md-dashboard",
    "## Results Dashboard\n\nROC, PR, bootstrap stability, SHAP, calibration — per model."))

# ── 24: Dashboard code ───────────────────────────────────────────
NEW_CELLS.append(make_code_cell("cell-dashboard", textwrap.dedent(r'''
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.calibration import calibration_curve

for model_name, r in all_results.items():
    X, y = r["X"], r["y"]
    en_yprob, xgb_yprob = r["en_yprob"], r["xgb_yprob"]

    print(f"\n{'#'*70}")
    print(f"  {model_name}: {r['label']}")
    print(f"{'#'*70}")

    # ── ROC + PR ──────────────────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))
    for name, yp, color in [
        (f"EN (AUC={r['en_auc']:.3f})", en_yprob, "#2980b9"),
        (f"XGB (AUC={r['xgb_auc']:.3f})", xgb_yprob, "#e74c3c"),
    ]:
        fpr, tpr, _ = roc_curve(y, yp)
        axes[0].plot(fpr, tpr, label=name, color=color, linewidth=2)
        prec, rec, _ = precision_recall_curve(y, yp)
        ap = average_precision_score(y, yp)
        axes[1].plot(rec, prec, label=f"{name.split('(')[0]}(AP={ap:.3f})", color=color, linewidth=2)
    axes[0].plot([0,1],[0,1],'k--',alpha=0.3)
    axes[0].set_title(f"ROC — {model_name}", fontsize=14)
    axes[0].set_xlabel("FPR"); axes[0].set_ylabel("TPR")
    axes[0].legend(fontsize=10); axes[0].grid(alpha=0.3)
    axes[1].set_title(f"Precision-Recall — {model_name}", fontsize=14)
    axes[1].set_xlabel("Recall"); axes[1].set_ylabel("Precision")
    axes[1].legend(fontsize=10); axes[1].grid(alpha=0.3)
    plt.tight_layout(); plt.show()

    # ── Bootstrap stability (top 15) ─────────────────────────────
    stab = r["stability"].head(15).sort_values("selection_freq")
    fig, ax = plt.subplots(figsize=(10, 7))
    colors = ["#e74c3c" if sr < 0.5 else "#2980b9"
              for sr in stab["sign_neg_rate"]]
    ax.barh(stab["feature"], stab["selection_freq"], color=colors, edgecolor="black", linewidth=0.3)
    ax.set_xlabel("Bootstrap Selection Frequency", fontsize=12)
    ax.set_title(f"Feature Stability — {model_name} (EN)\nRed=Negative, Blue=Positive", fontsize=14)
    ax.axvline(0.5, color="gray", linestyle="--", alpha=0.5)
    plt.tight_layout(); plt.show()

    # ── SHAP summary ─────────────────────────────────────────────
    try:
        fig, ax = plt.subplots(figsize=(10, 10))
        shap.summary_plot(r["shap_values"], r["X_display"], max_display=20, show=False)
        plt.title(f"SHAP — {model_name} (XGBoost)", fontsize=14)
        plt.tight_layout(); plt.show()
    except Exception as e:
        print(f"  SHAP plot error: {e}")

    # ── Calibration ──────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(8, 6))
    for name, yp, color in [("EN", en_yprob, "#2980b9"), ("XGB", xgb_yprob, "#e74c3c")]:
        prob_true, prob_pred = calibration_curve(y, yp, n_bins=10, strategy="uniform")
        ax.plot(prob_pred, prob_true, "o-", linewidth=2, label=name, color=color)
    ax.plot([0,1],[0,1],"k--",alpha=0.3)
    ax.set_xlabel("Mean predicted probability"); ax.set_ylabel("Fraction of positives")
    ax.set_title(f"Calibration — {model_name}", fontsize=14)
    ax.legend(); ax.grid(alpha=0.3)
    plt.tight_layout(); plt.show()
''').strip()))

# ── 25: markdown Issue 11 ────────────────────────────────────────
NEW_CELLS.append(make_md_cell("cell-md-issue11",
    "## Issue 11 — Quality Checks\n\nVerify RV features, no leakage, event rate, missing rates."))

# ── 26: Issue 11 code — quality checks ───────────────────────────
NEW_CELLS.append(make_code_cell("cell-quality", textwrap.dedent(r'''
print("=" * 60)
print("  QUALITY CHECKS")
print("=" * 60)

checks_passed = 0
checks_total = 0

# 1. RV features in reports
checks_total += 1
rv_in_echo = any('RVSize' in f or 'RVSystolic' in f
                  for spec in validated_specs.values()
                  for f in spec['features_valid'])
if rv_in_echo:
    print("  [PASS] RV features present in model features")
    checks_passed += 1
else:
    print("  [FAIL] RV features NOT found in any model")

# 2. No leakage: Echo after dialysis (in dialysis mode)
checks_total += 1
if CONFIG["ANCHOR_MODE"] == "dialysis":
    n_leak = (df_model["gap_echo_to_dial_days"] < 0).sum()
    if n_leak == 0:
        print(f"  [PASS] No echo-after-dialysis leakage (n={n_leak})")
        checks_passed += 1
    else:
        print(f"  [FAIL] Echo after dialysis: {n_leak} cases!")
else:
    print(f"  [PASS] Echo anchor mode — no dialysis leakage concern")
    checks_passed += 1

# 3. Event rate sanity
checks_total += 1
event_rate = df_model["target_1yr_death"].mean()
if 0.05 < event_rate < 0.90:
    print(f"  [PASS] Event rate = {event_rate:.1%} (reasonable)")
    checks_passed += 1
else:
    print(f"  [WARN] Event rate = {event_rate:.1%} (extreme)")

# 4. No features with >70% missing
checks_total += 1
high_missing = []
for model_name, spec in validated_specs.items():
    for f in spec['features_valid']:
        miss_rate = df_model[f].isna().mean()
        if miss_rate > 0.70:
            high_missing.append((model_name, f, miss_rate))
if not high_missing:
    print(f"  [PASS] No features with >70% missing")
    checks_passed += 1
else:
    print(f"  [WARN] Features with >70% missing:")
    for mn, f, mr in high_missing:
        print(f"    {mn}: {f} = {mr:.0%}")

# 5. All 5 models ran
checks_total += 1
expected_models = {"M0", "M1A", "M1B", "M2A", "M2B"}
ran_models = set(all_results.keys())
if expected_models <= ran_models:
    print(f"  [PASS] All 5 models ran: {sorted(ran_models)}")
    checks_passed += 1
else:
    missing_models = expected_models - ran_models
    print(f"  [FAIL] Missing models: {missing_models}")

# 6. Bootstrap tables exist
checks_total += 1
anchor = CONFIG["ANCHOR_MODE"]
stability_files = [f"feature_stability_logit_{anchor}_{m}.csv" for m in expected_models]
all_exist = all(os.path.exists(f"{CONFIG['OUTPUT_DIR']}/{sf}") for sf in stability_files)
if all_exist:
    print(f"  [PASS] All bootstrap stability files saved")
    checks_passed += 1
else:
    print(f"  [WARN] Some bootstrap stability files missing")

# 7. Incremental value computed
checks_total += 1
if os.path.exists(f"{CONFIG['OUTPUT_DIR']}/incremental_value_{anchor}.csv"):
    print(f"  [PASS] Incremental value file saved")
    checks_passed += 1
else:
    print(f"  [FAIL] Incremental value file missing")

print(f"\n  Result: {checks_passed}/{checks_total} checks passed")
print("=" * 60)

# ── Summary of output files ──────────────────────────────────────
print(f"\nOutput files in {CONFIG['OUTPUT_DIR']}:")
for f in sorted(os.listdir(CONFIG['OUTPUT_DIR'])):
    size = os.path.getsize(f"{CONFIG['OUTPUT_DIR']}/{f}")
    print(f"  {f} ({size:,} bytes)")
''').strip()))

# ── 27: markdown Anchor comparison ────────────────────────────────
NEW_CELLS.append(make_md_cell("cell-md-compare",
    "## Anchor Mode Comparison\n\nRe-run the full pipeline with `ANCHOR_MODE='dialysis'` for comparison (if currently in echo mode, and vice versa)."))

# ── 28: Anchor comparison code ────────────────────────────────────
NEW_CELLS.append(make_code_cell("cell-compare-anchors", textwrap.dedent(r'''
import copy

def compare_anchor_modes(df_raw, base_config):
    """
    Run the full pipeline for echo-anchored and dialysis-anchored (180d + 365d).
    Returns (all_anchor_results, comparison_df).
    """
    configs_to_run = {
        "echo_anchored": {"ANCHOR_MODE": "echo"},
        "dialysis_180d": {"ANCHOR_MODE": "dialysis", "ECHO_TO_DIALYSIS_WINDOW_DAYS": 180,
                          "ECHO_BEFORE_DIALYSIS_ONLY": True},
        "dialysis_365d": {"ANCHOR_MODE": "dialysis", "ECHO_TO_DIALYSIS_WINDOW_DAYS": 365,
                          "ECHO_BEFORE_DIALYSIS_ONLY": True},
    }

    anchor_results = {}
    for label, overrides in configs_to_run.items():
        cfg = copy.deepcopy(base_config)
        cfg.update(overrides)
        cfg["DATASET_END_DATE"] = None  # recompute
        print(f"\n{'='*60}")
        print(f"  Running: {label}")
        print(f"{'='*60}")

        try:
            cohort, _ = build_cohort(df_raw, cfg)
            target_df, _ = make_target(cohort, cfg)
            processed, _ = build_preprocessor(target_df, cfg)
            processed = build_constructs(processed)

            # Run M2A (Baseline + Echo-Raw) as representative
            m2a_feats = [f for f in (BASELINE_SMALL + ECHO_RAW) if f in processed.columns]
            X_run = processed[m2a_feats]
            y_run = processed["target_1yr_death"]

            en_pipe, en_yprob, _ = fit_elastic_net_logit(X_run, y_run, cfg)
            en_auc = roc_auc_score(y_run, en_yprob)
            stab = bootstrap_stability(en_pipe, X_run, y_run, B=100, random_state=42)
            top10 = list(stab.head(10)["feature"])

            anchor_results[label] = {
                "n": len(X_run), "mortality_rate": round(float(y_run.mean()), 4),
                "cv_auc": round(en_auc, 4), "top10": top10,
            }
            print(f"  N={len(X_run)}, AUC={en_auc:.4f}, Top: {', '.join(top10[:5])}")
        except Exception as e:
            print(f"  ERROR: {e}")
            anchor_results[label] = {"n": 0, "cv_auc": 0, "error": str(e)}

    # Jaccard overlap
    labels = list(anchor_results.keys())
    rows = []
    for i, l1 in enumerate(labels):
        for l2 in labels[i+1:]:
            t1 = set(anchor_results[l1].get("top10", []))
            t2 = set(anchor_results[l2].get("top10", []))
            jacc = len(t1 & t2) / len(t1 | t2) if t1 | t2 else 0
            rows.append({
                "mode_1": l1, "mode_2": l2,
                "jaccard_top10": round(jacc, 3),
                "overlap_features": list(t1 & t2),
                "auc_1": anchor_results[l1].get("cv_auc", 0),
                "auc_2": anchor_results[l2].get("cv_auc", 0),
            })

    comp_df = pd.DataFrame(rows)
    try:
        comp_df.to_csv(f"{base_config['OUTPUT_DIR']}/anchor_comparison_report.csv", index=False)
    except Exception:
        pass
    return anchor_results, comp_df

# ── Execute ──────────────────────────────────────────────────────
anchor_results, anchor_comparison = compare_anchor_modes(df, CONFIG)
print(f"\n{'='*60}")
print("  ANCHOR COMPARISON")
print(f"{'='*60}")
for label, r in anchor_results.items():
    print(f"  {label}: N={r.get('n',0)}, mortality={r.get('mortality_rate','?')}, AUC={r.get('cv_auc','?')}")
print()
display(anchor_comparison)
''').strip()))

# ═══════════════════════════════════════════════════════════════════
# APPLY CHANGES
# ═══════════════════════════════════════════════════════════════════

with open(NB_PATH, "r") as f:
    nb = json.load(f)

cells = nb["cells"]

# Replace cell 8 (CONFIG)
cells[8]["source"] = [CONFIG_SOURCE]
cells[8]["outputs"] = []

# Remove old cells 40-58 and insert new ones
# Keep cells 0-39 and 59-61
keep_before = cells[:40]
keep_after = cells[59:]

nb["cells"] = keep_before + NEW_CELLS + keep_after

# Print summary
print(f"Notebook restructured: {len(cells)} cells -> {len(nb['cells'])} cells")
print(f"Removed old cells 40-58 (19 cells)")
print(f"Added {len(NEW_CELLS)} new cells")
print()
for i, c in enumerate(nb["cells"]):
    ctype = c["cell_type"]
    cid = c.get("metadata", {}).get("id", "?")
    src = "".join(c.get("source", []))[:60].replace("\n", " ")
    print(f"  {i:2d} [{ctype:8s}] {cid:30s} | {src}")

# Save
with open(NB_PATH, "w") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)

print(f"\nSaved: {NB_PATH}")
