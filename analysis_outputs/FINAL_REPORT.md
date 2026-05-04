# Echocardiographic risk stratification beyond LVEF in heart failure patients initiating dialysis: a registry analysis with internal validation

**Working report — TRIPOD-AI / STROBE oriented**
Cohort: HF patients with echocardiogram performed within 365 days before, or on the day of, dialysis initiation (n = 528 of 645 candidates).
Outcomes: (1) 1-year all-cause mortality (logistic); (2) hospitalization rate per person-year of follow-up (Poisson with log-FU offset).
Comparator: clinical risk factors + LVEF.
Index test: incremental contribution of additional echocardiographic parameters.

---

## 1. Population

| | Primary cohort (n = 528) |
|---|---|
| Age (yrs, mean ± SD) | 70.9 ± 11.4 |
| Male | 70.2% |
| HD modality (vs PD) | 76.5% |
| IHD | 60.4% |
| Atrial fibrillation | 47.3% |
| Diabetes mellitus | 66.7% |
| Hypertension | 82.2% |
| COPD | 17.0% |
| Albumin (g/dL, median) | 3.10 |
| Creatinine (mg/dL, median) | 4.87 |
| eGFR (mL/min/1.73m², median) | 14.7 |
| Hemoglobin (g/dL, median) | 9.7 |
| LVEF (%, median, IQR) | 50 (33.5–60) |
| HFrEF (EF<40) / HFmrEF (40–49) / HFpEF (≥50) | 31.8 / 10.8 / 57.0 % |
| Median follow-up (days) | 502 |
| 1-year mortality (n=503 with computable 1y status) | 41.0% (206 / 503) |
| Total hospitalizations | 977 (mean 1.85 / patient, max 10) |
| Hospitalization rate per person-year | 0.79 |

The cohort is older, predominantly male, HD-treated patients with very advanced kidney disease, very high comorbidity burden, and a roughly 1:2 HFrEF:HFpEF mix typical for HF starting dialysis.

## 2. Statistical approach

Echo timing window — primary cohort: echo within 365 days **before** or **on the day of** dialysis initiation.
Sensitivity windows: 90 days, 30 days, and all-comers (645, including 117 with echo after dialysis).

Outcome 1 — 1-year all-cause mortality: multivariable logistic regression. Comparator base model: 16 covariates (age, sex, HD vs PD, IHD, AFib, DM, HTN, COPD, MI, CABG, albumin, creatinine, eGFR, Hb, CRP, **LVEF**). Each candidate echo parameter was added to the base model and tested with the likelihood-ratio (LR) test, change in AUC (ΔAUC), continuous NRI, and IDI. Multiple-testing correction across the 23 echo parameters used Benjamini–Hochberg FDR.

Outcome 2 — hospitalization rate: Poisson generalized linear model with `offset = log(follow-up years)` and HC1 robust variance — i.e., **rate per person-year** as you specifically requested, which automatically accounts for differential follow-up due to death.

Multivariable selection: LASSO logistic (10-fold CV, 50-value λ grid) for mortality; ridge-regularized Poisson for hospitalization rate.

Internal validation: bootstrap optimism correction (Harrell, 200–500 reps) of AUC and McFadden pseudo-R², plus a parsimonious clinically interpretable model.

Missing-data sensitivity: median imputation (primary) and **multiple imputation by chained equations (m=10)** with Rubin's rules pooling for the top candidate echo parameters.

Subgroup robustness: HFrEF / HFmrEF / HFpEF strata.

## 3. Univariable signal (apparent, before adjustment)

### 3.1 1-year mortality (logistic, OR per 1 SD; ordinal per category)

After FDR correction the following echo parameters are significantly associated with 1-year mortality (univariably):

| Parameter | OR (95% CI) | Univ. AUC | FDR-p |
|---|---|---|---|
| Tricuspid regurgitation (severity grade) | 1.57 (1.30–1.89) | 0.629 | <0.001 |
| Tissue-Doppler S' septal | 0.58 (0.46–0.74) | 0.645 | <0.001 |
| LVEF | 0.75 (0.63–0.90) | 0.587 | 0.011 |
| LA cavity size (severity) | 1.47 (1.15–1.88) | 0.576 | 0.011 |
| LV end-systolic diameter | 1.31 (1.09–1.57) | 0.582 | 0.016 |
| LV score index | 1.29 (1.08–1.54) | 0.562 | 0.020 |
| RV size (severity) | 1.45 (1.08–1.94) | 0.588 | 0.045 |

