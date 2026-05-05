"""Stage 3 - Univariable Descriptive Screening (independent local re-implementation).

Inputs:  outputs/params/stage1/, outputs/params/stage2_DEC044_FIXED_v2/
Outputs: outputs/params/stage3_local_run/

Models (univariable, one predictor at a time, complete-case for that predictor):
  - one_year_mortality_logistic  : logistic regression (OR, 95% CI)
  - survival_cox                 : Cox PH regression (HR, 95% CI)
  - hospitalization_negative_binomial : NB regression with alpha=1.0 fixed,
                                  offset = log_followup_years (IRR, 95% CI)

Coding:
  - continuous : z-score within the analytic sample, term = "<var>__z",
                 contrast = "per 1 SD increase".
  - categorical: most-frequent observed level (within main analytic sample) is
                 reference; one dummy term per non-reference level.
                 term = "<var>__level__<level_safe>".
                 contrast = "<level> vs <reference>".

Multiplicity: BH q-values within each outcome family. Descriptive only.
Stage 3 is advisory; no automatic variable selection.
"""

from __future__ import annotations

import json
import math
import os
import re
import sys
import warnings
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from statsmodels.duration.hazard_regression import PHReg
from statsmodels.genmod.families import NegativeBinomial
from statsmodels.genmod.generalized_linear_model import GLM
from statsmodels.tools.sm_exceptions import ConvergenceWarning, PerfectSeparationError

warnings.filterwarnings("ignore", category=ConvergenceWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=UserWarning)

ROOT = Path("/home/user/dialysis/outputs/params")
STAGE1 = ROOT / "stage1"
STAGE2 = ROOT / "stage2_DEC044_FIXED_v2"
STAGE3 = ROOT / "stage3_local_run"
STAGE3.mkdir(parents=True, exist_ok=True)

NB_ALPHA = 1.0  # DEC-059: screening only

TIMING_SENSITIVITY_ONLY = {"echo_to_dialysis_timing_category"}


# ------------------------------------------------------------------ helpers


def safe_level_name(s: str) -> str:
    """Sanitize a level for use in a term name (no spaces)."""
    return re.sub(r"\s+", "_", str(s).strip())


def bh_qvalues(pvals: list[float]) -> list[float]:
    """Benjamini-Hochberg q-values. Preserves order. NaNs kept as NaN."""
    arr = np.array(pvals, dtype=float)
    finite_idx = np.where(np.isfinite(arr))[0]
    q = np.full_like(arr, np.nan, dtype=float)
    if finite_idx.size == 0:
        return q.tolist()
    p = arr[finite_idx]
    n = p.size
    order = np.argsort(p)
    ranked = p[order]
    q_ranked = ranked * n / (np.arange(1, n + 1))
    # enforce monotonic non-increasing from the largest rank
    q_ranked = np.minimum.accumulate(q_ranked[::-1])[::-1]
    q_ranked = np.minimum(q_ranked, 1.0)
    q_sorted_back = np.empty_like(q_ranked)
    q_sorted_back[order] = q_ranked
    q[finite_idx] = q_sorted_back
    return q.tolist()


def zscore(s: pd.Series) -> tuple[pd.Series, float, float]:
    s = pd.to_numeric(s, errors="coerce")
    nn = s.dropna()
    mu, sd = float(nn.mean()), float(nn.std(ddof=1))
    if sd == 0 or not np.isfinite(sd):
        return s * np.nan, mu, sd
    return (s - mu) / sd, mu, sd


def most_frequent_level(s: pd.Series) -> str | None:
    nn = s.dropna()
    if nn.empty:
        return None
    return str(nn.value_counts().idxmax())


# ------------------------------------------------------------------ models


def fit_logistic(y: np.ndarray, X: np.ndarray, term_names: list[str]):
    Xc = sm.add_constant(X, has_constant="add")
    res = GLM(y, Xc, family=sm.families.Binomial()).fit()
    out = []
    for i, name in enumerate(term_names, start=1):  # skip const at 0
        b = res.params[i]
        se = res.bse[i]
        p = res.pvalues[i]
        lo, hi = b - 1.959963984540054 * se, b + 1.959963984540054 * se
        out.append((name, b, se, p, lo, hi))
    return out


