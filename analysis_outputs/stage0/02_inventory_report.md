# Stage 0 — Variable Inventory

Source: `01_clean_flat.csv` (n=645 patients, 82 columns)

Cleaning applied per DEC-011..029. See `03_cleaning_provenance.md`.

## Bucket counts

- **main**: 29
- **sensitivity**: 23
- **excluded**: 15
- **outcome**: 6
- **exploratory**: 4
- **identifier**: 1

## Full inventory by clinical axis


### Admin (5)

| Column | dtype | type | %miss | unique | Bucket | Proposed status |
|---|---|---|---|---|---|---|
| `patient_id` | object | continuous | 0.0% | 645 | **identifier** | Excluded |
| `DeathDate` | object | date | 21.6% | 494 | **nan** | Excluded — date kept for derivations |
| `Dialysis_Start_Date` | object | date | 0.0% | 615 | **nan** | Excluded — date kept for derivations |
| `Echo_Date` | object | date | 0.0% | 644 | **nan** | Excluded — date kept for derivations |
| `censor_or_event_date` | object | date | 0.0% | 494 | **nan** | Excluded — derived |

### Clinical (14)

| Column | dtype | type | %miss | unique | Bucket | Proposed status |
|---|---|---|---|---|---|---|
| `HD/PD` | object | categorical | 0.0% | 3 | **main** | Candidate covariate (full base) |
| `m/f` | object | categorical | 0.2% | 3 | **main** | Core clinical |
| `AgeAtFirstHFDate` | object | continuous | 0.0% | 435 | **main** | Core clinical |
| `Weight` | object | continuous | 14.0% | 233 | **exploratory** | Held for Stage 4 per DEC-017 |
| `BMI` | object | continuous | 18.8% | 488 | **exploratory** | Held for Stage 4 per DEC-017 |
| `MI_binary` | object | binary | 0.0% | 2 | **main** | Candidate covariate (full base) |
| `CABG_binary` | object | binary | 0.0% | 2 | **main** | Candidate covariate (full base) |
| `IHD_binary` | object | binary | 0.0% | 2 | **main** | Candidate covariate (full base) |
| `AFIB_binary` | object | binary | 0.0% | 2 | **main** | Candidate covariate (full base) |
| `HTN_binary` | object | binary | 0.0% | 2 | **main** | Candidate covariate (full base) |
| `Diabetes mellitus_binary` | object | binary | 0.0% | 2 | **main** | Candidate covariate (full base) |
| `DYSLIPIDEMIA_binary` | object | binary | 0.0% | 2 | **exploratory** | Held for Stage 4 per DEC-017 |
| `COPD_binary` | object | binary | 0.0% | 2 | **main** | Candidate covariate (full base) |
| `OncologicalDiagnosis_binary` | object | binary | 0.0% | 2 | **exploratory** | Held for Stage 4 per DEC-017 |

### Echo: LV structure / mass (8)

| Column | dtype | type | %miss | unique | Bucket | Proposed status |
|---|---|---|---|---|---|---|
| `LeftVentricleCavitySize` | object | categorical | 11.5% | 5 | **sensitivity** | Sensitivity (categorical) |
| `LeftVentricleWallThickness` | object | categorical | 38.6% | 4 | **sensitivity** | Sensitivity (categorical) |
| `LeftVentricleEndDiastolicDiameter` | object | continuous | 1.2% | 247 | **sensitivity** | Sensitivity |
| `LeftVentricleEndSystolicDiameter` | object | continuous | 1.4% | 272 | **sensitivity** | Sensitivity |
| `LeftVentricleInterventricularSeptumThickness` | object | continuous | 1.2% | 118 | **sensitivity** | Sensitivity |
| `LeftVentriclePosteriorWallThickness` | object | continuous | 1.6% | 102 | **sensitivity** | Sensitivity |
| `LeftVentricleEstimatedMass` | object | continuous | 1.7% | 567 | **sensitivity** | Sensitivity (use LVMI) |
| `LeftVentricleEstimatedMassIndex` | object | continuous | 9.6% | 151 | **main** | Candidate (LVMI) |

### Echo: LV systolic (other) (4)

