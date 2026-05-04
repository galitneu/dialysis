# Stage 0 — Variable Audit Report

**Source**: stage2_analysis_ready.csv | n=645 rows | 79 columns

## Cross-check vs clinician table

| Clinician variable | In dataset? | n with value |
|---|---|---|
| LV Cavity Size | ✓ | 616 |
| LV Wall Thickness | ✓ | 545 |
| LV Systolic Function | ✓ | 616 |
| RV Size | ✓ | 495 |
| Aortic Valve Structure (CLINICIAN listed) | ✗ MISSING | — |
| Aortic Regurgitation (CLINICIAN listed) | ✗ MISSING | — |
| Mitral Regurgitation | ✓ | 626 |
| Tricuspid Regurgitation | ✓ | 626 |
| LA Cavity Size | ✓ | 631 |
| RV Systolic Function | ✓ | 498 |
| ECHO SPAP | ✓ | 526 |

## Full inventory (grouped by axis)


### Admin (n=3)

| Column | dtype | type | %miss | unique | proposed status |
|---|---|---|---|---|---|
| `patient_id` | object | continuous | 0.0% | 645 | Excluded |
| `Dialysis_Start_Date` | object | categorical / string / date | 0.0% | 615 | Excluded |
| `selected_Echo_Date` | object | categorical / string / date | 0.0% | 644 | Excluded |

### Outcome (n=6)

| Column | dtype | type | %miss | unique | proposed status |
|---|---|---|---|---|---|
| `event` | object | binary | 0.0% | 2 | Outcome — secondary (Cox) |
| `time_to_event_days` | object | continuous | 0.0% | 513 | Outcome — secondary (Cox) |
| `time_to_event_years` | object | continuous | 0.0% | 513 | Outcome — secondary (Cox, redundant) |
| `followup_days` | object | continuous | 0.0% | 513 | Outcome — denominator for hosp rate |
| `died_1year` | object | binary | 4.2% | 2 | Outcome — primary (1y mortality) |
| `hosp_total` | object | continuous | 0.0% | 11 | Outcome — primary (hosp rate) |

### Timing (n=3)

| Column | dtype | type | %miss | unique | proposed status |
|---|---|---|---|---|---|
| `echo_to_dialysis_days` | object | continuous | 0.0% | 297 | Core clinical (covariate) |
| `echo_timing_class` | object | categorical / string / date | 0.0% | 3 | Descriptive only — used to define cohort |
| `echo_before_dialysis` | object | binary | 0.0% | 2 | Descriptive only — redundant with class |

### Clinical (n=11)

| Column | dtype | type | %miss | unique | proposed status |
|---|---|---|---|---|---|
| `AgeAtFirstHFDate` | object | continuous | 0.0% | 435 | Core clinical |
| `Age_z` | object | continuous | 0.0% | 435 | Excluded — pre-z-scored, redundant |
| `sex_male` | object | binary | 0.2% | 2 | Core clinical |
| `HD_binary` | object | binary | 0.0% | 2 | Candidate covariate (full base) |
| `IHD_binary` | object | binary | 0.0% | 2 | Candidate covariate (full base) |
| `AFIB_binary` | object | binary | 0.0% | 2 | Candidate covariate (full base) |
| `Diabetes mellitus_binary` | object | binary | 0.0% | 2 | Candidate covariate (full base) |
| `MI_binary` | object | binary | 0.0% | 2 | Candidate covariate (full base) |
| `CABG_binary` | object | binary | 0.0% | 2 | Candidate covariate (full base) |
| `HTN_binary` | object | binary | 0.0% | 2 | Candidate covariate (full base) |
| `COPD_binary` | object | binary | 0.0% | 2 | Candidate covariate (full base) |

### Lab (n=10)

| Column | dtype | type | %miss | unique | proposed status |
|---|---|---|---|---|---|
| `albumin-numeric result` | object | continuous | 0.2% | 39 | Candidate covariate (full base) |
| `albumin_z` | object | continuous | 0.2% | 39 | Excluded — pre-z-scored |
| `creatinine-numeric result` | object | continuous | 0.2% | 428 | Core clinical (parsimonious base) |
| `creatinine_z` | object | continuous | 0.2% | 428 | Excluded — pre-z-scored |
| `GFR` | object | continuous | 0.2% | 616 | Candidate covariate (alternative to creatinine) |
| `GFR_z` | object | continuous | 0.2% | 616 | Excluded — pre-z-scored |
| `hb-numeric result` | object | continuous | 10.2% | 105 | Candidate covariate (full base) |
| `crp-numeric result` | object | continuous | 3.9% | 595 | Candidate covariate (full base) |
| `sbp-numeric result` | object | continuous | 25.4% | 115 | Sensitivity (>20% missing) |
| `dbp-numeric result` | object | continuous | 21.2% | 77 | Sensitivity (>20% missing) |

### Echo: Benchmark (n=2)

| Column | dtype | type | %miss | unique | proposed status |
|---|---|---|---|---|---|
| `LV_EF` | object | continuous | 0.6% | 35 | Benchmark — fixed in all models |
| `LV_EF_z` | object | continuous | 0.6% | 35 | Excluded — pre-z-scored |

### Echo: LV structure / mass (n=11)

