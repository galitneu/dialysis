# Stage -1 Raw Audit — `echo_project_update.xlsx`

**Source**: /home/user/dialysis/echo_project_update.xlsx
**Shape**: 645 patients × 66 columns
**Unique patient IDs**: 645 (duplicates: 0)

## Variable inventory (grouped by inferred role)


### ID  (1 cols)

| # | Column | dtype | %miss(raw) | "No Value" str | unique | NULL semantics |
|---|---|---|---|---|---|---|
| 0 | `patient number` | object | 0.0% | 0 | 645 | Identifier — no missing expected |

### unknown  (15 cols)

| # | Column | dtype | %miss(raw) | "No Value" str | unique | NULL semantics |
|---|---|---|---|---|---|---|
| 1 | `HD/PD` | object | 0.0% | 0 | 3 | unclear |
| 2 | `m/f` | object | 0.2% | 0 | 3 | unclear |
| 7 | `LeftVentricleCavitySize` | object | 4.5% | 45 | 6 | unclear |
| 8 | `LeftVentricleWallThickness` | object | 15.5% | 143 | 6 | unclear |
| 9 | `LeftVentricleSystolicFunction` | object | 4.5% | 46 | 10 | unclear |
| 12 | `RVSize` | object | 23.3% | 195 | 5 | unclear |
| 13 | `RVSystolicFunction` | object | 22.8% | 194 | 5 | unclear |
| 14 | `LACavitySize` | object | 2.2% | 29 | 5 | unclear |
| 15 | `AorticValveStructure` | object | 13.6% | 106 | 12 | unclear |
| 16 | `AorticValveRegurgitation` | object | 29.0% | 156 | 7 | unclear |
| 18 | `MitralValveStructure` | object | 30.5% | 261 | 10 | unclear |
| 19 | `MitralRegurgitation` | object | 2.9% | 29 | 13 | unclear |
| 21 | `TricuspidValveStructure` | object | 36.4% | 339 | 7 | unclear |
| 22 | `TricuspidRegurgitation` | object | 2.9% | 26 | 7 | unclear |
| 23 | `ECHO_SPAP` | object | 18.4% | 0 | 4 | unclear |

### Continuous (echo or lab)  (33 cols)

| # | Column | dtype | %miss(raw) | "No Value" str | unique | NULL semantics |
|---|---|---|---|---|---|---|
| 3 | `AgeAtFirstHFDate` | object | 0.0% | 0 | 435 | NaN = not measured (true missing) |
| 11 | `LV_EF` | object | 0.6% | 0 | 35 | NaN = not measured (true missing) |
| 24 | `LeftVentricleEndDiastolicDiameter` | object | 1.2% | 0 | 247 | NaN = not measured (true missing) |
| 25 | `LeftVentricleEndSystolicDiameter` | object | 1.4% | 0 | 272 | NaN = not measured (true missing) |
| 26 | `LeftVentricleInterventricularSeptumThickness` | object | 1.2% | 0 | 118 | NaN = not measured (true missing) |
| 27 | `LeftVentriclePosteriorWallThickness` | object | 1.6% | 0 | 102 | NaN = not measured (true missing) |
| 28 | `LeftVentricleEstimatedMass` | object | 1.7% | 0 | 567 | NaN = not measured (true missing) |
| 29 | `LeftVentricleEstimatedMassIndex` | object | 9.6% | 0 | 151 | NaN = not measured (true missing) |
| 30 | `LeftVentricleScoreIndex` | object | 0.8% | 0 | 45 | NaN = not measured (true missing) |
| 31 | `EstimatedSysPAPressure` | object | 16.7% | 0 | 77 | NaN = not measured (true missing) |
| 32 | `MitralInflowPeakEWave` | object | 9.8% | 0 | 302 | NaN = not measured (true missing) |
| 33 | `TissueDopplerSVelocitySeptal` | object | 31.6% | 0 | 201 | NaN = not measured (true missing) |
| 34 | `TissueDopplerEVelositySeptal` | object | 17.7% | 0 | 245 | NaN = not measured (true missing) |
| 35 | `TissueDopplerEERatioSeptal` | object | 18.9% | 0 | 474 | NaN = not measured (true missing) |
| 36 | `TissueDopplerSVelocityLateral` | object | 20.3% | 0 | 233 | NaN = not measured (true missing) |
| 37 | `TissueDopplerEVelosityLateral` | object | 17.7% | 0 | 256 | NaN = not measured (true missing) |
| 38 | `TissueDopplerEERatioLateral` | object | 18.9% | 0 | 452 | NaN = not measured (true missing) |
| 40 | `Weight` | object | 14.0% | 0 | 233 | NaN = not measured (true missing) |
| 41 | `BMI` | object | 18.8% | 0 | 488 | NaN = not measured (true missing) |
| 51 | `sbp-numeric result` | object | 25.4% | 0 | 115 | NaN = not measured (true missing) |
| 52 | `dbp-numeric result` | object | 21.2% | 0 | 77 | NaN = not measured (true missing) |
| 54 | `GFR` | object | 0.2% | 0 | 616 | NaN = not measured (true missing) |
| 55 | `na-numeric result` | object | 0.5% | 0 | 56 | NaN = not measured (true missing) |
| 56 | `k-numeric result` | object | 0.5% | 0 | 69 | NaN = not measured (true missing) |
| 57 | `albumin-numeric result` | object | 0.2% | 0 | 39 | NaN = not measured (true missing) |
| 58 | `hb-numeric result` | object | 10.2% | 0 | 105 | NaN = not measured (true missing) |
| 59 | `urea-numeric result` | object | 0.6% | 0 | 267 | NaN = not measured (true missing) |
| 60 | `creatinine-numeric result` | object | 0.2% | 0 | 428 | NaN = not measured (true missing) |
| 61 | `ca-numeric result` | object | 0.2% | 0 | 58 | NaN = not measured (true missing) |
| 62 | `p-numeric result` | object | 0.2% | 0 | 129 | NaN = not measured (true missing) |
| 63 | `ua-numeric result` | object | 0.2% | 0 | 149 | NaN = not measured (true missing) |
| 64 | `crp-numeric result` | object | 3.9% | 0 | 595 | NaN = not measured (true missing) |
| 65 | `hba1c-numeric result` | object | 10.1% | 0 | 71 | NaN = not measured (true missing) |