| Column | dtype | type | %miss | unique | Bucket | Proposed status |
|---|---|---|---|---|---|---|
| `LeftVentricleSystolicFunction` | object | categorical | 11.6% | 8 | **main** | Candidate (categorical) |
| `LeftVentricleScoreIndex` | object | continuous | 0.8% | 45 | **sensitivity** | Sensitivity (overlap with EF) |
| `TissueDopplerSVelocitySeptal` | object | continuous | 31.6% | 201 | **sensitivity** | Sensitivity (>30% miss) |
| `TissueDopplerSVelocityLateral` | object | continuous | 20.3% | 233 | **sensitivity** | Sensitivity (~20% miss) |

### Echo: Text (4)

| Column | dtype | type | %miss | unique | Bucket | Proposed status |
|---|---|---|---|---|---|---|
| `LeftVentricleSummary` | object | categorical | 69.8% | 52 | **excluded** | Descriptive only — Hebrew text |
| `AorticValveSummary` | object | categorical | 78.6% | 42 | **excluded** | Descriptive only — Hebrew text |
| `MitralValveSummary` | object | categorical | 68.7% | 57 | **excluded** | Descriptive only — Hebrew text |
| `ProcedureSummary` | object | categorical | 0.0% | 644 | **excluded** | Descriptive only — Hebrew text |

### Echo: Benchmark (1)

| Column | dtype | type | %miss | unique | Bucket | Proposed status |
|---|---|---|---|---|---|---|
| `LV_EF` | object | continuous | 0.6% | 35 | **main** | Benchmark — fixed in all models |

### Echo: Right-heart / congestion (5)

| Column | dtype | type | %miss | unique | Bucket | Proposed status |
|---|---|---|---|---|---|---|
| `RVSize` | object | categorical | 53.5% | 4 | **sensitivity** | Sensitivity / exploratory (>50% miss per DEC-023) |
| `RVSystolicFunction` | object | categorical | 52.9% | 4 | **sensitivity** | Sensitivity / exploratory (>50% miss per DEC-023) |
| `TricuspidRegurgitation` | object | categorical | 7.0% | 6 | **main** | Candidate (categorical) |
| `ECHO_SPAP` | object | categorical | 18.4% | 4 | **main** | Candidate (categorical) |
| `EstimatedSysPAPressure` | object | continuous | 16.7% | 77 | **main** | Candidate (numeric SPAP) |

### Echo: LA / atrial (1)

| Column | dtype | type | %miss | unique | Bucket | Proposed status |
|---|---|---|---|---|---|---|
| `LACavitySize` | object | categorical | 6.7% | 4 | **main** | Candidate (categorical) |

### Echo: Valves (5)

| Column | dtype | type | %miss | unique | Bucket | Proposed status |
|---|---|---|---|---|---|---|
| `AorticValveStructure` | object | categorical | 30.2% | 10 | **sensitivity** | Sensitivity (categorical) |
| `AorticValveRegurgitation` | object | categorical | 53.2% | 6 | **sensitivity** | Sensitivity / exploratory (>50% miss per DEC-023) |
| `MitralValveStructure` | object | categorical | 71.8% | 8 | **excluded** | Excluded (>60% miss after No Value→NaN) |
| `MitralRegurgitation` | object | categorical | 7.4% | 9 | **main** | Candidate (categorical) |
| `TricuspidValveStructure` | object | categorical | 89.0% | 6 | **excluded** | Excluded (>85% miss) |

### Echo: LV diastolic / filling (5)

| Column | dtype | type | %miss | unique | Bucket | Proposed status |
|---|---|---|---|---|---|---|
| `MitralInflowPeakEWave` | object | continuous | 9.8% | 302 | **main** | Candidate |
| `TissueDopplerEVelositySeptal` | object | continuous | 17.7% | 245 | **main** | Candidate (was OMITTED previously) |
| `TissueDopplerEERatioSeptal` | object | continuous | 18.9% | 474 | **main** | Candidate |
| `TissueDopplerEVelosityLateral` | object | continuous | 17.7% | 256 | **main** | Candidate (was OMITTED previously) |
| `TissueDopplerEERatioLateral` | object | continuous | 18.9% | 452 | **main** | Candidate |

