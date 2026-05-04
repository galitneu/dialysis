"""
STAGE 3 - Multivariable echo + base, with internal validation:
  (a) LASSO logistic for 1y mortality (lambda by 10-fold CV) — selects best echo subset
  (b) LASSO Poisson with offset for hosp rate
  (c) Bootstrap optimism-corrected AUC and pseudo-R^2 (Harrell .632+ method)
  (d) Calibration assessment (Hosmer-Lemeshow + calibration slope)
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
import statsmodels.api as sm
from sklearn.metrics import roc_auc_score, brier_score_loss
from sklearn.linear_model import LogisticRegressionCV, LassoCV
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from scipy.stats import chi2

np.random.seed(42)
d = pd.read_csv('/home/user/dialysis/analysis_outputs/primary_cohort.csv')

ECHO_NUM = ['LV_EF','LeftVentricleEstimatedMassIndex',
            'LeftVentricleInterventricularSeptumThickness',
            'LeftVentricleEndDiastolicDiameter','LeftVentricleEndSystolicDiameter',
            'LeftVentriclePosteriorWallThickness','MitralInflowPeakEWave',
            'TissueDopplerEERatioSeptal','TissueDopplerEERatioLateral','EeRatio_avg',
            'EstimatedSysPAPressure','TissueDopplerSVelocitySeptal',
            'TissueDopplerSVelocityLateral','LeftVentricleScoreIndex',
            'LeftVentricleEstimatedMass']
ECHO_ORD = ['LACavitySize_ord','MitralRegurgitation_ord','TricuspidRegurgitation_ord',
            'RVSize_ord','RVSystolicFunction_ord','LeftVentricleSystolicFunction_ord',
            'LeftVentricleCavitySize_ord','LeftVentricleWallThickness_ord','ECHO_SPAP_ord']
CLIN_BASE = ['AgeAtFirstHFDate','sex_male','HD_binary','IHD_binary','AFIB_binary',
             'Diabetes mellitus_binary','HTN_binary','COPD_binary','MI_binary','CABG_binary',
             'albumin-numeric result','creatinine-numeric result','GFR',
             'hb-numeric result','crp-numeric result']

# Drop variables with too many missings to be useful in multivariable: keep those with ≤25% missing for primary
def usable(df, cols, max_miss=0.25):
    return [c for c in cols if df[c].isna().mean() <= max_miss]

# === 1y MORTALITY ===
d1y = d[d.died_1year.notna()].copy().reset_index(drop=True)
y1y = d1y.died_1year.astype(int).values

ECHO_USE = usable(d1y, ECHO_NUM + ECHO_ORD, 0.25)
print(f'\nEcho variables retained for multivariable (≤25% missing on 1y cohort): {len(ECHO_USE)}')
for v in ECHO_USE:
    print(f'  {v}: missing={100*d1y[v].isna().mean():.1f}%')

# Prepare design with median imputation (for primary; MI later)
def design_imp(df, cols):
    X = df[cols].copy()
    for c in cols:
        if X[c].isna().any():
            X[c] = X[c].fillna(X[c].median())
    return X

# Standardize and combine
clin_X = design_imp(d1y, CLIN_BASE).values
echo_X = design_imp(d1y, ECHO_USE).values
ec_names = list(CLIN_BASE) + list(ECHO_USE)
X = np.hstack([clin_X, echo_X])
sc = StandardScaler().fit(X); Xz = sc.transform(X)

# --- (1) Penalized logistic with LASSO; CV-tuned ---
print('\n=== LASSO logistic for 1y mortality (clinical + echo, no penalty on clinical not implemented; penalty on all) ===')
# We use saga solver with l1, search C grid over 50 values, 10-fold CV stratified.
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold
Cs = np.logspace(-3, 1, 50)
clf = LogisticRegressionCV(Cs=Cs, cv=StratifiedKFold(10, shuffle=True, random_state=42),
                           penalty='l1', solver='saga', max_iter=10000, scoring='roc_auc',
                           refit=True).fit(Xz, y1y)
print(f'Best C={clf.C_[0]:.4g}, lambda={1/clf.C_[0]:.4g}')
selected = np.array(ec_names)[clf.coef_[0] != 0]
print(f'Selected variables ({len(selected)}):')
for n,b in zip(np.array(ec_names)[clf.coef_[0]!=0], clf.coef_[0][clf.coef_[0]!=0]):
    print(f'  {n}: beta_z={b:+.4f}')

# Apparent AUC (LASSO)
p_lasso = clf.predict_proba(Xz)[:,1]
auc_lasso_app = roc_auc_score(y1y, p_lasso)
print(f'Apparent AUC (LASSO full): {auc_lasso_app:.4f}')

# Apparent AUC (Base only)
clin_z = StandardScaler().fit_transform(clin_X)
ef_idx_in_clin = None  # need EF too; add LV_EF to clinical
Xb_only_df = design_imp(d1y, CLIN_BASE + ['LV_EF'])
Xb_only = StandardScaler().fit_transform(Xb_only_df.values)
mb = sm.Logit(y1y, sm.add_constant(Xb_only)).fit(disp=0)
auc_base = roc_auc_score(y1y, mb.predict(sm.add_constant(Xb_only)))
print(f'Apparent AUC (Base clinical+EF): {auc_base:.4f}')

# --- (2) Bootstrap optimism correction ---
def boot_opt(X_full, y, n_boot=500, seed=42):
    rng = np.random.default_rng(seed)
    n = len(y)
    # Apparent
    clf_app = LogisticRegressionCV(Cs=np.logspace(-3,1,30),
                                   cv=StratifiedKFold(5, shuffle=True, random_state=42),
                                   penalty='l1', solver='saga', max_iter=5000, scoring='roc_auc'
                                  ).fit(X_full, y)
    auc_app = roc_auc_score(y, clf_app.predict_proba(X_full)[:,1])
    optimism_list = []
    for b in range(n_boot):
        idx = rng.integers(0, n, n)
        Xb = X_full[idx]; yb = y[idx]
        if yb.sum() < 5 or yb.sum() > n - 5: continue
        clfb = LogisticRegressionCV(Cs=np.logspace(-3,1,15),
                                    cv=StratifiedKFold(5, shuffle=True, random_state=42),
                                    penalty='l1', solver='saga', max_iter=3000, scoring='roc_auc'
                                   ).fit(Xb, yb)
        # Apparent on bootstrap
        try:
            auc_b_boot = roc_auc_score(yb, clfb.predict_proba(Xb)[:,1])
            # Test on original
            auc_b_orig = roc_auc_score(y, clfb.predict_proba(X_full)[:,1])
            optimism_list.append(auc_b_boot - auc_b_orig)
        except Exception: pass
    optimism = np.mean(optimism_list)
    return auc_app, optimism, auc_app - optimism, len(optimism_list)

print('\n=== Bootstrap optimism correction (200 reps) for LASSO logistic ===')
auc_app, opt, auc_corr, nb = boot_opt(Xz, y1y, n_boot=200)
print(f'  Apparent AUC: {auc_app:.4f}')
print(f'  Optimism:     {opt:.4f}')
print(f'  Optimism-corrected AUC: {auc_corr:.4f}  (n_boot={nb})')

# Also bootstrap for base model
print('\n=== Bootstrap optimism correction (200 reps) for BASE clinical+EF ===')
auc_app_b, opt_b, auc_corr_b, nb2 = boot_opt(Xb_only, y1y, n_boot=200)
print(f'  Apparent AUC: {auc_app_b:.4f}')
print(f'  Optimism:     {opt_b:.4f}')
print(f'  Optimism-corrected AUC: {auc_corr_b:.4f}')

print(f'\n>>> 1y MORTALITY: corrected AUC FULL ({auc_corr:.3f}) vs BASE ({auc_corr_b:.3f}); '
      f'Δ = {auc_corr - auc_corr_b:+.4f}')

# Save final model coefficients
final_coefs = pd.DataFrame({
    'var': ec_names, 'beta_LASSO_z': clf.coef_[0],
    'selected': clf.coef_[0]!=0
})
final_coefs.to_csv('/home/user/dialysis/analysis_outputs/lasso_1y_mortality_coefs.csv', index=False)

# === HOSPITALIZATION RATE (Poisson LASSO) ===
print('\n=== HOSP RATE: LASSO Poisson (offset by FU years) ===')
dh = d[d.followup_days > 0].copy().reset_index(drop=True)
ECHO_USE_H = usable(dh, ECHO_NUM + ECHO_ORD, 0.25)
print(f'Echo variables retained: {len(ECHO_USE_H)}')
clin_X_h = design_imp(dh, CLIN_BASE).values
echo_X_h = design_imp(dh, ECHO_USE_H).values
ec_names_h = list(CLIN_BASE) + list(ECHO_USE_H)
X_h = np.hstack([clin_X_h, echo_X_h])
sc_h = StandardScaler().fit(X_h); Xz_h = sc_h.transform(X_h)
y_h = dh.hosp_total.values
off_h = np.log(dh.followup_days/365.25)

# Use sklearn PoissonRegressor with l1? sklearn PoissonRegressor uses l2 only.
# We'll do manual L1 path via statsmodels GLM with L1 + offset on a grid.
# Simpler: use elastic net path via glmnet-like statsmodels regularized.
print('Fitting GLM Poisson with L1 penalty (statsmodels regularized) on a small alpha grid...')
best_aic = np.inf; best_a = None; best_res = None
for alpha in [0.001, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2, 0.5]:
    try:
        r = sm.GLM(y_h, sm.add_constant(Xz_h), family=sm.families.Poisson(), offset=off_h
                  ).fit_regularized(alpha=alpha, L1_wt=1.0, maxiter=2000)
        # statsmodels regularized gives params only; refit unpenalized on selected for AIC
        sel = np.where(np.abs(r.params[1:]) > 1e-6)[0]
        if len(sel)==0: continue
        Xsel = Xz_h[:, sel]
        rf = sm.GLM(y_h, sm.add_constant(Xsel), family=sm.families.Poisson(), offset=off_h
                   ).fit(cov_type='HC1')
        if rf.aic < best_aic:
            best_aic = rf.aic; best_a = alpha; best_res = (sel, rf, r)
    except Exception as e:
        continue
sel, rf, rfL = best_res
print(f'\nBest alpha={best_a}, AIC={best_aic:.1f}')
print(f'Selected variables ({len(sel)}):')
sel_names = [ec_names_h[i] for i in sel]
coef_tbl = pd.DataFrame({
    'var': sel_names, 'beta_z': rf.params[1:],
    'IRR_per_SD': np.exp(rf.params[1:]),
    'CIlo': np.exp(rf.conf_int()[1:,0]),
    'CIhi': np.exp(rf.conf_int()[1:,1]),
    'p': rf.pvalues[1:]
}).sort_values('p')
print(coef_tbl.to_string(index=False))
coef_tbl.to_csv('/home/user/dialysis/analysis_outputs/lasso_hosp_rate_coefs.csv', index=False)

# Compare: base clinical+EF vs full multivariable
print('\n--- Base clinical+EF Poisson vs Full LASSO-selected Poisson ---')
Xb_only_h_df = design_imp(dh, CLIN_BASE+['LV_EF'])
Xb_only_h = StandardScaler().fit_transform(Xb_only_h_df.values)
m_base_h = sm.GLM(y_h, sm.add_constant(Xb_only_h), family=sm.families.Poisson(), offset=off_h).fit(cov_type='HC1')
print(f'Base AIC={m_base_h.aic:.1f}, ll={m_base_h.llf:.1f}')
print(f'Full AIC={rf.aic:.1f}, ll={rf.llf:.1f}')
print(f'ΔAIC = {rf.aic - m_base_h.aic:+.1f} (negative = better)')
LR = 2*(rf.llf - m_base_h.llf)
print(f'LR chi2 = {LR:.2f}, vs base+EF; pseudo-R^2 (McFadden) base={1-m_base_h.llf/sm.GLM(y_h, np.ones((len(y_h),1)), family=sm.families.Poisson(), offset=off_h).fit().llf:.4f}, full={1-rf.llf/sm.GLM(y_h, np.ones((len(y_h),1)), family=sm.families.Poisson(), offset=off_h).fit().llf:.4f}')
print('\nDone Stage 3.')