### Outcome / time origin  (3 cols)

| # | Column | dtype | %miss(raw) | "No Value" str | unique | NULL semantics |
|---|---|---|---|---|---|---|
| 4 | `DeathDate` | object | 21.6% | 0 | 494 | NaN in DeathDate = censored / alive at last FU; otherwise NaN = data error |
| 5 | `Dialysis_Start_Date` | object | 0.0% | 0 | 615 | NaN in DeathDate = censored / alive at last FU; otherwise NaN = data error |
| 6 | `Echo_Date` | object | 0.0% | 0 | 644 | NaN in DeathDate = censored / alive at last FU; otherwise NaN = data error |

### Echo text (descriptive only)  (4 cols)

| # | Column | dtype | %miss(raw) | "No Value" str | unique | NULL semantics |
|---|---|---|---|---|---|---|
| 10 | `LeftVentricleSummary` | object | 69.8% | 0 | 52 | NULL = no narrative entered (descriptive only; high missingness expected) |
| 17 | `AorticValveSummary` | object | 78.6% | 0 | 42 | NULL = no narrative entered (descriptive only; high missingness expected) |
| 20 | `MitralValveSummary` | object | 68.7% | 0 | 57 | NULL = no narrative entered (descriptive only; high missingness expected) |
| 39 | `ProcedureSummary` | object | 0.0% | 0 | 644 | NULL = no narrative entered (descriptive only; high missingness expected) |

### Comorbidity (atypical encoding)  (1 cols)

| # | Column | dtype | %miss(raw) | "No Value" str | unique | NULL semantics |
|---|---|---|---|---|---|---|
| 42 | `MI` | object | 70.1% | 0 | 175 | MIXED dtype object: some dates, some strings → INVESTIGATE |

### Comorbidity date — derive binary as notna()  (7 cols)

| # | Column | dtype | %miss(raw) | "No Value" str | unique | NULL semantics |
|---|---|---|---|---|---|---|
| 43 | `CABG` | object | 79.4% | 0 | 108 | Date-encoded comorbidity → NaN = NO condition (NOT missing) |
| 44 | `IHD` | object | 38.6% | 0 | 394 | Date-encoded comorbidity → NaN = NO condition (NOT missing) |
| 45 | `AFIB` | object | 53.0% | 0 | 300 | Date-encoded comorbidity → NaN = NO condition (NOT missing) |
| 46 | `HTN` | object | 17.4% | 0 | 529 | Date-encoded comorbidity → NaN = NO condition (NOT missing) |
| 47 | `Diabetes mellitus` | object | 36.4% | 0 | 409 | Date-encoded comorbidity → NaN = NO condition (NOT missing) |
| 48 | `DYSLIPIDEMIA` | object | 51.8% | 0 | 308 | Date-encoded comorbidity → NaN = NO condition (NOT missing) |
| 49 | `COPD` | object | 83.7% | 0 | 105 | Date-encoded comorbidity → NaN = NO condition (NOT missing) |

### Comorbidity flag  (1 cols)

| # | Column | dtype | %miss(raw) | "No Value" str | unique | NULL semantics |
|---|---|---|---|---|---|---|
| 50 | `OncologicalDiagnosis` | object | 77.8% | 0 | 1 | String marker: NaN vs 'Oncological diagnosis' → derive binary |

### Outcome (hosp count)  (1 cols)

| # | Column | dtype | %miss(raw) | "No Value" str | unique | NULL semantics |
|---|---|---|---|---|---|---|
| 53 | `hospitalization-count` | object | 0.0% | 0 | 11 | Always populated (0 or N) — no NaN expected |
