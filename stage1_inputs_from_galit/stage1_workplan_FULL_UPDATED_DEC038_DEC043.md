# Stage 1 Full Workplan — Analytic Dataset Preparation

**Project:** Dialysis mortality / echocardiography study  
**Stage:** Stage 1 — analytic dataset preparation  
**Primary source-of-truth input:** `stage0_updated_clean_flat.csv`  
**Do not use as source of truth:** the second LLM file `01_clean_flat.csv`; it may be retained only as an external QA/audit comparison file.  
**Core principle:** Stage 1 prepares analysis-ready datasets. It does **not** run final models, does **not** select final clusters, and does **not** make outcome-driven recoding decisions.

---

## 1. Stage 1 objectives

Stage 1 will transform the approved Stage 0 clean dataset into documented analytic datasets for the next analysis stages.

It must:

1. Apply the approved decision log.
2. Define outcome-specific analytic cohorts.
3. Apply exclusion rules without deleting records from the source file.
4. Handle missingness and implausible outliers according to pre-specified rules.
5. Apply clinician-approved category harmonization for categorical echo variables.
6. Produce timing-distribution summaries for echo-to-dialysis gaps.
7. Preserve free-text fields for future use while excluding them from current quantitative models.
8. Export clean, reproducible datasets and logs for Stage 2/modeling.

---

## 2. Required inputs

Stage 1 should load:

| File | Role |
|---|---|
| `stage0_updated_clean_flat.csv` | Source-of-truth patient-level dataset |
| `stage0_decision_log_FINAL_DEC038_DEC043.csv` | Updated decision log |
| `stage0_updated_stage1_eligible_main.csv` or final main list | Main candidate variables |
| `stage0_updated_sensitivity_exploratory.csv` or final sensitivity/exploratory list | Sensitivity/exploratory variables |
| `stage0_updated_descriptive_excluded.csv` | Descriptive/excluded variables |
| `stage0_updated_QA_flags.csv` | Stage 0 QA findings |
| `stage1_clinician_category_mapping_DEC037.csv` | Clinician-approved echo category mapping |

Validation checks at loading:

- `n = 645` rows before Stage 1 exclusions.
- `patient_id` exists and is unique.
- Required date/outcome fields exist.
- Required predictor-list files exist.
- No use of `01_clean_flat.csv` as analytic input.

---

## 3. Decision rules to implement

### 3.1 Comorbidity missingness

**Decision DEC-038:** Missing disease documentation means the condition is absent for binary covariate construction.

Examples:

- Missing `MI` date/entry → `MI_binary = 0`
- Present `MI` date/entry → `MI_binary = 1`
- Same logic for CABG, IHD, AFIB, HTN, diabetes, dyslipidemia, COPD, oncological diagnosis and similar comorbidity fields.

Raw disease-date fields should be retained for audit/future analyses but not used as main predictors.

### 3.2 Echo missingness

**Decision DEC-039:** Non-usable structured echo values are missing, not normal.

Treat as missing/effective missing:

- `No Value`
- `See below`
- unavailable/non-interpretable entries
- similar non-measurement values

Do not impute echo values in Stage 1. Use available measured values.

### 3.3 Same-day echo and death

**Decision DEC-040:** Patients whose `Echo_Date` is on the same calendar date as `DeathDate`, or after `DeathDate`, are excluded from Stage 1 analytic cohorts and reported.

Implementation:

- Keep them in the source file.
- Add them to `stage1_exclusions_log.csv`.
- Exclude from one-year mortality, Cox/survival, and hospitalization analytic datasets.
- Report count and percentage.

Create flags:

- `flag_echo_after_death`
- `flag_echo_same_day_as_death`
- `exclude_same_day_or_after_death`

### 3.4 Time zero and one-year mortality

Time zero is dialysis start:

- `Dialysis_Start_Date`

Define `died_1year` as:

| Condition | `died_1year` |
|---|---:|
| Death within 365 days from dialysis start | 1 |
| Alive with at least 365 days of follow-up | 0 |
| Not dead and less than 365 days follow-up | missing |

