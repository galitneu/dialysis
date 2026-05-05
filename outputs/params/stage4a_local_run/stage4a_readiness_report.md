# Stage 4a v3.1 readiness report
Generated: 2026-05-05T19:20:12

## Purpose
Evidence preparation for clinically-informed predictor lock-in. **Not** variable selection. Final inclusion is left to the committee.

## Inputs
- Stage 2: /home/user/dialysis/outputs/params/stage2_DEC044_FIXED_v2
- Stage 3: /home/user/dialysis/outputs/params/stage3_drive_v2 (DEC-059B enforced: complete-case for categorical predictors)

## QA gates
```
                                                                 gate status severity                                                                                       details
                                Gate 1 - Stage 2 critical files exist   PASS     info                                                                                   all present
                                Gate 2 - Stage 3 critical files exist   PASS     info                                                                                   all present
               Gate 3 - DEC-059B (categorical complete-case) enforced   PASS     info                                                         DEC-059B explicit in Stage 3 metadata
                        Gate 4 - Exactly 27 main_candidate predictors   PASS     info                                                  main_candidate=27, timing_sensitivity_only=1
                       Gate 5 - No silent missing-as-reference coding   PASS     info                           All categoricals with missingness use variable-level complete-case.
                      Gate 6 - All Stage 3 univariable fits succeeded   PASS     info                                                                                all 84 fits ok
Gate 7 - Stage 3 contrasts documented (term/reference_level/contrast)   PASS     info                                                                               columns present
                              Gate 8 - Three outcome families present   PASS     info present: ['hospitalization_negative_binomial', 'one_year_mortality_logistic', 'survival_cox']
```

## Predictor counts
- main_candidate: 27
- timing_sensitivity_only: 1

## EPV / capacity
```
                          outcome   n  events epv10_capacity_parameters epv15_capacity_parameters  main_candidate_total_approx_df  timing_sensitivity_total_approx_df                                                                                                                                                                              capacity_note
      one_year_mortality_logistic 617     239                        23                        15                              35                                   6                                                                                                                    EPV-based capacity is a soft cap; final adjustment set must respect it.
                     survival_cox 644     505                        50                        33                              35                                   6                                                                                                                    EPV-based capacity is a soft cap; final adjustment set must respect it.
hospitalization_negative_binomial 644    1177                                                                                  35                                   6 NB capacity should be judged by convergence, dispersion, person-time, total counts (n_events=1177), and model stability; classic EPV not directly applicable. Stage 2 var/mean ratio=2.78.
```

## Df burden by domain
```
                        clinical_domain  n_variables  total_approx_df                                                                                                                                   variables
                            Comorbidity            7                7                                          AFIB_binary; CABG_binary; COPD_binary; Diabetes mellitus_binary; HTN_binary; IHD_binary; MI_binary
                           Demographics            2                2                                                                                                                       AgeAtFirstHFDate; m/f
                      Dialysis modality            1                1                                                                                                                                       HD/PD
           Diastolic / filling pressure            5                5 MitralInflowPeakEWave; TissueDopplerEERatioLateral; TissueDopplerEERatioSeptal; TissueDopplerEVelosityLateral; TissueDopplerEVelositySeptal
               Echo timing / provenance            2                7                                                                                     days_echo_to_dialysis; echo_to_dialysis_timing_category
            LA / chronic filling burden            1                3                                                                                                                                LACavitySize
              LV structure / remodeling            1                1                                                                                                             LeftVentricleEstimatedMassIndex
                   LV systolic function            1                1                                                                                                                                       LV_EF
Pulmonary pressure / right-sided burden            2                4                                                                                                           ECHO_SPAP; EstimatedSysPAPressure
            Renal / labs / inflammation            4                4                                                    albumin-numeric result; creatinine-numeric result; crp-numeric result; hb-numeric result
                       Valvular disease            2                6                                                                     mitral_regurgitation_clin_grouped; tricuspid_regurgitation_clin_grouped
```

## Missingness / n_model audit summary
- variable-outcome rows: 84
- WARNING_HIGH_MISSINGNESS rows: 0
- FAIL_SILENT_REFERENCE_RISK rows: 0

## Statistical collinearity (Spearman |rho|>=0.70)
- flagged pairs: 0

## Soft correlations (|rho|>=0.60)
- pairs: 4

## Clinical overlap (Stage 2 advisory layer)
- advisory_flag rows: 4

## Cardiology priorities (8 markers across 5 themes)
Cardiology-prioritized: LV_EF, TissueDopplerEERatioSeptal, EstimatedSysPAPressure, ECHO_SPAP, tricuspid_regurgitation_clin_grouped. Literature-supported: LeftVentricleEstimatedMassIndex, LACavitySize. Outcome-specific discovery: MitralInflowPeakEWave (hospitalization).

## Discovery candidates (data signal in >=1 outcome and not cardiology-prior)
```
                         variable              clinical_domain        candidate_logic_type  any_p_below_0_05
                 AgeAtFirstHFDate                 Demographics             core_adjustment              True
           albumin-numeric result  Renal / labs / inflammation primary_clinical_supporting              True
        creatinine-numeric result  Renal / labs / inflammation primary_clinical_supporting              True
      TissueDopplerEERatioLateral Diastolic / filling pressure primary_clinical_supporting              True
    TissueDopplerEVelosityLateral Diastolic / filling pressure primary_clinical_supporting              True
     TissueDopplerEVelositySeptal Diastolic / filling pressure primary_clinical_supporting              True
            days_echo_to_dialysis     Echo timing / provenance       sensitivity_or_timing              True
                      AFIB_binary                  Comorbidity primary_clinical_supporting              True
                      CABG_binary                  Comorbidity primary_clinical_supporting              True
                      COPD_binary                  Comorbidity primary_clinical_supporting              True
         Diabetes mellitus_binary                  Comorbidity             core_adjustment              True
                       HTN_binary                  Comorbidity             core_adjustment              True
                       IHD_binary                  Comorbidity             core_adjustment              True
mitral_regurgitation_clin_grouped             Valvular disease primary_clinical_supporting              True
```

## Reviewer 2 risk mitigation
1. Stage 4a is **not** automated variable selection.
2. p-values and q-values are descriptive only (DEC-062).
3. Clinical priors do **not** eliminate discovery candidates.
4. Discovery candidates are **not** selected by p-value alone; they require clinical plausibility and non-redundancy.
5. Stage 3 used variable-level complete-case (DEC-059B); the Stage 5 missingness strategy will be documented separately.
6. Penalized regression (LASSO) is reserved for sensitivity analyses (DEC-066).
7. Outcome-specific evidence is documented per outcome with explicit rationale; shared core adjustment set will be discussed separately.
8. Final inclusion requires `decision_basis` and `decision_reason_free_text` in the committee lock-in template.

## Committee instruction
```
Stage 4a does not finalize model predictors.
Committee lock-in decisions are required before Stage 5.
```