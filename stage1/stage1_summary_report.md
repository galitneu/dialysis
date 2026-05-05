# Stage 1 (Notebook 1) — Summary report

**Run**: 2026-05-05T10:45:58.789100
**Source**: `stage0_updated_clean_flat.csv` (md5 `85b3eeeb42a718453c8ba35ffc2159fc`)

## Cohort flow

| Step | n |
|---|---|
| Source patients | 645 |
| Excluded by DEC-040 (echo same-day or after death) | 1 (echo_after_death=0, echo_same_day=1) |
| Eligible base (not excluded) | 644 |
| 1-year mortality cohort (`died_1year` ∈ {0,1}) | 617 (events = 239) |
| Survival cohort | 644 (events = 505) |
| Hospitalization cohort | 644 (total hosp = 1177) |

## Decisions applied
- **DEC-029**: source-of-truth = `stage0_updated_clean_flat.csv`
- **DEC-030**: outliers flagged, not central-imputed; in analytic data the implausible cell → NaN; patient retained
- **DEC-031**: outcome / admin / follow-up columns are not predictors
- **DEC-032**: `days_echo_to_dialysis` is the single canonical timing covariate
- **DEC-033**: `RVSize`, `RVSystolicFunction`, `AorticValveRegurgitation` → exploratory/sensitivity only
- **DEC-034**: GFR not used together with creatinine (creatinine kept; GFR moved to sensitivity)
- **DEC-035**: SBP, DBP → sensitivity/descriptive only
- **DEC-036**: `years_since_MI` → exploratory only
- **DEC-037**: clinician-approved category mapping applied to 11 echo categorical vars (3 unchanged, 8 collapsed)
- **DEC-038**: comorbidity NaN = no condition (binary indicators created upstream; verified)
- **DEC-039**: "No Value" / "See below" → missing, not Normal
- **DEC-040**: same-day or after-death echo excluded from analytic cohort
- **DEC-041**: no maximum echo→dialysis cutoff; distribution and predefined categories produced
- **DEC-042**: free-text echo summaries retained but not used as predictors
- **DEC-043**: original variables preserved; `<var>_clin_grouped` parallel; counts before/after reported

## Outlier actions (DEC-030)
variable side  value_before  threshold
     BMI  low      3.746098         12
     BMI high     81.216160         70

## Echo-to-dialysis timing distribution

```
       category   n  pct
 after_dialysis 107 16.6
       same_day  11  1.7
   before_0_30d 132 20.5
  before_31_90d  90 14.0
 before_91_180d  95 14.7
before_181_365d 209 32.4
 before_gt_365d   1  0.2
        missing   0  0.0
```

## Variables and roles

| Group | n | source |
|---|---|---|
| Main predictors  | 27 | Stage 0 final |
| Sensitivity      | 30 | Stage 0 final |
| Excluded         | 45 | Stage 0 final |
| Free-text retained (DEC-042) | 4 | n/a (descriptive) |

## Open items still requiring confirmation
- **OPEN-002**: confirm 2025-08-16 as the official administrative censor date (currently provisional). Does not block analytic computations.

## Files produced
- `notebook1_stage1.py`
- `stage1_categorical_counts_before_after.csv`
- `stage1_clinician_category_mapping_applied.csv`
- `stage1_comorbidity_binary_check.csv`
- `stage1_echo_effective_missingness.csv`
- `stage1_echo_to_dialysis_extreme_gaps.csv`
- `stage1_echo_to_dialysis_timing_categories.csv`
- `stage1_echo_to_dialysis_timing_summary.csv`
- `stage1_exclusions_log.csv`
- `stage1_exploratory_analysis.csv`
- `stage1_hospitalization_analysis.csv`
- `stage1_input_validation.csv`
- `stage1_main_analysis.csv`
- `stage1_missingness_report.csv`
- `stage1_oneyear_mortality.csv`
- `stage1_outlier_action_log.csv`
- `stage1_run_metadata.json`
- `stage1_sensitivity_analysis.csv`
- `stage1_survival_analysis.csv`
- `stage1_variable_processing_log.csv`
