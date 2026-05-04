# Decision Log
**Echocardiographic risk stratification beyond LVEF in HF patients initiating dialysis**

Format: `ID | DATE | STAGE | DECIDED_BY | DECISION | RATIONALE | SOURCE | OUTCOME_INFORMED`

> `OUTCOME_INFORMED = N` means the decision was made on clinical or data-quality grounds without inspecting any outcome model.
> `OUTCOME_INFORMED = Y` means the decision was made or modified after seeing outcome-related results — must be flagged.

---

## DEC-001 | 2026-05-04 | Stage -1 (Restart) | Galit (clinician) + Claude (analyst)
**DECISION**: Restart the analysis under a locked exploratory framework. Previous work is preserved as historical record but is not the primary analysis.
**RATIONALE**: Discovery that (a) variables (e′ velocities) were omitted from screening; (b) categorical variables were treated as ordinal-linear, hiding non-monotonic patterns; (c) prior plan was iteratively reactive rather than locked.
**SOURCE**: Methodological audit
**OUTCOME_INFORMED**: N (procedural)

## DEC-002 | 2026-05-04 | Stage -1 | Galit
**DECISION**: Frame the study explicitly as exploratory. All p-values are descriptive. No confirmatory claims.
**RATIONALE**: Retrospective single-cohort design; data already inspected; no external validation.
**SOURCE**: Galit's plan, principle 1
**OUTCOME_INFORMED**: N

## DEC-003 | 2026-05-04 | Stage -1 | Galit
**DECISION**: EF is a fixed benchmark in every model, not a variable in the LV-systolic axis to be selected against.
**RATIONALE**: The research question is "what adds beyond EF?" — EF must always be present.
**SOURCE**: Galit, alignment correction 1
**OUTCOME_INFORMED**: N

## DEC-004 | 2026-05-04 | Stage -1 | Galit
**DECISION**: TR is reassigned to the right-heart / congestion axis (with SPAP, RV size, RV systolic function), not the valves axis.
**RATIONALE**: In dialysis HF cohorts, TR primarily reflects right-heart pressure overload and congestion — its clinical meaning is hemodynamic, not valvular pathology.
**SOURCE**: Galit, alignment correction 2
**OUTCOME_INFORMED**: N (clinical reasoning)

## DEC-005 | 2026-05-04 | Stage -1 | Galit
**DECISION**: Stage 3 (univariable screening) is descriptive only. No automatic variable selection by p-value threshold.
**RATIONALE**: p-value alone is insufficient (per Galit's principle 3); selection requires clinical rationale, coverage, signal, non-overlap, stability.
**SOURCE**: Galit, alignment correction 4
**OUTCOME_INFORMED**: N

## DEC-006 | 2026-05-04 | Stage -1 | Galit
**DECISION**: Primary analysis uses complete-case per analysis, with explicit N. Median/mode imputation is NOT primary. MICE is sensitivity only.
**RATIONALE**: Imputation injects model-driven structure into a primary inferential model; we want N-explicit results.
**SOURCE**: Galit, alignment correction 6
**OUTCOME_INFORMED**: N

## DEC-007 | 2026-05-04 | Stage -1 | Galit
**DECISION**: Stage 4 is hard lock-in. Any change after Stage 4 is labeled post-hoc and reported separately.
**RATIONALE**: Prevent HARKing; preserve the integrity of the candidate model.
**SOURCE**: Galit, alignment correction 5
**OUTCOME_INFORMED**: N (procedural)

## DEC-008 | 2026-05-04 | Stage -1 | Galit
**DECISION**: Maximum 3 echo additions per primary multivariable model, beyond the base + EF.
**RATIONALE**: EPV ≥ 10; parsimony; prevent overfitting; one representative per relevant clinical axis.
**SOURCE**: SAP, multivariable rules
**OUTCOME_INFORMED**: N

## DEC-009 | 2026-05-04 | Stage -1 | Galit + Claude
**DECISION**: Two clinical bases will be reported in parallel: parsimonious (age, sex, creatinine, echo-to-dialysis days) and full clinical.
**RATIONALE**: Parsimonious base mirrors the comparator analysis; full base controls for confounding more thoroughly. Both shown for transparency.
**SOURCE**: SAP discussion
**OUTCOME_INFORMED**: N

## DEC-010 | 2026-05-04 | Stage 0 commencing | Claude
**DECISION**: Begin Stage 0 — variable audit only. No models. Stop at STOP-1 for Galit's review of variable inventory and axis classification.
**RATIONALE**: Per locked plan.
**SOURCE**: SAP, Stage sequencing
**OUTCOME_INFORMED**: N

---

*Subsequent entries will be added in chronological order.*
