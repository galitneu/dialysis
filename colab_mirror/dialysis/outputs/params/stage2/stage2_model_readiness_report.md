# Stage 2 — Model-Readiness Report

**Generated:** 2026-05-05T12:16:45
**Stage 1 source:** stage1_prepare_analytic_datasets_FIXED_v2 (DEC-044 alias mapping)

## Cohort flow

- **main_analysis**: n=644 (after DEC-040 exclusion)
- **one_year_mortality**: n=617 (died_1year not missing) | events_1y=239 (38.74%)
- **survival**: n=644 (event valid + time_to_event>=0) | events=505 (78.42%) | median FU=556.0d
- **hospitalization**: n=644 (hosp_total valid + followup_days>0) | total hosp=1177 | rate=0.725/p-y
- **sensitivity**: n=644 (all main + sens predictors)

## Decisions applied

- DEC-044: alias mapping for MR/TR/AR labels; merged correctly.
- DEC-045..048: this stage is descriptive + model-readiness only.
- DEC-047: NO p-values in Table 1.

## Missingness flags (vars with >20% missing in main analysis)

_No main predictors with >20% missing._

## Echo timing distribution (main cohort)
- median -70.0d, IQR (-227, -5)
- range [-366, 67]

## Outliers (from Stage 1 DEC-030)

 patient_id variable  original_value                                 action
      362.0      BMI       81.216160 set_to_missing_in_stage1_analytic_copy
      407.0      BMI        3.746098 set_to_missing_in_stage1_analytic_copy

## Collinearity flags (Spearman |r| ≥ 0.70)

_No high-correlation pairs among main continuous predictors._

## Clinical overlap flags (advisory)
                family                                                         vars                                                                              note  enforced
       Kidney function                                             creatinine + GFR                                  main: creatinine; sensitivity: GFR (per DEC-034)      True
    Pulmonary pressure                           EstimatedSysPAPressure + ECHO_SPAP     do not include together; one is numeric, one is categorical of same construct     False
               LV mass LeftVentricleEstimatedMass + LeftVentricleEstimatedMassIndex                                             prefer LVMI; main is LVMI per Stage 0      True
                Timing       days_echo_to_dialysis + (months variants, gap variant)                                          use days_echo_to_dialysis only (DEC-032)      True
Outcomes vs predictors              event/event_1y/hosp_total/hospitalization-count                                                never used as predictors (DEC-031)      True
  EF/systolic function                        LV_EF + LeftVentricleSystolicFunction high overlap; LV_EF is benchmark; LeftVentricleSystolicFunction is in sensitivity      True
    Diastolic function        TissueDoppler E/e ratio septal/lateral + e velocities    overlap within Echo: LV diastolic axis; Stage 4 should pick one representative     False

## Model readiness per outcome
                 outcome  n_cohort  n_events  n_candidate_predictors_main  events_per_variable_main_only  recommended_max_predictors flag_low_epv                                                  note  total_hospitalizations  mean_hosp_total  var_hosp_total  overdispersion_ratio_var_over_mean  sum_followup_years  rate_per_person_year overdispersion_flag                                                                                 candidate_predictor_capacity_note
      one_year_mortality       617     239.0                           27                           8.85                        23.0         True Conservative rule of thumb: >=10 events per variable.                     NaN              NaN             NaN                                 NaN                 NaN                   NaN                 NaN                                                                                                               NaN
  survival_full_followup       644     505.0                           27                          18.70                        50.0        False Conservative rule of thumb: >=10 events per variable.                     NaN              NaN             NaN                                 NaN                 NaN                   NaN                 NaN                                                                                                               NaN
hospitalization_count_NB       644       NaN                           27                            NaN                         NaN          NaN                                                   NaN                  1177.0            1.828           5.082                               2.781             1623.49                 0.725                True Total events (1177); EPV not directly applicable to NB. Aim for parsimonious model. Suggested max predictors ~ 27

## Open issues / decisions needed before Stage 3
- OPEN-002: confirm administrative censor date (working: 2025-08-16).
- Stage 4 candidate selection: confirm one representative per axis.

## Outputs (this stage)

- `run_stage2.py`
- `stage2_KM_overall_descriptive.csv`
- `stage2_categorical_distributions.csv`
- `stage2_clinical_overlap_flags.csv`
- `stage2_cohort_summary.csv`
- `stage2_collinearity_flags.csv`
- `stage2_continuous_distributions.csv`
- `stage2_echo_timing_category_counts.csv`
- `stage2_echo_timing_distribution.csv`
- `stage2_grouped_category_stability.csv`
- `stage2_input_validation.csv`
- `stage2_missingness_by_dataset.csv`
- `stage2_missingness_flags.csv`
- `stage2_model_readiness_by_outcome.csv`
- `stage2_outcome_summary.csv`
- `stage2_predictor_correlation_matrix.csv`
- `stage2_run_metadata.json`
- `stage2_table1_by_oneyear_mortality.csv`
- `stage2_table1_overall.csv`

## Plots (this stage)

- `plots/stage2_KM_overall_descriptive.png`
- `plots/stage2_bar_ECHO_SPAP.png`
- `plots/stage2_bar_HD_PD.png`
- `plots/stage2_bar_LACavitySize.png`
- `plots/stage2_bar_m_f.png`
- `plots/stage2_bar_mitral_regurgitation_clin_grouped.png`
- `plots/stage2_bar_tricuspid_regurgitation_clin_grouped.png`
- `plots/stage2_correlation_heatmap.png`
- `plots/stage2_echo_timing_histogram.png`
- `plots/stage2_hist_AgeAtFirstHFDate.png`
- `plots/stage2_hist_EstimatedSysPAPressure.png`
- `plots/stage2_hist_LV_EF.png`
- `plots/stage2_hist_LeftVentricleEstimatedMassIndex.png`
- `plots/stage2_hist_MitralInflowPeakEWave.png`
- `plots/stage2_hist_TissueDopplerEERatioLateral.png`
- `plots/stage2_hist_TissueDopplerEERatioSeptal.png`
- `plots/stage2_hist_TissueDopplerEVelosityLateral.png`
- `plots/stage2_hist_TissueDopplerEVelositySeptal.png`
- `plots/stage2_hist_albumin-numeric_result.png`
- `plots/stage2_hist_creatinine-numeric_result.png`
- `plots/stage2_hist_crp-numeric_result.png`
- `plots/stage2_hist_days_echo_to_dialysis.png`
- `plots/stage2_hist_hb-numeric_result.png`
- `plots/stage2_hosp_count_distribution.png`