| Column | dtype | type | %miss | unique | proposed status |
|---|---|---|---|---|---|
| `LeftVentricleEstimatedMassIndex` | object | continuous | 10.4% | 146 | Candidate (LVMI) |
| `LVMI_z` | object | continuous | 10.4% | 146 | Excluded — pre-z-scored |
| `LeftVentricleInterventricularSeptumThickness` | object | continuous | 1.2% | 117 | Sensitivity |
| `IVS_z` | object | continuous | 1.2% | 117 | Excluded — pre-z-scored |
| `LeftVentricleEndDiastolicDiameter` | object | continuous | 1.2% | 247 | Sensitivity |
| `LVEDD_z` | object | continuous | 1.2% | 247 | Excluded — pre-z-scored |
| `LeftVentricleEstimatedMass` | object | continuous | 2.5% | 562 | Sensitivity (use LVMI instead) |
| `LeftVentricleEndSystolicDiameter` | object | continuous | 1.4% | 272 | Sensitivity |
| `LeftVentriclePosteriorWallThickness` | object | continuous | 2.0% | 99 | Sensitivity |
| `LeftVentricleCavitySize` | object | categorical / string / date | 4.5% | 6 | Sensitivity (categorical) |
| `LeftVentricleWallThickness` | object | categorical / string / date | 15.5% | 5 | Sensitivity (categorical) |

### Echo: LV diastolic / filling (n=8)

| Column | dtype | type | %miss | unique | proposed status |
|---|---|---|---|---|---|
| `MitralInflowPeakEWave` | object | continuous | 9.8% | 302 | Candidate |
| `Ewave_z` | object | continuous | 9.8% | 302 | Excluded — pre-z-scored |
| `TissueDopplerEERatioSeptal` | object | continuous | 18.9% | 474 | Candidate |
| `EeRatioSep_z` | object | continuous | 18.9% | 474 | Excluded — pre-z-scored |
| `TissueDopplerEVelositySeptal` | object | continuous | 17.7% | 245 | Candidate (was previously OMITTED) |
| `TissueDopplerEVelosityLateral` | object | continuous | 17.7% | 255 | Candidate (was previously OMITTED) |
| `TissueDopplerEERatioLateral` | object | continuous | 18.9% | 452 | Candidate |
| `EeRatio_avg` | object | continuous | 18.4% | 516 | Candidate (derived) |

### Echo: Right-heart / congestion (n=6)

| Column | dtype | type | %miss | unique | proposed status |
|---|---|---|---|---|---|
| `EstimatedSysPAPressure` | object | continuous | 16.7% | 77 | Candidate (numeric SPAP) |
| `SPAP_z` | object | continuous | 16.7% | 77 | Excluded — pre-z-scored |
| `TricuspidRegurgitation` | object | categorical / string / date | 2.9% | 7 | Candidate (categorical, merged) |
| `RVSize` | object | categorical / string / date | 23.3% | 5 | Candidate (categorical, RVH dropped) |
| `RVSystolicFunction` | object | categorical / string / date | 22.8% | 5 | Candidate (categorical) |
| `ECHO_SPAP` | object | categorical / string / date | 18.4% | 4 | Candidate (categorical) |

### Echo: LA / atrial (n=1)

| Column | dtype | type | %miss | unique | proposed status |
|---|---|---|---|---|---|
| `LACavitySize` | object | categorical / string / date | 2.2% | 5 | Candidate (categorical) |

### Echo: Valves (n=1)

| Column | dtype | type | %miss | unique | proposed status |
|---|---|---|---|---|---|
| `MitralRegurgitation` | object | categorical / string / date | 2.9% | 7 | Candidate (categorical, merged) |

### Echo: LV systolic (other) (n=4)

| Column | dtype | type | %miss | unique | proposed status |
|---|---|---|---|---|---|
| `LeftVentricleScoreIndex` | object | continuous | 0.8% | 45 | Sensitivity (overlap with EF) |
| `LeftVentricleSystolicFunction` | object | categorical / string / date | 4.5% | 8 | Candidate (categorical) |
| `TissueDopplerSVelocitySeptal` | object | continuous | 31.6% | 201 | Candidate |
| `TissueDopplerSVelocityLateral` | object | continuous | 20.3% | 233 | Candidate |

### QC flag (n=13)

| Column | dtype | type | %miss | unique | proposed status |
|---|---|---|---|---|---|
| `flag_missing_dialysis_date` | object | binary | 0.0% | 1 | Excluded |
| `flag_missing_echo_date` | object | binary | 0.0% | 1 | Excluded |
| `flag_no_patient_level_followup_date` | object | binary | 0.0% | 1 | Excluded |
| `flag_death_before_dialysis` | object | binary | 0.0% | 1 | Excluded |
| `flag_negative_followup` | object | binary | 0.0% | 1 | Excluded |
| `flag_echo_after_dialysis` | object | binary | 0.0% | 2 | Used to define cohort |
| `flag_echo_same_day` | object | binary | 0.0% | 2 | Used to define cohort |
| `flag_echo_more_than_365d_before_dialysis` | object | binary | 0.0% | 1 | Used to define cohort |
| `flag_short_followup_for_1y_outcome` | object | binary | 0.0% | 2 | Used to define cohort |
| `flag_multiple_echo_records` | object | binary | 0.0% | 1 | Excluded |
| `flag_hosp_1y_not_computable` | object | binary | 0.0% | 1 | Excluded |
| `flag_manual_review_needed` | object | binary | 0.0% | 1 | Excluded |
| `flag_primary_analysis_exclusion_candidate` | object | binary | 0.0% | 2 | Used to define cohort |