The one-year mortality analytic cohort includes only patients with non-missing `died_1year`, after cohort exclusions.

### 3.5 Echo-to-dialysis timing

**Decision DEC-041:** No maximum echo-to-dialysis gap cutoff is applied in Stage 1.

Use only:

- `days_echo_to_dialysis`

Do not use duplicate/inverse timing variables together.

Stage 1 must produce:

- summary statistics of `days_echo_to_dialysis`
- histogram or plot-ready count table
- timing categories
- list of extreme timing gaps
- optional sensitivity cohort indicators

Suggested timing categories:

| Category | Definition |
|---|---|
| `after_dialysis` | `days_echo_to_dialysis > 0` |
| `same_day` | `days_echo_to_dialysis = 0` |
| `before_0_30d` | -30 to -1 days |
| `before_31_90d` | -90 to -31 days |
| `before_91_180d` | -180 to -91 days |
| `before_181_365d` | -365 to -181 days |
| `before_gt_365d` | < -365 days |

### 3.6 Free-text fields

**Decision DEC-042:** Free-text echo summaries are retained but not modeled.

Keep columns such as:

- `LeftVentricleSummary`
- `AorticValveSummary`
- `MitralValveSummary`
- `ProcedureSummary`

Role: `retained_for_future_text_or_NLP_review`; not predictors in Stage 1 quantitative datasets.

### 3.7 Categorical harmonization

**Decision DEC-037 + DEC-043:** Apply clinician-approved category merging and export before/after frequencies.

Rules:

- Preserve original variables.
- Create new grouped variables with `_clin_grouped` suffix.
- Use grouped variables in main modeling where the parent variable is eligible.
- Rare categories marked by clinicians as “ignore” are not independent model levels. They should be flagged as `Rare/ignored` or set to missing in analysis-specific datasets, while original values are preserved.
- Merging is based on clinical meaning and sparse-category management, not outcome associations.

Clinician-approved mappings:

| Original variable | New variable | Rule |
|---|---|---|
| `LeftVentricleCavitySize` | `lv_cavity_size_clin_grouped` | Moderate + Severe combined; Small = Rare/ignored |
| `LeftVentricleWallThickness` | `lv_wall_thickness_clin_grouped` | Moderate + Severe combined |
| `LeftVentricleSystolicFunction` | `lv_systolic_function_clin_grouped` | No change; create mirrored grouped variable only for naming consistency if useful |
| `RVSize` | `rv_size_clin_grouped` | RVH = Rare/ignored; other categories unchanged |
| `AorticValveStructure` | `aortic_valve_structure_clin_grouped` | Bioprosthesis + Prosthetic combined; Focal calcification/Bicuspid/Not well seen = Rare/ignored |
| `AorticValveRegurgitation` | `aortic_regurgitation_clin_grouped` | Mild-to-moderate combined with Mild; Moderate + Mod-severe + Severe combined |
| `MitralRegurgitation` | `mitral_regurgitation_clin_grouped` | Moderate + Mod-severe + Severe combined |
| `TricuspidRegurgitation` | `tricuspid_regurgitation_clin_grouped` | Moderate + Mod-severe + Severe combined |
| `LACavitySize` | `la_cavity_size_clin_grouped` | No change |
| `RVSystolicFunction` | `rv_systolic_function_clin_grouped` | No change |
| `ECHO_SPAP` | `echo_spap_clin_grouped` | No change |

---

## 4. Stage 1 notebook sections

### Section 1 — Setup

- Import packages.
- Define file paths.
- Create output directory with `parents=True, exist_ok=True`.
- Write run metadata: timestamp, input file hash, row/column count.

Expected outputs:

- `stage1_run_metadata.json`

### Section 2 — Load source and decision files

- Load `stage0_updated_clean_flat.csv`.
- Load decision log and variable lists.
- Validate row count, unique `patient_id`, and required columns.

Expected outputs:

- validation printout
- `stage1_input_validation.csv`

### Section 3 — Baseline cohort integrity checks

Check:

- missing IDs
- duplicate IDs
- date parsing success
- impossible follow-up times
- missing outcome support fields
- same-day/after-death echo flags

Expected outputs:

- `stage1_cohort_integrity_checks.csv`

### Section 4 — Apply cohort exclusion rules

Create exclusion log without deleting rows from source.

Required columns:

- `patient_id`
- `exclusion_reason`
- `exclusion_rule_id`
- `excluded_from_oneyear_mortality`
- `excluded_from_survival`
- `excluded_from_hospitalization`
- `notes`

At minimum, exclude same-day/after-death echo cases from analytic cohorts per DEC-040.

Expected outputs:

- `stage1_exclusions_log.csv`
- summary count in `stage1_summary_report.md`

### Section 5 — Outcome-specific analytic cohorts

Create separate cohorts.

#### 5.1 One-year mortality cohort

Criteria:

- not excluded by cohort rules
- `died_1year` is not missing

Expected N before same-day/death exclusion: approximately 618.

Output:

- `stage1_oneyear_mortality.csv`

#### 5.2 Survival cohort

Criteria:

- not excluded by cohort rules
- valid `event`
- valid `time_to_event_days`
- `time_to_event_days >= 0`

Output:

- `stage1_survival_analysis.csv`

#### 5.3 Hospitalization cohort

Criteria:

- not excluded by cohort rules
- valid `hosp_total`
- valid `followup_days`
- `followup_days > 0`

Create:

- `followup_years = followup_days / 365.25`
- `log_followup_years = log(followup_years)` for later Negative Binomial offset

Output:

- `stage1_hospitalization_analysis.csv`

### Section 6 — Outlier handling

Use Stage 0 QA flags plus Stage 1 checks.

Rules:

- Do not replace continuous outliers with mode, mean, or median.
- If a unit-conversion error is clinically and technically confirmed, correct it and log the rule.
- If no safe correction exists, set the implausible value to missing in analysis datasets.
- Do not remove an entire patient because of a non-outcome outlier.

Create:

- `stage1_outlier_action_log.csv`

Columns:

- `patient_id`
- `variable`
- `original_value`
- `action`
- `new_value`
- `reason`
- `requires_clinical_review`
- `decision_id`

### Section 7 — Comorbidity binary verification

Verify binary coding for comorbidities using DEC-038.

Check:

- values are 0/1
- no unexpected missing in binary variables
- raw date/entry columns retained but not used as main predictors

Output:

- `stage1_comorbidity_binary_check.csv`

### Section 8 — Echo missingness handling

Apply DEC-039 and document effective missingness.

For structured echo variables:

- convert `No Value`, `See below`, and other non-measurement entries to missing in analysis-ready derived columns, or count them as effective missing.
- preserve original columns.

Output:

- `stage1_echo_effective_missingness.csv`

### Section 9 — Clinician-approved categorical harmonization

Apply mapping rules from DEC-037.

For each categorical echo variable:

1. Count categories before grouping.
2. Apply clinician-approved grouping.
3. Count categories after grouping.
4. Export mapping and counts.
5. Preserve original variable.

Outputs:

- `stage1_clinician_category_mapping_applied.csv`
- `stage1_categorical_counts_before_after.csv`
- optional plot-ready files per variable or one combined file

### Section 10 — Echo-to-dialysis timing distribution

Apply DEC-041.

Create:

- `days_echo_to_dialysis` summary statistics
- timing categories
- histogram/plot-ready counts
- extreme gap list

Outputs:

- `stage1_echo_to_dialysis_timing_summary.csv`
- `stage1_echo_to_dialysis_timing_categories.csv`
- `stage1_echo_to_dialysis_extreme_gaps.csv`

### Section 11 — Missingness reports

Generate missingness by:

- full Stage 1 cohort
- one-year mortality cohort
- survival cohort
- hospitalization cohort
- main variables
- sensitivity variables
- exploratory variables

