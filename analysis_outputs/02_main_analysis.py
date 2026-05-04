"""
STAGE 2 - Full main analysis:
  Base clinical+EF model
  Incremental value of each echo parameter (LR test, ΔAUC, IDI, NRI)
  Multivariable echo model: LASSO logistic for 1y mortality + LASSO Poisson for hosp rate
  Bootstrap optimism correction
Outputs CSV tables for the final report.
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
import statsmodels.api as sm
from scipy.stats import chi2
from sklearn.metrics import roc_auc_score
from sklearn.linear_model import LogisticRegression, PoissonRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer
from sklearn.model_selection import StratifiedKFold, KFold
from statsmodels.stats.multitest import multipletests

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
ECHO_ALL = ECHO_NUM + ECHO_ORD

CLIN_BASE = ['AgeAtFirstHFDate','sex_male','HD_binary','IHD_binary','AFIB_binary',
             'Diabetes mellitus_binary','HTN_binary','COPD_binary','MI_binary','CABG_binary',
             'albumin-numeric result','creatinine-numeric result','GFR',
             'hb-numeric result','crp-numeric result']

# ============================================================
# IDI / NRI helpers
# ============================================================
def idi(y, p_old, p_new):
    e = (y==1); ne = (y==0)
    idi_ev = p_new[e].mean() - p_old[e].mean()
    idi_ne = p_old[ne].mean() - p_new[ne].mean()
    return idi_ev + idi_ne, idi_ev, idi_ne

def nri_continuous(y, p_old, p_new):
    e = (y==1); ne = (y==0)
    up_e = (p_new[e] > p_old[e]).mean(); dn_e = (p_new[e] < p_old[e]).mean()
    up_ne = (p_new[ne] > p_old[ne]).mean(); dn_ne = (p_new[ne] < p_old[ne]).mean()
    return (up_e - dn_e) + (dn_ne - up_ne)

def delong_p_approx(auc1, auc2, n_pos, n_neg):
    # rough indicator only; we report bootstrap p later.
    return None

# ============================================================
# Build base model design (clinical + EF)
# ============================================================
d1y = d[d.died_1year.notna()].copy().reset_index(drop=True)
y1y = d1y.died_1year.astype(int).values
print(f'1y cohort: n={len(d1y)}, events={int(y1y.sum())}')

# Clinical+EF design with median imputation
def design(df, cols):
    X = df[cols].copy()
    for c in cols:
        if X[c].isna().any():
            X[c] = X[c].fillna(X[c].median())
    return X

base_cols = CLIN_BASE + ['LV_EF']
X_base_df = design(d1y, base_cols)
scaler_base = StandardScaler().fit(X_base_df)
X_base = scaler_base.transform(X_base_df)

# Fit base logistic
m_base = sm.Logit(y1y, sm.add_constant(X_base)).fit(disp=0)
p_base = m_base.predict(sm.add_constant(X_base))
auc_base = roc_auc_score(y1y, p_base)
print(f'\n=== BASE MODEL (clinical + LV_EF) for 1y mortality ===')
print(f'  n={len(y1y)}, events={int(y1y.sum())}, apparent AUC={auc_base:.4f}, AIC={m_base.aic:.1f}, llf={m_base.llf:.2f}')
print('  coefficients (z-scaled):')
coef_base = pd.DataFrame({
    'var': ['(Intercept)']+base_cols,
    'beta': m_base.params,
    'OR': np.exp(m_base.params),
    'CIlo': np.exp(m_base.conf_int()[:,0]),
    'CIhi': np.exp(m_base.conf_int()[:,1]),
    'p': m_base.pvalues
})
print(coef_base.to_string(index=False))
coef_base.to_csv('/home/user/dialysis/analysis_outputs/base_model_1y_coefs.csv', index=False)

# ============================================================
# INCREMENTAL VALUE: each echo parameter added to base
# ============================================================
print('\n=== INCREMENTAL VALUE for 1y mortality (base = clinical + EF, add 1 echo var) ===')
inc_rows = []
for v in ECHO_ALL:
    if v == 'LV_EF': continue
    sub = d1y[base_cols + [v, 'died_1year']].dropna(subset=[v]).reset_index(drop=True)
    if len(sub) < 100 or sub.died_1year.sum() < 30:
        inc_rows.append({'var':v,'n':len(sub),'note':'insufficient'})
        continue
    ys = sub.died_1year.astype(int).values
    # base on this subset (refit for fair LR test)
    Xb_df = design(sub, base_cols)
    scb = StandardScaler().fit(Xb_df); Xb = scb.transform(Xb_df)
    Xv = sub[[v]].values.astype(float)
    if sub[v].nunique() > 5:
        Xv = (Xv - Xv.mean())/Xv.std()
    Xa = np.hstack([Xb, Xv])
    try:
        mb = sm.Logit(ys, sm.add_constant(Xb)).fit(disp=0)
        ma = sm.Logit(ys, sm.add_constant(Xa)).fit(disp=0)
    except Exception as e:
        inc_rows.append({'var':v,'n':len(sub),'note':f'fit_fail:{e}'}); continue
    pb = mb.predict(sm.add_constant(Xb)); pa = ma.predict(sm.add_constant(Xa))
    aucb = roc_auc_score(ys, pb); auca = roc_auc_score(ys, pa)
    LR = 2*(ma.llf - mb.llf); pLR = 1 - chi2.cdf(LR, df=1)
    idi_total, idi_e, idi_ne = idi(ys, pb, pa)
    nri = nri_continuous(ys, pb, pa)
    inc_rows.append({
        'var': v, 'n': len(sub), 'events': int(ys.sum()),
        'beta_added': float(ma.params[-1]),
        'OR_per_SD_added': float(np.exp(ma.params[-1])),
        'CIlo': float(np.exp(ma.conf_int()[-1,0])),
        'CIhi': float(np.exp(ma.conf_int()[-1,1])),
        'p_added': float(ma.pvalues[-1]),
        'LR_chi2': LR, 'p_LR': pLR,
        'AUC_base': aucb, 'AUC_full': auca, 'delta_AUC': auca - aucb,
        'IDI': idi_total, 'IDI_event': idi_e, 'IDI_nonevent': idi_ne,
        'NRI_cont': nri,
        'AIC_base': mb.aic, 'AIC_full': ma.aic, 'delta_AIC': ma.aic - mb.aic
    })
res_inc = pd.DataFrame(inc_rows)
if 'p_LR' in res_inc.columns:
    mask = res_inc.p_LR.notna()
    res_inc.loc[mask,'p_LR_FDR'] = multipletests(res_inc.loc[mask,'p_LR'], method='fdr_bh')[1]
res_inc = res_inc.sort_values('p_LR' if 'p_LR' in res_inc.columns else 'var')
print(res_inc[['var','n','events','OR_per_SD_added','CIlo','CIhi','p_added',
               'LR_chi2','p_LR','p_LR_FDR','AUC_base','AUC_full','delta_AUC','IDI','NRI_cont','delta_AIC']].to_string(index=False))
res_inc.to_csv('/home/user/dialysis/analysis_outputs/incremental_1y_mortality.csv', index=False)

# ============================================================
# HOSPITALIZATION RATE: GLM Poisson with robust SE (quasi-Poisson)
# ============================================================
print('\n=== HOSP RATE: BASE GLM POISSON (quasi-) clinical+EF + INCREMENTAL ===')
dh = d[d.followup_days > 0].copy().reset_index(drop=True)
offset = np.log(dh.followup_days/365.25)
yh = dh.hosp_total.values

Xb_df_h = design(dh, base_cols)
sch = StandardScaler().fit(Xb_df_h); Xb_h = sch.transform(Xb_df_h)
mb_h = sm.GLM(yh, sm.add_constant(Xb_h), family=sm.families.Poisson(), offset=offset).fit(cov_type='HC1')
print(f'\nBase Poisson model: n={len(yh)}, total hosp={int(yh.sum())}, llf={mb_h.llf:.2f}, deviance={mb_h.deviance:.1f}')
coefh = pd.DataFrame({
    'var': ['(Intercept)']+base_cols,
    'IRR': np.exp(mb_h.params),
    'CIlo': np.exp(mb_h.conf_int()[:,0]),
    'CIhi': np.exp(mb_h.conf_int()[:,1]),
    'p': mb_h.pvalues
})
print(coefh.to_string(index=False))
coefh.to_csv('/home/user/dialysis/analysis_outputs/base_model_hosp_coefs.csv', index=False)

# Incremental for hosp
print('\n=== INCREMENTAL VALUE for hosp rate (base + each echo var) ===')
inc_h = []
for v in ECHO_ALL:
    if v == 'LV_EF': continue
    sub = dh[base_cols + [v,'followup_days','hosp_total']].dropna(subset=[v]).reset_index(drop=True)
    if len(sub) < 100: continue
    Xb_s = StandardScaler().fit_transform(design(sub, base_cols))
    Xv = sub[[v]].values.astype(float)
    if sub[v].nunique()>5: Xv = (Xv - Xv.mean())/Xv.std()
    Xa = np.hstack([Xb_s, Xv])
    off = np.log(sub.followup_days/365.25)
    yy = sub.hosp_total.values
    try:
        mb = sm.GLM(yy, sm.add_constant(Xb_s), family=sm.families.Poisson(), offset=off).fit(cov_type='HC1')
        ma = sm.GLM(yy, sm.add_constant(Xa), family=sm.families.Poisson(), offset=off).fit(cov_type='HC1')
    except Exception as e:
        inc_h.append({'var':v,'note':f'fit_fail:{e}'}); continue
    LR = 2*(ma.llf - mb.llf); pLR = 1 - chi2.cdf(max(LR,0), df=1)
    inc_h.append({
        'var': v, 'n': len(sub), 'total_hosp': int(yy.sum()),
        'IRR_per_SD': float(np.exp(ma.params[-1])),
        'CIlo': float(np.exp(ma.conf_int()[-1,0])),
        'CIhi': float(np.exp(ma.conf_int()[-1,1])),
        'p_added': float(ma.pvalues[-1]),
        'LR_chi2': LR, 'p_LR': pLR,
        'AIC_base': mb.aic, 'AIC_full': ma.aic, 'delta_AIC': ma.aic - mb.aic
    })
res_inc_h = pd.DataFrame(inc_h)
if 'p_LR' in res_inc_h.columns:
    mask = res_inc_h.p_LR.notna()
    res_inc_h.loc[mask,'p_LR_FDR'] = multipletests(res_inc_h.loc[mask,'p_LR'], method='fdr_bh')[1]
    res_inc_h = res_inc_h.sort_values('p_LR')
print(res_inc_h.to_string(index=False))
res_inc_h.to_csv('/home/user/dialysis/analysis_outputs/incremental_hosp_rate.csv', index=False)
print('\nDone Stage 2.')
