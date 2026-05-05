"""
Stage 3 — Univariable descriptive screening
Independent local implementation per spec dated 2026-05-05.

Outcomes:
  1) one_year_mortality      -> Logistic regression
  2) full survival           -> Cox proportional hazards
  3) hospitalization burden  -> Negative Binomial (alpha=1.0 screening), offset = log(followup_years)

Stage 3 is descriptive/advisory only. No automatic variable selection.
"""

import os, json, math, warnings
from datetime import datetime, timezone
from hashlib import sha256

import numpy as np
import pandas as pd

import statsmodels.api as sm
from statsmodels.discrete.discrete_model import Logit
from statsmodels.duration.hazard_regression import PHReg
from statsmodels.genmod.generalized_linear_model import GLM
from statsmodels.genmod.families import NegativeBinomial as NBFamily

warnings.filterwarnings("ignore")

# ---------- Paths ----------
STAGE1 = "/home/user/dialysis/outputs/params/stage1"
STAGE2 = "/home/user/dialysis/outputs/params/stage2_DEC044_FIXED_v2"
OUT    = "/home/user/dialysis/outputs/params/stage3_local_run"
os.makedirs(OUT, exist_ok=True)

Z975 = 1.959963984540054  # 97.5th percentile of N(0,1)

# Variables that should NOT be treated as ordinary main candidates in Stage 4 -
# they are advisory timing/sensitivity-only.
TIMING_SENSITIVITY_VARS = {"days_echo_to_dialysis", "echo_to_dialysis_timing_category"}

# ---------- Provenance and inputs ----------
def file_sha(path):
    with open(path, "rb") as f:
        return sha256(f.read()).hexdigest()

def load_inputs():
    oy = pd.read_csv(f"{STAGE1}/stage1_oneyear_mortality.csv")
    sv = pd.read_csv(f"{STAGE1}/stage1_survival_analysis.csv")
    hp = pd.read_csv(f"{STAGE1}/stage1_hospitalization_analysis.csv")
    pl = pd.read_csv(f"{STAGE1}/stage1_main_predictor_list.csv").iloc[:, 0].tolist()
    cc = pd.read_csv(f"{STAGE2}/stage2_column_classification.csv")
    with open(f"{STAGE1}/stage1_run_metadata.json") as f: s1_meta = json.load(f)
    with open(f"{STAGE2}/stage2_run_metadata.json") as f: s2_meta = json.load(f)
    return dict(oneyear=oy, survival=sv, hosp=hp, predictors=pl, classification=cc,
                s1_meta=s1_meta, s2_meta=s2_meta)

# ---------- Design matrix per predictor ----------
def build_design(df, predictor, ptype):
    """
    Returns (X dataframe with one or more columns, list of term-info dicts, status).
    Continuous: standardized to z = (x - mean)/sd (sample SD).
    Categorical: dummy encoded with the most frequent non-missing level as reference.
    Rows with missing predictor values are kept as NaN; caller drops them later.
    """
    s = df[predictor]

    if ptype == "continuous":
        x = pd.to_numeric(s, errors="coerce")
        nm = x.notna()
        if nm.sum() < 10:
            return None, None, "skipped_few_obs"
        mean = float(x[nm].mean())
        sd = float(x[nm].std(ddof=1))
        if (not np.isfinite(sd)) or sd <= 0:
            return None, None, "skipped_zero_sd"
        z = (x - mean) / sd
        col = f"{predictor}__z"
        X = pd.DataFrame({col: z}, index=df.index)
        terms = [{
            "term": col,
            "predictor": predictor,
            "type": "continuous",
            "level": "",
            "reference_level": "",
            "contrast": "per 1 SD",
            "n_nonmissing": int(nm.sum()),
            "mean": mean,
            "sd": sd,
        }]
        return X, terms, "ok"

    # categorical / binary
    s_str = s.astype("object")
    counts = s_str.value_counts(dropna=True)
    if len(counts) < 2:
        return None, None, "skipped_one_level"
    # reference = most frequent level
    ref = counts.index[0]
    non_ref = [lvl for lvl in counts.index if lvl != ref]
    parts = {}
    terms = []
    for lvl in non_ref:
        col = f"{predictor}__{lvl}"
        d = (s_str == lvl).astype(float)
        d[s_str.isna()] = np.nan
        parts[col] = d
        terms.append({
            "term": col,
            "predictor": predictor,
            "type": "categorical",
            "level": str(lvl),
            "reference_level": str(ref),
            "contrast": f"{lvl} vs {ref}",
            "n_nonmissing": int(s_str.notna().sum()),
            "level_count": int(counts[lvl]),
            "ref_count": int(counts[ref]),
        })
    X = pd.DataFrame(parts, index=df.index)
    return X, terms, "ok"

