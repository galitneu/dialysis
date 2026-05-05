"""Compare local Stage 3 to NEW (v2) Drive Stage 3 effect estimates."""

import numpy as np
import pandas as pd

LOCAL = pd.read_csv("/home/user/dialysis/outputs/params/stage3_local_run/stage3_univariable_effect_estimates.csv")
DRIVE = pd.read_csv("/home/user/dialysis/outputs/params/stage3_drive_v2/stage3_univariable_effect_estimates.csv")

print("Local cols:", list(LOCAL.columns))
print("Drive cols:", list(DRIVE.columns))
print(f"\nLocal rows: {len(LOCAL)} | Drive rows: {len(DRIVE)}")

key = ["outcome_family", "variable", "term"]
m = LOCAL.merge(DRIVE, on=key, how="outer", suffixes=("_local", "_drive"), indicator=True)
print(f"\nMerge summary:\n{m._merge.value_counts()}\n")

# Overall numeric agreement
def stats(c):
    a, b = m[f"{c}_local"], m[f"{c}_drive"]
    diff = (a - b).abs()
    return c, int(diff.notna().sum()), float(diff.max()), float(diff.mean())

print(f"{'metric':<32} {'n':>5} {'max_abs_diff':>15} {'mean_abs_diff':>15}")
for c in ["estimate","ci95_low","ci95_high","p_value","raw_beta","q_value_bh_within_outcome","n_model"]:
    if f"{c}_local" in m.columns and f"{c}_drive" in m.columns:
        n,m_,me_ = stats(c)[1:]
        print(f"{c:<32} {n:>5} {m_:>15.6g} {me_:>15.6g}")

# Per outcome family
print("\n--- Per outcome family ---")
for fam, sub in m.groupby("outcome_family"):
    est_diff = (sub.estimate_local - sub.estimate_drive).abs()
    p_diff = (sub.p_value_local - sub.p_value_drive).abs()
    n_diff = (sub.n_model_local - sub.n_model_drive).abs() if "n_model_drive" in m.columns else None
    print(f"  {fam}: n={est_diff.notna().sum()}")
    print(f"    estimate max_abs={est_diff.max():.6g} mean_abs={est_diff.mean():.6g}")
    print(f"    p_value  max_abs={p_diff.max():.6g} mean_abs={p_diff.mean():.6g}")
    if n_diff is not None:
        print(f"    n_model  max_abs={int(n_diff.max())}")

# Top 10 diffs
print("\n--- Top 10 |estimate diff| (with new Drive) ---")
m["est_diff_abs"] = (m.estimate_local - m.estimate_drive).abs()
print(
    m.sort_values("est_diff_abs", ascending=False).head(10)[
        ["outcome_family","variable","term","estimate_local","estimate_drive","p_value_local","p_value_drive","n_model_local","n_model_drive"]
    ].to_string(index=False)
)

# Compare reference levels and contrasts
print("\n--- contrast/reference disagreement ---")
ref_diff = m[(m.contrast_local != m.contrast_drive) | (m.reference_level_local.fillna("") != m.reference_level_drive.fillna(""))]
ref_diff = ref_diff[ref_diff.contrast_local.notna() & ref_diff.contrast_drive.notna()]  # exclude pure missing
print(f"  rows with contrast/reference diff: {len(ref_diff)}")
if not ref_diff.empty:
    print(ref_diff[["outcome_family","variable","term","contrast_local","contrast_drive","reference_level_local","reference_level_drive"]].head(10).to_string(index=False))

# n_model agreement
print("\n--- n_model disagreement ---")
n_diff = m[m.n_model_local != m.n_model_drive][["outcome_family","variable","n_model_local","n_model_drive"]].drop_duplicates()
if n_diff.empty:
    print("  PERFECT n_model agreement")
else:
    print(n_diff.to_string(index=False))