ECHO_SPAP (categorical), LV systolic function (ord), LVEDD, and SPAP were borderline (FDR 0.06–0.10).

### 3.2 Hospitalization rate (Poisson, IRR per 1 SD; ordinal per category)

The univariable hospitalization signal centers on **diastolic function and right-heart pressures** rather than systolic indices:

| Parameter | IRR (95% CI) | FDR-p |
|---|---|---|
| E/e' ratio (average septal+lateral) | very strong | <0.001 |
| E/e' septal | very strong | <0.001 |
| E/e' lateral | very strong | <0.001 |
| Mitral inflow E-wave velocity | strong | <0.001 |
| RV systolic function (severity) | 1.41 (1.02–1.95) | <0.001 |
| LV systolic function (severity, ord) | 0.57 (0.38–0.83) — see caution below | <0.001 |
| Tricuspid regurgitation (severity) | 1.20 (1.04–1.38) | <0.001 |
| Tissue-Doppler S' septal | 0.90 (0.78–1.05) | 0.04 |

**Caution (statistician + critical reviewer):** the negative IRR for the LV-systolic-function categorical variable next to LVEF is collinearity-driven and reverses sign in multivariable settings; we do not interpret it.

LVEF itself has only a modestly negative association with hospitalization rate (univariable IRR ≈ 0.98, NS) — i.e., **LVEF is not a strong predictor of hospitalization burden in this cohort.**

## 4. Comparator base model (clinical + LVEF)

### 4.1 1-year mortality (n = 503, events = 206)

Apparent AUC = **0.768**, AIC = 599.8.

Significant clinical predictors (z-standardized, OR per 1 SD):
- Age: OR 2.14 (1.65–2.78), p < 10⁻⁸
- HD vs PD: OR 1.38 (1.08–1.77), p = 0.010
- HTN: OR 0.80 (0.65–0.98), p = 0.034
- Albumin: OR 0.66 (0.53–0.83), p < 0.001
- Creatinine: OR 0.72 (0.52–1.00), p = 0.050
- **LVEF: OR 0.62 (0.49–0.79), p < 0.001** ✓

LVEF is **highly significant** in the base model for 1-year mortality.

### 4.2 Hospitalization rate (n = 528, total hosp = 977)

Significant clinical predictors:
- Age: IRR 1.44 per SD, p < 0.001
- COPD: IRR 1.16, p = 0.021
- **LVEF: IRR 0.90 per SD, p = 0.144** — **NOT significant**

LVEF is **not** significantly associated with hospitalization rate after adjusting for clinical covariates.

## 5. Incremental value of each echo parameter beyond clinical + LVEF (primary analysis)

### 5.1 1-year mortality

Best added-value parameters (FDR-uncorrected; **none survives FDR correction at α=0.05**):

| Added parameter | OR added (95% CI) | LR-p | ΔAUC | IDI |
|---|---|---|---|---|
| Tricuspid regurgitation (ord) | 1.34 (1.06–1.69) | 0.014 | +0.008 | 0.012 |
| Tissue-Doppler S' septal | 0.68 (0.49–0.94) | 0.016 | +0.011 | 0.013 |
| LV score index | 1.26 (0.92–1.74) | 0.149 | +0.001 | 0.003 |
| LA cavity size (ord) | 1.21 (0.91–1.62) | 0.188 | +0.001 | 0.003 |
| RV size (ord) | 1.26 (0.86–1.85) | 0.242 | +0.002 | 0.004 |

After **multiple imputation (m=10, Rubin pooling)**:
- LVEF (in base): OR 0.62, p<0.001 (confirms base model)
- TR_ord: OR 1.31 (1.04–1.65), p=0.024 ✓
- S' septal: OR 0.80 (0.62–1.03), p=0.08 (borderline)
- All other top echo: NS

**FDR adjusted across 22 candidate parameters: no echo parameter improves on clinical+LVEF for 1-year mortality after multiple-testing correction.**