def fit_cox(time: np.ndarray, event: np.ndarray, X: np.ndarray, term_names: list[str]):
    res = PHReg(time, X, status=event).fit()
    out = []
    for i, name in enumerate(term_names):
        b = res.params[i]
        se = res.bse[i]
        p = res.pvalues[i]
        lo, hi = b - 1.959963984540054 * se, b + 1.959963984540054 * se
        out.append((name, b, se, p, lo, hi))
    return out


def fit_nb(y: np.ndarray, X: np.ndarray, offset: np.ndarray, term_names: list[str]):
    Xc = sm.add_constant(X, has_constant="add")
    res = GLM(
        y,
        Xc,
        family=NegativeBinomial(alpha=NB_ALPHA),
        offset=offset,
    ).fit()
    out = []
    for i, name in enumerate(term_names, start=1):
        b = res.params[i]
        se = res.bse[i]
        p = res.pvalues[i]
        lo, hi = b - 1.959963984540054 * se, b + 1.959963984540054 * se
        out.append((name, b, se, p, lo, hi))
    return out


# ------------------------------------------------------------------ design matrix


def design_for_predictor(df: pd.DataFrame, var: str, var_type: str, ref_lookup: dict[str, str]):
    """Return (subset_df, X, term_names, contrasts, coding, ref_level, var_type_emit)."""
    if var_type == "continuous":
        z, _, sd = zscore(df[var])
        sub = df.assign(_z=z).dropna(subset=["_z"])
        if sd == 0 or sub.empty:
            return None
        X = sub[["_z"]].to_numpy(dtype=float)
        term_names = [f"{var}__z"]
        contrasts = ["per 1 SD increase"]
        return sub, X, term_names, contrasts, "continuous_per_1SD", "", "continuous"

    # categorical
    sub = df.dropna(subset=[var]).copy()
    if sub.empty:
        return None
    sub[var] = sub[var].astype(str)
    ref = ref_lookup.get(var) or most_frequent_level(sub[var])
    if ref is None:
        return None
    levels = [lv for lv in sub[var].value_counts().index.tolist() if lv != ref]
    if not levels:
        return None
    cols = []
    term_names = []
    contrasts = []
    for lv in levels:
        col = (sub[var] == lv).astype(int).to_numpy()
        cols.append(col)
        term_names.append(f"{var}__level__{safe_level_name(lv)}")
        contrasts.append(f"{lv} vs {ref}")
    X = np.column_stack(cols).astype(float)
    return sub, X, term_names, contrasts, "categorical_dummy_vs_reference", ref, "categorical"


# ------------------------------------------------------------------ main


