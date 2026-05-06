# Stage 4 — Algorithm Protocol (LOCKED before execution)

**Date:** 2026-05-06
**Goal:** Pre-specify the clustering algorithm, K range, selection criteria, and stability tests **before** seeing any clustering output.

⚠️ **This document is locked.** Any change after Stage 5 runs requires a new DEC entry that explicitly supersedes the lock.

---

## Algorithms to run

Three algorithms run on identical preprocessed input:

| Algorithm | Why included | Distance/assumption |
|---|---|---|
| **K-means** | Standard, fast, geometric centroids | Euclidean, spherical clusters |
| **Ward (hierarchical)** | Provides dendrogram, robust to noise | Euclidean, minimum variance |
| **Gaussian Mixture Model (GMM)** | Allows soft cluster membership, probabilistic | Mahalanobis-like, elliptical clusters |

K-means + Ward + GMM is the standard "consensus triad" in clinical phenotyping (Shah et al. 2015, Cohen et al. 2020).

---

## K range to test

**K = 2, 3, 4, 5, 6**

Lower bound 2 because anything <2 isn't clustering. Upper bound 6 because:
- n=602
- Rule 4 (charter): minimum cluster n=30 for inference
- 602/6 ≈ 100 — uneven splits could push some clusters under 30
- More than 6 clusters in n=602 is rarely interpretable

---

## Selection criteria for K (PRE-SPECIFIED — applied BEFORE looking at outcome separation)

**Primary criterion — Multi-criterion ranking:**

For each K, compute:
1. **Silhouette score** — internal cluster cohesion vs separation (higher = better)
2. **Calinski-Harabasz index** — between-cluster vs within-cluster variance (higher = better)
3. **Davies-Bouldin index** — average similarity between clusters (lower = better)
4. **Bootstrap stability** — fraction of patients consistently grouped together across 100 bootstrap resamples (higher = better)

K that performs best across ≥3 of 4 criteria within each algorithm is preferred.

**Tiebreaker:** Prefer **lower K** when criteria are within 5%. Parsimony.

**Hard floor:** Any K with a cluster smaller than 30 patients is disqualified.

---

## Cross-algorithm consensus (Rule 3 of charter)

After selecting K within each algorithm, evaluate cross-algorithm agreement using **Adjusted Rand Index (ARI)**:

| ARI | Interpretation |
|---|---|
| ≥0.7 | Strong consensus — phenotypes are robust |
| 0.5-0.7 | Moderate consensus — phenotypes likely real but algorithm-dependent |
| <0.5 | Weak consensus — phenotypes are unstable, **report as exploratory only** |

If two of three algorithms reach ARI ≥0.5 with the third, we have a viable phenotype solution. If ARI <0.5 across the board — **honest negative result reported per Rule 6**.

---

## Stability test (bootstrap)

For the chosen (algorithm, K):
1. Draw 100 bootstrap samples (n=602 with replacement) from the preprocessed matrix
2. Re-fit clustering on each
3. For each pair of original patients, compute fraction of bootstraps where they end in the same cluster
4. **Stability score:** average within-cluster co-assignment frequency
5. Cluster considered stable if mean stability ≥ 0.7

Unstable clusters are flagged. If >1 cluster is unstable, the entire solution is downgraded to "exploratory."

---

## Sensitivity analyses

After primary clustering is locked:

1. **Extended variable set** (24 vars from Stage 2 sensitivity set) — does adding 6 more variables change cluster assignments? Compute ARI between core and extended.
2. **Without kNN-imputed variables** — does dropping the 6 imputed variables change cluster assignments? (Tests robustness to imputation.)
3. **Comparison to prior clustering** — concordance with `cluster_assignments_all_solutions.csv` per DEC-PHENO-002 sanity check.

---

## What constitutes "success" — PRE-SPECIFIED

The phenotyping is considered **methodologically valid** if:
- ✅ At least one K has ARI ≥ 0.5 across ≥2 algorithms
- ✅ All clusters in the chosen solution have n ≥ 30
- ✅ Bootstrap stability ≥ 0.7 for all clusters
- ✅ Each cluster has a clinically describable profile (CARD/NEPH judgment)

The phenotyping is considered **methodologically failed** (and reported as such) if:
- ❌ ARI < 0.5 across all pairs
- ❌ Multiple clusters with n < 30
- ❌ Bootstrap stability < 0.5
- ❌ No clinically coherent description possible

A failed result is still reported — as a negative finding. This is per Rule 6 (honest reporting).

---

## What this protocol does NOT do

- Does not link clusters to outcomes (deferred to Stage 7)
- Does not rerun if results are "underwhelming"
- Does not select K based on which value gives "best" outcome separation

---

## Output files (Stage 5)

The clustering script will produce:

| File | Content |
|---|---|
| `stage5_cluster_assignments_all_solutions.csv` | One row per patient × algorithm × K |
| `stage5_cluster_quality_metrics.csv` | Silhouette, CH, DB, stability for each (algo, K) |
| `stage5_cross_algorithm_ARI.csv` | ARI between every algorithm pair, per K |
| `stage5_chosen_solution.csv` | Patient → final phenotype assignment for the chosen (algo, K) |
| `stage5_chosen_solution_metadata.json` | Which algorithm and K was chosen, why |