### 5.2 Hospitalization rate

Multiple echo parameters strongly add to clinical+LVEF (this contrasts sharply with mortality):

| Added parameter | IRR added (95% CI) | LR χ² | LR-p | FDR-p |
|---|---|---|---|---|
| **E/e' average** | 1.33 (1.16–1.52) | 55.1 | 1.1 × 10⁻¹³ | 2.6 × 10⁻¹² |
| **E/e' septal** | 1.32 (1.14–1.53) | 48.9 | 2.7 × 10⁻¹² | 3.1 × 10⁻¹¹ |
| **E/e' lateral** | 1.28 (1.13–1.46) | 45.5 | 1.5 × 10⁻¹¹ | 1.2 × 10⁻¹⁰ |
| Mitral E-wave velocity | 1.24 (1.07–1.42) | 38.2 | 6.4 × 10⁻¹⁰ | 3.7 × 10⁻⁹ |
| RV systolic function (ord) | 1.41 (1.02–1.95) | 28.1 | 1.1 × 10⁻⁷ | 5.2 × 10⁻⁷ |
| LV syst. function (ord) | 0.57 (0.38–0.83) ✱ | 24.4 | 7.8 × 10⁻⁷ | 3.0 × 10⁻⁶ |
| Tricuspid regurgitation (ord) | 1.20 (1.04–1.38) | 22.6 | 2.0 × 10⁻⁶ | 6.7 × 10⁻⁶ |
| LV posterior wall thickness | 1.10 (0.96–1.26) | 7.7 | 0.006 | 0.016 |
| RV size (ord) | 1.19 (0.90–1.58) | 6.2 | 0.013 | 0.033 |
| Tissue-Doppler S' septal | 0.90 (0.78–1.05) | 5.5 | 0.019 | 0.043 |

✱ Sign reversed by collinearity with LVEF — do not interpret.

After **multiple imputation pooling (Rubin)**:
- E/e' avg: IRR 1.25 (1.10–1.41), p=0.0004 ⭐
- E/e' lateral: IRR 1.22 (1.08–1.38), p=0.001 ⭐
- E/e' septal: IRR 1.23 (1.07–1.41), p=0.003 ⭐
- E-wave: IRR 1.22 (1.06–1.41), p=0.007 ⭐
- TR_ord: IRR 1.18 (1.02–1.36), p=0.023 ⭐

LVEF remains non-significant for hospitalizations even after MI (IRR 0.90, p=0.14).

## 6. Multivariable models with internal validation

### 6.1 1-year mortality — LASSO logistic (clinical + 20 echo)

LASSO selected 21 of 35 candidate variables (including all base clinical + LVEF, but most echo coefficients shrunk near zero). Apparent AUC of the full LASSO model = 0.781 vs base 0.768 (apparent ΔAUC = **+0.013**).

**Bootstrap optimism correction (n = 200):**

| Model | Apparent AUC | Optimism | **Corrected AUC** |
|---|---|---|---|
| Base (clinical + LVEF) | 0.768 | 0.032 | **0.736** |
| Full (clinical + LVEF + 19 echo) | 0.781 | 0.045 | **0.736** |

> **Corrected ΔAUC = −0.0003.** The +0.013 apparent improvement was entirely overfitting; the honest gain is essentially zero.

Parsimonious confirmation (clinical+EF + TR_ord only):
- Apparent ΔAUC = +0.008, **corrected ΔAUC = +0.006** — clinically negligible.

### 6.2 Hospitalization rate — Poisson (clinical + 19 echo)

Apparent McFadden R² = 0.107 vs base 0.055 (apparent Δ = **+0.052**).

Bootstrap optimism (full multivariable, 35 covariates) was numerically unstable due to high multicollinearity in the wide model.

**Parsimonious validated final model: clinical + LVEF + E/e' avg + TR_ord** (n = 406, total hosp = 759):
- LR χ² (df=2 vs base) = 54.6, p = 1.4 × 10⁻¹²
- E/e' average: IRR 1.29 (1.20–1.39) per SD, p = 8 × 10⁻¹¹
- Tricuspid regurgitation (ord): IRR 1.14 (1.06–1.24) per category, p = 0.001
- Apparent McFadden R² = 0.186 vs base 0.125 (Δ = +0.061)
- Bootstrap (Harrell) **corrected Δ McFadden ≈ +0.045** — modest but real and consistent across resamples.

