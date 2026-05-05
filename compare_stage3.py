"""Compare local Stage 3 effect estimates to Drive Stage 3 effect estimates.

Joins on (outcome_family, variable, term) and computes diffs.
"""

from pathlib import Path

import numpy as np
import pandas as pd

LOCAL = Path("/home/user/dialysis/outputs/params/stage3_local_run/stage3_univariable_effect_estimates.csv")
DRIVE = Path("/home/user/dialysis/outputs/params/stage3_drive_existing/stage3_univariable_effect_estimates.csv")

local = pd.read_csv(LOCAL)
drive = pd.read_csv(DRIVE)

key = ["outcome_family", "variable", "term"]
print(f"Local rows: {len(local)}, Drive rows: {len(drive)}")
print(f"Local outcome_family counts:\n{local.outcome_family.value_counts()}\n")
print(f"Drive outcome_family counts:\n{drive.outcome_family.value_counts()}\n")

both_keys = pd.merge(local[key], drive[key], on=key, how="outer", indicator=True)
print(f"Key match summary:\n{both_keys._merge.value_counts()}\n")

m = local.merge(drive, on=key, how="outer", suffixes=("_local", "_drive"))

# Compare numeric columns
def diff_stats(name, a, b):
    diff = (a - b).abs()
    rel = diff / b.abs()
    return {
        "metric": name,
        "n_compared": int(diff.notna().sum()),
        "max_abs_diff": float(diff.max()),
        "mean_abs_diff": float(diff.mean()),
        "max_rel_diff": float(rel.replace([np.inf, -np.inf], np.nan).max()),
    }


cols = ["estimate", "ci95_low", "ci95_high", "p_value", "raw_beta", "q_value_bh_within_outcome"]
rows = []
for c in cols:
    a = m[f"{c}_local"]
    b = m[f"{c}_drive"]
    rows.append(diff_stats(c, a, b))
print(pd.DataFrame(rows).to_string(index=False))

# Per-outcome diff summary
print("\n--- Max abs diff in `estimate` per outcome family ---")
for fam, sub in m.groupby("outcome_family"):
    diff = (sub.estimate_local - sub.estimate_drive).abs()
    print(f"  {fam}: n={diff.notna().sum()} max_abs_diff={diff.max():.6g} mean_abs_diff={diff.mean():.6g}")

print("\n--- p_value comparison: do orderings match? ---")
for fam, sub in m.groupby("outcome_family"):
    sub = sub.sort_values("variable")
    p_local = sub.p_value_local
    p_drive = sub.p_value_drive
    corr = p_local.corr(p_drive)
    log_corr = np.log10(p_local).corr(np.log10(p_drive))
    print(f"  {fam}: p Pearson r={corr:.6f}, log10(p) Pearson r={log_corr:.6f}")

# Largest discrepancies
print("\n--- Top 10 largest |estimate| diffs ---")
m["est_diff_abs"] = (m.estimate_local - m.estimate_drive).abs()
print(
    m.sort_values("est_diff_abs", ascending=False)
    .head(10)[["outcome_family", "variable", "term", "estimate_local", "estimate_drive", "p_value_local", "p_value_drive", "n_model_local", "n_model_drive"]]
    .to_string(index=False)
)

print("\n--- Top 10 largest |p_value| diffs ---")
m["p_diff_abs"] = (m.p_value_local - m.p_value_drive).abs()
print(
    m.sort_values("p_diff_abs", ascending=False)
    .head(10)[["outcome_family", "variable", "term", "p_value_local", "p_value_drive", "estimate_local", "estimate_drive"]]
    .to_string(index=False)
)

# Reference levels and contrasts comparison
print("\n--- Contrast / reference disagreement (top 20) ---")
ref_diff = m[(m.contrast_local != m.contrast_drive) | (m.reference_level_local != m.reference_level_drive)]
print(ref_diff[["outcome_family", "variable", "term", "contrast_local", "contrast_drive", "reference_level_local", "reference_level_drive"]].head(20).to_string(index=False) if not ref_diff.empty else "  none")

# n_model agreement
print("\n--- n_model disagreement ---")
n_diff = m[m.n_model_local != m.n_model_drive]
if n_diff.empty:
    print("  perfect agreement on n_model")
else:
    print(n_diff[["outcome_family", "variable", "n_model_local", "n_model_drive"]].drop_duplicates().to_string(index=False))
