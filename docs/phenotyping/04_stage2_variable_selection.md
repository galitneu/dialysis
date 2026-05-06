# Stage 2 — Variable Selection for Clustering

**Date:** 2026-05-06
**Goal:** Decide which variables enter the clustering algorithm.

---

## Available pool after DEC-PHENO-004 dropouts

After dropping variables with >25% original missingness (per DEC-PHENO-004):

**Excluded** (>25% missing):
- LeftVentricleWallThickness (37.7%)
- AorticValveStructure (30.1%)
- TissueDopplerSVelocitySeptal (31.6%)
- sbp-numeric result (25.4%) ← borderline, drop per committee preference

**Remaining pool: 47 candidate variables** across 6 domains.

---

## Committee Deliberation

### CARD (Cardiologist) — clinical priorities

> "For HF phenotyping, the field has converged on these core dimensions:
> 1. **Systolic function** — LV_EF (essential)
> 2. **LV geometry/hypertrophy** — wall thickness or mass index
> 3. **LV size** — end-diastolic diameter
> 4. **Diastolic function / filling pressure** — E/e' septal, E wave, LA size
> 5. **Pulmonary hemodynamics** — SPAP
> 6. **Right side / regurgitation** — TR severity
> 7. **Cardiac rhythm** — AFIB
>
> A meaningful HF phenotyping needs at least one variable per dimension. Without that, the clusters won't map to recognized HF subtypes."

### NEPH (Nephrologist) — dialysis-specific markers

> "From renal/dialysis perspective, key markers:
> 1. **Modality** — HD vs PD
> 2. **Nutrition/inflammation** — albumin, CRP
> 3. **Renal residual** — creatinine, urea, GFR
> 4. **Anemia** — hemoglobin
> 5. **Mineral metabolism** — calcium, phosphate
> 6. **Diabetes** — major comorbidity, affects vascular access and prognosis
>
> Comorbidity profile (HTN, DM, IHD) shapes the population substantially."

### EPI (Epidemiologist) — caution on scope

> "For n=645, classical clustering recommendations suggest 10-15 variables for stable solutions. With more variables we get curse of dimensionality and noisy distance metrics. We need to **prioritize**, not include everything."

### STAT (Statistician) — methodological considerations

> "Two principles:
> 1. **Avoid redundancy** — LV mass and LV mass index correlate r=0.881; choose one.
> 2. **Use scaled continuous + binary indicators**; avoid one-hot of high-cardinality categoricals (each level becomes a sparse binary, distorting distances).
>
> For categoricals with >3 levels (LACavitySize, MR, TR, ECHO_SPAP, LV systolic function, LV cavity size) — collapse to clinical groupings (e.g., 'Normal/Mild' vs 'Moderate/Severe') before clustering, OR convert to ordinal scores."

### SKEP (Skeptic) — what we don't include matters

> "Whatever we exclude, mention in the report. Reviewers will ask 'why did you not use X?'. We need pre-specified rationale, not post-hoc."

### PM (Project Manager) — keep moving

> "We're at decision time. The committee is converging. Lead investigator needs a recommended primary set + a sensitivity set, then we proceed."

---

## Proposed Variable Sets

### Core Set (16 variables) — primary clustering input

Designed to span all clinical dimensions while keeping dimensionality manageable.

| # | Variable | Type | Domain | Missing % | Rationale |
|---|---|---|---|---|---|
| 1 | AgeAtFirstHFDate | continuous | demographics | 0.0 | core demographic |
| 2 | sex_male | binary | demographics | 0.2 | sex differences in HF |
| 3 | HD_binary | binary | demographics | 0.0 | dialysis modality |
| 4 | AFIB_binary | binary | comorbidity | 0.0 | rhythm/atrial dysfunction |
| 5 | Diabetes_binary | binary | comorbidity | 0.0 | major metabolic comorbidity |
| 6 | LV_EF | continuous | echo systolic | 0.6 | core HF marker |
| 7 | LeftVentricleEndDiastolicDiameter | continuous | echo structure | 1.2 | LV remodeling |
| 8 | LeftVentriclePosteriorWallThickness | continuous | echo structure | 2.0 | LV hypertrophy |
| 9 | LeftVentricleEstimatedMass | continuous | echo structure | 2.5 | total LV burden |
| 10 | MitralInflowPeakEWave | continuous | echo function | 9.8 | filling velocity |
| 11 | TissueDopplerEERatioSeptal | continuous | echo function | 18.9 | filling pressure (E/e') |
| 12 | EstimatedSysPAPressure | continuous | echo hemodynamics | 16.7 | pulmonary pressure |
| 13 | LACavity_dilated | binary (collapsed) | echo structure | 6.7 | LA dilatation (Mod/Sev vs Normal/Mild) |
| 14 | TR_moderate_or_severe | binary (collapsed) | echo regurg | 7.0 | TR burden |
| 15 | albumin-numeric result | continuous | lab nutrition | 0.2 | nutrition/inflammation |
| 16 | creatinine-numeric result | continuous | lab renal | 0.2 | muscle mass / renal |
| 17 | crp-numeric result | continuous | lab inflammation | 3.9 | systemic inflammation |
| 18 | hb-numeric result | continuous | lab anemia | 10.2 | anemia |

**(actually 18 variables — STAT comment: still acceptable for n=645)**

### Sensitivity Set (extended, 24 variables)

Adds:
- BMI (19.2% missing, kNN)
- Weight (14.1%)
- LeftVentricleScoreIndex (0.8%)
- LeftVentricleEstimatedMassIndex (10.4%)
- TissueDopplerEVelositySeptal (17.7%) — alternative diastolic marker
- urea (0.6%)

---

## Variables EXCLUDED — with rationale

| Variable | Reason |
|---|---|
| LeftVentricleWallThickness | 37.7% missing — too distorted |
| AorticValveStructure | 30.1% missing — too distorted |
| TissueDopplerSVelocitySeptal | 31.6% missing — too distorted |
| sbp-numeric result | 25.4% missing — borderline, dropped per DEC-PHENO-004 |
| dbp-numeric result | 21.2% missing — kept in sensitivity set; dropped from core |
| LV_EstimatedMassIndex | redundant with LV_EstimatedMass (r=0.881) — kept Mass, dropped Index in core |
| LeftVentricleSystolicFunction | redundant with continuous LV_EF — kept LV_EF only |
| LeftVentricleCavitySize | redundant with LeftVentricleEndDiastolicDiameter — kept continuous |
| ECHO_SPAP | redundant with continuous EstimatedSysPAPressure |
| MitralRegurgitation | included only if collapsed binary helps; otherwise excluded |
| TissueDopplerEVelosity Lateral, EERatio Lateral, SVelocity Lateral | redundant with septal counterparts; lateral often less reliable |
| Comorbidities other than AFIB, DM | exclude HTN, IHD, MI, CABG, dyslipidemia, COPD from core to avoid binary inflation; can use as descriptive characterization |
| ca, p, na, k, GFR, hba1c, ua | secondary labs; included only in sensitivity set |
| HD/PD | included as binary (HD_binary) |
| time/date variables | not appropriate for cross-sectional phenotyping |

---

## Outcomes EXPLICITLY excluded (Rule 2 of charter)

The following are NEVER inputs to clustering:
- event, event_1y, died_1year, died_1y
- time_to_event_days, time_to_event_years
- hosp_total, hospitalization-count
- followup_*, DeathDate, data_cutoff_date
