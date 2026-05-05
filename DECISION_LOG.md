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

## DEC-018 | 2026-05-05 | Stage -1 → Stage 0 | Galit
**DECISION**: In LV Systolic Function, merge `Preserved` (and whitespace variants) into `Normal`.
**RATIONALE**: "Preserved systolic function" and "normal systolic function" describe the same clinical state; the duplication reflects reporting-style variation, not a distinct phenotype. Harmonization, not classification.
**SOURCE**: Galit, OPEN-001 resolution
**OUTCOME_INFORMED**: N

## DEC-019 | 2026-05-05 | Stage -1 → Stage 0 | Galit
**DECISION**: For MitralRegurgitation, harmonize plain-English entries to the Roman-numeral grading scale:
- `Trace` → `Trivial`
- `Mild` → `Mild (I)`
- `Moderate` → `Moderate (II)`
- `Severe` → `Severe (IV)`
**RATIONALE**: Same grading semantics, different reporter conventions. Mapping is conservative (plain `Moderate` → `Moderate (II)` rather than the higher `Moderately-severe (III)`). Pre-outcome decision based on grading-scale equivalence.
**SOURCE**: Galit, OPEN-002 resolution
**OUTCOME_INFORMED**: N

## DEC-020 | 2026-05-05 | Stage -1 → Stage 0 | Galit
**DECISION**: Use `2025-08-16` as the **working** administrative censor date, derived from the dataset maximum. This is **not** confirmed as the official data cutoff. All time-to-event computations and any survival language in the report must label it as a working / candidate cutoff pending source confirmation.
**RATIONALE**: Allows the analysis pipeline to proceed without blocking on an external confirmation, while preserving transparency that the value is provisional.
**SOURCE**: Galit, OPEN-003 resolution
**OUTCOME_INFORMED**: N
**FOLLOW-UP REQUIRED**: confirm with data source whether 2025-08-16 is the true administrative cutoff before report finalization.

---

## DEC-021 | 2026-05-05 | Stage 0 commencing | Claude
**DECISION**: Stage 0 begins. Tasks: apply data-cleaning decisions DEC-011 through DEC-020 to the raw file `echo_project_update.xlsx`; produce a cleaned flat file (one row per patient); produce variable inventory with clinical axis and proposed status. **No outcome modeling, no clinical category merging** (clinical merging belongs to Stage 1).
**RATIONALE**: Per locked SAP and Galit instruction "ולהמשיך ל־Stage 0 בלבד".
**SOURCE**: Locked SAP + Galit go-ahead
**OUTCOME_INFORMED**: N

---

## STOP-2 corrections (DEC-022 .. DEC-029) — Galit review

## DEC-022 | 2026-05-05 | Stage 0 (correction) | Galit
**DECISION**: Convert each comorbidity column to a binary indicator using `df[col].notna()`. The binary equals 1 if the source value is non-null (a date or a label like "Oncological diagnosis") and 0 otherwise. The original date column is preserved (parsed where parseable) for reference but excluded from primary modeling.
**RATIONALE**: Explicit DEC for the binarization step (previously only implied by DEC-013). Required so the provenance file can reference a specific decision ID rather than an inferred one. Also addresses the OncologicalDiagnosis case where the source column stores text rather than dates.
**SOURCE**: Galit STOP-2 correction, item 4
**OUTCOME_INFORMED**: N

## DEC-023 | 2026-05-05 | Stage 0 (correction) | Galit
**DECISION**: Reclassify the following from `Candidate` to `Sensitivity / exploratory only`:
- `RVSize` (53.5% effective missing)
- `RVSystolicFunction` (52.9% effective missing)
- `AorticValveRegurgitation` (53.2% effective missing)
**RATIONALE**: Per DEC-015, variables above 50% effective missing should not enter the primary multivariable model as standard candidates. They may still be analyzed descriptively or as sensitivity.
**SOURCE**: Galit STOP-2 correction, item 1
**OUTCOME_INFORMED**: N

## DEC-024 | 2026-05-05 | Stage 0 (correction) | Galit
**DECISION**: Whitespace stripping must not be applied to columns whose effective dtype is `datetime`. The Stage 0 script will detect comorbidity date columns and skip them in the whitespace-strip step. Provenance entries that previously logged "whitespace_strip" on date columns will be removed; if any actual transformation occurred, it is purely cosmetic round-trip (string → datetime → string) and not a value change.
**RATIONALE**: Galit STOP-2 correction, item 5. Avoid misleading provenance entries.
**SOURCE**: Galit STOP-2 correction, item 5
**OUTCOME_INFORMED**: N

