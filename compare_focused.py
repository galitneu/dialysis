"""Drill into the comparison: separate continuous, no-missing-cat, and missing-cat."""

import numpy as np
import pandas as pd

LOCAL = pd.read_csv("/home/user/dialysis/outputs/params/stage3_local_run/stage3_univariable_effect_estimates.csv")
DRIVE = pd.read_csv("/home/user/dialysis/outputs/params/stage3_drive_existing/stage3_univariable_effect_estimates.csv")

key = ["outcome_family", "variable", "term"]
m = LOCAL.merge(DRIVE, on=key, how="inner", suffixes=("_local", "_drive"))

# Identify variables WITH missing in main-analysis dataset
main = pd.read_csv("/home/user/dialysis/outputs/params/stage1/stage1_main_analysis.csv")
missing_counts = main.isna().sum()
vars_with_missing = set(missing_counts[missing_counts > 0].index)
print("Predictors with missing in main-analysis:")
for v, n in missing_counts[missing_counts > 0].items():
    print(f"  {v}: {n} missing")

# Group rows
m["pred_has_missing"] = m["variable"].isin(vars_with_missing)
m["is_continuous"] = m["variable_type_local"] == "continuous"

print("\n" + "=" * 70)
print("AGREEMENT BY VARIABLE TYPE / MISSINGNESS")
print("=" * 70)

groups = [
    ("continuous (no missing)", m[m.is_continuous & ~m.pred_has_missing]),
    ("continuous (with missing)", m[m.is_continuous & m.pred_has_missing]),
    ("categorical (no missing)", m[~m.is_continuous & ~m.pred_has_missing]),
    ("categorical (with missing)", m[~m.is_continuous & m.pred_has_missing]),
]
for label, sub in groups:
    if sub.empty:
        continue
    est_diff = (sub.estimate_local - sub.estimate_drive).abs()
    p_diff = (sub.p_value_local - sub.p_value_drive).abs()
    n_diff = (sub.n_model_local - sub.n_model_drive).abs()
    print(f"\n{label}: n_rows={len(sub)}")
    print(f"  estimate: max_abs_diff={est_diff.max():.6g}, mean={est_diff.mean():.6g}")
    print(f"  p_value : max_abs_diff={p_diff.max():.6g}, mean={p_diff.mean():.6g}")
    print(f"  n_model : max_abs_diff={int(n_diff.max())}, mean={n_diff.mean():.2f}")

print("\n" + "=" * 70)
print("CONTINUOUS WITH MISSING — n_model breakdown")
print("=" * 70)
cwm = m[m.is_continuous & m.pred_has_missing][["outcome_family","variable","n_model_local","n_model_drive"]].drop_duplicates()
print(cwm.to_string(index=False))

print("\n" + "=" * 70)
print("CATEGORICAL WITH NO MISSING — should be perfect")
print("=" * 70)
cn = m[~m.is_continuous & ~m.pred_has_missing][["outcome_family","variable","term","estimate_local","estimate_drive","p_value_local","p_value_drive","n_model_local","n_model_drive"]]
print(cn.to_string(index=False))
