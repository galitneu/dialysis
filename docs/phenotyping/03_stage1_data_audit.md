# Stage 1 — Data Audit

**Date:** 2026-05-06
**Goal:** Identify the dataset to use for clustering and verify its state.

---

## Available datasets in repo

| Dataset | Location | Shape | Status |
|---|---|---|---|
| Raw base | `base_analysis_dataset.xlsx` → `base_analysis_dataset` sheet | 645 × 83 | unprocessed continuous + categorical |
| Stage 2 ready | `stage2_analysis_ready.csv` | 645 × 79 | sex/age z-scored, some encoding done |
| **Clustering Matrix** | `base_analysis_dataset.xlsx` → `Clustering_Matrix` sheet | **645 × 90** | **fully encoded + z-scored + imputed; passes Stage 3 QA** |

---

## The "Clustering_Matrix" — what it is

Per the **Stage 3 QA summary** (also in the xlsx):
- 645 patients, 89 features (after one-hot encoding of 10 categoricals into 48 dummy columns)
- Continuous variables (33): z-scored
- Binary/one-hot (50+): unscaled (0/1)
- Imputation: median for continuous (32 vars), most_frequent for categorical (9 vars)
- 0 remaining NaNs
- 0 near-zero-variance flagged
- Marked: "✅ Matrix ready for clustering"

This is the matrix that the prior `cluster_assignments_all_solutions.csv` was built from.

---

## The methodological issue (per lead investigator)

> "The clusters were built without good cleaning of the data. I would not build on them — maybe take direction only."

Audit confirms this concern. Looking at the **Imputation_Log**, **19 of 41 imputed variables exceed 10% imputation**. The most concerning:

| Variable | % imputed | method |
|---|---|---|
| LeftVentricleWallThickness | **37.7%** | most_frequent |
| TissueDopplerSVelocitySeptal | **31.6%** | median |
| AorticValveStructure | **30.1%** | most_frequent |
| sbp | 25.4% | median |
| dbp | 21.2% | median |
| TissueDopplerSVelocityLateral | 20.3% | median |
| BMI | 19.2% | median |
| TissueDopplerEERatioSeptal/Lateral | 18.9% / 18.9% | median |
| ECHO_SPAP | 18.4% | most_frequent |
| TissueDopplerEVelositySeptal/Lateral | 17.7% / 17.7% | median |
| EstimatedSysPAPressure | 16.7% | median |

**Of these 19 high-imputation variables, 11 are echo variables** — exactly the variables most relevant to clinical phenotyping.

---

## Why median imputation at >15% is a real problem for clustering

**The mechanism:**
1. Median imputation places all imputed patients at the **same exact value** (the population median)
2. After z-scoring, that value becomes 0
3. In a clustering algorithm, 100+ patients now have **identical values** on multiple variables
4. Distance metrics treat all imputed patients as **artificially identical** to each other on those variables
5. Clusters get pulled toward the median, hiding genuine variation

**The result:**
- Distorted distance computation
- Reduced cluster separation
- Potentially spurious "central cluster" of patients with imputed values
- Biased toward modal types

**Most_frequent imputation for categoricals has the same issue** — 243 patients all assigned "Mildly increased" wall thickness creates a fake-uniform group.

---

## Committee Deliberation

### EPI (Epidemiologist)
> "Selection bias risk: patients with missing echo Doppler may differ systematically from patients with complete echo. Median imputation hides this by making them look 'average.' We don't know whether they're truly average — they might be sicker patients whose exam was abbreviated. Imputation by reasonable values changes the cohort interpretation."

### STAT (Statistician)
> "Multiple imputation (MI) would be the right answer for inference. For clustering, MI is harder because we'd get k different cluster assignments. The right move depends on what we're claiming. If we're saying 'these phenotypes describe the cohort,' high imputation rates make that claim shaky.
>
> Two acceptable paths:
> 1. **Drop high-imputation variables** — sacrifice information, gain validity
> 2. **Restrict to complete-case** — sacrifice sample size, gain validity
> Either is defensible. The current matrix (full set + median imputation) is harder to defend."

### NEPH (Nephrologist)
> "From the dialysis perspective: Tissue Doppler Doppler measurements are technically demanding. Patients with poor echo windows (often the sickest) get incomplete exams. So missingness is **clinically informative**, not random. Imputing it away erases real signal about who got a complete workup vs. who didn't."

### CARD (Cardiologist)
> "Wall thickness, Doppler velocities, E/e' ratio, SPAP — these are exactly the variables that define HFpEF vs HFrEF subtypes. If we want phenotypes, we want these variables. But if 30% of patients have wall thickness imputed to 'Mildly increased' (the mode), we'll create a fake 'mildly increased wall' cluster that's actually missing-data artifact.
>
> My preference: keep variables with <15% missingness as primary clustering features. Use higher-missing variables only as **descriptive characterization** of clusters, not as cluster inputs."

### PM (Project Manager)
> "Three options on the table. Cost/timeline:
> 1. Reuse current matrix as-is — 0 cost, but the lead investigator already said no.
> 2. Build new matrix with stricter imputation rules — 1-2 hours.
> 3. Use only complete-case on a smaller variable set — 30 min.
> Don't reinvent the dataset. Reuse cleaning logic, change imputation rules and variable inclusion."

### SKEP (Skeptic)
> "Even if we do this right, sample size is small (n=645). Phenotyping with 10+ algorithms × multiple K values × bootstrap stability tests will eat power fast. We should commit upfront to either:
> - A single algorithm pipeline pre-specified (gold standard)
> - Or honest descriptive phenotyping with explicit caveats
>
> Avoid building 30 solutions and then 'discovering' which is best. That's exactly what we're trying to fix."

---

## Decisions to make in DEC-PHENO-004

The committee identifies **three decisions** to lock at this stage:

### Decision A — Which dataset to use as the source

- **A1.** Reuse `Clustering_Matrix` as-is
- **A2.** Rebuild from `base_analysis_dataset` sheet with new preprocessing rules
- **A3.** Use a curated subset of `Clustering_Matrix` (drop high-imputation columns)

### Decision B — Imputation strategy for clustering

- **B1.** Median/most-frequent (current approach)
- **B2.** Drop variables with >15% missingness
- **B3.** Drop variables with >10% missingness (more conservative)
- **B4.** Use kNN imputation (preserves correlations better than median)
- **B5.** Complete-case only (drop patients with any missingness)

### Decision C — Variable selection scope

- **C1.** All 89 features in current matrix
- **C2.** Reduced set (e.g., one variable per construct, drop redundancy)
- **C3.** Pre-defined clinical-physiological set from literature

These decisions are interdependent. The committee will deliberate them together in **DEC-PHENO-004** and **DEC-PHENO-005**.

---

## Stage 1 Output Files

This audit doc itself.

No data files generated yet — that happens in Stage 3 after preprocessing decisions are locked.