# ---------- Model fitters ----------
def _ci(beta, se):
    lo = beta - Z975 * se
    hi = beta + Z975 * se
    return lo, hi

def fit_logit_for(df, predictor, ptype, outcome_col="died_1year"):
    X, terms, st = build_design(df, predictor, ptype)
    if st != "ok":
        return [], {"predictor": predictor, "outcome": "one_year_mortality",
                    "model": "logistic", "status": st}
    y = df[outcome_col]
    full = pd.concat([y.rename("__y"), X], axis=1).dropna()
    n = len(full); events = int(full["__y"].sum())
    if n < 20:
        return [], {"predictor": predictor, "outcome": "one_year_mortality",
                    "model": "logistic", "status": "skipped_few_obs", "n": n, "events": events}
    if events < 5 or n - events < 5:
        return [], {"predictor": predictor, "outcome": "one_year_mortality",
                    "model": "logistic", "status": "skipped_few_events", "n": n, "events": events}
    Xa = sm.add_constant(full[X.columns], has_constant="add")
    try:
        res = Logit(full["__y"], Xa).fit(disp=0, maxiter=200)
    except Exception as e:
        return [], {"predictor": predictor, "outcome": "one_year_mortality",
                    "model": "logistic", "status": f"fit_failed:{e.__class__.__name__}",
                    "n": n, "events": events}
    rows = []
    for t in terms:
        term = t["term"]
        base = {"outcome": "one_year_mortality", "model": "logistic",
                "effect_label": "OR", "n": n, "events": events,
                "person_years": np.nan, **t}
        if term not in res.params.index:
            rows.append({**base, "beta": np.nan, "se": np.nan, "effect": np.nan,
                         "ci_lower": np.nan, "ci_upper": np.nan, "pvalue": np.nan,
                         "status": "term_dropped"})
            continue
        b = float(res.params[term]); se = float(res.bse[term])
        lo, hi = _ci(b, se)
        rows.append({**base, "beta": b, "se": se, "effect": math.exp(b),
                     "ci_lower": math.exp(lo), "ci_upper": math.exp(hi),
                     "pvalue": float(res.pvalues[term]), "status": "ok"})
    return rows, {"predictor": predictor, "outcome": "one_year_mortality",
                  "model": "logistic", "status": "ok", "n": n, "events": events,
                  "n_terms": len(terms)}

