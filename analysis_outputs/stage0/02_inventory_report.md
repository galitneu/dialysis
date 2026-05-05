# Stage 0 — Variable Inventory

Source: `01_clean_flat.csv` (n=645 patients, 83 columns)

Cleaning applied per DEC-011..020 (see `03_cleaning_provenance.md`).

Status legend:
- **Core clinical**: pre-specified by clinicians, in every model
- **Benchmark**: LV_EF, fixed in all models
- **Candidate**: fits a clinical axis and may be selected at Stage 4
- **Sensitivity**: relevant but missingness/overlap concerns
- **Descriptive only**: reported but not modeled
- **Excluded**: not used (date columns kept for derivations, free text, redundant, very high missing)


## Admin (5)

| Column | dtype | type | %miss | unique | Status |
|---|---|---|---|---|---|
| `patient number` | object | continuous | 0.0% | 645 | Excluded |
| `DeathDate` | object | date | 21.6% | 494 | Excluded — date kept for derivations |
| `Dialysis_Start_Date` | object | date | 0.0% | 615 | Excluded — date kept for derivations |
| `Echo_Date` | object | date | 0.0% | 644 | Excluded — date kept for derivations |
| `censor_or_event_date` | object | date | 0.0% | 494 | Excluded — derived |

## Clinical (14)

| Column | dtype | type | %miss | unique | Status |
|---|---|---|---|---|---|
| `HD/PD` | object | categorical | 0.0% | 2 | Candidate covariate (full base) |
| `m/f` | object | categorical | 0.2% | 2 | Core clinical |
| `AgeAtFirstHFDate` | object | continuous | 0.0% | 435 | Core clinical |
| `Weight` | object | continuous | 14.0% | 233 | Descriptive only (held for Stage 4 per DEC-017) |
| `BMI` | object | continuous | 18.8% | 488 | Descriptive only (held for Stage 4 per DEC-017) |
| `MI_binary` | object | binary | 0.0% | 2 | Candidate covariate (full base) |
| `CABG_binary` | object | binary | 0.0% | 2 | Candidate covariate (full base) |
| `IHD_binary` | object | binary | 0.0% | 2 | Candidate covariate (full base) |
| `AFIB_binary` | object | binary | 0.0% | 2 | Candidate covariate (full base) |
| `HTN_binary` | object | binary | 0.0% | 2 | Candidate covariate (full base) |
| `Diabetes mellitus_binary` | object | binary | 0.0% | 2 | Candidate covariate (full base) |
| `DYSLIPIDEMIA_binary` | object | binary | 0.0% | 2 | Descriptive only (held for Stage 4 per DEC-017) |
| `COPD_binary` | object | binary | 0.0% | 2 | Candidate covariate (full base) |
| `OncologicalDiagnosis_binary` | object | binary | 0.0% | 2 | Descriptive only (held for Stage 4 per DEC-017) |

## Echo: LV structure / mass (8)

| Column | dtype | type | %miss | unique | Status |
|---|---|---|---|---|---|
| `LeftVentricleCavitySize` | object | categorical | 11.5% | 5 | Sensitivity (categorical) |
| `LeftVentricleWallThickness` | object | categorical | 38.6% | 4 | Sensitivity (categorical) |
| `LeftVentricleEndDiastolicDiameter` | object | continuous | 1.2% | 247 | Sensitivity |
| `LeftVentricleEndSystolicDiameter` | object | continuous | 1.4% | 272 | Sensitivity |
| `LeftVentricleInterventricularSeptumThickness` | object | continuous | 1.2% | 118 | Sensitivity |
| `LeftVentriclePosteriorWallThickness` | object | continuous | 1.6% | 102 | Sensitivity |
| `LeftVentricleEstimatedMass` | object | continuous | 1.7% | 567 | Sensitivity (use LVMI instead) |
| `LeftVentricleEstimatedMassIndex` | object | continuous | 9.6% | 151 | Candidate (LVMI) |

## Echo: LV systolic (other) (4)

| Column | dtype | type | %miss | unique | Status |
|---|---|---|---|---|---|
| `LeftVentricleSystolicFunction` | object | categorical | 11.6% | 7 | Candidate (categorical) |
| `LeftVentricleScoreIndex` | object | continuous | 0.8% | 45 | Sensitivity (overlap with EF) |
| `TissueDopplerSVelocitySeptal` | object | continuous | 31.6% | 201 | Sensitivity (>30% effective miss) |
| `TissueDopplerSVelocityLateral` | object | continuous | 20.3% | 233 | Sensitivity (~20% miss) |

## Echo: Text (4)

| Column | dtype | type | %miss | unique | Status |
|---|---|---|---|---|---|
| `LeftVentricleSummary` | object | categorical | 70.1% | 42 | Descriptive only — Hebrew free text |
| `AorticValveSummary` | object | categorical | 78.8% | 33 | Descriptive only — Hebrew free text |
| `MitralValveSummary` | object | categorical | 68.7% | 45 | Descriptive only — Hebrew free text |
| `ProcedureSummary` | object | categorical | 0.0% | 644 | Descriptive only — Hebrew free text |

## Echo: Benchmark (1)

| Column | dtype | type | %miss | unique | Status |
|---|---|---|---|---|---|
| `LV_EF` | object | continuous | 0.6% | 35 | Benchmark — fixed in all models |

## Echo: Right-heart / congestion (5)

