"""Stage 4a v3.1 - Predictor Lock-in Evidence & Committee Preparation.

Independent local re-implementation per the v3 spec PLUS the committee's v3.1
amendments (candidate-logic hierarchy, decision-basis fields, reviewer-2
defensibility notes, explicit outcome-relevance flags + rationales,
descriptive-only signal columns).

Stage 4a does NOT select variables. It produces an evidence package for a
clinically-informed committee lock-in. All final-decision fields are left
blank.

Inputs:
  outputs/params/stage2_DEC044_FIXED_v2/
  outputs/params/stage3_drive_v2/    # canonical Stage 3 with DEC-059B

Outputs:
  outputs/params/stage4a_local_run/
"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path("/home/user/dialysis/outputs/params")
STAGE2 = ROOT / "stage2_DEC044_FIXED_v2"
STAGE3 = ROOT / "stage3_drive_v2"
STAGE4 = ROOT / "stage4a_local_run"
STAGE4.mkdir(parents=True, exist_ok=True)

NOTEBOOK_VERSION = "stage4a_v3.1_local"
RUN_TS = datetime.now().isoformat(timespec="seconds")

TIMING_VARS = {"days_echo_to_dialysis", "echo_to_dialysis_timing_category"}

# ---------------------------------------------------------------- domain map

DOMAIN_MAP = {
    "AgeAtFirstHFDate": "Demographics",
    "m/f": "Demographics",
    "creatinine-numeric result": "Renal / labs / inflammation",
    "albumin-numeric result": "Renal / labs / inflammation",
    "hb-numeric result": "Renal / labs / inflammation",
    "crp-numeric result": "Renal / labs / inflammation",
    "LV_EF": "LV systolic function",
    "LeftVentricleEstimatedMassIndex": "LV structure / remodeling",
    "TissueDopplerEERatioSeptal": "Diastolic / filling pressure",
    "TissueDopplerEERatioLateral": "Diastolic / filling pressure",
    "TissueDopplerEVelositySeptal": "Diastolic / filling pressure",
    "TissueDopplerEVelosityLateral": "Diastolic / filling pressure",
    "MitralInflowPeakEWave": "Diastolic / filling pressure",
    "LACavitySize": "LA / chronic filling burden",
    "EstimatedSysPAPressure": "Pulmonary pressure / right-sided burden",
    "ECHO_SPAP": "Pulmonary pressure / right-sided burden",
    "tricuspid_regurgitation_clin_grouped": "Valvular disease",
    "mitral_regurgitation_clin_grouped": "Valvular disease",
    "AFIB_binary": "Comorbidity",
    "CABG_binary": "Comorbidity",
    "COPD_binary": "Comorbidity",
    "Diabetes mellitus_binary": "Comorbidity",
    "HTN_binary": "Comorbidity",
    "IHD_binary": "Comorbidity",
    "MI_binary": "Comorbidity",
    "HD/PD": "Dialysis modality",
    "days_echo_to_dialysis": "Echo timing / provenance",
    "echo_to_dialysis_timing_category": "Echo timing / provenance",
}

# ----------------------------------------- cardiology priorities & discovery

CARDIOLOGY_PRIORITIES = {
    "LV_EF": (
        "cardiology_prioritized",
        "Cardiology input",
        "Abnormal LV systolic function (EF) was prioritized by cardiology input.",
    ),
    "TissueDopplerEERatioSeptal": (
        "cardiology_prioritized",
        "Cardiology input",
        "Cardiology prioritized diastolic dysfunction; full Renal Lutati definitions "
        "were not feasible due to missing data, so septal E/e' is the available "
        "representative marker.",
    ),
    "EstimatedSysPAPressure": (
        "cardiology_prioritized",
        "Cardiology input",
        "Pulmonary pressure (continuous SPAP) was prioritized by cardiology input.",
    ),
    "ECHO_SPAP": (
        "cardiology_prioritized",
        "Cardiology input",
        "Categorical SPAP is the alternative pulmonary-pressure representation; do "
        "not include with EstimatedSysPAPressure simultaneously without a plan.",
    ),
    "tricuspid_regurgitation_clin_grouped": (
        "cardiology_prioritized",
        "Cardiology input",
        "Tricuspid regurgitation was prioritized by cardiology input and may "
        "reflect right-sided/pulmonary burden.",
    ),
    "LeftVentricleEstimatedMassIndex": (
        "literature_supported",
        "Literature (uremia/dialysis cohorts)",
        "LVMI is literature-supported as relevant in uremia/dialysis populations.",
    ),
    "LACavitySize": (
        "literature_supported",
        "Literature (uremia/dialysis cohorts)",
        "LA size is literature-supported as a chronic filling burden marker.",
    ),
    "MitralInflowPeakEWave": (
        "outcome_specific_novel",
        "Stage 3 hospitalization signal",
        "Peak E wave appeared relevant for hospitalization outcomes; should be "
        "considered an outcome-specific discovery candidate, not a primary "
        "mortality predictor.",
    ),
}

# committee-recommended candidate-logic taxonomy (v3.1)
LOGIC_CORE_ADJUSTMENT = {
    "AgeAtFirstHFDate", "m/f", "HD/PD",
    "Diabetes mellitus_binary", "HTN_binary", "IHD_binary",
}
LOGIC_PRIMARY_ECHO = {
    "LV_EF", "TissueDopplerEERatioSeptal", "EstimatedSysPAPressure",
    "ECHO_SPAP", "tricuspid_regurgitation_clin_grouped",
    "LeftVentricleEstimatedMassIndex", "LACavitySize",
}
LOGIC_OUTCOME_SPECIFIC = {"MitralInflowPeakEWave"}
LOGIC_TIMING = {"days_echo_to_dialysis", "echo_to_dialysis_timing_category"}


def candidate_logic_type(v: str) -> str:
    if v in LOGIC_TIMING:
        return "sensitivity_or_timing"
    if v in LOGIC_CORE_ADJUSTMENT:
        return "core_adjustment"
    if v in LOGIC_PRIMARY_ECHO:
        return "primary_echo_domain"
    if v in LOGIC_OUTCOME_SPECIFIC:
        return "outcome_specific_exploratory"
    return "primary_clinical_supporting"  # remaining echo/lab/comorbidity vars


# ----------------------------------------------------------------- helpers

def safe_read_csv(p: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(p)
    except Exception:
        return pd.DataFrame()


def best_row_per(eff: pd.DataFrame, fam: str, var: str) -> pd.Series | None:
    sub = eff[(eff.outcome_family == fam) & (eff.variable == var)]
    if sub.empty:
        return None
    sub = sub.copy()
    sub["_p_finite"] = sub["p_value"].fillna(1.0)
    return sub.loc[sub["_p_finite"].idxmin()]


# ----------------------------------------------------------------- inputs

predictor_roles = pd.read_csv(STAGE3 / "stage3_predictor_roles.csv")
col_class = pd.read_csv(STAGE2 / "stage2_column_classification.csv")
col_class_main = col_class[col_class.dataset == "main"].set_index("variable")["stage2_type"].to_dict()
eff = pd.read_csv(STAGE3 / "stage3_univariable_effect_estimates.csv")
audit = pd.read_csv(STAGE3 / "stage3_missing_handling_audit.csv")
stage2_meta = json.loads((STAGE2 / "stage2_run_metadata.json").read_text())
stage3_meta = json.loads((STAGE3 / "stage3_run_metadata.json").read_text())
mr_outcome = pd.read_csv(STAGE2 / "stage2_model_readiness_by_outcome.csv")
top30 = pd.read_csv(STAGE2 / "stage2_top30_spearman_correlations.csv")
collin = safe_read_csv(STAGE2 / "stage2_collinearity_flags.csv")
overlap = pd.read_csv(STAGE2 / "stage2_clinical_overlap_flags.csv")
miss_flags = safe_read_csv(STAGE2 / "stage2_missingness_flags.csv")
grouped_stab = safe_read_csv(STAGE2 / "stage2_grouped_category_stability.csv")

# ---------------------------------------------------------------- QA gates

qa_rows: list[dict] = []


def gate(g: str, status: str, severity: str, details: str):
    qa_rows.append({"gate": g, "status": status, "severity": severity, "details": details})


# Gate 1: Stage 2 critical files
crit_s2 = [
    "stage2_column_classification.csv", "stage2_model_readiness_by_outcome.csv",
    "stage2_clinical_overlap_flags.csv", "stage2_run_metadata.json",
]
miss_s2 = [f for f in crit_s2 if not (STAGE2 / f).exists()]
gate(
    "Gate 1 - Stage 2 critical files exist",
    "PASS" if not miss_s2 else "FAIL",
    "hard_stop" if miss_s2 else "info",
    "all present" if not miss_s2 else f"missing: {miss_s2}",
)

# Gate 2: Stage 3 critical files
crit_s3 = [
    "stage3_univariable_effect_estimates.csv", "stage3_predictor_roles.csv",
    "stage3_missing_handling_audit.csv", "stage3_run_metadata.json",
]
miss_s3 = [f for f in crit_s3 if not (STAGE3 / f).exists()]
gate(
    "Gate 2 - Stage 3 critical files exist",
    "PASS" if not miss_s3 else "FAIL",
    "hard_stop" if miss_s3 else "info",
    "all present" if not miss_s3 else f"missing: {miss_s3}",
)

# Gate 3: DEC-059B exists in Stage 3 metadata or audit
s3_meta_text = json.dumps(stage3_meta)
dec059b_present = (
    "DEC-059B" in s3_meta_text
    or (audit.get("missing_handling", pd.Series(dtype=str))
        .astype(str)
        .str.contains("variable_level_complete_case_for_predictor")
        .any())
)
gate(
    "Gate 3 - DEC-059B (categorical complete-case) enforced",
    "PASS" if dec059b_present else "FAIL",
    "hard_stop" if not dec059b_present else "info",
    (
        "DEC-059B explicit in Stage 3 metadata" if "DEC-059B" in s3_meta_text
        else "Inferred from missing_handling=variable_level_complete_case_for_predictor"
    ) if dec059b_present else "DEC-059B not detected",
)

# Gate 4: exactly 27 main candidates
n_main = int((predictor_roles.predictor_role == "main_candidate").sum())
n_timing = int((predictor_roles.predictor_role == "timing_sensitivity_only").sum())
gate(
    "Gate 4 - Exactly 27 main_candidate predictors",
    "PASS" if n_main == 27 else "FAIL",
    "hard_stop" if n_main != 27 else "info",
    f"main_candidate={n_main}, timing_sensitivity_only={n_timing}",
)

# Gate 5: no silent missing-as-reference
violations = audit[
    (audit.variable_type.fillna("") == "categorical")
    & (audit.n_missing_predictor > 0)
    & (audit.n_model >= audit.n_input_rows)
]
# our audit doesn't always have variable_type populated; also flag by
# missing_handling
silent = audit[
    (audit.n_missing_predictor > 0)
    & (~audit.missing_handling.astype(str).str.contains("complete_case_for_predictor"))
]
flagged = pd.concat([violations, silent]).drop_duplicates()
gate(
    "Gate 5 - No silent missing-as-reference coding",
    "PASS" if flagged.empty else "FAIL",
    "hard_stop" if not flagged.empty else "info",
    "All categoricals with missingness use variable-level complete-case." if flagged.empty
    else f"{len(flagged)} rows violate complete-case rule",
)

# Gate 6: all Stage 3 model fits succeeded
fail_fits = audit[~audit.status.astype(str).str.lower().isin({"ok"})]
gate(
    "Gate 6 - All Stage 3 univariable fits succeeded",
    "PASS" if fail_fits.empty else "WARN",
    "warning" if not fail_fits.empty else "info",
    f"{len(fail_fits)} non-ok fits" if not fail_fits.empty else "all 84 fits ok",
)

# Gate 7: term/reference/contrast columns documented in effect estimates
needed_cols = {"term", "reference_level", "contrast"}
have = needed_cols.issubset(set(eff.columns))
gate(
    "Gate 7 - Stage 3 contrasts documented (term/reference_level/contrast)",
    "PASS" if have else "FAIL",
    "hard_stop" if not have else "info",
    "columns present" if have else f"missing: {needed_cols - set(eff.columns)}",
)

# Gate 8: three outcome families
fams_present = set(eff.outcome_family.unique())
fams_required = {
    "one_year_mortality_logistic", "survival_cox", "hospitalization_negative_binomial",
}
gate(
    "Gate 8 - Three outcome families present",
    "PASS" if fams_required.issubset(fams_present) else "FAIL",
    "hard_stop" if not fams_required.issubset(fams_present) else "info",
    f"present: {sorted(fams_present)}",
)

qa_gates = pd.DataFrame(qa_rows)
qa_gates.to_csv(STAGE4 / "stage4a_committee_QA_gates.csv", index=False)

hard_stops = qa_gates[(qa_gates.severity == "hard_stop") & (qa_gates.status == "FAIL")]
if not hard_stops.empty:
    print("HARD STOP - QA gates failed:")
    print(hard_stops.to_string(index=False))
    raise SystemExit(1)

# -------------------------------------------------- predictor metadata frame

vars_all = predictor_roles["variable"].tolist()
role_map = dict(zip(predictor_roles.variable, predictor_roles.predictor_role))
type_map = dict(zip(predictor_roles.variable, predictor_roles.stage2_type))


def approx_df(var: str) -> int:
    vt = type_map.get(var, "categorical")
    if vt == "continuous":
        return 1
    # categorical: count observed levels in audit (subtract 1)
    sub = audit[audit.variable == var]
    if sub.empty:
        return 1
    # find #levels via effect_estimates (one row per non-ref level)
    n_levels_ne_ref = (eff[eff.variable == var].term.nunique())
    if n_levels_ne_ref > 0:
        # estimate per-outcome consistent: pick max across families
        per_fam = (
            eff[eff.variable == var]
            .groupby("outcome_family")["term"]
            .nunique()
        )
        return int(per_fam.max()) if not per_fam.empty else 1
    return 1


# ---------------------------------------------- soft correlations and overlap

soft_pairs = top30[top30.abs_rho >= 0.60].copy()
soft_pairs["domain_var1"] = soft_pairs.var1.map(DOMAIN_MAP).fillna("Other")
soft_pairs["domain_var2"] = soft_pairs.var2.map(DOMAIN_MAP).fillna("Other")
soft_pairs["review_question"] = (
    "Within domain " + soft_pairs.domain_var1
    + " (or pair " + soft_pairs.var1 + " / " + soft_pairs.var2
    + "): retain a single representative or split across main/sensitivity?"
)
soft_pairs.to_csv(STAGE4 / "stage4a_soft_correlation_review_table.csv", index=False)

# statistical collinearity (>=0.70) — empty here but emit headers
if collin.empty or "abs_rho" not in collin.columns:
    pd.DataFrame(columns=["var1", "var2", "spearman_rho", "abs_rho", "pairwise_n", "flag"]).to_csv(
        STAGE4 / "stage4a_statistical_collinearity_review_table.csv", index=False,
    )
else:
    collin.to_csv(STAGE4 / "stage4a_statistical_collinearity_review_table.csv", index=False)

# clinical overlap layer
overlap_out = overlap.copy()
overlap_out.to_csv(STAGE4 / "stage4a_clinical_overlap_review_table.csv", index=False)


def soft_partner_for(v: str) -> tuple[str, float]:
    rows = soft_pairs[(soft_pairs.var1 == v) | (soft_pairs.var2 == v)]
    if rows.empty:
        return ("", float("nan"))
    top = rows.loc[rows.abs_rho.idxmax()]
    other = top.var2 if top.var1 == v else top.var1
    return (other, float(top.abs_rho))


def overlap_summary_for(v: str) -> str:
    rows = overlap[((overlap.var1 == v) | (overlap.var2 == v)) & (overlap.advisory_flag.astype(str).str.lower() == "true")]
    if rows.empty:
        return "no overlap flag"
    parts = []
    for _, r in rows.iterrows():
        partner = r.var2 if r.var1 == v else r.var1
        parts.append(f"{partner} ({r.clinical_family})")
    return "overlap with: " + "; ".join(parts)


# ---------------------------------------------- evidence matrix and triage

FAMS = [
    ("one_year_mortality_logistic", "1y"),
    ("survival_cox", "survival"),
    ("hospitalization_negative_binomial", "hosp"),
]


def stage3_signal_summary(v: str) -> dict:
    out: dict[str, object] = {}
    for fam, short in FAMS:
        r = best_row_per(eff, fam, v)
        if r is None:
            out[f"best_effect_{short}"] = float("nan")
            out[f"best_p_{short}"] = float("nan")
            out[f"best_q_{short}"] = float("nan")
            out[f"best_contrast_{short}"] = ""
            out[f"effect_measure_{short}"] = ""
            continue
        out[f"best_effect_{short}"] = float(r["estimate"])
        out[f"best_p_{short}"] = float(r["p_value"])
        out[f"best_q_{short}"] = float(r["q_value_bh_within_outcome"])
        out[f"best_contrast_{short}"] = str(r["contrast"])
        out[f"effect_measure_{short}"] = str(r["effect_measure"])
    return out


def signal_phrase(estimate: float, p: float, measure: str, contrast: str) -> str:
    if not np.isfinite(p) or not np.isfinite(estimate):
        return "no estimate"
    direction = "elevated" if estimate > 1 else ("reduced" if estimate < 1 else "neutral")
    sig = "p<0.05" if p < 0.05 else ("p<0.10" if p < 0.10 else "p>=0.10")
    return f"{measure}={estimate:.3f} ({contrast}); {sig}; {direction}"


# build evidence matrix
ev_rows = []
for v in vars_all:
    role = role_map[v]
    vt = type_map[v]
    domain = DOMAIN_MAP.get(v, "Other")
    df_v = approx_df(v)

    # missingness from Stage 3 audit (max across outcomes)
    asub = audit[audit.variable == v]
    if asub.empty:
        miss_pct = float("nan")
        n_min = float("nan")
        n_miss_max = float("nan")
    else:
        miss_pct = float(asub.missing_predictor_pct.max())
        n_min = int(asub.n_model.min())
        n_miss_max = int(asub.n_missing_predictor.max())

    # missing pct from Stage 2 (sensitivity dataset rows are flagged separately;
    # for main predictors, derive from Stage 3 audit which is per main analytic
    # cohort)
    s3_sig = stage3_signal_summary(v)

    has_sig = {
        f"has_stage3_signal_{short}":
        bool(np.isfinite(s3_sig[f"best_p_{short}"]) and s3_sig[f"best_p_{short}"] < 0.05)
        for _, short in FAMS
    }
    consistent = sum(int(v_) for v_ in has_sig.values())
    any_p05 = any(
        np.isfinite(s3_sig[f"best_p_{short}"]) and s3_sig[f"best_p_{short}"] < 0.05
        for _, short in FAMS
    )
    any_q10 = any(
        np.isfinite(s3_sig[f"best_q_{short}"]) and s3_sig[f"best_q_{short}"] < 0.10
        for _, short in FAMS
    )

    # collinearity / overlap layers
    cr = collin if not collin.empty else pd.DataFrame()
    stat_collin = (
        not cr.empty
        and "var1" in cr.columns
        and ((cr.var1 == v) | (cr.var2 == v)).any()
    )
    soft_partner, soft_rho = soft_partner_for(v)
    soft_flag = bool(np.isfinite(soft_rho) and soft_rho >= 0.60)
    overlap_sum = overlap_summary_for(v)
    clin_overlap = overlap_sum != "no overlap flag"

    # cardiology / discovery
    if v in CARDIOLOGY_PRIORITIES:
        priority, p_src, p_reason = CARDIOLOGY_PRIORITIES[v]
    elif role == "timing_sensitivity_only":
        priority, p_src, p_reason = ("timing_sensitivity_only", "Methodological", "Timing/provenance variable; not a primary biological predictor.")
    elif domain == "Demographics" or v in {"HD/PD", "Diabetes mellitus_binary", "HTN_binary", "IHD_binary"}:
        priority, p_src, p_reason = ("core_adjustment", "Methodological", "Standard adjustment / confounder rationale; consider as core adjustment regardless of univariable signal.")
    elif any_p05 and v not in CARDIOLOGY_PRIORITIES:
        priority, p_src, p_reason = ("data_signal_discovery", "Stage 3 descriptive signal", "Univariable signal in at least one outcome; not a cardiology-prioritized variable.")
    else:
        priority, p_src, p_reason = ("overlap_representative", "Methodological", "Available main candidate; may serve as a domain representative pending committee review.")

    discovery_candidate = bool(any_p05 and v not in CARDIOLOGY_PRIORITIES and role == "main_candidate")
    innovation_potential = (
        "high" if v in {"MitralInflowPeakEWave"} or discovery_candidate
        else ("medium" if priority == "literature_supported" else "low")
    )
    plausibility = (
        "high" if priority in {"cardiology_prioritized", "literature_supported", "core_adjustment"}
        else ("medium" if priority in {"data_signal_discovery", "outcome_specific_novel"} else "uncertain")
    )
    novelty_rationale = (
        "Novel hospitalization-specific filling-pressure marker." if v == "MitralInflowPeakEWave"
        else (
            "Data-informed signal with clinical plausibility; warrants committee review."
            if discovery_candidate else
            ("Established/expected predictor." if priority in {"cardiology_prioritized", "core_adjustment"}
             else "")
        )
    )

    # candidate logic type (committee v3.1 hierarchy)
    logic = candidate_logic_type(v)

    # outcome-specific evidence-support flags + rationales (committee v3.1)
    relevance = {}
    rationale = {}
    for fam, short in FAMS:
        p = s3_sig[f"best_p_{short}"]
        est = s3_sig[f"best_effect_{short}"]
        contrast = s3_sig[f"best_contrast_{short}"]
        measure = s3_sig[f"effect_measure_{short}"]
        # outcome relevance is "supported" if descriptive signal OR cardiology
        # priority OR a core-adjustment rationale applies. It is NOT "selected".
        sig = np.isfinite(p) and p < 0.05
        supported = bool(
            sig
            or v in CARDIOLOGY_PRIORITIES
            or logic == "core_adjustment"
        )
        relevance[f"outcome_relevance_flag_{short}"] = "supported" if supported else "limited"
        # rationale per outcome
        bits = []
        if logic == "core_adjustment":
            bits.append("core adjustment / confounder")
        if v in CARDIOLOGY_PRIORITIES and short != "hosp":
            bits.append("cardiology prior")
        if v in CARDIOLOGY_PRIORITIES and short == "hosp" and v == "MitralInflowPeakEWave":
            bits.append("hospitalization-specific exploratory (filling pressure)")
        elif v == "MitralInflowPeakEWave" and short != "hosp":
            bits.append("not primary for this outcome; sensitivity only")
        if sig:
            bits.append(f"Stage 3 descriptive {signal_phrase(est, p, measure, contrast)}")
        elif np.isfinite(p):
            bits.append(f"Stage 3 descriptive p={p:.3f} (no signal)")
        if not bits:
            bits.append("limited evidence; committee discretion")
        rationale[f"rationale_{short}"] = "; ".join(bits)

    # preliminary recommendation (advisory; not a decision)
    if role == "timing_sensitivity_only":
        prelim = "timing_sensitivity_only"
    elif logic == "core_adjustment":
        prelim = "core_adjustment_candidate"
    elif priority == "cardiology_prioritized":
        prelim = "strong_clinical_echo_candidate"
    elif priority == "literature_supported":
        prelim = "literature_supported_echo_candidate"
    elif v == "MitralInflowPeakEWave":
        prelim = "outcome_specific_candidate_hospitalization"
    elif clin_overlap or soft_flag:
        prelim = "overlap_review_needed"
    elif discovery_candidate:
        prelim = "data_signal_discovery_candidate"
    elif np.isfinite(miss_pct) and miss_pct >= 0.20:
        prelim = "low_priority_or_sparse"
    else:
        prelim = "needs_committee_review"

    # committee_review_priority
    if prelim in {"core_adjustment_candidate", "strong_clinical_echo_candidate"}:
        review_pri = "high"
    elif prelim in {"literature_supported_echo_candidate", "outcome_specific_candidate_hospitalization", "data_signal_discovery_candidate"}:
        review_pri = "medium"
    elif prelim == "overlap_review_needed":
        review_pri = "medium"
    elif prelim == "timing_sensitivity_only":
        review_pri = "sensitivity"
    else:
        review_pri = "low"

    notes = ""
    if v == "MitralInflowPeakEWave":
        notes = "Strong NB hospitalization signal; consider hosp-specific use only."
    if soft_flag and not pd.isna(soft_partner) and soft_partner:
        notes = (notes + " " if notes else "") + (
            f"Soft Spearman correlation with {soft_partner} (|rho|={soft_rho:.2f}); "
            "split across main/sensitivity if needed."
        )

    row = {
        "variable": v,
        "predictor_role": role,
        "variable_type": vt,
        "clinical_domain": domain,
        "candidate_logic_type": logic,
        "approx_df": df_v,
        "max_missing_pct_stage3": miss_pct,
        "min_n_model_stage3": n_min,
        "n_missing_predictor_max": n_miss_max,
        **s3_sig,
        **has_sig,
        "consistent_signal_count": consistent,
        "any_p_below_0_05": any_p05,
        "any_q_below_0_10": any_q10,
        "clinical_overlap_flag": clin_overlap,
        "clinical_overlap_summary": overlap_sum,
        "statistical_collinearity_flag": stat_collin,
        "soft_correlation_flag": soft_flag,
        "top_soft_correlation_partner": soft_partner,
        "top_soft_correlation_abs_rho": soft_rho,
        "external_clinical_priority": priority,
        "external_clinical_priority_source": p_src,
        "external_clinical_priority_reason": p_reason,
        "evidence_source_type": (
            "cardiology_prior" if priority == "cardiology_prioritized"
            else ("literature_support" if priority == "literature_supported"
                  else ("data_signal" if discovery_candidate else
                        ("core_adjustment" if logic == "core_adjustment" else "supporting")))
        ),
        "data_signal_discovery_candidate": discovery_candidate,
        "innovation_potential": innovation_potential,
        "clinical_plausibility": plausibility,
        "novelty_rationale": novelty_rationale,
        "stage3_signal_is_descriptive_only": True,
        "inclusion_not_based_on_pvalue": True,
        **relevance,
        **rationale,
        "preliminary_recommendation": prelim,
        "committee_review_priority": review_pri,
        "notes_for_committee": notes,
    }
    ev_rows.append(row)

ev = pd.DataFrame(ev_rows)
ev.to_csv(STAGE4 / "stage4a_predictor_evidence_matrix.csv", index=False)

# ---------------------------------------------- EPV / capacity dashboard

oy = mr_outcome[mr_outcome.outcome == "one_year_mortality"].iloc[0]
sv = mr_outcome[mr_outcome.outcome == "survival"].iloc[0]
hp = mr_outcome[mr_outcome.outcome == "hospitalization"].iloc[0]

# total approx df only across main_candidates (timing handled separately)
main_df_total = int(ev[ev.predictor_role == "main_candidate"].approx_df.sum())
timing_df_total = int(ev[ev.predictor_role == "timing_sensitivity_only"].approx_df.sum())

epv_rows = [
    {
        "outcome": "one_year_mortality_logistic",
        "n": int(oy.n), "events": int(oy.n_events),
        "epv10_capacity_parameters": int(oy.recommended_max_predictors_epv10),
        "epv15_capacity_parameters": int(oy.recommended_max_predictors_epv15),
        "main_candidate_total_approx_df": main_df_total,
        "timing_sensitivity_total_approx_df": timing_df_total,
        "capacity_note": (
            "EPV-based capacity is a soft cap; final adjustment set must respect it."
        ),
    },
    {
        "outcome": "survival_cox",
        "n": int(sv.n), "events": int(sv.n_events),
        "epv10_capacity_parameters": int(sv.recommended_max_predictors_epv10),
        "epv15_capacity_parameters": int(sv.recommended_max_predictors_epv15),
        "main_candidate_total_approx_df": main_df_total,
        "timing_sensitivity_total_approx_df": timing_df_total,
        "capacity_note": "EPV-based capacity is a soft cap; final adjustment set must respect it.",
    },
    {
        "outcome": "hospitalization_negative_binomial",
        "n": int(hp.n), "events": int(hp.n_events),
        "epv10_capacity_parameters": "",
        "epv15_capacity_parameters": "",
        "main_candidate_total_approx_df": main_df_total,
        "timing_sensitivity_total_approx_df": timing_df_total,
        "capacity_note": (
            "NB capacity should be judged by convergence, dispersion, person-time, "
            f"total counts (n_events={int(hp.n_events)}), and model stability; "
            "classic EPV not directly applicable. "
            f"Stage 2 var/mean ratio={hp.overdispersion_ratio_var_over_mean:.2f}."
        ),
    },
]
pd.DataFrame(epv_rows).to_csv(STAGE4 / "stage4a_epv_capacity_dashboard.csv", index=False)

# df burden by domain
domain_rows = (
    ev.groupby("clinical_domain")
    .agg(
        n_variables=("variable", "count"),
        total_approx_df=("approx_df", "sum"),
        variables=("variable", lambda s: "; ".join(sorted(s))),
    )
    .reset_index()
    .sort_values("clinical_domain")
)
domain_rows.to_csv(STAGE4 / "stage4a_df_burden_by_domain.csv", index=False)

# ---------------------------------------------- missingness & n_model audit

audit_rows = []
top_miss_rows = []
for _, r in audit.iterrows():
    v = r.variable
    role = role_map.get(v, "")
    vt = type_map.get(v, "")
    pct = float(r.missing_predictor_pct or 0.0)
    if pct >= 0.20:
        astatus = "WARNING_HIGH_MISSINGNESS"
    elif (pd.notna(r.n_model) and pd.notna(r.n_input_rows)
          and r.n_missing_predictor > 0
          and r.n_model >= r.n_input_rows):
        astatus = "FAIL_SILENT_REFERENCE_RISK"
    else:
        astatus = "OK"
    row = {
        "variable": v,
        "predictor_role": role,
        "variable_type": vt,
        "outcome_family": r.outcome_family,
        "n_input_rows": int(r.n_input_rows),
        "n_available_predictor": int(r.n_available_predictor),
        "n_missing_predictor": int(r.n_missing_predictor),
        "missing_predictor_pct": pct,
        "n_model": int(r.n_model),
        "missing_handling": r.missing_handling,
        "audit_status": astatus,
    }
    audit_rows.append(row)
    if pct >= 0.10:
        top_miss_rows.append(row)

pd.DataFrame(audit_rows).to_csv(
    STAGE4 / "stage4a_missingness_and_n_model_audit_from_stage3.csv", index=False
)
pd.DataFrame(sorted(top_miss_rows, key=lambda x: -x["missing_predictor_pct"])).to_csv(
    STAGE4 / "stage4a_top_missingness_stage3_audit.csv", index=False
)

# ---------------------------------------------- cardiology + discovery review

card_rows = []
for v in vars_all:
    if role_map[v] == "timing_sensitivity_only":
        continue
    domain = DOMAIN_MAP.get(v, "Other")
    priority, p_src, p_reason = CARDIOLOGY_PRIORITIES.get(
        v, ("non_priority_main_candidate", "Methodological", "Available main candidate; not in cardiology priority list.")
    )
    s3_sig = stage3_signal_summary(v)
    sig_summary = "; ".join(
        f"{short}: " + signal_phrase(s3_sig[f"best_effect_{short}"], s3_sig[f"best_p_{short}"], s3_sig[f"effect_measure_{short}"], s3_sig[f"best_contrast_{short}"])
        for _, short in FAMS
    )
    overlap_sum = overlap_summary_for(v)
    sp, sr = soft_partner_for(v)
    if np.isfinite(sr):
        overlap_sum = f"{overlap_sum}; soft Spearman with {sp} (|rho|={sr:.2f})"
    discovery = (
        any(
            np.isfinite(s3_sig[f"best_p_{short}"]) and s3_sig[f"best_p_{short}"] < 0.05
            for _, short in FAMS
        )
        and v not in CARDIOLOGY_PRIORITIES
    )
    plaus = "high" if v in CARDIOLOGY_PRIORITIES or v in LOGIC_CORE_ADJUSTMENT else (
        "medium" if discovery else "uncertain"
    )
    inn = "high" if discovery or v == "MitralInflowPeakEWave" else (
        "medium" if priority == "literature_supported" else "low"
    )
    novelty = (
        "Hospitalization-specific filling-pressure exploratory candidate."
        if v == "MitralInflowPeakEWave"
        else ("Data-informed signal not in cardiology priors; warrants discussion." if discovery else "")
    )
    cq = (
        "Retain as cardiology prior; review missingness/overlap." if v in CARDIOLOGY_PRIORITIES
        else ("Retain as discovery candidate?" if discovery
              else ("Routine adjustment / confounder?" if v in LOGIC_CORE_ADJUSTMENT
                    else "Routine main candidate; representative or omit?"))
    )
    card_rows.append({
        "variable": v,
        "clinical_domain": domain,
        "external_clinical_priority": priority,
        "external_clinical_priority_source": p_src,
        "external_clinical_priority_reason": p_reason,
        "evidence_source_type": (
            "cardiology_prior" if priority == "cardiology_prioritized"
            else ("literature_support" if priority == "literature_supported"
                  else ("data_signal" if discovery else "supporting"))
        ),
        "data_signal_discovery_candidate": discovery,
        "innovation_potential": inn,
        "clinical_plausibility": plaus,
        "novelty_rationale": novelty,
        "stage3_signal_summary": sig_summary,
        "overlap_summary": overlap_sum,
        "committee_question": cq,
    })

card_df = pd.DataFrame(card_rows)
card_df.to_csv(STAGE4 / "stage4a_cardiology_priorities_and_discovery_review_table.csv", index=False)

# ---------------------------------------------- domain review table

domain_review_rows = []
DOMAIN_QUESTIONS = {
    "LV systolic function":
        "Should LV_EF alone represent systolic function?",
    "LV structure / remodeling":
        "Should LVMI be retained, or merged with systolic function?",
    "Diastolic / filling pressure":
        "Should TissueDopplerEERatioSeptal be the primary diastolic representative? "
        "Is MitralInflowPeakEWave hospitalization-specific only?",
    "LA / chronic filling burden":
        "Should LA size be retained as a separate chronic filling burden marker?",
    "Pulmonary pressure / right-sided burden":
        "Should pulmonary pressure (continuous SPAP vs categorical ECHO_SPAP) and TR both enter, or one held for sensitivity?",
    "Valvular disease":
        "Should TR be the primary valvular representative? Mitral regurgitation as secondary?",
    "Renal / labs / inflammation":
        "Which labs/inflammation markers (creatinine, albumin, hb, crp) form the renal/sepsis-burden adjustment set?",
    "Comorbidity":
        "Which comorbidities are core adjustments versus secondary?",
    "Demographics":
        "Confirm age/sex as core adjustment.",
    "Dialysis modality":
        "Confirm HD/PD as core adjustment.",
    "Echo timing / provenance":
        "Use timing variables only for sensitivity (not main).",
}

for dom, sub in ev.groupby("clinical_domain"):
    main_sub = sub[sub.predictor_role == "main_candidate"]
    strongest = (
        main_sub.assign(_min_p=main_sub[["best_p_1y", "best_p_survival", "best_p_hosp"]].min(axis=1))
        .sort_values("_min_p")
        .head(3)["variable"].tolist()
    )
    cardio = main_sub[main_sub.external_clinical_priority.isin({"cardiology_prioritized", "literature_supported"})].variable.tolist()
    discovery = main_sub[main_sub.data_signal_discovery_candidate].variable.tolist()
    overlaps = main_sub[main_sub.clinical_overlap_flag | main_sub.soft_correlation_flag].variable.tolist()
    domain_review_rows.append({
        "clinical_domain": dom,
        "variables_in_domain": "; ".join(sorted(sub.variable.tolist())),
        "n_variables": len(sub),
        "total_approx_df": int(sub.approx_df.sum()),
        "strongest_stage3_signals": "; ".join(strongest),
        "external_clinical_priorities": "; ".join(cardio),
        "discovery_candidates": "; ".join(discovery),
        "overlap_concerns": "; ".join(overlaps),
        "recommended_committee_question": DOMAIN_QUESTIONS.get(dom, ""),
    })
pd.DataFrame(domain_review_rows).to_csv(STAGE4 / "stage4a_domain_review_table.csv", index=False)

# ---------------------------------------------- timing sensitivity plan

timing_plan = pd.DataFrame([
    {
        "variable": "days_echo_to_dialysis",
        "role": "main_candidate (continuous timing)",
        "primary_model_use": "single timing covariate if needed; do not combine with category",
        "recommended_sensitivity_use": "compare with echo_to_dialysis_timing_category in sensitivity",
        "do_not_combine_with": "echo_to_dialysis_timing_category",
        "notes": "Continuous form preserves df=1 and avoids categorical degeneracy.",
    },
    {
        "variable": "echo_to_dialysis_timing_category",
        "role": "timing_sensitivity_only",
        "primary_model_use": "not in main models",
        "recommended_sensitivity_use": "categorical timing as sensitivity vs continuous form",
        "do_not_combine_with": "days_echo_to_dialysis",
        "notes": "Use to probe non-linearity / regime effects; do not include alongside continuous timing.",
    },
])
timing_plan.to_csv(STAGE4 / "stage4a_timing_sensitivity_plan.csv", index=False)

# ---------------------------------------------- committee lock-in template

LOCKIN_BLANKS = [
    "include_1y_main", "include_survival_main", "include_hosp_main",
    "sensitivity_only", "exclude_from_main",
    "final_decision", "decision_reason", "committee_notes",
    "representative_variable_reason",
    "retain_despite_not_cardiology_prioritized",
    "reason_to_exclude_despite_cardiology_priority",
    # v3.1 additions
    "final_include_1y", "final_include_survival", "final_include_hosp",
    "decision_basis", "decision_reason_free_text",
    "reviewer_defensibility_note",
]


def build_lockin_row(r: pd.Series, *, compact: bool) -> dict:
    common = {
        "variable": r["variable"],
        "predictor_role": r["predictor_role"],
        "clinical_domain": r["clinical_domain"],
        "candidate_logic_type": r["candidate_logic_type"],
        "variable_type": r["variable_type"],
        "approx_df": r["approx_df"],
        "max_missing_pct_stage3": r["max_missing_pct_stage3"],
        "min_n_model_stage3": r["min_n_model_stage3"],
        "best_signal_summary": (
            f"1y: {signal_phrase(r['best_effect_1y'], r['best_p_1y'], r['effect_measure_1y'], r['best_contrast_1y'])} | "
            f"survival: {signal_phrase(r['best_effect_survival'], r['best_p_survival'], r['effect_measure_survival'], r['best_contrast_survival'])} | "
            f"hosp: {signal_phrase(r['best_effect_hosp'], r['best_p_hosp'], r['effect_measure_hosp'], r['best_contrast_hosp'])}"
        ),
        "overlap_summary": r["clinical_overlap_summary"],
        "external_clinical_priority": r["external_clinical_priority"],
        "external_clinical_priority_reason": r["external_clinical_priority_reason"],
        "evidence_source_type": r["evidence_source_type"],
        "data_signal_discovery_candidate": r["data_signal_discovery_candidate"],
        "innovation_potential": r["innovation_potential"],
        "clinical_plausibility": r["clinical_plausibility"],
        "novelty_rationale": r["novelty_rationale"],
        "stage3_signal_is_descriptive_only": True,
        "inclusion_not_based_on_pvalue": True,
        "outcome_relevance_flag_1y": r["outcome_relevance_flag_1y"],
        "outcome_relevance_flag_survival": r["outcome_relevance_flag_survival"],
        "outcome_relevance_flag_hosp": r["outcome_relevance_flag_hosp"],
        "rationale_1y": r["rationale_1y"],
        "rationale_survival": r["rationale_survival"],
        "rationale_hosp": r["rationale_hosp"],
        "preliminary_recommendation": r["preliminary_recommendation"],
        "committee_review_priority": r["committee_review_priority"],
    }
    if not compact:
        common.update({
            "best_effect_1y": r["best_effect_1y"], "best_p_1y": r["best_p_1y"], "best_q_1y": r["best_q_1y"],
            "best_effect_survival": r["best_effect_survival"], "best_p_survival": r["best_p_survival"], "best_q_survival": r["best_q_survival"],
            "best_effect_hosp": r["best_effect_hosp"], "best_p_hosp": r["best_p_hosp"], "best_q_hosp": r["best_q_hosp"],
            "consistent_signal_count": r["consistent_signal_count"],
            "any_p_below_0_05": r["any_p_below_0_05"],
            "any_q_below_0_10": r["any_q_below_0_10"],
            "clinical_overlap_flag": r["clinical_overlap_flag"],
            "statistical_collinearity_flag": r["statistical_collinearity_flag"],
            "soft_correlation_flag": r["soft_correlation_flag"],
            "top_soft_correlation_partner": r["top_soft_correlation_partner"],
            "top_soft_correlation_abs_rho": r["top_soft_correlation_abs_rho"],
            "shared_core_candidate": r["candidate_logic_type"] == "core_adjustment",
            "outcome_specific_candidate": r["candidate_logic_type"] == "outcome_specific_exploratory",
            "sensitivity_model_candidate": r["candidate_logic_type"] == "sensitivity_or_timing",
            "recommended_missingness_strategy_stage5": (
                "MICE multiple imputation if main; otherwise complete-case sensitivity"
                if r["max_missing_pct_stage3"] >= 0.10 else "complete-case acceptable"
            ),
            "reviewer2_risk_flag": (
                "watch for p-value-driven appearance"
                if r["data_signal_discovery_candidate"] else ""
            ),
        })
    for f in LOCKIN_BLANKS:
        common[f] = ""
    return common


full_template = pd.DataFrame([build_lockin_row(r, compact=False) for _, r in ev.iterrows()])
full_template.to_csv(STAGE4 / "stage4a_committee_lockin_template.csv", index=False)

compact_template = pd.DataFrame([build_lockin_row(r, compact=True) for _, r in ev.iterrows()])
compact_template.to_csv(STAGE4 / "stage4a_committee_lockin_template_COMPACT.csv", index=False)

# ---------------------------------------------- decision log + status

decisions = [
    ("DEC-060", "Stage 4a is evidence preparation, not automated variable selection."),
    ("DEC-061", "Model capacity is evaluated using approximate degrees of freedom, not only predictor names."),
    ("DEC-062", "Stage 3 p-values/q-values are descriptive only."),
    ("DEC-063", "Predictors are grouped into clinical domains/families."),
    ("DEC-064", "Statistical collinearity, soft correlations, and clinical overlap are reviewed as separate layers."),
    ("DEC-065", "Timing variables are adjustment/sensitivity candidates, not ordinary main predictors."),
    ("DEC-066", "LASSO/penalized regression may be used later only as sensitivity analysis."),
    ("DEC-067", "Final model specs are generated only after explicit committee lock-in decisions."),
    ("DEC-068", "Stage 3 DEC-059B is a prerequisite for Stage 4a."),
    ("DEC-069", "Stage 4a includes missingness/n_model audit to prevent silent missing-as-reference errors."),
    ("DEC-070", "Stage 4a outputs a committee lock-in template with blank final decision fields."),
    ("DEC-071", "Stage 4a explicitly balances cardiology-prioritized predictors with data-informed discovery candidates."),
    ("DEC-071A", "v3.1: Candidate-logic hierarchy (core_adjustment / primary_echo_domain / outcome_specific_exploratory / sensitivity_or_timing / primary_clinical_supporting) documented per predictor."),
    ("DEC-071B", "v3.1: Outcome-relevance flags + per-outcome rationales replace any 'selected_for_outcome' framing; final include columns left blank."),
    ("DEC-071C", "v3.1: Lock-in template includes decision_basis, decision_reason_free_text, and reviewer_defensibility_note as required justification fields."),
]
pd.DataFrame(decisions, columns=["decision_id", "decision"]).to_csv(
    STAGE4 / "stage4a_decision_log_DEC060_DEC071.csv", index=False
)

# Status snapshot
n_main_can = int((ev.predictor_role == "main_candidate").sum())
n_timing_can = int((ev.predictor_role == "timing_sensitivity_only").sum())
status = pd.DataFrame([{
    "stage": "Stage 4a v3.1",
    "qa_pass": (qa_gates.status == "PASS").all() or (
        not (qa_gates[qa_gates.severity == "hard_stop"].status == "FAIL").any()
    ),
    "n_main_candidates": n_main_can,
    "n_timing_sensitivity_only": n_timing_can,
    "lockin_template_blanks_kept": True,
    "dec_059b_enforced": dec059b_present,
}])
status.to_csv(STAGE4 / "stage4a_status.csv", index=False)

# ---------------------------------------------- run metadata

meta = {
    "stage": "Stage 4a",
    "notebook_version": NOTEBOOK_VERSION,
    "run_timestamp": RUN_TS,
    "stage2_input_dir": str(STAGE2),
    "stage3_input_dir": str(STAGE3),
    "stage4a_output_dir": str(STAGE4),
    "required_decisions": [
        "DEC-059B",
        "DEC-060", "DEC-061", "DEC-062", "DEC-063", "DEC-064", "DEC-065",
        "DEC-066", "DEC-067", "DEC-068", "DEC-069", "DEC-070", "DEC-071",
        "DEC-071A", "DEC-071B", "DEC-071C",
    ],
    "qa_gate_summary": qa_gates[["gate", "status", "severity"]].to_dict(orient="records"),
    "n_main_candidates": n_main_can,
    "n_timing_sensitivity": n_timing_can,
    "committee_lockin_template_final_decision_fields_blank": LOCKIN_BLANKS,
    "outputs_created": [
        "stage4a_committee_QA_gates.csv",
        "stage4a_predictor_evidence_matrix.csv",
        "stage4a_committee_lockin_template.csv",
        "stage4a_committee_lockin_template_COMPACT.csv",
        "stage4a_epv_capacity_dashboard.csv",
        "stage4a_df_burden_by_domain.csv",
        "stage4a_missingness_and_n_model_audit_from_stage3.csv",
        "stage4a_top_missingness_stage3_audit.csv",
        "stage4a_soft_correlation_review_table.csv",
        "stage4a_clinical_overlap_review_table.csv",
        "stage4a_statistical_collinearity_review_table.csv",
        "stage4a_cardiology_priorities_and_discovery_review_table.csv",
        "stage4a_domain_review_table.csv",
        "stage4a_timing_sensitivity_plan.csv",
        "stage4a_decision_log_DEC060_DEC071.csv",
        "stage4a_status.csv",
        "stage4a_run_metadata.json",
        "stage4a_readiness_report.md",
    ],
    "stage2_version_label": stage2_meta.get("stage2_version_label", ""),
    "stage3_decisions_marker": stage3_meta.get("decisions_marker", ""),
}
(STAGE4 / "stage4a_run_metadata.json").write_text(json.dumps(meta, indent=2))

# ---------------------------------------------- readiness report

lines = [
    "# Stage 4a v3.1 readiness report",
    f"Generated: {RUN_TS}",
    "",
    "## Purpose",
    "Evidence preparation for clinically-informed predictor lock-in. **Not** "
    "variable selection. Final inclusion is left to the committee.",
    "",
    "## Inputs",
    f"- Stage 2: {STAGE2}",
    f"- Stage 3: {STAGE3} (DEC-059B enforced: complete-case for categorical predictors)",
    "",
    "## QA gates",
    "```",
    qa_gates.to_string(index=False),
    "```",
    "",
    f"## Predictor counts",
    f"- main_candidate: {n_main_can}",
    f"- timing_sensitivity_only: {n_timing_can}",
    "",
    "## EPV / capacity",
    "```",
    pd.DataFrame(epv_rows).to_string(index=False),
    "```",
    "",
    "## Df burden by domain",
    "```",
    domain_rows.to_string(index=False),
    "```",
    "",
    "## Missingness / n_model audit summary",
    f"- variable-outcome rows: {len(audit_rows)}",
    f"- WARNING_HIGH_MISSINGNESS rows: "
    f"{sum(1 for r in audit_rows if r['audit_status']=='WARNING_HIGH_MISSINGNESS')}",
    f"- FAIL_SILENT_REFERENCE_RISK rows: "
    f"{sum(1 for r in audit_rows if r['audit_status']=='FAIL_SILENT_REFERENCE_RISK')}",
    "",
    "## Statistical collinearity (Spearman |rho|>=0.70)",
    f"- flagged pairs: {0 if collin.empty or 'abs_rho' not in collin.columns else int((collin.abs_rho>=0.70).sum())}",
    "",
    "## Soft correlations (|rho|>=0.60)",
    f"- pairs: {len(soft_pairs)}",
    "",
    "## Clinical overlap (Stage 2 advisory layer)",
    f"- advisory_flag rows: {int((overlap.advisory_flag.astype(str).str.lower()=='true').sum())}",
    "",
    "## Cardiology priorities (8 markers across 5 themes)",
    "Cardiology-prioritized: LV_EF, TissueDopplerEERatioSeptal, EstimatedSysPAPressure, "
    "ECHO_SPAP, tricuspid_regurgitation_clin_grouped. "
    "Literature-supported: LeftVentricleEstimatedMassIndex, LACavitySize. "
    "Outcome-specific discovery: MitralInflowPeakEWave (hospitalization).",
    "",
    "## Discovery candidates (data signal in >=1 outcome and not cardiology-prior)",
    "```",
    ev[ev.data_signal_discovery_candidate][[
        "variable", "clinical_domain", "candidate_logic_type", "any_p_below_0_05",
    ]].to_string(index=False),
    "```",
    "",
    "## Reviewer 2 risk mitigation",
    "1. Stage 4a is **not** automated variable selection.",
    "2. p-values and q-values are descriptive only (DEC-062).",
    "3. Clinical priors do **not** eliminate discovery candidates.",
    "4. Discovery candidates are **not** selected by p-value alone; they require "
    "clinical plausibility and non-redundancy.",
    "5. Stage 3 used variable-level complete-case (DEC-059B); the Stage 5 "
    "missingness strategy will be documented separately.",
    "6. Penalized regression (LASSO) is reserved for sensitivity analyses (DEC-066).",
    "7. Outcome-specific evidence is documented per outcome with explicit rationale; "
    "shared core adjustment set will be discussed separately.",
    "8. Final inclusion requires `decision_basis` and `decision_reason_free_text` "
    "in the committee lock-in template.",
    "",
    "## Committee instruction",
    "```",
    "Stage 4a does not finalize model predictors.",
    "Committee lock-in decisions are required before Stage 5.",
    "```",
]
(STAGE4 / "stage4a_readiness_report.md").write_text("\n".join(lines))

print("Stage 4a v3.1 outputs written to:", STAGE4)
print(f"  predictor evidence matrix: {len(ev)} rows")
print(f"  committee_lockin_template (full): {full_template.shape}")
print(f"  committee_lockin_template_COMPACT: {compact_template.shape}")
print(f"  QA gates: {len(qa_gates)} (pass={int((qa_gates.status=='PASS').sum())})")