def fit_cox_for(df, predictor, ptype):
    X, terms, st = build_design(df, predictor, ptype)
    if st != "ok":
        return [], {"predictor": predictor, "outcome": "survival",
                    "model": "cox", "status": st}
    full = pd.concat([df[["time_to_event_days", "event"]], X], axis=1).dropna()
    full = full[full["time_to_event_days"] > 0]
    n = len(full); events = int(full["event"].sum())
    if n < 20:
        return [], {"predictor": predictor, "outcome": "survival",
                    "model": "cox", "status": "skipped_few_obs", "n": n, "events": events}
    if events < 5:
        return [], {"predictor": predictor, "outcome": "survival",
                    "model": "cox", "status": "skipped_few_events", "n": n, "events": events}
    try:
        m = PHReg(endog=full["time_to_event_days"].values,
                  exog=full[X.columns].values,
                  status=full["event"].values,
                  ties="efron")
        res = m.fit()
    except Exception as e:
        return [], {"predictor": predictor, "outcome": "survival",
                    "model": "cox", "status": f"fit_failed:{e.__class__.__name__}",
                    "n": n, "events": events}
    rows = []
    for i, t in enumerate(terms):
        base = {"outcome": "survival", "model": "cox",
                "effect_label": "HR", "n": n, "events": events,
                "person_years": np.nan, **t}
        if i >= len(res.params):
            rows.append({**base, "beta": np.nan, "se": np.nan, "effect": np.nan,
                         "ci_lower": np.nan, "ci_upper": np.nan, "pvalue": np.nan,
                         "status": "term_dropped"})
            continue
        b = float(res.params[i]); se = float(res.bse[i])
        lo, hi = _ci(b, se)
        rows.append({**base, "beta": b, "se": se, "effect": math.exp(b),
                     "ci_lower": math.exp(lo), "ci_upper": math.exp(hi),
                     "pvalue": float(res.pvalues[i]), "status": "ok"})
    return rows, {"predictor": predictor, "outcome": "survival", "model": "cox",
                  "status": "ok", "n": n, "events": events, "n_terms": len(terms)}

def fit_nb_for(df, predictor, ptype):
    X, terms, st = build_design(df, predictor, ptype)
    if st != "ok":
        return [], {"predictor": predictor, "outcome": "hospitalization",
                    "model": "negbin", "status": st}
    needed = ["hosp_total", "followup_years"]
    full = pd.concat([df[needed], X], axis=1).dropna()
    full = full[full["followup_years"] > 0]
    n = len(full)
    total_hosp = int(full["hosp_total"].sum())
    person_years = float(full["followup_years"].sum())
    if n < 20:
        return [], {"predictor": predictor, "outcome": "hospitalization",
                    "model": "negbin", "status": "skipped_few_obs",
                    "n": n, "events": total_hosp, "person_years": person_years}
    Xa = sm.add_constant(full[X.columns], has_constant="add")
    offset = np.log(full["followup_years"].values)
    try:
        glm = GLM(full["hosp_total"].values, Xa, family=NBFamily(alpha=1.0), offset=offset)
        res = glm.fit()
    except Exception as e:
        return [], {"predictor": predictor, "outcome": "hospitalization",
                    "model": "negbin", "status": f"fit_failed:{e.__class__.__name__}",
                    "n": n, "events": total_hosp, "person_years": person_years}
    rows = []
    for t in terms:
        term = t["term"]
        base = {"outcome": "hospitalization", "model": "negbin",
                "effect_label": "IRR", "n": n,
                "events": total_hosp, "person_years": person_years, **t}
        if term not in res.params.index:
            rows.append({**base, "beta": np.nan, "se": np.nan, "effect": np.nan,
                         "ci_lower": np.nan, "ci_upper": np.nan, "pvalue": np.nan,
                         "status": "term_dropped"})
            continue
        b = float(res.params[term]); se = float(res.bse[term])
        lo, hi = _ci(b, se)
        rows.append({**base, "beta": b, "se": se, "effect": math.exp(b),
                     "ci_lower": math.exp(lo), "ci_upper": math.exp(hi),
                     "pvalue": float(res.pvalues[term]), "status": "ok"})
    return rows, {"predictor": predictor, "outcome": "hospitalization",
                  "model": "negbin", "status": "ok", "n": n,
                  "events": total_hosp, "person_years": person_years,
                  "n_terms": len(terms)}