## DEC-025 | 2026-05-05 | Stage 0 (correction) | Galit
**DECISION**: Add a Stage 0 QA outliers report flagging biologically implausible values for these variables, without auto-correction:
- `BMI`: flag values < 12 or > 70
- `Weight`: flag values < 30 kg or > 200 kg
- `LeftVentricleInterventricularSeptumThickness` (cm): flag values > 2.5
- `LeftVentriclePosteriorWallThickness` (cm): flag values > 2.0
- `LeftVentricleEstimatedMass` (g): flag values > 600
- `LeftVentricleEstimatedMassIndex` (g/m²): flag values > 300
Produces `04_qa_outliers.csv` with patient ID, variable, value, threshold, side. Decisions about correction or exclusion of specific outliers are deferred to Stage 1 / clinician review.
**RATIONALE**: Galit STOP-2 correction, item 2. Establishes a record of suspect values before any modeling.
**SOURCE**: Galit STOP-2 correction, item 2
**OUTCOME_INFORMED**: N

## DEC-026 | 2026-05-05 | Stage 0 (correction) | Galit
**DECISION**: Lock the explicit definition of `died_1year` and embed it in code + provenance:
- `1` if `death_event==1` AND `time_to_event_days ≤ 365`
- `0` if `death_event==0` AND `followup_days ≥ 365` (sufficient follow-up, alive at 1 year)
- `0` if `death_event==1` AND `time_to_event_days > 365` (died, but after the 1-year window)
- `NaN` if `death_event==0` AND `followup_days < 365` (insufficient follow-up to determine 1-year status)
Primary 1-year-mortality analysis must restrict to patients with `died_1year ∈ {0, 1}`; the NaN subset is reported as a separate "insufficient follow-up" group.
**RATIONALE**: Galit STOP-2 correction, item 6. Removes any ambiguity in primary outcome construction.
**SOURCE**: Galit STOP-2 correction, item 6
**OUTCOME_INFORMED**: N

## DEC-027 | 2026-05-05 | Stage 0 (correction) | Galit
**DECISION**: Adopt a canonical naming convention for the analytic flat file. The clean flat file produced by Stage 0 will use these names exclusively; downstream stages must use the same names:
- `patient_id` (renamed from `patient number`)
- `gap_echo_to_dial_days` (positive = echo before dialysis)
- `death_event` (binary, full follow-up)
- `time_to_event_days` (days from dialysis to death-or-censor)
- `followup_days` (alias of time_to_event_days for clarity)
- `died_1year` (per DEC-026)
- `hosp_total` (canonical name; raw column `hospitalization-count` mapped to it)
The decision log and provenance will reference these names.
**RATIONALE**: Galit STOP-2 correction, item 7. Prevents downstream breaks.
**SOURCE**: Galit STOP-2 correction, item 7
**OUTCOME_INFORMED**: N

## DEC-028 | 2026-05-05 | Stage 0 (correction) | Galit
**DECISION**: The Stage 0 inventory will be split into four explicit lists, one CSV each:
1. `inventory_main.csv` — variables eligible for the primary multivariable model
2. `inventory_sensitivity.csv` — eligible only for sensitivity analyses
3. `inventory_exploratory.csv` — exploratory only (very high missing or overlap)
4. `inventory_excluded.csv` — excluded / descriptive-only
A variable appears in exactly one list. The combined `02_variable_inventory.csv` remains for full transparency, but the four split files are the operational reference for downstream stages.
**RATIONALE**: Galit STOP-2 correction, item 8.
**SOURCE**: Galit STOP-2 correction, item 8
**OUTCOME_INFORMED**: N

## DEC-029 | 2026-05-05 | Stage 0 (correction) | Galit
**DECISION**: The Stage 0 cleaning provenance file (`03_cleaning_provenance.md`) must reference an explicit DEC-NNN for every action. Any action whose mapping to a DEC-NNN was previously implicit will be re-mapped:
- whitespace_strip → DEC-011
- no_value_to_nan → DEC-012
- see_below_to_nan → DEC-014
- preserved_to_normal → DEC-018
- mr_english_to_roman → DEC-019
- comorb_*_to_binary → **DEC-022** (new explicit)
- working_censor_date → DEC-020
- echo_after_death_flag → DEC-016
- derived_time_vars → DEC-020 + DEC-026
- hosp_rename → DEC-027 (canonical naming)
- patient_id_rename → DEC-027 (canonical naming)
- skip whitespace_strip on date cols → DEC-024
**RATIONALE**: Galit STOP-2 corrections, items 3, 4, 5.
**SOURCE**: Galit STOP-2 correction, items 3, 4, 5
**OUTCOME_INFORMED**: N

---

*Stage 0 to be re-run with these corrections before STOP-2 closure.*
