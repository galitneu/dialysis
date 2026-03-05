#!/usr/bin/env python3
"""
Add Stable Cardiac Predictors section to notebook.
Inserts after cell 66 (quality checks), before cell 67 (anchor comparison).
"""
import json, textwrap

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

NEW_CELLS = []

# ── Markdown header ──────────────────────────────────────────────
NEW_CELLS.append(make_md_cell("cell-md-stable-predictors", textwrap.dedent(r'''
## Stable Cardiac Predictors

**Goal:** Identify echo measures that are stable predictors of 1-year mortality
beyond the demographic+lab baseline.

Pipeline:
1. Fit Elastic Net on `BASELINE_SMALL + ECHO_RAW` (no constructs)
2. Bootstrap stability (B=200): selection_freq, median_OR, sign consistency
3. XGBoost + SHAP on same feature set
4. Rank echo features only — flag stable predictors
5. Sensitivity: repeat for 365-day echo-to-dialysis window
6. Compare which predictors remain stable across both windows
''').strip()))

# ── Main analysis cell ───────────────────────────────────────────
NEW_CELLS.append(make_code_cell("cell-stable-predictors", textwrap.dedent(r'''
# ══════════════════════════════════════════════════════════════════
# STABLE CARDIAC PREDICTORS — single feature set analysis
# ══════════════════════════════════════════════════════════════════
import copy

def run_stable_predictor_analysis(df_raw, config, label="default"):
    """
    Run the full stable-predictor pipeline:
      1. build_cohort + make_target + build_preprocessor
      2. Elastic Net on BASELINE_SMALL + ECHO_RAW
      3. Bootstrap stability (B=200)
      4. XGBoost + SHAP
      5. Rank echo features + flag stable predictors

    Returns: (stable_df, en_auc, xgb_auc, df_model_local)
    """
    cfg = copy.deepcopy(config)
    cfg["DATASET_END_DATE"] = None  # recompute

    # ── Cohort + target ──────────────────────────────────────────
    cohort, c_report = build_cohort(df_raw, cfg)
    target_df, t_report = make_target(cohort, cfg)
    processed, _ = build_preprocessor(target_df, cfg)

    print(f"  [{label}] Cohort: {c_report['n_input']} -> {c_report['n_output']}")
    print(f"  [{label}] Target: N={t_report['n_final']}, "
          f"events={t_report['n_events']}, rate={t_report['event_rate']:.1%}")

    # ── Feature set: BASELINE_SMALL + ECHO_RAW (no constructs) ──
    all_features = BASELINE_SMALL + ECHO_RAW
    available = [f for f in all_features if f in processed.columns]
    missing = [f for f in all_features if f not in processed.columns]
    if missing:
        print(f"  [{label}] Missing features (skipped): {missing}")
    print(f"  [{label}] Using {len(available)} features")

    X = processed[available].copy()
    y = processed["target_1yr_death"].copy()

    # ── 1. Elastic Net with CV ───────────────────────────────────
    print(f"  [{label}] Fitting Elastic Net...")
    en_pipe, en_yprob, en_params = fit_elastic_net_logit(X, y, cfg)
    en_auc = roc_auc_score(y, en_yprob)
    print(f"  [{label}] EN CV AUC: {en_auc:.4f} | params: {en_params}")

    # ── 2. Bootstrap stability (B=200) ───────────────────────────
    print(f"  [{label}] Bootstrap stability (B={cfg['BOOTSTRAP_N']})...")
    stability = bootstrap_stability(en_pipe, X, y,
                                     B=cfg['BOOTSTRAP_N'],
                                     random_state=cfg['RANDOM_STATE'])

    # ── 3. XGBoost + SHAP ────────────────────────────────────────
    print(f"  [{label}] Fitting XGBoost + SHAP...")
    xgb_pipe, xgb_yprob = fit_xgb(X, y, cfg)
    xgb_auc = roc_auc_score(y, xgb_yprob)
    shap_imp, _, _ = compute_shap_importance(xgb_pipe, X)
    print(f"  [{label}] XGB CV AUC: {xgb_auc:.4f}")

    # ── 4. Build echo-only ranking table ─────────────────────────
    # Merge stability + SHAP
    merged = stability.merge(shap_imp, on="feature", how="left")

    # Add missing rate
    merged["missing_rate"] = merged["feature"].apply(
        lambda f: round(float(X[f].isna().mean()), 3) if f in X.columns else np.nan)

    # Filter to echo features only (not in BASELINE_SMALL)
    baseline_set = set(BASELINE_SMALL)
    echo_only = merged[~merged["feature"].isin(baseline_set)].copy()

    # ── 5. Flag stable predictors ────────────────────────────────
    # Criteria:
    #   selection_frequency >= 0.60
    #   sign_pos_rate >= 0.80 OR <= 0.20 (consistent direction)
    #   mean_abs_shap in top 20
    top20_shap = set(shap_imp.head(20)["feature"])

    echo_only["is_stable_predictor"] = (
        (echo_only["selection_freq"] >= 0.60) &
        ((echo_only["sign_pos_rate"] >= 0.80) | (echo_only["sign_pos_rate"] <= 0.20)) &
        (echo_only["feature"].isin(top20_shap))
    ).astype(int)

    # Sort by selection_freq descending
    echo_only = echo_only.sort_values("selection_freq", ascending=False).reset_index(drop=True)

    # Select output columns
    output_cols = [
        "feature", "missing_rate", "selection_freq",
        "median_OR", "sign_pos_rate", "mean_abs_beta",
        "mean_abs_shap", "is_stable_predictor",
    ]
    # Only keep columns that exist
    output_cols = [c for c in output_cols if c in echo_only.columns]
    result = echo_only[output_cols].copy()

    n_stable = int(result["is_stable_predictor"].sum())
    stable_names = list(result[result["is_stable_predictor"] == 1]["feature"])
    print(f"\n  [{label}] Stable cardiac predictors ({n_stable}):")
    for name in stable_names:
        row = result[result["feature"] == name].iloc[0]
        print(f"    {name}: sel={row['selection_freq']:.0%}, "
              f"OR={row['median_OR']:.2f}, "
              f"sign_pos={row['sign_pos_rate']:.0%}, "
              f"SHAP={row.get('mean_abs_shap', 0):.4f}")

    return result, en_auc, xgb_auc, processed


# ══════════════════════════════════════════════════════════════════
# RUN 1: Primary window (CONFIG as-is, typically 180d)
# ══════════════════════════════════════════════════════════════════
print("=" * 60)
print("  STABLE PREDICTOR ANALYSIS — Primary window")
print("=" * 60)

stable_180, en_auc_180, xgb_auc_180, _ = run_stable_predictor_analysis(
    df, CONFIG, label=f"window_{CONFIG['ECHO_TO_DIALYSIS_WINDOW_DAYS']}d")

# Save
anchor = CONFIG["ANCHOR_MODE"]
stable_180.to_csv(f"{CONFIG['OUTPUT_DIR']}/stable_cardiac_predictors.csv", index=False)
print(f"\nSaved: stable_cardiac_predictors.csv")
print(f"EN AUC = {en_auc_180:.4f}, XGB AUC = {xgb_auc_180:.4f}")
display(stable_180)
''').strip()))