Output:

- `stage1_missingness_report.csv`

### Section 12 — Construct final predictor sets

Build final Stage 1 datasets.

#### Main dataset

Use main-eligible variables after removing:

- outcome variables
- administrative/date-only variables
- duplicate timing variables
- variables assigned to sensitivity/exploratory only
- unresolved variables
- free-text fields

Include grouped categorical variables where applicable.

Output:

- `stage1_main_analysis.csv`

#### Sensitivity dataset

Include:

- GFR alternative to creatinine
- SBP/DBP
- RVSize/RVSystolicFunction
- AorticValveRegurgitation
- alternative SPAP representation
- echo-before-dialysis indicators/cohorts

Output:

- `stage1_sensitivity_analysis.csv`

#### Exploratory dataset

Include:

- variables with high missingness
- `years_since_MI`
- rare valve features
- retained but non-main clinical variables

Output:

- `stage1_exploratory_analysis.csv`

### Section 13 — Final summary report

Export a human-readable report with:

- input source
- N before/after exclusions
- exclusion counts
- outcome cohort Ns
- outlier actions
- missingness overview
- categorical grouping summary
- timing-gap distribution summary
- remaining open decisions
- files generated

Output:

- `stage1_summary_report.md`

---

## 5. Required final outputs

Stage 1 should export:

| File | Purpose |
|---|---|
| `stage1_main_analysis.csv` | Main analytic dataset |
| `stage1_oneyear_mortality.csv` | One-year mortality cohort |
| `stage1_survival_analysis.csv` | Cox/survival cohort |
| `stage1_hospitalization_analysis.csv` | Hospitalization-rate cohort |
| `stage1_sensitivity_analysis.csv` | Sensitivity dataset |
| `stage1_exploratory_analysis.csv` | Exploratory dataset |
| `stage1_exclusions_log.csv` | Patient-level exclusion log |
| `stage1_outlier_action_log.csv` | Outlier handling log |
| `stage1_variable_processing_log.csv` | Variable transformations log |
| `stage1_missingness_report.csv` | Missingness report |
| `stage1_echo_effective_missingness.csv` | Echo-specific missingness report |
| `stage1_clinician_category_mapping_applied.csv` | Applied category mapping |
| `stage1_categorical_counts_before_after.csv` | Category frequencies before/after grouping |
| `stage1_echo_to_dialysis_timing_summary.csv` | Timing summary |
| `stage1_echo_to_dialysis_timing_categories.csv` | Timing-category counts |
| `stage1_echo_to_dialysis_extreme_gaps.csv` | Extreme timing gaps |
| `stage1_summary_report.md` | Human-readable summary |
| `stage1_run_metadata.json` | Reproducibility metadata |

---

## 6. Things Stage 1 must not do

Stage 1 must **not**:

- run final predictive models;
- run final Cox/Negative Binomial models;
- select clustering K;
- perform outcome-driven feature selection;
- correct outliers using mode/mean/median;
- delete patients because of BMI/weight/LV mass outliers;
- use `01_clean_flat.csv` as source of truth;
- use outcome/follow-up/admin variables as predictors;
- use all duplicate timing variables together;
- use GFR and creatinine together in the same base model;
- treat `No Value` as normal;
- drop free-text fields from the source dataset;
- silently merge categories without exporting before/after counts.

---

## 7. Remaining items for clinician/statistician review after Stage 1 outputs

Stage 1 should prepare these for review:

1. Frequency and percentage of same-day/after-death echo exclusions.
2. Distribution of echo-to-dialysis timing gaps.
3. Number of extreme echo-to-dialysis gaps.
4. Category frequencies before/after clinician grouping.
5. Outlier action log for BMI, Weight, LV mass, LVMI, IVS/PW, and E/e' values.
6. Final N for one-year mortality, survival, and hospitalization cohorts.
7. Missingness profile of main variables.

Only after these are reviewed should the project proceed to final modeling stages.
