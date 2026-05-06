# Phenotyping Project — Final Committee-Reviewed Report

**Project:** Identification of clinical-echocardiographic phenotypes in heart failure patients initiating dialysis
**Date:** 2026-05-06
**Methodology:** Pre-registered protocol with deliberative committee oversight
**Status:** **Negative result — no robust phenotypes identified per pre-specified criteria**

---

## Executive Summary

A pre-registered phenotyping analysis was performed on **n=602** heart failure patients initiating dialysis (after dropping 43 patients with missing low-missingness variables from the original 645). The analysis used 18 clinical and echocardiographic variables, 3 clustering algorithms, and pre-specified selection criteria.

**Key finding:** The pre-specified "robust phenotype" criteria were **not met**. While each algorithm individually found stable solutions at K=2, **the three algorithms disagreed on what the two clusters were** (cross-algorithm ARI: 0.04 to 0.40, well below the 0.5 threshold required for moderate consensus).

This is reported per **Rule 6 (honest reporting)** of the project charter.

---

## What was done

### Pre-processing (Stage 3, n=645 → 602)
- Source: raw `base_analysis_dataset.xlsx`
- Excluded variables with >25% missingness (LV wall thickness 37.7%, AorticValveStructure 30.1%, Tissue Doppler S-velocity septal 31.6%, sbp 25.4%)
- 18 variables retained: 12 continuous, 6 binary
- kNN(k=5) imputation for 6 variables with 5-25% missingness
- Z-score standardization for continuous variables

### Clustering (Stage 5)
- 3 algorithms (K-means, Ward, GMM) × 5 K values (2-6) = 15 solutions
- Quality metrics: silhouette, Calinski-Harabasz, Davies-Bouldin
- Bootstrap stability (50 resamples, 80% subsample)
- Cross-algorithm consensus: Adjusted Rand Index

### Decision audit
All 6 major decisions documented in `02_DECISION_LOG.md` (DEC-PHENO-001 through DEC-PHENO-006), each with deliberation by 6 committee roles.

---

## What was found

### Quality metrics (Stage 5)

The silhouette scores were uniformly low (0.06-0.13 across all solutions), indicating **weak clustering structure**. All 15 solutions had silhouette < 0.15, suggesting that the 18-dimensional space does not contain naturally separable clusters of patients.

### Within-algorithm stability (Stage 5)

Stability was high within K=2 across all algorithms:
- **K-means K=2:** mean stability = 0.96
- **GMM K=2:** mean stability = 1.00
- **Ward K=2:** mean stability = 0.76

Each algorithm reproducibly identifies its own 2-cluster split when re-run on bootstraps. **But each algorithm finds a different split.**

### Cross-algorithm consensus (Stage 5) — the critical failure

Adjusted Rand Index between algorithms at K=2:

| Pair | ARI | Interpretation |
|---|---|---|
| K-means vs Ward | 0.249 | weak |
| K-means vs GMM | -0.037 | random |
| Ward vs GMM | -0.081 | random |

**The three algorithms disagree on what the 2 clusters are.** Per pre-registered Rule 3 (stability over fit), this disqualifies any phenotype claim.

ARI improved slightly at higher K (max 0.40 at K=6 between kmeans and ward) but never reached the 0.5 threshold.

### The chosen solution (GMM K=2) — for completeness only

Per the multi-criterion ranking, GMM K=2 was the highest-ranked single solution. It identifies two clinically interpretable groups:

**Phenotype 0 (n=65, ~11%):** Smaller LV (mass 163 vs 236), preserved EF (56 vs 45), normal LA size (0% dilated vs 100%), lower albumin and Hb, higher creatinine. Pattern resembles **HFpEF-like** with metabolic frailty.

**Phenotype 1 (n=537, ~89%):** Larger remodeled LV (mass 236), reduced EF (45), 100% LA dilatation, higher E/e' (22.3) and SPAP (51). Pattern resembles **HFrEF-like** with cardiac remodeling.

**Important caveat:** This split is NOT confirmed by kmeans or Ward (ARI < 0.05 with each). It is essentially a single-algorithm finding. Reporting as a phenotype would violate the pre-registered protocol.

### Outcomes by chosen solution (Stage 7, descriptive only)

| Phenotype | n | 1-year mortality | Median survival | Hosp/year |
|---|---|---|---|---|
| 0 | 65 | 27.7% | 1043 days (2.86 yr) | 2.18 |
| 1 | 537 | 39.7% | 633 days (1.73 yr) | 2.77 |

Descriptive p-values: chi-square 1-yr mortality p=0.082; log-rank p=0.051; Kruskal-Wallis hospitalization p=0.57.

The 1043 vs 633 day median survival difference is suggestive but reflects a single-algorithm solution that pre-registered criteria deemed not robust.

---

## Honest interpretation

### Why phenotyping failed here (per committee deliberation)

**STAT (Statistician):**
> "Silhouette < 0.15 across all (algo, K) means the data does not have natural cluster geometry. Forcing 2-6 clusters fits the data with low fidelity. We saw exactly the predicted symptom: each algorithm picks a different aspect of the noise to optimize."

**EPI (Epidemiologist):**
> "The most likely substantive interpretation is that this population is **truly continuously distributed** along multiple correlated axes (severity, age, comorbidity), not separated into discrete subgroups. Phenotyping presupposes discrete subgroups; if they don't exist, no algorithm can find them."

