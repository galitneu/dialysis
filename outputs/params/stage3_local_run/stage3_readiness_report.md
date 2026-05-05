# Stage 3 readiness report (independent local re-implementation)
Generated: 2026-05-05T14:04:39

- Main candidates: 27
- Timing/sensitivity-only: 1
- All screened: 28

## Fit status by outcome family
```
status                             ok
outcome_family                       
hospitalization_negative_binomial  28
one_year_mortality_logistic        28
survival_cox                       28
```

## Top 5 by p-value within each outcome family

### one_year_mortality_logistic
```
                            variable                                                 term  estimate  ci95_low  ci95_high      p_value  q_value_bh_within_outcome
                    AgeAtFirstHFDate                                  AgeAtFirstHFDate__z  1.603936  1.339970   1.919901 2.607372e-07                   0.000011
           creatinine-numeric result                         creatinine-numeric result__z  0.634970  0.531304   0.758862 5.909565e-07                   0.000012
              albumin-numeric result                            albumin-numeric result__z  0.659172  0.555725   0.781875 1.709498e-06                   0.000023
tricuspid_regurgitation_clin_grouped tricuspid_regurgitation_clin_grouped__level__Trivial  0.374500  0.233195   0.601429 4.831671e-05                   0.000400
                               LV_EF                                             LV_EF__z  0.712199  0.604603   0.838942 4.876496e-05                   0.000400
```

### survival_cox
```
                            variable                                                            term  estimate  ci95_low  ci95_high      p_value  q_value_bh_within_outcome
                    AgeAtFirstHFDate                                             AgeAtFirstHFDate__z  1.493910  1.357762   1.643710 1.828281e-16               7.495951e-15
          TissueDopplerEERatioSeptal                                   TissueDopplerEERatioSeptal__z  1.297333  1.182337   1.423514 3.867259e-08               7.927881e-07
           creatinine-numeric result                                    creatinine-numeric result__z  0.789481  0.719324   0.866481 6.417224e-07               8.770206e-06
                               LV_EF                                                        LV_EF__z  0.812020  0.745547   0.884418 1.764764e-06               1.808883e-05
tricuspid_regurgitation_clin_grouped tricuspid_regurgitation_clin_grouped__level__Moderate-to-Severe  1.741299  1.375742   2.203991 3.964202e-06               3.250646e-05
```

### hospitalization_negative_binomial
```
                            variable                                                 term  estimate  ci95_low  ci95_high      p_value  q_value_bh_within_outcome
                    AgeAtFirstHFDate                                  AgeAtFirstHFDate__z  1.374081  1.240793   1.521687 1.032551e-09               4.233461e-08
          TissueDopplerEERatioSeptal                        TissueDopplerEERatioSeptal__z  1.364726  1.221197   1.525124 4.144315e-08               8.495845e-07
tricuspid_regurgitation_clin_grouped tricuspid_regurgitation_clin_grouped__level__Trivial  0.486851  0.372373   0.636523 1.418231e-07               1.938249e-06
               MitralInflowPeakEWave                             MitralInflowPeakEWave__z  1.316275  1.185047   1.462035 2.921334e-07               2.994368e-06
         TissueDopplerEERatioLateral                       TissueDopplerEERatioLateral__z  1.270399  1.136379   1.420224 2.580996e-05               2.116416e-04
```