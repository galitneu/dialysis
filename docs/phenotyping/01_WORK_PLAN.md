# Phenotyping Project — Work Plan

**Goal:** Identify clinically meaningful phenotypes among heart failure patients initiating dialysis, on properly cleaned data, using pre-specified methodology.

**Working principle:** Build forward, not backward. Don't reuse the prior clustering (acknowledged by lead investigator as built on insufficiently cleaned data). Treat that work as **direction-setting only**.

---

## Stage Overview

| Stage | Goal | Outputs | Committee role |
|---|---|---|---|
| **1. Data audit** | Identify and verify the cleaned dataset to use | `stage1_data_audit.md`, `stage1_audit.csv` | EPI, STAT, PM |
| **2. Variable selection** | Decide which variables enter clustering | `stage2_variable_selection.md`, `stage2_variables.csv` | NEPH, CARD, EPI |
| **3. Preprocessing** | Lock imputation, scaling, encoding | `stage3_preprocessing.md`, `stage3_preprocessed_X.csv` | STAT, SKEP |
| **4. Algorithm protocol** | Pre-specify algorithms, K range, selection criteria | `stage4_algorithm_protocol.md` | STAT, SKEP |
| **5. Clustering execution** | Run clustering as locked in stage 4 | `stage5_clustering_results.csv`, `stage5_clustering_diagnostics.md` | STAT |
| **6. Validation** | Stability tests + clinical face validity | `stage6_validation.md`, `stage6_stability.csv` | STAT, CARD, NEPH, SKEP |
| **7. Outcome linkage** | Descriptive outcome differences (no inference yet) | `stage7_outcomes.md`, `stage7_outcome_tables.csv` | EPI, STAT, SKEP |
| **8. Final report** | Synthesize for clinical audience | `stage8_final_report.md` | All |

---

## Hard Rules (Locked Now)

These are non-negotiable principles, set before any analysis:

### Rule 1 — Pre-specification
Stage 4 (algorithm protocol) is locked **before** Stage 5 runs. No looking at clustering results before locking algorithm/K choice.

### Rule 2 — No outcome use in clustering
Outcomes (mortality, hospitalization) are **never** inputs to clustering. Linking outcomes happens only in Stage 7, descriptively.

### Rule 3 — Stability over fit
A phenotype that disagrees across algorithms is suspect, regardless of within-algorithm fit metrics. We require **multi-algorithm consensus** before claiming a phenotype.

### Rule 4 — Minimum cluster size
Any phenotype with n<30 is **descriptive only** and cannot be used for outcome inference (insufficient power).

### Rule 5 — Decision logging
Every stage produces a `DEC-PHENO-XXX` entry in `02_DECISION_LOG.md`. No silent decisions.

### Rule 6 — Honest reporting
If clustering doesn't yield interpretable phenotypes — that is the result. We do not force-fit a "story."

---

## Estimated Effort

| Stage | Approx time | Compute |
|---|---|---|
| 1 | 30 min | trivial |
| 2 | 30 min | none |
| 3 | 30 min | trivial |
| 4 | 30 min | none |
| 5 | 1 hour | moderate |
| 6 | 1 hour | moderate |
| 7 | 30 min | trivial |
| 8 | 30 min | none |
| **Total** | **~5 hours** | |

This is a focused project, not a full second study. If validation fails — we stop honestly.

---

## Success Criteria

The project is **successful** if:
- Phenotypes identified are **stable across ≥2 algorithms** (Rule 3)
- Each phenotype has a **clinically describable profile** (CARD/NEPH approval)
- Phenotypes show **face-valid outcome separation** in Stage 7

The project is also **successful** (different way) if:
- We honestly conclude that phenotypes cannot be reliably identified in this dataset
- We document why (sample size, heterogeneity, etc.)
- This becomes a methodological note, not a phenotype paper

The project **fails** if:
- We compromise pre-specification to chase a story
- We ignore validation failures
- We over-interpret unstable phenotypes