# ── Sensitivity: 365-day window ──────────────────────────────────
NEW_CELLS.append(make_md_cell("cell-md-stable-365",
    "### Sensitivity: 365-day echo-to-dialysis window"))

NEW_CELLS.append(make_code_cell("cell-stable-365", textwrap.dedent(r'''
# ══════════════════════════════════════════════════════════════════
# RUN 2: Sensitivity — 365-day window
# ══════════════════════════════════════════════════════════════════
print("=" * 60)
print("  STABLE PREDICTOR ANALYSIS — 365-day window sensitivity")
print("=" * 60)

config_365 = copy.deepcopy(CONFIG)
config_365["ECHO_TO_DIALYSIS_WINDOW_DAYS"] = 365

stable_365, en_auc_365, xgb_auc_365, _ = run_stable_predictor_analysis(
    df, config_365, label="window_365d")

stable_365.to_csv(f"{CONFIG['OUTPUT_DIR']}/stable_cardiac_predictors_365.csv", index=False)
print(f"\nSaved: stable_cardiac_predictors_365.csv")
print(f"EN AUC = {en_auc_365:.4f}, XGB AUC = {xgb_auc_365:.4f}")
display(stable_365)
''').strip()))

# ── Overlap comparison ───────────────────────────────────────────
NEW_CELLS.append(make_md_cell("cell-md-stable-overlap",
    "### Predictor Overlap: 180d vs 365d window"))

