# Phenotyping Project — Decision Log

**Format:** Each decision is `DEC-PHENO-XXX` with timestamp, issue, options, deliberation, decision, rationale.

---

## DEC-PHENO-001 — Project scope and governance

**Date:** 2026-05-06
**Issue:** How should the phenotyping project be governed?

**Options considered:**
- A) Quick exploratory clustering, no formal governance
- B) Full deliberative committee with multi-role review
- C) Outsource to external collaborators

**Deliberation:**
- **PM:** Option A risks the same problem the prior clustering had — undocumented decisions. Option C delays everything.
- **STAT:** Option B forces pre-specification, which is the core methodological need.
- **SKEP:** Option B also creates an audit trail if this becomes a manuscript.

**Decision:** **Option B** — formal deliberative committee, structured per `00_CHARTER.md`, work plan per `01_WORK_PLAN.md`.

**Rationale:** The prior clustering's main weakness was insufficient cleaning and undocumented decisions. The new project must address both.

---

## DEC-PHENO-002 — Do not reuse prior clustering

**Date:** 2026-05-06
**Issue:** Should the existing `cluster_assignments_all_solutions.csv` (15 solutions: kmeans/ward/gmm × K=2-6) be used as a starting point?

**Options considered:**
- A) Use prior solutions, validate them
- B) Discard entirely, start fresh
- C) Use only as direction-setting for new build

**Deliberation:**
- **Lead investigator:** "Built without good cleaning of the data."
- **STAT:** If preprocessing was wrong, downstream results inherit the error. Validation can't fix bad input.
- **EPI:** Reuse risks confirmation bias toward the known structure.
- **PM:** Option C costs nothing extra and may be useful for sanity checks at the end.

**Decision:** **Option C** — discard prior solutions for inference, but optionally compare at the end as a sanity check.

**Rationale:** Don't anchor to a flawed analysis, but don't waste the prior signal either. Use it only as post-hoc concordance check after locked Stage 5.

---

## DEC-PHENO-003 — Hard rules locked

**Date:** 2026-05-06
**Issue:** What baseline rules govern the project?

**Decision:** Six hard rules locked per `01_WORK_PLAN.md` "Hard Rules" section:
1. Pre-specification (Stage 4 locked before Stage 5)
2. No outcomes in clustering input
3. Stability across algorithms required
4. Minimum cluster n=30 for inference
5. All decisions logged
6. Honest reporting (negative result is acceptable)

**Rationale:** These prevent the most common phenotyping pitfalls: post-hoc cluster selection, outcome leakage, single-algorithm artifacts, over-interpretation of small clusters, p-hacking.

---

## DEC-PHENO-004 — Source dataset and imputation strategy

**Date:** 2026-05-06
**Issue:** Which dataset and imputation approach to use? (See Stage 1 audit for context.)

**Findings driving the decision:**
- 19 of 41 imputed variables exceed 10% imputation
- 11 of these are echo variables (most relevant to phenotyping)
- 4 echo variables exceed 17% imputation; one wall thickness exceeds 37%
- Median/most-frequent imputation collapses imputed patients to identical values, distorting clustering distances

**Options considered:**
- A1. Reuse current `Clustering_Matrix` as-is
- A2. Rebuild from raw with new preprocessing rules
- A3. Use curated subset of current matrix (drop high-imputation columns)

- B1. Keep median/most_frequent imputation
- B2. Drop variables with >15% imputation
- B3. Drop variables with >10% imputation
- B4. kNN imputation (preserves correlation)
- B5. Complete-case only

**Deliberation:**
- **STAT:** B5 (complete-case) preserves validity but reduces n significantly. Need to check what n we'd have left.
- **NEPH:** The echo Doppler variables aren't missing at random — sicker patients often have abbreviated exams. So neither median imputation nor "drop variables with high missingness" is ideal. Both have failure modes.
- **CARD:** From the cardiology literature, phenotyping requires variables like E/e', SPAP, wall thickness. We can't drop them all and still have a meaningful HF phenotyping.
- **EPI:** Compromise: drop variables with >20% imputation (the most distorted), keep moderate-imputation variables (10-20%), but use kNN imputation for them which preserves variable correlations better than median.
- **PM:** This is achievable in 1-2 hours. Acceptable cost.
- **SKEP:** Whatever we choose, we must report imputation rates per cluster in the final results. Phenotypes that rely on heavily-imputed variables get a caveat.

**Decision:** **Hybrid approach: A2 (rebuild) + B2-modified + B4-modified**

Specifically:
1. **Source data:** Rebuild from `base_analysis_dataset` sheet (raw values), not from the existing `Clustering_Matrix`.
2. **Variable inclusion:**
   - **Drop** any variable with >25% original missingness (creates artifact-prone clusters)
   - **Keep** variables with <25% missingness, but only if clinically justified by NEPH/CARD
3. **Imputation:**
   - **kNN imputation (k=5)** for moderate-missingness variables (5-25%)
   - **No imputation needed** for variables <5% missing — drop those few patients (will be handled in Stage 3)
4. **Result reporting:** Imputation rate per variable per cluster reported in Stage 6 validation.

