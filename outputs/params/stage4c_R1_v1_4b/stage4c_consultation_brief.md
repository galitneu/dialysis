
# Stage 4c Consultation Brief — DEC-093-R1 v1.4 Committee-Checked

Generated: 2026-05-06T15:00:19

## Status

These analyses are **not final Stage 5 models**. They were generated after Stage 4b identified unresolved feasibility issues and are intended for consultation with a biostatistician and nephrologist.

## Study aim

Evaluate whether echocardiographic parameters around dialysis initiation improve risk stratification for mortality and hospitalization burden beyond LV_EF alone.

## Model tiers evaluated

These are hierarchical **predictor sets**, not the entire set of project models. They are evaluated across outcome-specific model families and missingness/sensitivity strategies.

- Model B: clinical baseline + LV_EF
- C-minimal: Model B + E/e′ septal
- C-lite: Model B + E/e′ septal + EstimatedSysPAPressure + LACavitySize
- C-full: Model B + E/e′ septal + EstimatedSysPAPressure + TR + LACavitySize

## Key questions for consultation

1. Should C-minimal complete-case be the primary model, with C-lite/C-full as mandatory MI sensitivity?
2. Or should C-lite/C-full with MI become primary due to high complete-case loss?
3. For hospitalization burden, should NB or ZINB be the Stage 5 primary count model? This must be decided empirically using model fit, convergence, interpretability, and clinical plausibility.
4. Does the ≥6-month survivor sensitivity analysis materially change hospitalization findings?
5. How should PH warnings in Cox be handled in Stage 5?
6. Should C-minimal be the primary interpretive model with C-lite/C-full as MI/sensitivity models?
7. Does C-minimal preserve enough clinical meaning for the question of incremental value beyond EF?
8. If C-lite/C-full lose too many patients, are any lower-missingness substitutes clinically acceptable within the same echo domain?

## Feasibility summary

| outcome            | model_tier   | model_type        |   n_complete |   complete_case_loss_pct |   df |   events_per_df_or_counts_per_df | convergence_status   | warnings                                                                     |
|:-------------------|:-------------|:------------------|-------------:|-------------------------:|-----:|---------------------------------:|:---------------------|:-----------------------------------------------------------------------------|
| one_year_mortality | Model_B      | logistic          |          612 |                 0.810373 |    6 |                          39.5    | OK                   |                                                                              |
| survival           | Model_B      | cox               |          639 |                 0.776398 |    6 |                          83.5    | OK                   |                                                                              |
| hospitalization    | Model_B      | negative_binomial |          639 |                 0.776398 |    6 |                         194      | OK                   | NB_Pearson_dispersion=7.817; Poisson_scale_dispersion=7.817; alpha=3.117e-08 |
| one_year_mortality | C_minimal    | logistic          |          497 |                19.4489   |    7 |                          26.4286 | OK                   |                                                                              |
| survival           | C_minimal    | cox               |          518 |                19.5652   |    7 |                          57.8571 | OK                   |                                                                              |
| hospitalization    | C_minimal    | negative_binomial |          518 |                19.5652   |    7 |                         136.429  | OK                   | NB_Pearson_dispersion=1.761; Poisson_scale_dispersion=4.516; alpha=1.497     |
| one_year_mortality | C_lite       | logistic          |          398 |                35.4943   |   10 |                          16.4    | OK                   |                                                                              |
| survival           | C_lite       | cox               |          415 |                35.559    |   10 |                          34      | OK                   |                                                                              |
| hospitalization    | C_lite       | negative_binomial |          415 |                35.559    |   10 |                          78.1    | OK                   | NB_Pearson_dispersion=7.261; Poisson_scale_dispersion=7.261; alpha=1.988e-28 |
| one_year_mortality | C_full       | logistic          |          391 |                36.6288   |   11 |                          14.8182 | OK                   |                                                                              |
| survival           | C_full       | cox               |          408 |                36.646    |   11 |                          30.4545 | OK                   |                                                                              |
| hospitalization    | C_full       | negative_binomial |          408 |                36.646    |   11 |                          69.6364 | OK                   | NB_Pearson_dispersion=7.348; Poisson_scale_dispersion=7.348; alpha=1.262e-26 |

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
- `stage4c_early_mortality_6m_description.csv`
- `stage4c_hospitalization_NB_ZINB_6m_survivor_sensitivity.csv`

## Interpretation guardrail

Do not choose the final Stage 5 primary model solely because a p-value or estimate looks favorable. Stage 4c is for consultation regarding missingness, robustness, PH diagnostics, early-mortality sensitivity, and count-model specification.

## Draft limitations language for hospitalization outcome

Hospitalization data were available as total counts without dates of individual admissions. Therefore, recurrent-event models or competing-risk recurrent-event approaches could not be applied. Although hospitalization rates were modeled using follow-up time as an offset, early mortality may have reduced the opportunity to observe hospitalizations and may therefore lead to underestimation of hospitalization burden among the sickest patients. A sensitivity analysis restricted to patients with at least 6 months of observed survival time was therefore added for Stage 5 planning.