| Column | dtype | type | %miss | unique | Status |
|---|---|---|---|---|---|
| `RVSize` | object | categorical | 53.5% | 4 | Candidate (categorical) |
| `RVSystolicFunction` | object | categorical | 52.9% | 4 | Candidate (categorical) |
| `TricuspidRegurgitation` | object | categorical | 7.0% | 6 | Candidate (categorical) |
| `ECHO_SPAP` | object | categorical | 18.4% | 4 | Candidate (categorical) |
| `EstimatedSysPAPressure` | object | continuous | 16.7% | 77 | Candidate (numeric SPAP) |

## Echo: LA / atrial (1)

| Column | dtype | type | %miss | unique | Status |
|---|---|---|---|---|---|
| `LACavitySize` | object | categorical | 6.7% | 4 | Candidate (categorical) |

## Echo: Valves (5)

| Column | dtype | type | %miss | unique | Status |
|---|---|---|---|---|---|
| `AorticValveStructure` | object | categorical | 30.2% | 8 | Sensitivity (categorical) |
| `AorticValveRegurgitation` | object | categorical | 53.2% | 6 | Candidate (categorical, was OMITTED from stage2) |
| `MitralValveStructure` | object | categorical | 71.8% | 7 | Excluded (>60% effective miss after No Value→NaN) |
| `MitralRegurgitation` | object | categorical | 7.4% | 8 | Candidate (categorical) |
| `TricuspidValveStructure` | object | categorical | 89.0% | 4 | Excluded (>85% effective miss) |

## Echo: LV diastolic / filling (5)

| Column | dtype | type | %miss | unique | Status |
|---|---|---|---|---|---|
| `MitralInflowPeakEWave` | object | continuous | 9.8% | 302 | Candidate |
| `TissueDopplerEVelositySeptal` | object | continuous | 17.7% | 245 | Candidate (was previously OMITTED) |
| `TissueDopplerEERatioSeptal` | object | continuous | 18.9% | 474 | Candidate |
| `TissueDopplerEVelosityLateral` | object | continuous | 17.7% | 256 | Candidate (was previously OMITTED) |
| `TissueDopplerEERatioLateral` | object | continuous | 18.9% | 452 | Candidate |

## Clinical (date) (9)

| Column | dtype | type | %miss | unique | Status |
|---|---|---|---|---|---|
| `MI` | object | date | 70.2% | 174 | Excluded — date kept; binary used |
| `CABG` | object | date | 79.4% | 108 | Excluded — date kept; binary used |
| `IHD` | object | date | 38.6% | 394 | Excluded — date kept; binary used |
| `AFIB` | object | date | 53.0% | 300 | Excluded — date kept; binary used |
| `HTN` | object | date | 17.4% | 529 | Excluded — date kept; binary used |
| `Diabetes mellitus` | object | date | 36.4% | 409 | Excluded — date kept; binary used |
| `DYSLIPIDEMIA` | object | date | 51.8% | 308 | Excluded — date kept; binary used |
| `COPD` | object | date | 83.7% | 105 | Excluded — date kept; binary used |
| `OncologicalDiagnosis` | object | categorical | 77.8% | 1 | Excluded — date kept; binary used |

## Lab (14)

| Column | dtype | type | %miss | unique | Status |
|---|---|---|---|---|---|
| `sbp-numeric result` | object | continuous | 25.4% | 115 | Sensitivity (>20% missing) |
| `dbp-numeric result` | object | continuous | 21.2% | 77 | Sensitivity (>20% missing) |
| `GFR` | object | continuous | 0.2% | 616 | Candidate covariate (alternative to creatinine) |
| `na-numeric result` | object | continuous | 0.5% | 56 | Sensitivity (held for Stage 4) |
| `k-numeric result` | object | continuous | 0.5% | 69 | Sensitivity (held for Stage 4) |
| `albumin-numeric result` | object | continuous | 0.2% | 39 | Candidate covariate (full base) |
| `hb-numeric result` | object | continuous | 10.2% | 105 | Candidate covariate (full base) |
| `urea-numeric result` | object | continuous | 0.6% | 267 | Sensitivity (held for Stage 4) |
| `creatinine-numeric result` | object | continuous | 0.2% | 428 | Core clinical (parsimonious base) |
| `ca-numeric result` | object | continuous | 0.2% | 58 | Sensitivity (held for Stage 4) |
| `p-numeric result` | object | continuous | 0.2% | 129 | Sensitivity (held for Stage 4) |
| `ua-numeric result` | object | continuous | 0.2% | 149 | Sensitivity (held for Stage 4) |
| `crp-numeric result` | object | continuous | 3.9% | 595 | Candidate covariate (full base) |
| `hba1c-numeric result` | object | continuous | 10.1% | 71 | Sensitivity (held for Stage 4) |

## Outcome (6)

| Column | dtype | type | %miss | unique | Status |
|---|---|---|---|---|---|
| `hospitalization-count` | object | continuous | 0.0% | 11 | Excluded — duplicate of hosp_total |
| `death_event` | object | binary | 0.0% | 2 | Outcome — secondary (Cox) |
| `time_to_event_days` | object | continuous | 0.0% | 513 | Outcome — secondary (Cox) |
| `followup_days` | object | continuous | 0.0% | 513 | Outcome — denominator for hosp rate |
| `died_1year` | object | binary | 4.2% | 2 | Outcome — primary (1y mortality) |
| `hosp_total` | object | continuous | 0.0% | 11 | Outcome — primary (hosp rate) |

## Outcome QC (1)

| Column | dtype | type | %miss | unique | Status |
|---|---|---|---|---|---|
| `flag_echo_after_death` | object | binary | 0.0% | 2 | Used to define cohort exclusion |

## Timing (1)

| Column | dtype | type | %miss | unique | Status |
|---|---|---|---|---|---|
| `gap_echo_to_dial_days` | object | continuous | 0.0% | 297 | Core clinical (covariate) |
