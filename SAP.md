# Restart Locked Exploratory Analysis Plan
**Echocardiographic risk stratification beyond LVEF in HF patients initiating dialysis**

> **Framing**: This is a *retrospective exploratory* risk stratification study. Univariable
> associations are used for **screening and description**, not for confirmatory inference.
> All p-values are descriptive. No external validation. Internal validation only.
> This plan is a **restart locked plan** — not a true pre-specified SAP, since the data
> has been previously inspected. It is a discipline imposed at the restart point.

## Lock-in principles

1. **EF is a fixed benchmark**, not just one variable in a clinical axis. All models include EF; analysis tests "what adds beyond EF".
2. **TR is part of the right-heart / congestion axis** (with SPAP, RV size, RV systolic function), not the valves axis.
3. **Category merging is pre-outcome and clinician-driven only.** It is performed at Stage 1 with no reference to outcomes.
4. **Stage 3 screening is descriptive and hypothesis-generating**; it does not automatically select variables by p-value threshold.
5. **Stage 4 is real lock-in**: candidate models freeze. Anything added after = post-hoc.
6. **Primary analyses are complete-case** with explicit N. **MICE** is sensitivity only.
7. **Decision log includes `OUTCOME_INFORMED` flag** for every decision — pre/post outcome screening.
8. **Models are small.** Max 1 representative per clinical axis. EPV ≥ 10.

## Stages

```
Stage 0  →  Data audit & variable inventory          [STOP-1]
Stage 1  →  Clinician category harmonization (pre-outcome)  [STOP-2]
Stage 2  →  Descriptive cohort & outcomes
Stage 3  →  Exploratory univariable screening (descriptive only)
Stage 4  →  Candidate selection meeting (clinical + screening) [STOP-3 = LOCK-IN]
Stage 5  →  Multivariable candidate models (≤ 3 echo additions per model)
Stage 6  →  Sensitivity analyses
Stage 7  →  Clinical translation / risk profiles
```

## Outcomes (locked)

| Outcome | Definition | Model | Primary/Secondary |
|---|---|---|---|
| 1-year all-cause mortality | binary at 365d | Logistic regression | **Primary 1** |
| Hospitalization rate | `hosp_total` per person-year FU | Poisson GLM, `offset = log(FU_yrs)`, HC1 robust SE | **Primary 2** |
| Time-to-death (full FU) | days from dialysis start | Cox PH | Secondary |

## Cohort (locked)

- **Primary**: echo within 365 days before, or on the day of, dialysis start (n≈528)
- **Sensitivity**: 90d (n≈224), 30d (n≈135), all-comers including post-dialysis echo (n=645)

## Clinical axes (locked)

| Axis | Variables (post-merging) | Notes |
|---|---|---|
| Benchmark (fixed) | LVEF | Always in every model |
| LV systolic (other) | S′ septal/lateral, LV systolic function (cat) | Beyond EF |
| LV diastolic / filling | E/e′ avg/septal/lateral, e′ septal/lateral, E-wave | One representative per model |
| LV structure / mass | LVMI, IVS, PW thickness, LVEDD, LVESD, LV mass, LV cavity size, LV wall thickness | One representative |
| LA / atrial | LA cavity size | Single variable |
| **Right-heart / congestion** | **TR, SPAP numeric, ECHO_SPAP cat, RV size, RV systolic function** | One representative — **TR moved here** |
| Valves | MR; AR (if in data); AV structure (if in data) | One representative |

## Base clinical models (both reported)

| Base | Variables |
|---|---|
| **Parsimonious (A)** | Age, sex, creatinine, echo_to_dialysis_days |
| **Full (B)** | + HD/PD, IHD, AFib, DM, HTN, COPD, MI, CABG, albumin, GFR, Hb, CRP |

EF is added to both as benchmark.

## Multivariable rules

- Max **3 echo additions** beyond base + EF in any primary model
- One representative per clinical axis
- Forward selection guided by clinical reasoning + screening signal
- LASSO / group LASSO as sensitivity for variable selection
- **EF stays in all models regardless of statistical significance** (it is the benchmark)

## Variable status classification

| Status | Definition |
|---|---|
| **Core clinical** | Pre-specified by cardiologists |
| **Candidate** | Fits clinical axis AND showed signal in screening |
| **Sensitivity** | Relevant but limited by missingness or overlap |
| **Descriptive only** | Reported but not modeled |
| **Excluded** | Not relevant / too missing / unreliable |

## Missing data

- **Primary**: complete-case per analysis, with explicit N reporting
- **Sensitivity**: MICE m=10 with Rubin pooling for top candidates
- Median/mode imputation **not** used as primary

## Multiple comparisons

- Univariable screening: BH-FDR within each outcome family
- Incremental tests: BH-FDR within each {outcome × base}
- Final candidate models: descriptive p-values only — exploratory framing

## Decision log fields

```
ID | DATE | STAGE | DECIDED_BY | DECISION | RATIONALE | SOURCE | OUTCOME_INFORMED (Y/N)
```

## STOP points

| # | After stage | What is shown for approval |
|---|---|---|
| **STOP-1** | 0 (Audit) | Full variable inventory, missingness, axis classification |
| **STOP-2** | 1 (Merging) | Final category mapping per variable |
| **STOP-3** | 4 (Lock-in) | Candidate variable list + chosen multivariable structure |
| **STOP-4** | 5 (Models) | Model coefficients before sensitivity |
| **STOP-5** | 6 (Sensitivity) | Sensitivity-corrected metrics |
| **STOP-6** | 7 (Final) | Draft final report |

## Final pre-specified deliverables

- `SAP.md` (this document, frozen)
- `DECISION_LOG.md` (running)
- `00_audit.csv`, `01_category_merging.json`
- `02_univariable_screen.csv`
- `03_candidate_lockin.md`
- `04_final_models.csv`, `05_sensitivity_*.csv`
- `bootstrap_*.csv`
- `FINAL_REPORT.md`
- All Python scripts (seed=42, reproducible)

## Sign-off

This plan represents the agreed restart framework. Any deviation requires an entry in the decision log.

Plan locked: 2026-05-04 (Stage 0 commencing).
