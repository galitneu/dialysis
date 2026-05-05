# Stage 3 readiness report (independent local run)

Generated: 2026-05-05T13:43:51Z
Stage 1 input: `/home/user/dialysis/outputs/params/stage1`
Stage 2 input: `/home/user/dialysis/outputs/params/stage2_DEC044_FIXED_v2`
Stage 2 version label: `stage2_DEC044_FIXED_v2`

## Predictor inventory
- predictors screened: **27**
- main_candidate: **26**
- timing_sensitivity_only: **1** (['days_echo_to_dialysis'])

## Cohorts and outcomes
- **oneyear**: {'n_rows': 617, 'outcome': 'died_1year', 'events': 239}
- **survival**: {'n_rows': 644, 'events': 505}
- **hospitalization**: {'n_rows': 644, 'total_hosp': 1177, 'person_years': 1623.4880219028064}

## Model run summary
- total term-level rows in effect estimates: 105
- term rows with status=ok: 105
- model fits failed: 0
- model fits skipped (few obs/events/etc.): 0

## Methodological notes
- Continuous predictors are standardized; effects reported per 1 SD.
- Categorical predictors use the most frequent non-missing level as the reference, with explicit `term`, `reference_level`, `contrast`.
- Hospitalization model uses NB(alpha=1.0) with `offset(log(followup_years))`. alpha=1.0 is a screening approximation; final dispersion is estimated/validated in Stage 5.
- BH FDR q-values are reported within each outcome at the term level. q-values are descriptive only and must not drive variable selection.
- This run did NOT write anything to Google Drive.

## Outputs
- `stage3_model_fit_status.csv`
- `stage3_predictor_roles.csv`
- `stage3_run_metadata.json`
- `stage3_stage2_provenance_checks.csv`
- `stage3_stage4_triage_table.csv`
- `stage3_univariable_effect_estimates.csv`
- `stage3_univariable_variable_summary.csv`