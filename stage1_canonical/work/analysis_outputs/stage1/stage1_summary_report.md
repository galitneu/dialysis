# Stage 1 Summary Report

Generated: 2026-05-05T10:52:49
Input: `stage0_updated_clean_flat.csv`
Input rows/columns: 645 / 91

## Key decisions applied
- DEC-038: Missing comorbidity documentation interpreted as absence for binary covariates.
- DEC-039: Unusable echo values treated as missing/effective missing, not normal.
- DEC-040: Same-calendar-date echo/death or echo-after-death excluded from analytic cohorts and reported.
- DEC-041: No maximum echo-to-dialysis gap cutoff at Stage 1; distribution exported for clinician review.
- DEC-042: Echo free-text fields retained for future text/NLP review, not modeled now.
- DEC-043: Echo category distributions before/after clinician grouping exported.

## Cohort sizes
| dataset                              |   n_rows |   n_cols |
|:-------------------------------------|---------:|---------:|
| input_full                           |      645 |      107 |
| analysis_base_after_DEC040_exclusion |      644 |      107 |
| stage1_main_analysis                 |      644 |       35 |
| stage1_oneyear_mortality             |      617 |       31 |
| stage1_survival_analysis             |      644 |       32 |
| stage1_hospitalization_analysis      |      644 |       34 |
| stage1_sensitivity_analysis          |      644 |       65 |

## Exclusion summary
| metric                             |   n |   pct_of_645 |
|:-----------------------------------|----:|-------------:|
| n_echo_after_death                 |   0 |         0    |
| n_echo_same_day_as_death           |   1 |         0.16 |
| n_excluded_same_day_or_after_death |   1 |         0.16 |

## Outputs
- `stage1_categorical_counts_before_after.csv`
- `stage1_clinician_category_mapping_applied.csv`
- `stage1_cohort_summary.csv`
- `stage1_comorbidity_binary_check.csv`
- `stage1_echo_effective_missingness.csv`
- `stage1_echo_to_dialysis_extreme_gaps.csv`
- `stage1_echo_to_dialysis_timing_categories.csv`
- `stage1_echo_to_dialysis_timing_summary.csv`
- `stage1_exclusions_log.csv`
- `stage1_exclusions_summary.csv`
- `stage1_exploratory_analysis.csv`
- `stage1_hospitalization_analysis.csv`
- `stage1_input_validation.csv`
- `stage1_main_analysis.csv`
- `stage1_main_predictor_list.csv`
- `stage1_missingness_report.csv`
- `stage1_oneyear_mortality.csv`
- `stage1_outlier_action_log.csv`
- `stage1_predictor_list_exclusions.csv`
- `stage1_run_metadata.json`
- `stage1_sensitivity_analysis.csv`
- `stage1_sensitivity_exploratory_predictor_list.csv`
- `stage1_survival_analysis.csv`
- `stage1_text_fields_retention_log.csv`
- `stage1_variable_processing_log.csv`