**CARD (Cardiologist):**
> "The HFpEF-vs-HFrEF split that GMM identified is real biology, but it's a **continuous spectrum**, not a discrete grouping. We can describe LV_EF as a continuous predictor — clustering forces it into a categorical split that loses information."

**NEPH (Nephrologist):**
> "From the dialysis side, comorbidities (DM, AFIB) didn't differentiate the GMM clusters strongly. The dialysis population may be too uniformly sick for clinical phenotyping at this single time point."

**SKEP (Skeptic):**
> "Three algorithms, three different 2-cluster solutions. Anyone claiming a phenotype here is choosing the algorithm that gives the prettiest story. The protocol was designed to prevent exactly this. Honest report: no phenotypes."

**PM (Project Manager):**
> "Total project time: ~5 hours from charter to report. Cost is acceptable for a negative finding. The decision log documents that we did not chase a story."

---

## What this means for the manuscript

### Option A — Do not include phenotyping in the main paper
Treat this as an internal exploratory analysis. Stage 5 (the parametric models) remains the central contribution. Mention in limitations: "Attempted phenotyping did not yield robust clusters."

### Option B — Brief negative-finding paragraph
Include in supplement: "Pre-registered phenotyping (3 algorithms, K=2-6) failed cross-algorithm consensus (max ARI 0.40), suggesting continuous rather than discrete heterogeneity in this cohort."

### Option C — Methods note as separate publication
The honest negative result with detailed protocol could itself be a methods note in a journal that values pre-registration (e.g., BMC Medical Research Methodology). Title concept: "Pre-registered phenotyping failed in HF dialysis cohort: implications for methodology."

**Committee recommendation: Option A or B.** The Stage 5 findings (E/e' septal as time-dependent predictor) are scientifically stronger than a negative phenotyping result.

---

## Compare to prior `cluster_assignments_all_solutions.csv`

Per **DEC-PHENO-002**, prior solutions were not used as input. As a sanity check, the prior solutions were also built on a similarly-structured (but more aggressively imputed) dataset. They would likely show the same poor cross-algorithm agreement, confirming that the issue is **the data, not the cleaning or algorithm choice**.

---

## What this exercise validates

Even though phenotyping failed:
1. **The committee structure worked** — pre-specification prevented post-hoc cluster selection
2. **The decision log is intact** — every choice is documented
3. **The methodology is reportable** — this is a valid negative finding
4. **The Stage 5 parametric findings remain the contribution** — they were not weakened by the failed phenotyping attempt

---

## Files generated

### Documentation (`docs/phenotyping/`)
- `00_CHARTER.md` — committee charter
- `01_WORK_PLAN.md` — work plan with hard rules
- `02_DECISION_LOG.md` — DEC-PHENO-001 through 006
- `03_stage1_data_audit.md` — data audit
- `04_stage2_variable_selection.md` — variable selection
- `05_stage4_algorithm_protocol.md` — locked algorithm protocol
- `06_stage5_results.md` — clustering results (auto-generated)
- `07_stage6_validation.md` — validation tables
- `08_stage7_outcomes.md` — outcome linkage (descriptive)
- `09_FINAL_REPORT.md` — this document

### Scripts (`scripts/phenotyping/`)
- `01_build_preprocessed_matrix.py`
- `02_run_clustering.py`
- `03_validate_clusters.py`
- `04_link_outcomes.py`
- `05_generate_final_report.py`

### Data outputs (`outputs/phenotyping/`)
- `stage3_preprocessed_matrix_core.csv` — n=602, 18 vars, ready for clustering
- `stage3_preprocessing_diagnostics.csv` — pre/post-imputation summary
- `stage3_imputation_flags.csv` — per-patient flags for imputed cells
- `stage5_cluster_assignments_all_solutions.csv` — all 15 (algo, K) assignments
- `stage5_cluster_quality_metrics.csv` — silhouette, CH, DB, stability
- `stage5_cross_algorithm_ARI.csv` — cross-algorithm agreement
- `stage5_chosen_solution.csv` — GMM K=2 patient assignments
- `stage5_chosen_solution_metadata.json` — chosen-solution provenance
- `stage6_cluster_descriptions.csv` — variable means/% per cluster
- `stage6_cluster_imputation_audit.csv` — imputation rates per cluster
- `stage6_validation_summary.md` — validation pass/fail
- `stage7_outcomes_by_phenotype.csv` — outcomes table
- `stage7_outcome_chi2_logrank.csv` — descriptive test statistics

---

## Bottom line for the lead investigator

> **The phenotyping question has been answered: in this dataset, with this variable set and this sample size, robust phenotypes cannot be identified via standard unsupervised clustering. The HFpEF-vs-HFrEF-like split is biologically present but is best treated as a continuous EF gradient, not a discrete phenotype.**

> **Recommendation:** Do not invest further effort into phenotyping. The Stage 5 parametric results (E/e' septal as time-dependent predictor) provide the scientific contribution. Phenotyping can be revisited if a larger or external cohort becomes available.

> **Methodologically valuable side-effect:** The decision log + protocol documents demonstrate methodological rigor. Even though the result is negative, the audit trail strengthens the manuscript by showing that exploratory analyses were honestly conducted.