NEW_CELLS.append(make_code_cell("cell-stable-overlap", textwrap.dedent(r'''
# ══════════════════════════════════════════════════════════════════
# OVERLAP COMPARISON — which predictors stay stable in both windows?
# ══════════════════════════════════════════════════════════════════

# Get stable sets
stable_set_180 = set(stable_180[stable_180["is_stable_predictor"] == 1]["feature"])
stable_set_365 = set(stable_365[stable_365["is_stable_predictor"] == 1]["feature"])

# Build overlap table — all echo features
all_echo_features = sorted(
    set(stable_180["feature"]).union(set(stable_365["feature"]))
)

overlap_rows = []
for feat in all_echo_features:
    overlap_rows.append({
        "feature": feat,
        "stable_180": int(feat in stable_set_180),
        "stable_365": int(feat in stable_set_365),
        "stable_both": int(feat in stable_set_180 and feat in stable_set_365),
    })

overlap_df = pd.DataFrame(overlap_rows)
# Sort: stable_both first, then stable in either window
overlap_df = overlap_df.sort_values(
    ["stable_both", "stable_180", "stable_365"],
    ascending=False
).reset_index(drop=True)

overlap_df.to_csv(f"{CONFIG['OUTPUT_DIR']}/stable_predictor_overlap.csv", index=False)

# Summary
n_both = overlap_df["stable_both"].sum()
n_only_180 = ((overlap_df["stable_180"] == 1) & (overlap_df["stable_365"] == 0)).sum()
n_only_365 = ((overlap_df["stable_180"] == 0) & (overlap_df["stable_365"] == 1)).sum()

print(f"Stable in BOTH windows:   {n_both}")
print(f"Stable in 180d only:      {n_only_180}")
print(f"Stable in 365d only:      {n_only_365}")
print(f"\nFeatures stable in both windows:")
both_stable = overlap_df[overlap_df["stable_both"] == 1]["feature"].tolist()
for f in both_stable:
    print(f"  → {f}")

print(f"\nSaved: stable_predictor_overlap.csv")
display(overlap_df)

# ── Performance comparison ────────────────────────────────────────
print(f"\nPerformance comparison:")
primary_window = CONFIG['ECHO_TO_DIALYSIS_WINDOW_DAYS']
print(f"  {primary_window}d window: EN AUC={en_auc_180:.4f}, XGB AUC={xgb_auc_180:.4f}")
print(f"  365d window: EN AUC={en_auc_365:.4f}, XGB AUC={xgb_auc_365:.4f}")
''').strip()))

# ══════════════════════════════════════════════════════════════════
# APPLY
# ══════════════════════════════════════════════════════════════════
with open(NB_PATH, "r") as f:
    nb = json.load(f)

cells = nb["cells"]

# Insert after cell 66 (quality checks), before cell 67 (anchor comparison)
INSERT_AT = 67
nb["cells"] = cells[:INSERT_AT] + NEW_CELLS + cells[INSERT_AT:]

print(f"Inserted {len(NEW_CELLS)} cells at position {INSERT_AT}")
print(f"Total cells: {len(nb['cells'])}")

# Print new cells
for i in range(INSERT_AT, INSERT_AT + len(NEW_CELLS)):
    c = nb["cells"][i]
    cid = c.get("metadata", {}).get("id", "?")
    src = "".join(c.get("source", []))[:70].replace("\n", " ")
    print(f"  {i} [{c['cell_type']:8s}] {cid:35s} | {src}")

with open(NB_PATH, "w") as f:
    json.dump(nb, f, indent=1, ensure_ascii=False)
print(f"\nSaved: {NB_PATH}")
