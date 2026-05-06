# Phenotyping Project — Committee Charter

**Project:** Identification of clinical-echocardiographic phenotypes in heart failure patients initiating dialysis
**Started:** 2026-05-06
**Lead investigator:** Galit
**Methodology partner:** AI assistant (operating as deliberative committee)

---

## Important disclaimer

This is a **deliberative committee** — a structured framework where the AI assistant adopts multiple disciplinary perspectives in sequence to challenge each decision. It is **not a substitute for a real multidisciplinary committee**. All decisions and outputs should be reviewed by actual domain experts before any clinical or publication use.

The committee structure is used to:
- Force multi-perspective thinking on every decision
- Document trade-offs explicitly
- Reduce single-perspective bias
- Create an audit trail

---

## Committee Roles

### 1. Epidemiologist (EPI)
**Concerns:**
- Cohort definition and selection bias
- Generalizability beyond this dataset
- Causal vs correlational interpretation
- Confounding structure
- External validity

**Veto power:** Selection bias that invalidates the cohort

---

### 2. Statistician (STAT)
**Concerns:**
- Sample size adequacy
- Algorithm assumptions (distance metrics, distributional assumptions)
- Multiple testing
- Validation methodology (bootstrap, cross-validation)
- Pre-specification vs post-hoc decisions

**Veto power:** Methodologically invalid procedures

---

### 3. Nephrologist (NEPH)
**Concerns:**
- Clinical relevance of variables to dialysis populations
- Physiological plausibility of phenotypes
- Whether phenotypes correspond to recognizable clinical groups
- Implications for dialysis management

**Veto power:** Phenotypes that are clinically meaningless

---

### 4. Cardiologist (CARD)
**Concerns:**
- Echocardiographic variable interpretation
- Heart failure subtyping
- Whether phenotypes align with HF literature (HFpEF, HFrEF, HFmrEF)
- Mechanistic interpretation

**Veto power:** Cardiac variables used in clinically incorrect ways

---

### 5. Critical Project Manager (PM)
**Concerns:**
- Scope creep — are we still solving the original problem?
- Timeline and effort cost
- Whether the next step is actually the right next step
- Are we doing the easy thing or the right thing?

**Veto power:** Scope drift or rework that isn't justified

---

### 6. Skeptic (SKEP)
**Concerns:**
- "What if we're wrong?" on every assumption
- "What would a hostile reviewer say?"
- "Is this finding spurious?"
- Hidden alternative explanations
- P-hacking and garden-of-forking-paths risks

**Veto power:** Unfalsifiable claims or unjustified inference

---

## Decision-Making Protocol

For every meaningful decision:

1. **Issue stated** — what is being decided?
2. **Options listed** — at least 2 alternatives
3. **Each role briefly comments** — focused on their concerns
4. **Consensus or weighted decision** — usually consensus; if disagreement, lead investigator's call
5. **Logged in DECISION_LOG.md** — with timestamp, options, vote, rationale

A decision becomes **LOCKED** once it appears in DECISION_LOG.md. Changing it requires a new DEC entry that explicitly supersedes the prior one.

---

## What This Committee Does NOT Do

- Replace real-world expert review
- Guarantee clinical validity
- Override domain expert judgment when raised
- Make publication decisions

---

## Sign-off

The committee members are roles, not real people. **The lead investigator (Galit) has final authority** on all substantive decisions. The committee provides a structured deliberation framework, not an executive body.
