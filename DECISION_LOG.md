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

## DEC-011 | 2026-05-05 | Stage -1 (audit cleaning) | Galit
**DECISION**: Strip whitespace and merge categories that differ only by trailing/leading spaces (e.g., `Thickened` ↔ `Thickened `, `Normal` ↔ `Normal `, `Prosthetic` ↔ `Prosthetic `, `Preserved` ↔ `Preserved `).
**RATIONALE**: Trivial data-entry artifact; collapsing is unambiguous.
**SOURCE**: Galit STOP-1 approval, item 1
**OUTCOME_INFORMED**: N

## DEC-012 | 2026-05-05 | Stage -1 | Galit
**DECISION**: Treat the explicit string `"No Value"` as missing (NaN) for all echo variables.
**RATIONALE**: It is a sentinel produced by the echo reporting system to denote "could not be measured / not assessed", semantically equivalent to NaN.
**SOURCE**: Galit STOP-1 approval, item 2
**OUTCOME_INFORMED**: N

## DEC-013 | 2026-05-05 | Stage -1 | Galit
**DECISION**: For comorbidity columns stored as date types, treat NaN/blank as "no condition". Create a binary variable `<comorb>_binary = comorbidity_date.notna()`.
**RATIONALE**: The semantic of NULL in these columns is "no diagnosis date recorded → condition absent". Confirmed by the original data dictionary and by inspection in the Stage -1 audit.
**SOURCE**: Galit STOP-1 approval, item 3
**OUTCOME_INFORMED**: N

## DEC-014 | 2026-05-05 | Stage -1 | Galit
**DECISION**: Treat the string `"See below"` (and analogous referrals) as missing, **unless and until** an explicit text-extraction step is approved.
**RATIONALE**: Without parsing the free-text Hebrew summaries we cannot recover the underlying value reliably; default to NaN for safety. Marked as a possible Stage 6 sensitivity.
**SOURCE**: Galit STOP-1 approval, item 4
**OUTCOME_INFORMED**: N

## DEC-015 | 2026-05-05 | Stage -1 | Galit
**DECISION**: Document effective missingness (NaN ∪ "No Value" ∪ "See below") for every variable. **Variables with > 60% effective missing will not enter the primary multivariable model.** They may still be reported descriptively or used as sensitivity.
**RATIONALE**: Avoid models built on heavily imputed/sparse data; preserve interpretability and stability.
**SOURCE**: Galit STOP-1 approval, item 5
**OUTCOME_INFORMED**: N

## DEC-016 | 2026-05-05 | Stage -1 | Galit
**DECISION**: Flag the single patient with `Echo_Date > DeathDate` for review and exclusion. Document the exclusion in this log; do not silently drop.
**RATIONALE**: Logical impossibility = data error; explicit accounting required.
**SOURCE**: Galit STOP-1 approval, item 6
**OUTCOME_INFORMED**: N

## DEC-017 | 2026-05-05 | Stage -1 | Galit
**DECISION**: Newly accessible variables (BMI, Weight, DYSLIPIDEMIA / DYSLIPIDEMIA_binary, OncologicalDiagnosis, additional labs Na/K/Ca/P/Urea/Ua/hba1c, AorticValveStructure, AorticValveRegurgitation, MitralValveStructure, TricuspidValveStructure) are **not** automatically added to the clinical base. They are inventoried and held for explicit Stage 4 decision.
**RATIONALE**: Discipline; prevents drift of the base model based on what was found in raw.
**SOURCE**: Galit STOP-1 approval, item 7
**OUTCOME_INFORMED**: N

---

## Open items pending Galit's clinical/data confirmation (no execution until resolved)

### OPEN-001 | LV Systolic Function: how to map "Preserved" (n=58)
- **Option A**: merge with `Normal` (clinical equivalence in modern HF nomenclature: HFpEF = preserved EF)
- **Option B**: keep as a distinct category
- **Recommendation**: A, but Galit to confirm
- **Owner**: Clinician

### OPEN-002 | MitralRegurgitation: harmonization of mixed encodings
The raw MR column contains both Roman-numeral grades (`Trivial`, `Mild (I)`, `Mild-to-moderate (I-II)`, `Moderate (II)`, `Moderately-severe (III)`, `Severe (IV)`) and plain-English grades (`Mild`, `Trace`, `Moderate`, `Severe`).
- **Proposed mapping**: `Trace`→`Trivial`; `Mild`→`Mild (I)`; `Moderate`→`Moderate (II)`; `Severe`→`Severe (IV)`
- Ambiguity: plain `Moderate` may correspond to either `Moderate (II)` *or* `Moderately-severe (III)`; safest to map to `Moderate (II)`.
- **Owner**: Clinician

### OPEN-003 | Censor date 2025-08-16
The original notebook used the dataset-max date (2025-08-16) as a proxy administrative censor date. This is a strong assumption.
- Until Galit confirms 2025-08-16 is the **true** administrative data-cutoff date, it is labeled `candidate censor date` and not treated as fact.
- If true: use as is.
- If untrue: need a different censor reference, which would change all time-to-event calculations.
- **Owner**: Galit (data-source confirmation)

---

*Awaiting OPEN-001, OPEN-002, OPEN-003 before Stage 0 commences.*