**Rationale:** This balances four concerns: validity (preserves correlation structure via kNN), interpretability (drops the most extreme cases), sample size (avoids complete-case attrition), and methodological transparency (reports what was imputed).

**Threshold of 25%** chosen because:
- LeftVentricleWallThickness (37.7%), TissueDopplerSVelocitySeptal (31.6%), AorticValveStructure (30.1%) — too distorted, drop
- sbp (25.4%) — borderline, lead investigator should choose
- Everything ≤21.2% — kept with kNN imputation

---

## DEC-PHENO-005 — Variable selection for clustering

**Date:** 2026-05-06
**Issue:** Which variables enter the clustering algorithm? (See `04_stage2_variable_selection.md`.)

**Options considered:**
- Maximalist (45+ variables) — high power loss, redundancy
- Core set (15-18 variables) — balanced
- Minimalist (8-10 variables) — risk missing clinical dimensions
- Pre-defined literature set

**Deliberation:**
- **CARD:** Insists on coverage of systolic, diastolic, structural, hemodynamic, rhythm.
- **NEPH:** Insists on dialysis modality, comorbidity (DM), nutrition (albumin), inflammation (CRP), anemia (Hb).
- **STAT:** Maximum 20 variables for stable clustering at n=645.
- **EPI:** Demand pre-registration of selection logic.
- **SKEP:** Document every exclusion explicitly.
- **PM:** Lock and move on.

**Decision:** **Core set of 18 variables** as listed in Stage 2 doc:
- 5 demographic/comorbidity (age, sex, HD/PD, AFIB, DM)
- 8 echo (LV_EF, LV-EDD, LV PWT, LV mass, MitralInflow E, E/e' septal, SPAP, LA dilatation, TR moderate-severe)
- 4 lab (albumin, creatinine, CRP, hemoglobin)

Plus an **extended sensitivity set of 24** for stability comparison.

**Rationale:** 18 variables span all clinically required HF + dialysis dimensions, with redundancy minimized. Sensitivity set tests whether adding 6 more changes results — a way to test robustness without inflating the primary input.

**Categorical handling:** Multi-level echo categoricals (LACavitySize, TR) collapsed to clinically meaningful binaries (Mod/Severe vs Normal/Mild). Avoids one-hot expansion that distorts distance metrics.


---

## DEC-PHENO-006 — Algorithm protocol locked

**Date:** 2026-05-06
**Issue:** Lock all algorithm choices before clustering runs (per Hard Rule 1).

**Decision:** Per `05_stage4_algorithm_protocol.md`:

- **Algorithms:** K-means, Ward (hierarchical), GMM
- **K range:** 2-6
- **Selection criteria (per algorithm):** multi-criterion ranking on silhouette, Calinski-Harabasz, Davies-Bouldin, bootstrap stability; tiebreaker = lower K
- **Hard floor:** any cluster <30 patients disqualifies that K
- **Cross-algorithm consensus:** ARI thresholds (≥0.7 strong, 0.5-0.7 moderate, <0.5 unstable)
- **Stability test:** 100 bootstrap resamples, threshold 0.7
- **Success criteria:** pre-specified in Stage 4 doc
- **Failure criteria:** also pre-specified — failure leads to honest negative report (per Rule 6)

**Rationale:** Pre-specifying every threshold prevents post-hoc K selection and protects against p-hacking through cluster choice.


---

## DEC-PHENO-007 — Phenotyping result accepted as negative; not pursued further

**Date:** 2026-05-06
**Issue:** How to interpret and act on the negative phenotyping result?

**Findings:**
- All algorithms found stable solutions at K=2 within-algorithm
- Cross-algorithm ARI maxed at 0.40 (kmeans vs ward at K=6); at chosen K=2, max ARI=0.249
- Silhouette uniformly <0.15 across all 15 (algo, K) combinations
- GMM K=2 produces an HFpEF-like vs HFrEF-like split with face validity but is not algorithm-replicated

**Options considered:**
- A. Accept the negative result per Rule 6, do not include phenotyping in primary manuscript
- B. Override the locked criteria and report GMM K=2 as a finding anyway
- C. Try alternative variable subsets, hoping for a "luckier" combination
- D. Use a different methodology (e.g., mixture-of-Cox phenotyping)

**Deliberation:**
- **STAT:** B is exactly the post-hoc behavior the protocol forbids. C is a garden-of-forking-paths violation. D is a different study, not this one.
- **CARD:** The HFpEF-HFrEF split is real biology but is captured better by LV_EF as continuous than by clustering.
- **EPI:** A is the methodologically clean choice. The protocol functioned as designed.
- **SKEP:** Without B/C, the manuscript loses no integrity. With B/C, it loses everything.
- **PM:** Time-bounded result. Move on.

**Decision:** **Option A** — accept negative result, do not include phenotypes in primary manuscript.

**Rationale:** The pre-registered protocol functioned correctly. The data does not support discrete phenotypes. Reporting otherwise would violate Rules 3 and 6 of the charter. The Stage 5 parametric findings (E/e' septal time-dependent effect) remain the scientific contribution.