### Clinical (date) (9)

| Column | dtype | type | %miss | unique | Bucket | Proposed status |
|---|---|---|---|---|---|---|
| `MI` | object | date | 70.1% | 175 | **excluded** | Excluded — date kept; binary used |
| `CABG` | object | date | 79.4% | 108 | **excluded** | Excluded — date kept; binary used |
| `IHD` | object | date | 38.6% | 394 | **excluded** | Excluded — date kept; binary used |
| `AFIB` | object | date | 53.0% | 300 | **excluded** | Excluded — date kept; binary used |
| `HTN` | object | date | 17.4% | 529 | **excluded** | Excluded — date kept; binary used |
| `Diabetes mellitus` | object | date | 36.4% | 409 | **excluded** | Excluded — date kept; binary used |
| `DYSLIPIDEMIA` | object | date | 51.8% | 308 | **excluded** | Excluded — date kept; binary used |
| `COPD` | object | date | 83.7% | 105 | **excluded** | Excluded — date kept; binary used |
| `OncologicalDiagnosis` | object | categorical | 77.8% | 1 | **excluded** | Excluded — date kept; binary used |

### Lab (14)

| Column | dtype | type | %miss | unique | Bucket | Proposed status |
|---|---|---|---|---|---|---|
| `sbp-numeric result` | object | continuous | 25.4% | 115 | **sensitivity** | Sensitivity (>20% missing) |
| `dbp-numeric result` | object | continuous | 21.2% | 77 | **sensitivity** | Sensitivity (>20% missing) |
| `GFR` | object | continuous | 0.2% | 616 | **main** | Candidate covariate (alternative to creatinine) |
| `na-numeric result` | object | continuous | 0.5% | 56 | **sensitivity** | Held for Stage 4 |
| `k-numeric result` | object | continuous | 0.5% | 69 | **sensitivity** | Held for Stage 4 |
| `albumin-numeric result` | object | continuous | 0.2% | 39 | **main** | Candidate covariate (full base) |
| `hb-numeric result` | object | continuous | 10.2% | 105 | **main** | Candidate covariate (full base) |
| `urea-numeric result` | object | continuous | 0.6% | 267 | **sensitivity** | Held for Stage 4 |
| `creatinine-numeric result` | object | continuous | 0.2% | 428 | **main** | Core clinical (parsimonious base) |
| `ca-numeric result` | object | continuous | 0.2% | 58 | **sensitivity** | Held for Stage 4 |
| `p-numeric result` | object | continuous | 0.2% | 129 | **sensitivity** | Held for Stage 4 |
| `ua-numeric result` | object | continuous | 0.2% | 149 | **sensitivity** | Held for Stage 4 |
| `crp-numeric result` | object | continuous | 3.9% | 595 | **main** | Candidate covariate (full base) |
| `hba1c-numeric result` | object | continuous | 10.1% | 71 | **sensitivity** | Held for Stage 4 |

### Outcome (5)

| Column | dtype | type | %miss | unique | Bucket | Proposed status |
|---|---|---|---|---|---|---|
| `hosp_total` | object | continuous | 0.0% | 11 | **outcome** | Outcome — primary (hosp rate) |
| `death_event` | object | binary | 0.0% | 2 | **outcome** | Outcome — secondary (Cox) |
| `time_to_event_days` | object | continuous | 0.0% | 513 | **outcome** | Outcome — secondary (Cox) |
| `followup_days` | object | continuous | 0.0% | 513 | **outcome** | Outcome — denominator for hosp rate |
| `died_1year` | object | binary | 4.2% | 2 | **outcome** | Outcome — primary (1y mortality) |

### Timing (1)

| Column | dtype | type | %miss | unique | Bucket | Proposed status |
|---|---|---|---|---|---|---|
| `gap_echo_to_dial_days` | object | continuous | 0.0% | 297 | **main** | Core clinical (covariate) |

### Outcome QC (1)

| Column | dtype | type | %miss | unique | Bucket | Proposed status |
|---|---|---|---|---|---|---|
| `flag_echo_after_death` | object | binary | 0.0% | 2 | **outcome** | Used to define cohort exclusion |
