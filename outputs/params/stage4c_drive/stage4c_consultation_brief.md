
# Stage 4c Consultation Brief — DEC-093

Generated: 2026-05-06T11:40:56

## Status

These analyses are **not final Stage 5 models**. They were generated after Stage 4b identified unresolved feasibility issues and are intended for consultation with a biostatistician and nephrologist.

## Study aim

Evaluate whether echocardiographic parameters around dialysis initiation improve risk stratification for mortality and hospitalization burden beyond LV_EF alone.

## Model tiers evaluated

- Model B: clinical baseline + LV_EF
- C-minimal: Model B + E/e′ septal
- C-lite: Model B + E/e′ septal + EstimatedSysPAPressure + LACavitySize
- C-full: Model B + E/e′ septal + EstimatedSysPAPressure + TR + LACavitySize

## Key questions for consultation

1. Should C-minimal complete-case be the primary model, with C-lite/C-full as mandatory MI sensitivity?
2. Or should C-lite/C-full with MI become primary due to high complete-case loss?
3. For hospitalization burden, is NB acceptable as primary with ZINB/Hurdle sensitivity, or should a zero-inflated/hurdle model be preferred?
4. How should the albumin PH warning in Cox be handled in Stage 5?
5. Does C-minimal preserve enough clinical meaning for the question of incremental value beyond EF?
6. If C-lite/C-full lose too many patients, are any lower-missingness substitutes clinically acceptable within the same echo domain?

## Feasibility summary

| outcome            | model_tier   | model_type        |   n_complete |   complete_case_loss_pct |   df |   events_per_df_or_counts_per_df | convergence_status   | warnings                 |
|:-------------------|:-------------|:------------------|-------------:|-------------------------:|-----:|---------------------------------:|:---------------------|:-------------------------|
| one_year_mortality | Model_B      | logistic          |          612 |                 0.810373 |    6 |                          39.5    | OK                   |                          |
| survival           | Model_B      | cox               |          639 |                 0.776398 |    6 |                          83.5    | OK                   |                          |
| hospitalization    | Model_B      | negative_binomial |          639 |                 0.776398 |    6 |                         194      | OK                   | Pearson_dispersion=7.817 |
| one_year_mortality | C_minimal    | logistic          |          497 |                19.4489   |    7 |                          26.4286 | OK                   |                          |
| survival           | C_minimal    | cox               |          518 |                19.5652   |    7 |                          57.8571 | OK                   |                          |
| hospitalization    | C_minimal    | negative_binomial |          518 |                19.5652   |    7 |                         136.429  | OK                   | Pearson_dispersion=4.516 |
| one_year_mortality | C_lite       | logistic          |          398 |                35.4943   |   10 |                          16.4    | OK                   |                          |
| survival           | C_lite       | cox               |          415 |                35.559    |   10 |                          34      | OK                   |                          |
| hospitalization    | C_lite       | negative_binomial |          415 |                35.559    |   10 |                          78.1    | OK                   | Pearson_dispersion=7.261 |
| one_year_mortality | C_full       | logistic          |          391 |                36.6288   |   11 |                          14.8182 | OK                   |                          |
| survival           | C_full       | cox               |          408 |                36.646    |   11 |                          30.4545 | OK                   |                          |
| hospitalization    | C_full       | negative_binomial |          408 |                36.646    |   11 |                          69.6364 | OK                   | Pearson_dispersion=7.348 |

## Output files

- `stage4c_model_feasibility_summary.csv`
- `stage4c_completecase_estimates.csv`
- `stage4c_completecase_vs_MI_comparison.csv`
- `stage4c_hospitalization_model_comparison.csv`
- `stage4c_hospitalization_zero_outlier_diagnostics.csv`
- `stage4c_missingness_impact.csv`
- `stage4c_candidate_substitution_due_to_missingness.csv`
- `stage4c_candidate_substitution_missingness_long.csv`
- `stage4c_cox_ph_consultation_status.csv`

## Interpretation guardrail

Do not choose the final Stage 5 primary model solely because a p-value or estimate looks favorable. Stage 4c is for consultation regarding missingness, robustness, and count-model specification.