# ---------- BH q-values ----------
def bh_q(pvals):
    p = np.asarray(pvals, dtype=float)
    out = np.full_like(p, np.nan, dtype=float)
    mask = ~np.isnan(p)
    if mask.sum() == 0:
        return out
    idx = np.where(mask)[0]
    pp = p[mask]
    n = len(pp)
    order = np.argsort(pp)
    ranked = pp[order]
    q = ranked * n / (np.arange(n) + 1)
    # enforce monotonicity
    q = np.minimum.accumulate(q[::-1])[::-1]
    q = np.minimum(q, 1.0)
    inv = np.empty(n, dtype=int)
    inv[order] = np.arange(n)
    out[idx] = q[inv]
    return out

# ---------- Provenance checks ----------
def provenance_checks(d):
    rows = []
    s2 = d["s2_meta"]
    s1 = d["s1_meta"]
    rows.append(("stage2_version_label_is_FIXED_v2",
                 s2.get("stage2_version_label") == "stage2_DEC044_FIXED_v2"))
    rows.append(("stage2_collinearity_method_is_spearman",
                 s2.get("collinearity_screening_method") == "Spearman rank correlation"))
    rows.append(("DEC-044_in_decisions", "DEC-044" in s2.get("decisions_applied", [])))
    rows.append(("DEC-051_in_decisions", "DEC-051" in s2.get("decisions_applied", [])))
    rows.append(("stage1_n_main_predictors_is_27", s1.get("n_main_predictors") == 27))
    rows.append(("predictor_list_len_is_27", len(d["predictors"]) == 27))
    rows.append(("oneyear_n_is_617", len(d["oneyear"]) == 617))
    rows.append(("survival_n_is_644", len(d["survival"]) == 644))
    rows.append(("hosp_n_is_644", len(d["hosp"]) == 644))
    rows.append(("hosp_has_followup_years", "followup_years" in d["hosp"].columns))
    return pd.DataFrame(rows, columns=["check", "passed"])