def main() -> int:
    run_ts = datetime.now().isoformat(timespec="seconds")

    # Load Stage 1 datasets
    main_df = pd.read_csv(STAGE1 / "stage1_main_analysis.csv")
    oy_df = pd.read_csv(STAGE1 / "stage1_oneyear_mortality.csv")
    surv_df = pd.read_csv(STAGE1 / "stage1_survival_analysis.csv")
    hosp_df = pd.read_csv(STAGE1 / "stage1_hospitalization_analysis.csv")

    col_class = pd.read_csv(STAGE2 / "stage2_column_classification.csv")
    col_class = col_class[col_class["dataset"] == "main"].copy()

    # Predictor list - all 28 from Stage 2 main classification
    all_vars = col_class["variable"].tolist()
    type_map = dict(zip(col_class["variable"], col_class["stage2_type"]))

    predictor_roles_rows = []
    main_candidates = []
    for v in all_vars:
        role = (
            "timing_sensitivity_only" if v in TIMING_SENSITIVITY_ONLY else "main_candidate"
        )
        predictor_roles_rows.append(
            {"dataset": "main", "variable": v, "stage2_type": type_map[v], "predictor_role": role}
        )
        if role == "main_candidate":
            main_candidates.append(v)
    pd.DataFrame(predictor_roles_rows).to_csv(STAGE3 / "stage3_predictor_roles.csv", index=False)

    # Reference levels = most-frequent in main analytic sample
    ref_lookup = {
        v: most_frequent_level(main_df[v])
        for v in all_vars
        if type_map[v] == "categorical"
    }

    estimates_rows = []
    fit_status_rows = []

    # ----- 1) one-year mortality (logistic) -----
    oy_df = oy_df.dropna(subset=["died_1year"]).copy()
    oy_df["died_1year"] = oy_df["died_1year"].astype(int)
    for v in all_vars:
        role = "timing_sensitivity_only" if v in TIMING_SENSITIVITY_ONLY else "main_candidate"
        spec = design_for_predictor(oy_df, v, type_map[v], ref_lookup)
        if spec is None:
            fit_status_rows.append(
                {
                    "outcome_family": "one_year_mortality_logistic",
                    "variable": v,
                    "predictor_role": role,
                    "status": "skipped",
                    "reason": "no usable design (constant or all missing)",
                }
            )
            continue
        sub, X, term_names, contrasts, coding, ref_level, vt = spec
        y = sub["died_1year"].to_numpy(dtype=int)
        n = int(y.size)
        events = int(y.sum())
        try:
            results = fit_logistic(y, X, term_names)
            status, reason = "ok", ""
        except (PerfectSeparationError, np.linalg.LinAlgError, ValueError) as e:
            status, reason = "failed", f"{type(e).__name__}: {e}"
            results = []
        fit_status_rows.append(
            {
                "outcome_family": "one_year_mortality_logistic",
                "variable": v,
                "predictor_role": role,
                "status": status,
                "reason": reason,
            }
        )
        for (term, b, se, p, lo, hi), contrast in zip(results, contrasts):
            estimates_rows.append(
                {
                    "outcome_family": "one_year_mortality_logistic",
                    "variable": v,
                    "predictor_role": role,
                    "term": term,
                    "contrast": contrast,
                    "variable_type": vt,
                    "coding": coding,
                    "reference_level": ref_level,
                    "n_model": n,
                    "events_or_total_count": events,
                    "effect_measure": "OR",
                    "estimate": math.exp(b),
                    "ci95_low": math.exp(lo),
                    "ci95_high": math.exp(hi),
                    "p_value": p,
                    "raw_beta": b,
                    "raw_beta_ci95_low": lo,
                    "raw_beta_ci95_high": hi,
                    "nb_alpha_screening_fixed": np.nan,
                }
            )

    # ----- 2) survival (Cox) -----
    surv_df = surv_df.dropna(subset=["event", "time_to_event_days"]).copy()
    # require positive time
    surv_df = surv_df[surv_df["time_to_event_days"] > 0].copy()
    for v in all_vars:
        role = "timing_sensitivity_only" if v in TIMING_SENSITIVITY_ONLY else "main_candidate"
        spec = design_for_predictor(surv_df, v, type_map[v], ref_lookup)
        if spec is None:
            fit_status_rows.append(
                {
                    "outcome_family": "survival_cox",
                    "variable": v,
                    "predictor_role": role,
                    "status": "skipped",
                    "reason": "no usable design",
                }
            )
            continue
        sub, X, term_names, contrasts, coding, ref_level, vt = spec
        time = sub["time_to_event_days"].to_numpy(dtype=float)
        event = sub["event"].astype(int).to_numpy()
        n = int(event.size)
        events = int(event.sum())
        try:
            results = fit_cox(time, event, X, term_names)
            status, reason = "ok", ""
        except (np.linalg.LinAlgError, ValueError) as e:
            status, reason = "failed", f"{type(e).__name__}: {e}"
            results = []
        fit_status_rows.append(
            {
                "outcome_family": "survival_cox",
                "variable": v,
                "predictor_role": role,
                "status": status,
                "reason": reason,
            }
        )
        for (term, b, se, p, lo, hi), contrast in zip(results, contrasts):
            estimates_rows.append(
                {
                    "outcome_family": "survival_cox",
                    "variable": v,
                    "predictor_role": role,
                    "term": term,
                    "contrast": contrast,
                    "variable_type": vt,
                    "coding": coding,
                    "reference_level": ref_level,
                    "n_model": n,
                    "events_or_total_count": events,
                    "effect_measure": "HR",
                    "estimate": math.exp(b),
                    "ci95_low": math.exp(lo),
                    "ci95_high": math.exp(hi),
                    "p_value": p,
                    "raw_beta": b,
                    "raw_beta_ci95_low": lo,
                    "raw_beta_ci95_high": hi,
                    "nb_alpha_screening_fixed": np.nan,
                }
            )

    # ----- 3) hospitalization (Negative Binomial, alpha=1.0 fixed) -----
    hosp_df = hosp_df.dropna(subset=["hosp_total", "log_followup_years"]).copy()
    hosp_df = hosp_df[np.isfinite(hosp_df["log_followup_years"])].copy()
    for v in all_vars:
        role = "timing_sensitivity_only" if v in TIMING_SENSITIVITY_ONLY else "main_candidate"
        spec = design_for_predictor(hosp_df, v, type_map[v], ref_lookup)
        if spec is None:
            fit_status_rows.append(
                {
                    "outcome_family": "hospitalization_negative_binomial",
                    "variable": v,
                    "predictor_role": role,
                    "status": "skipped",
                    "reason": "no usable design",
                }
            )
            continue
        sub, X, term_names, contrasts, coding, ref_level, vt = spec
        y = sub["hosp_total"].astype(int).to_numpy()
        offset = sub["log_followup_years"].astype(float).to_numpy()
        n = int(y.size)
        total = int(y.sum())
        try:
            results = fit_nb(y, X, offset, term_names)
            status, reason = "ok", ""
        except (np.linalg.LinAlgError, ValueError) as e:
            status, reason = "failed", f"{type(e).__name__}: {e}"
            results = []
        fit_status_rows.append(
            {
                "outcome_family": "hospitalization_negative_binomial",
                "variable": v,
                "predictor_role": role,
                "status": status,
                "reason": reason,
            }
        )
        for (term, b, se, p, lo, hi), contrast in zip(results, contrasts):
            estimates_rows.append(
                {
                    "outcome_family": "hospitalization_negative_binomial",
                    "variable": v,
                    "predictor_role": role,
                    "term": term,
                    "contrast": contrast,
                    "variable_type": vt,
                    "coding": coding,
                    "reference_level": ref_level,
                    "n_model": n,
                    "events_or_total_count": total,
                    "effect_measure": "IRR",
                    "estimate": math.exp(b),
                    "ci95_low": math.exp(lo),
                    "ci95_high": math.exp(hi),
                    "p_value": p,
                    "raw_beta": b,
                    "raw_beta_ci95_low": lo,
                    "raw_beta_ci95_high": hi,
                    "nb_alpha_screening_fixed": NB_ALPHA,
                }
            )

    eff = pd.DataFrame(estimates_rows)
    eff["abs_log_effect"] = eff["raw_beta"].abs()

    # BH q-values within each outcome family
    eff["q_value_bh_within_outcome"] = np.nan
    for fam, sub in eff.groupby("outcome_family"):
        q = bh_qvalues(sub["p_value"].tolist())
        eff.loc[sub.index, "q_value_bh_within_outcome"] = q

    eff = eff[
        [
            "outcome_family",
            "variable",
            "predictor_role",
            "term",
            "contrast",
            "variable_type",
            "coding",
            "reference_level",
            "n_model",
            "events_or_total_count",
            "effect_measure",
            "estimate",
            "ci95_low",
            "ci95_high",
            "p_value",
            "raw_beta",
            "raw_beta_ci95_low",
            "raw_beta_ci95_high",
            "nb_alpha_screening_fixed",
            "q_value_bh_within_outcome",
            "abs_log_effect",
        ]
    ].sort_values(
        ["outcome_family", "p_value", "variable", "term"], na_position="last"
    )
    eff.to_csv(STAGE3 / "stage3_univariable_effect_estimates.csv", index=False)

    # Variable-level summary: best (smallest p) term per (outcome_family, variable)
    best_idx = eff.groupby(["outcome_family", "variable"])["p_value"].idxmin()
    var_summary = eff.loc[best_idx.dropna()].copy().reset_index(drop=True)
    var_summary.to_csv(STAGE3 / "stage3_univariable_variable_summary.csv", index=False)

    # Fit status table
    fit_status_df = pd.DataFrame(fit_status_rows)
    fit_status_df.to_csv(STAGE3 / "stage3_model_fit_status.csv", index=False)

    # Triage table for Stage 4: one row per variable, with min p and best estimate per outcome
    fams = [
        ("hospitalization_negative_binomial", "hospitalization_negative_binomial"),
        ("one_year_mortality_logistic", "one_year_mortality_logistic"),
        ("survival_cox", "survival_cox"),
    ]
    triage_rows = []
    for v in all_vars:
        role = "timing_sensitivity_only" if v in TIMING_SENSITIVITY_ONLY else "main_candidate"
        row = {
            "variable": v,
            "stage2_type": type_map[v],
            "predictor_role": role,
        }
        for fam, prefix in fams:
            sub = eff[(eff.outcome_family == fam) & (eff.variable == v)]
            if sub.empty:
                row[f"{prefix}__min_p"] = np.nan
                row[f"{prefix}__q_bh"] = np.nan
                row[f"{prefix}__best_estimate"] = np.nan
                row[f"{prefix}__effect_measure"] = ""
            else:
                idx = sub["p_value"].idxmin()
                row[f"{prefix}__min_p"] = sub.loc[idx, "p_value"]
                row[f"{prefix}__q_bh"] = sub.loc[idx, "q_value_bh_within_outcome"]
                row[f"{prefix}__best_estimate"] = sub.loc[idx, "estimate"]
                row[f"{prefix}__effect_measure"] = sub.loc[idx, "effect_measure"]
        row["stage3_note"] = (
            "Stage 3 does not select variables. Use in Stage 4 with clinical "
            "overlap, EPV and missingness."
        )
        triage_rows.append(row)
    triage = pd.DataFrame(triage_rows)
    triage.to_csv(STAGE3 / "stage3_stage4_triage_table.csv", index=False)

    # Input validation
    iv = pd.DataFrame(
        [
            {
                "check": "stage1_main_analysis_rows",
                "value": main_df.shape[0],
                "expected": 644,
                "passed": main_df.shape[0] == 644,
            },
            {
                "check": "stage1_oneyear_rows",
                "value": oy_df.shape[0],
                "expected": 617,
                "passed": oy_df.shape[0] == 617,
            },
            {
                "check": "stage1_survival_rows",
                "value": surv_df.shape[0],
                "expected": 644,
                "passed": surv_df.shape[0] == 644,
            },
            {
                "check": "stage1_hospitalization_rows",
                "value": hosp_df.shape[0],
                "expected": 644,
                "passed": hosp_df.shape[0] == 644,
            },
            {
                "check": "n_main_candidates",
                "value": len(main_candidates),
                "expected": 27,
                "passed": len(main_candidates) == 27,
            },
            {
                "check": "n_predictors_total",
                "value": len(all_vars),
                "expected": 28,
                "passed": len(all_vars) == 28,
            },
        ]
    )
    iv.to_csv(STAGE3 / "stage3_input_validation.csv", index=False)

    # Stage 2 provenance checks
    s2_meta = json.loads((STAGE2 / "stage2_run_metadata.json").read_text())
    prov_rows = [
        {
            "check": "stage2_version_label",
            "value": s2_meta.get("stage2_version_label", ""),
            "expected": "stage2_DEC044_FIXED_v2",
            "passed": s2_meta.get("stage2_version_label") == "stage2_DEC044_FIXED_v2",
        },
        {
            "check": "stage2_collinearity_method",
            "value": s2_meta.get("collinearity_screening_method", ""),
            "expected": "Spearman rank correlation",
            "passed": s2_meta.get("collinearity_screening_method")
            == "Spearman rank correlation",
        },
        {
            "check": "stage2_decisions_include_DEC051",
            "value": ",".join(s2_meta.get("decisions_applied", [])),
            "expected": "contains DEC-051",
            "passed": "DEC-051" in s2_meta.get("decisions_applied", []),
        },
    ]
    pd.DataFrame(prov_rows).to_csv(STAGE3 / "stage3_stage2_provenance_checks.csv", index=False)

    # Decision log
    decisions = [
        ("DEC-052", "Stage 3 is univariable descriptive screening only; no final selection."),
        ("DEC-053", "Continuous predictors modeled per 1 SD."),
        ("DEC-054", "Categorical predictors dummy-coded vs most-frequent reference; explicit term/reference/contrast."),
        ("DEC-055", "Logistic for 1y mortality; Cox for survival; NB with log(followup_years) offset for hospitalization."),
        ("DEC-056", "BH q-values reported as descriptive context only."),
        ("DEC-057", "Timing variable echo_to_dialysis_timing_category is timing_sensitivity_only."),
        ("DEC-058", "Stage 2 DEC044/DEC051 FIXED v2 expected as input; provenance recorded."),
        ("DEC-059", "Negative Binomial alpha=1.0 fixed for Stage 3 screening only; Stage 5 will refit dispersion."),
    ]
    pd.DataFrame(decisions, columns=["decision_id", "decision"]).to_csv(
        STAGE3 / "stage3_decision_log.csv", index=False
    )

    # Run metadata
    s1_meta = json.loads((STAGE1 / "stage1_run_metadata.json").read_text())
    meta = {
        "stage": "Stage 3",
        "run_timestamp": run_ts,
        "stage1_input_dir": str(STAGE1),
        "stage2_input_dir": str(STAGE2),
        "stage3_output_dir": str(STAGE3),
        "n_main_predictors": len(main_candidates),
        "main_predictors": main_candidates,
        "n_sensitivity_only_predictors": len(all_vars) - len(main_candidates),
        "sensitivity_only_predictors": [v for v in all_vars if v not in main_candidates],
        "all_screened_predictors": all_vars,
        "stage2_expected_version": "stage2_DEC044_FIXED_v2 with DEC-051 Spearman collinearity screening",
        "stage1_version": s1_meta.get("decision_scope", ""),
        "nb_alpha_screening_fixed": NB_ALPHA,
        "nb_alpha_note": "Negative Binomial alpha=1.0 fixed for Stage 3 screening only; final dispersion will be handled in Stage 5.",
        "methodological_boundary": "Univariable screening outputs are advisory only and should not be interpreted as final variable selection.",
        "model_software": {
            "logistic": "statsmodels.GLM Binomial",
            "cox": "statsmodels.duration.PHReg (Breslow ties)",
            "negative_binomial": f"statsmodels.GLM NegativeBinomial(alpha={NB_ALPHA})",
        },
        "outputs": [
            "stage3_input_validation.csv",
            "stage3_univariable_effect_estimates.csv",
            "stage3_univariable_variable_summary.csv",
            "stage3_model_fit_status.csv",
            "stage3_stage4_triage_table.csv",
            "stage3_decision_log.csv",
            "stage3_run_metadata.json",
            "stage3_predictor_roles.csv",
            "stage3_stage2_provenance_checks.csv",
            "stage3_readiness_report.md",
        ],
    }
    (STAGE3 / "stage3_run_metadata.json").write_text(json.dumps(meta, indent=2))

    # Readiness report
    fit_summary = (
        fit_status_df.groupby(["outcome_family", "status"]).size().unstack(fill_value=0)
    )
    rep_lines = [
        "# Stage 3 readiness report (independent local re-implementation)",
        f"Generated: {run_ts}",
        "",
        f"- Main candidates: {len(main_candidates)}",
        f"- Timing/sensitivity-only: {len(all_vars) - len(main_candidates)}",
        f"- All screened: {len(all_vars)}",
        "",
        "## Fit status by outcome family",
        "```",
        fit_summary.to_string(),
        "```",
        "",
        "## Top 5 by p-value within each outcome family",
    ]
    for fam in ["one_year_mortality_logistic", "survival_cox", "hospitalization_negative_binomial"]:
        sub = (
            eff[eff.outcome_family == fam]
            .sort_values("p_value")
            .head(5)[["variable", "term", "estimate", "ci95_low", "ci95_high", "p_value", "q_value_bh_within_outcome"]]
        )
        rep_lines.append(f"\n### {fam}\n```")
        rep_lines.append(sub.to_string(index=False))
        rep_lines.append("```")
    (STAGE3 / "stage3_readiness_report.md").write_text("\n".join(rep_lines))

    print(f"Stage 3 complete. Outputs in: {STAGE3}")
    print(f"Effect estimate rows: {len(eff)}")
    print(f"Variable summary rows: {len(var_summary)}")
    print(f"Fit status rows: {len(fit_status_df)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
