# Stage 0 — Cleaning Provenance

Every transformation applied to the raw file `echo_project_update.xlsx` in producing `01_clean_flat.csv`. Each row links the action to a specific decision-log entry (DEC-NNN).

| # | Decision | Action | Detail |
|---|---|---|---|
| 1 | DEC-012 | no_value_to_nan | LeftVentricleCavitySize: 45 cells |
| 2 | DEC-012 | no_value_to_nan | LeftVentricleWallThickness: 143 cells |
| 3 | DEC-012 | no_value_to_nan | LeftVentricleSystolicFunction: 46 cells |
| 4 | DEC-012 | no_value_to_nan | RVSize: 195 cells |
| 5 | DEC-012 | no_value_to_nan | RVSystolicFunction: 194 cells |
| 6 | DEC-012 | no_value_to_nan | LACavitySize: 29 cells |
| 7 | DEC-012 | no_value_to_nan | AorticValveStructure: 106 cells |
| 8 | DEC-012 | no_value_to_nan | AorticValveRegurgitation: 156 cells |
| 9 | DEC-012 | no_value_to_nan | MitralValveStructure: 261 cells |
| 10 | DEC-012 | no_value_to_nan | MitralRegurgitation: 29 cells |
| 11 | DEC-012 | no_value_to_nan | TricuspidValveStructure: 339 cells |
| 12 | DEC-012 | no_value_to_nan | TricuspidRegurgitation: 26 cells |
| 13 | DEC-014 | see_below_to_nan | LeftVentricleWallThickness: 6 cells |
| 14 | DEC-014 | see_below_to_nan | AorticValveStructure: 1 cells |
| 15 | DEC-014 | see_below_to_nan | MitralValveStructure: 5 cells |
| 16 | DEC-018 | preserved_to_normal | LeftVentricleSystolicFunction: 33 cells |
| 17 | DEC-019 | mr_english_to_roman | MR: 6 × "Trace" -> "Trivial" |
| 18 | DEC-019 | mr_english_to_roman | MR: 3 × "Moderate" -> "Moderate (II)" |
| 19 | DEC-019 | mr_english_to_roman | MR: 2 × "Severe" -> "Severe (IV)" |
| 20 | DEC-022 | comorb_null_to_binary | MI -> MI_binary (n_pos=193, 29.9%) |
| 21 | DEC-022 | comorb_null_to_binary | CABG -> CABG_binary (n_pos=133, 20.6%) |
| 22 | DEC-022 | comorb_null_to_binary | IHD -> IHD_binary (n_pos=396, 61.4%) |
| 23 | DEC-022 | comorb_null_to_binary | AFIB -> AFIB_binary (n_pos=303, 47.0%) |
| 24 | DEC-022 | comorb_null_to_binary | HTN -> HTN_binary (n_pos=533, 82.6%) |
| 25 | DEC-022 | comorb_null_to_binary | Diabetes mellitus -> Diabetes mellitus_binary (n_pos=410, 63.6%) |
| 26 | DEC-022 | comorb_null_to_binary | DYSLIPIDEMIA -> DYSLIPIDEMIA_binary (n_pos=311, 48.2%) |
| 27 | DEC-022 | comorb_null_to_binary | COPD -> COPD_binary (n_pos=105, 16.3%) |
| 28 | DEC-022 | comorb_null_to_binary | OncologicalDiagnosis -> OncologicalDiagnosis_binary (n_pos=143, 22.2%) |
| 29 | DEC-027 | canonical_rename | patient number -> patient_id |
| 30 | DEC-027 | canonical_rename | hospitalization-count -> hosp_total |
| 31 | DEC-020 | working_censor_date | set to 2025-08-16 (provisional, pending source confirmation) |
| 32 | DEC-020 | derived_time_vars | gap_echo_to_dial_days, death_event, time_to_event_days, followup_days |
| 33 | DEC-026 | died_1year | 1=240, 0=378, NaN=27 (insufficient FU) |
| 34 | DEC-016 | echo_after_death_flag | 1 patient(s) flagged for cohort exclusion |
| 35 | DEC-025 | qa_outliers | 21 outlier flags across 6 variables -> 04_qa_outliers.csv |