# ---------- Main ----------
def main():
    d = load_inputs()
    oy, sv, hp = d["oneyear"], d["survival"], d["hosp"]
    cc = d["classification"]
    type_map = dict(zip(cc["variable"], cc["stage2_type"]))
    predictors = d["predictors"]

    # Provenance
    prov = provenance_checks(d)
    prov.to_csv(f"{OUT}/stage3_stage2_provenance_checks.csv", index=False)

    # Predictor roles
    roles = pd.DataFrame([
        {"predictor": p,
         "stage2_type": type_map.get(p, "unknown"),
         "role": "timing_sensitivity_only" if p in TIMING_SENSITIVITY_VARS else "main_candidate"}
        for p in predictors
    ])
    roles.to_csv(f"{OUT}/stage3_predictor_roles.csv", index=False)

    # Run all models
    all_rows = []
    fit_status = []
    for p in predictors:
        ptype = type_map.get(p, None)
        if ptype is None:
            fit_status.append({"predictor": p, "outcome": "all", "model": "all",
                               "status": "no_classification"})
            continue
        for fitter, df, name in [
            (lambda dfp: fit_logit_for(dfp, p, ptype), oy, "logit"),
            (lambda dfp: fit_cox_for(dfp, p, ptype),   sv, "cox"),
            (lambda dfp: fit_nb_for(dfp, p, ptype),    hp, "nb"),
        ]:
            rows, status = fitter(df)
            all_rows.extend(rows)
            fit_status.append(status)

    eff = pd.DataFrame(all_rows)
    fits = pd.DataFrame(fit_status)

    # BH within each outcome (term-level)
    if len(eff):
        eff["qvalue"] = np.nan
        for outc, grp in eff.groupby("outcome"):
            qs = bh_q(grp["pvalue"].values)
            eff.loc[grp.index, "qvalue"] = qs

        # Friendly column ordering
        col_order = ["outcome", "model", "predictor", "type", "term",
                     "level", "reference_level", "contrast",
                     "effect_label", "effect", "ci_lower", "ci_upper",
                     "beta", "se", "pvalue", "qvalue",
                     "n", "events", "person_years",
                     "n_nonmissing", "level_count", "ref_count", "mean", "sd",
                     "status"]
        for c in col_order:
            if c not in eff.columns: eff[c] = np.nan
        eff = eff[col_order + [c for c in eff.columns if c not in col_order]]
        eff.to_csv(f"{OUT}/stage3_univariable_effect_estimates.csv", index=False)

        # Variable-level summary: smallest p across terms within outcome
        var_summ = []
        for (pred, outc), grp in eff[eff["status"] == "ok"].groupby(["predictor", "outcome"]):
            i = grp["pvalue"].idxmin() if grp["pvalue"].notna().any() else None
            best = grp.loc[i] if i is not None else None
            var_summ.append({
                "predictor": pred,
                "outcome": outc,
                "n_terms": len(grp),
                "min_pvalue": float(grp["pvalue"].min()) if i is not None else np.nan,
                "min_qvalue": float(grp["qvalue"].min()) if i is not None else np.nan,
                "best_term": best["term"] if best is not None else "",
                "best_effect": best["effect"] if best is not None else np.nan,
                "best_ci_lower": best["ci_lower"] if best is not None else np.nan,
                "best_ci_upper": best["ci_upper"] if best is not None else np.nan,
                "best_contrast": best["contrast"] if best is not None else "",
                "n": best["n"] if best is not None else np.nan,
                "events": best["events"] if best is not None else np.nan,
            })
        var_summ_df = pd.DataFrame(var_summ)
        var_summ_df.to_csv(f"{OUT}/stage3_univariable_variable_summary.csv", index=False)

        # Triage table for Stage 4: wide format (variable rows, outcomes columns)
        if len(var_summ_df):
            triage_parts = []
            for outc in ["one_year_mortality", "survival", "hospitalization"]:
                sub = var_summ_df[var_summ_df["outcome"] == outc][[
                    "predictor", "best_effect", "best_ci_lower", "best_ci_upper",
                    "min_pvalue", "min_qvalue", "best_contrast"]].copy()
                rename = {c: f"{outc}__{c}" for c in sub.columns if c != "predictor"}
                sub = sub.rename(columns=rename)
                triage_parts.append(sub)
            triage = triage_parts[0]
            for s in triage_parts[1:]:
                triage = triage.merge(s, on="predictor", how="outer")
            # add role
            triage = triage.merge(roles[["predictor", "role", "stage2_type"]], on="predictor", how="left")
            ordered = ["predictor", "role", "stage2_type"] + [c for c in triage.columns
                                                              if c not in {"predictor","role","stage2_type"}]
            triage = triage[ordered]
            triage.to_csv(f"{OUT}/stage3_stage4_triage_table.csv", index=False)

    fits.to_csv(f"{OUT}/stage3_model_fit_status.csv", index=False)

    # Run metadata
    s1_main_path = f"{STAGE1}/stage1_main_predictor_list.csv"
    s2_meta_path = f"{STAGE2}/stage2_run_metadata.json"
    meta = {
        "stage": "stage3_univariable_screening",
        "implementation": "independent_local_run",
        "run_datetime_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "decisions_applied": ["DEC-052 (univariable screening only, no selection)",
                              "DEC-053 (3 outcomes)",
                              "DEC-054 (continuous standardized per 1 SD)",
                              "DEC-055 (categorical: most-frequent level reference, contrasts)",
                              "DEC-056 (NB alpha=1.0 screening approximation)",
                              "DEC-057 (BH FDR within outcome, advisory)",
                              "DEC-058 (q-values descriptive only)",
                              "DEC-059 (timing variables flagged sensitivity, not main)"],
        "stage1_input_dir": STAGE1,
        "stage2_input_dir": STAGE2,
        "stage2_version_label": d["s2_meta"].get("stage2_version_label"),
        "stage1_version_provenance": "FIXED_v2 (DEC-044)",
        "n_predictors_screened": len(predictors),
        "n_main_candidates": int(sum(p not in TIMING_SENSITIVITY_VARS for p in predictors)),
        "n_timing_sensitivity_only": int(sum(p in TIMING_SENSITIVITY_VARS for p in predictors)),
        "datasets": {
            "oneyear": {"n_rows": int(len(oy)), "outcome": "died_1year",
                        "events": int(oy["died_1year"].sum())},
            "survival": {"n_rows": int(len(sv)), "events": int(sv["event"].sum())},
            "hospitalization": {"n_rows": int(len(hp)),
                                "total_hosp": int(hp["hosp_total"].sum()),
                                "person_years": float(hp["followup_years"].sum())},
        },
        "models": {
            "one_year_mortality": "Logit (statsmodels)",
            "survival": "PHReg ties=efron (statsmodels Cox)",
            "hospitalization": "GLM NegativeBinomial alpha=1.0 with offset=log(followup_years)",
        },
        "input_hashes": {
            "stage1_main_predictor_list.csv": file_sha(s1_main_path),
            "stage2_run_metadata.json": file_sha(s2_meta_path),
        },
        "no_files_written_to_drive": True,
    }
    with open(f"{OUT}/stage3_run_metadata.json", "w") as f:
        json.dump(meta, f, indent=2)

    # Readiness report
    n_total = len(eff) if len(eff) else 0
    n_ok = int((eff["status"] == "ok").sum()) if n_total else 0
    n_failed = int((fits["status"].str.startswith("fit_failed").fillna(False)).sum())
    n_skipped = int(fits["status"].str.startswith("skipped").fillna(False).sum())
    md = []
    md.append("# Stage 3 readiness report (independent local run)")
    md.append("")
    md.append(f"Generated: {meta['run_datetime_utc']}")
    md.append(f"Stage 1 input: `{STAGE1}`")
    md.append(f"Stage 2 input: `{STAGE2}`")
    md.append(f"Stage 2 version label: `{meta['stage2_version_label']}`")
    md.append("")
    md.append("## Predictor inventory")
    md.append(f"- predictors screened: **{len(predictors)}**")
    md.append(f"- main_candidate: **{meta['n_main_candidates']}**")
    md.append(f"- timing_sensitivity_only: **{meta['n_timing_sensitivity_only']}** "
              f"({sorted(TIMING_SENSITIVITY_VARS & set(predictors))})")
    md.append("")
    md.append("## Cohorts and outcomes")
    for k, v in meta["datasets"].items():
        md.append(f"- **{k}**: {v}")
    md.append("")
    md.append("## Model run summary")
    md.append(f"- total term-level rows in effect estimates: {n_total}")
    md.append(f"- term rows with status=ok: {n_ok}")
    md.append(f"- model fits failed: {n_failed}")
    md.append(f"- model fits skipped (few obs/events/etc.): {n_skipped}")
    md.append("")
    md.append("## Methodological notes")
    md.append("- Continuous predictors are standardized; effects reported per 1 SD.")
    md.append("- Categorical predictors use the most frequent non-missing level "
              "as the reference, with explicit `term`, `reference_level`, `contrast`.")
    md.append("- Hospitalization model uses NB(alpha=1.0) with `offset(log(followup_years))`. "
              "alpha=1.0 is a screening approximation; final dispersion is estimated/validated in Stage 5.")
    md.append("- BH FDR q-values are reported within each outcome at the term level. "
              "q-values are descriptive only and must not drive variable selection.")
    md.append("- This run did NOT write anything to Google Drive.")
    md.append("")
    md.append("## Outputs")
    for fn in sorted(os.listdir(OUT)):
        md.append(f"- `{fn}`")
    with open(f"{OUT}/stage3_readiness_report.md", "w") as f:
        f.write("\n".join(md))

    print("DONE. Outputs in", OUT)
    print("- effect rows:", n_total, "| ok:", n_ok)
    print("- fits failed:", n_failed, "| skipped:", n_skipped)


if __name__ == "__main__":
    main()