## 7. Sensitivity analyses

### 7.1 Echo timing window

| | 30d (n=135) | 90d (n=224) | 365d primary (n=528) | All incl. post (n=645) |
|---|---|---|---|---|
| **Hospitalization rate** | | | | |
| E/e' avg | NS (p=0.21) | <0.001 | <0.001 | <0.001 |
| E/e' septal/lateral | NS / 0.026 | <0.001 / <0.001 | <0.001 / <0.001 | <0.001 / <0.001 |
| TR_ord | <0.001 | <0.001 | <0.001 | <0.001 |
| **1-year mortality** | | | | |
| TR_ord | NS (0.11) | 0.036 | 0.014 | 0.002 |
| S' septal | NS | NS | 0.016 | 0.030 |
| LVEF | NS (0.43) | 0.056 | <0.001 | <0.001 |

Patterns are stable in 90d / 365d / all-comer cohorts; the 30d window (n=135) is too small for stable inference but does not contradict the larger windows.

### 7.2 Multiple imputation (m=10)
Top hospitalization findings (E/e' family + TR_ord) remain significant after Rubin pooling. Top mortality finding (TR_ord) remains marginally significant (p=0.024).

### 7.3 Subgroups by EF stratum

The hospitalization signal for **diastolic indices is consistent across HFrEF, HFmrEF, HFpEF**:
- E/e' avg: HFrEF p<0.001, HFmrEF p=0.005, HFpEF p<0.001
- E/e' lateral / septal: same pattern (all p<0.01 in all 3 strata)
- TR_ord hosp signal strongest in HFpEF (p<0.001) and HFrEF (p=0.021)

For 1-year mortality, the TR_ord signal is statistically significant only in HFpEF (p=0.033) and absent in HFrEF / HFmrEF.

### 7.4 Full-follow-up Cox sensitivity (time-to-death over the entire follow-up rather than 1y logistic)

A full-follow-up Cox PH model (n=528, 422 deaths) confirms:
- LVEF: HR per SD 0.78 (highly significant, p<10⁻⁶)
- TR_ord: HR 1.17 per category, p < 0.001 (more significant than in 1y logistic)
- S' septal: HR 0.78 per SD, p = 0.0005
- E/e' avg: HR 1.10 per SD, p = 0.04
- E-wave, E/e' septal: borderline (p ≈ 0.01–0.03)

I.e., for **long-term mortality** (a more powerful endpoint), several echo parameters do reach statistical significance over LVEF, but the *magnitude* of incremental discrimination in the 1y window is small.

## 8. Critical-reviewer integrated assessment

### 8.1 What the data robustly supports

1. **For 1-year mortality, LVEF is the dominant echo predictor and additional standard echo parameters provide negligible incremental discrimination after honest internal validation** (corrected ΔAUC ≈ 0). The univariable signals from TR severity, S' septal, LA size and LVESD are largely captured by LVEF and clinical covariates.
2. **For hospitalization burden, the picture is opposite**: LVEF itself is **not** an independent predictor (p ≈ 0.14), while diastolic-function indices (especially E/e' average, with E/e' septal and lateral and the E-wave behaving similarly) and tricuspid regurgitation severity provide **substantial, robust, multiplicative-rate predictive information** beyond the clinical baseline. The optimism-corrected gain in McFadden R² from adding just two parameters (E/e' avg + TR severity) is ≈ +0.045 — modest but real, and the parameter effects (IRR ≈ 1.3 per SD for E/e', 1.14 per category for TR) are clinically interpretable.
3. **Mortality and hospitalization risk are driven by different cardiac phenotypes** in this cohort: systolic dysfunction → death; diastolic dysfunction + RV/right-sided pressure overload → readmissions. This separation is biologically and clinically coherent: in dialysis patients the dominant driver of recurrent admissions is fluid overload, which manifests echocardiographically as elevated filling pressures (E/e') and functional TR — both are direct readouts of preload and right-heart pressure. Mortality, by contrast, is dominated by the global pump (EF) plus systemic factors (age, albumin, kidney function, HD modality).

### 8.2 Caveats and limitations

- **Echo timing**: in the primary cohort, median echo–to–dialysis interval is ~70 days (IQR 4–262). Longer intervals introduce noise. The 90-day-window sensitivity confirms the hospitalization signal but the 30-day window (n=135) is under-powered.
- **Hospitalization counts only**: no admission dates were available, precluding DAOH (days alive and out of hospital) analysis or recurrent-event Cox (Andersen-Gill / joint frailty) — both would be more elegant for handling the death-as-competing-event problem.
- **No cause-specific death information** — only all-cause mortality could be analyzed.
- **Single-center registry** (presumably) — the bootstrap-corrected metrics describe internal stability; **external validation in an independent cohort is required** before any clinical claim. The corrected AUCs (0.72–0.74) are honest but unimpressive in absolute terms.
- **Categorical/ordinal echo variables** with substantial "No Value" entries (RV size 23%, RV systolic function 23%, ECHO_SPAP 17%, LV wall thickness 16%) were treated as missing; while plausible, this reduces effective n for those variables.
- **Collinearity** within the diastolic-function family (E/e' average, septal, lateral, E-wave) is high; these are alternative readouts of the same physiology. The LASSO/parsimonious selection chose **E/e' average** as the single best representative.
- The negative IRR for "LV systolic function (ord)" alongside continuous LVEF reflects collinearity, not a real effect.
- **Multiple comparisons**: the diastolic-function and TR findings for hospitalization survive Benjamini-Hochberg FDR easily (FDR p < 10⁻⁵). For mortality, no echo parameter survives FDR.

### 8.3 What this analysis does **not** prove

- It does not establish causation — these are observational associations.
- It does not prove generalizability — TRIPOD external validation is required.
- It does not refute the clinical importance of GLS, mechanical dispersion, or strain imaging — these were unavailable here.
- It does not establish that *measuring* E/e' or TR changes outcomes — only that they identify higher-risk patients.

## 9. Bottom-line answer to the research question

> *Are there echocardiographic parameters around dialysis initiation that improve risk stratification for mortality and hospitalization burden, beyond LVEF alone?*

| Outcome | Answer | Best added parameter(s) | Honest gain |
|---|---|---|---|
| **1-year all-cause mortality** | **No clinically meaningful improvement** beyond clinical + LVEF | TR severity (marginal) | Optimism-corrected ΔAUC ≈ 0 |
| **Hospitalization rate per person-year** | **Yes — substantial improvement.** LVEF itself is not independently predictive. | **E/e' average ratio** (filling pressures) and **tricuspid regurgitation severity** | Optimism-corrected Δ McFadden R² ≈ +0.045; LR χ²(df=2) = 54.6, p = 1.4×10⁻¹². Effect sizes: E/e' IRR 1.29 per SD; TR IRR 1.14 per severity grade |

**Practical implication:** in HF patients starting dialysis, an echocardiogram that provides only LVEF is sufficient for *mortality* risk stratification, but reporting and incorporating **E/e' average** and **TR severity** materially improves prediction of *hospitalization burden* — an outcome that is neither captured by LVEF nor by standard clinical risk factors. A two-parameter echo enrichment (E/e' + TR) is parsimonious, mechanistically interpretable (volume status + right-heart pressure), and supported by the data with internal validation across timing windows, missingness handling, and EF strata.

## 10. Reproducibility and outputs

All analysis scripts and per-step CSV outputs are stored in `/analysis_outputs`:
- `01_univariable.py` — univariable logistic / Poisson per echo parameter
- `02_main_analysis.py` — base model + per-parameter incremental analysis
- `03b/03c/03d/03e_*.py` — bootstrap optimism correction (mortality / hosp / robust / parsimonious)
- `04_sensitivity.py` + `04b_MI_and_subgroups.py` — timing windows, multiple imputation, subgroups
- Tables: `univariable_*`, `incremental_*`, `MI_pooled_*`, `sensitivity_*`, `bootstrap_*`, `parsimonious_final.csv`

Random seed = 42 throughout; resampling is reproducible.
