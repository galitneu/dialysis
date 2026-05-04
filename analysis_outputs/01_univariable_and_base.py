"""
STAGE A: Univariable echo associations + base clinical+EF model
Heart failure patients starting dialysis: do echo parameters add incremental
value beyond LV_EF for predicting mortality and hospitalization burden?
"""
import warnings
warnings.filterwarnings('ignore')
import numpy as np
import pandas as pd
from statsmodels.duration.hazard_regression import PHReg
from sksurv.metrics import concordance_index_censored
from scipy.stats import chi2
import statsmodels.api as sm

d = pd.read_csv('/home/user/dialysis/analysis_outputs/primary_cohort.csv')

# --- variable lists ---
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
             'Diabetes mellitus_binary','HTN_binary','COPD_binary',
             'albumin-numeric result','GFR','hb-numeric result']

T = d['time_to_event_days'].values
E = d['event'].astype(int).values
y_surv = np.array([(bool(e), t) for e,t in zip(E,T)], dtype=[('event',bool),('t',float)])

# ============================================================
# 1) UNIVARIABLE COX for each echo parameter (continuous → standardized)
# ============================================================
def fit_cox_univ(d, var, T=T, E=E):
    sub = d[[var]].copy()
    sub['T']=T; sub['E']=E
    sub = sub.dropna()
    if len(sub) < 30 or sub.E.sum() < 10: return None
    x = sub[[var]].values.astype(float)
    # standardize for comparability
    x = (x - x.mean())/x.std() if x.std()>0 else x
    try:
        m = PHReg(sub['T'].values, x, status=sub['E'].values).fit()
        hr = float(np.exp(m.params[0])); lo = float(np.exp(m.conf_int()[0,0])); hi = float(np.exp(m.conf_int()[0,1]))
        p = float(m.pvalues[0])
        # C-index
        risk = (x @ m.params).flatten()
        c = concordance_index_censored(sub.E.values.astype(bool), sub.T.values, risk)[0]
        return {'var':var,'n':len(sub),'events':int(sub.E.sum()),
                'HR_per_SD':hr,'CI_lo':lo,'CI_hi':hi,'p':p,'C_index':c}
    except Exception as e:
        return {'var':var,'n':len(sub),'error':str(e)}

print('=== UNIVARIABLE Cox (HR per 1 SD) ===')
rows=[]
for v in ECHO_ALL:
    r = fit_cox_univ(d, v)
    if r is not None: rows.append(r)
res_univ = pd.DataFrame(rows).sort_values('p')
print(res_univ.to_string(index=False))
res_univ.to_csv('/home/user/dialysis/analysis_outputs/univariable_cox.csv', index=False)

# ============================================================
# 2) BASE clinical + EF model (with mean imputation for labs)
# ============================================================
print('\n=== BASE CLINICAL + EF MODEL (Cox) ===')
base = d[CLIN_BASE + ['LV_EF']].copy()
# mean-impute (for now); we'll do MI in sensitivity
for c in base.columns:
    base[c] = base[c].fillna(base[c].median())
# standardize continuous
to_z = ['AgeAtFirstHFDate','albumin-numeric result','GFR','hb-numeric result','LV_EF']
for c in to_z:
    base[c+'_z'] = (base[c]-base[c].mean())/base[c].std()
X_base_cols = [c+'_z' if c in to_z else c for c in CLIN_BASE+['LV_EF']]
X_base = base[X_base_cols].values.astype(float)
m_base = PHReg(T, X_base, status=E).fit()
print(m_base.summary().as_text())
# Risk score
risk_base = (X_base @ m_base.params).flatten()
c_base, _, _, _, _ = concordance_index_censored(E.astype(bool), T, risk_base)
ll_base = m_base.llf
k_base = X_base.shape[1]
print(f'\nBase model: C-index={c_base:.4f}, log-lik={ll_base:.2f}, k={k_base}')

np.save('/home/user/dialysis/analysis_outputs/risk_base.npy', risk_base)
pd.DataFrame({'var':X_base_cols,'beta':m_base.params,
              'HR':np.exp(m_base.params),
              'CIlo':np.exp(m_base.conf_int()[:,0]),
              'CIhi':np.exp(m_base.conf_int()[:,1]),
              'p':m_base.pvalues}).to_csv(
    '/home/user/dialysis/analysis_outputs/base_model_coefs.csv', index=False)

# ============================================================
# 3) INCREMENTAL VALUE: add each echo parameter to base
# ============================================================
print('\n=== INCREMENTAL VALUE OF EACH ECHO PARAMETER (added to base clinical+EF) ===')
inc_rows=[]
for v in ECHO_ALL:
    if v == 'LV_EF': continue
    Xv = d[[v]].copy()
    # standardize
    if Xv[v].nunique()>5:  # continuous
        Xv[v] = (Xv[v]-Xv[v].mean())/Xv[v].std()
    # combine
    sub = pd.concat([base[X_base_cols].reset_index(drop=True),
                     Xv.reset_index(drop=True)], axis=1)
    sub['T']=T; sub['E']=E
    sub = sub.dropna()
    if len(sub) < 100 or sub.E.sum() < 30:
        inc_rows.append({'var':v,'n':len(sub),'events':int(sub.E.sum()),'note':'insufficient'})
        continue
    Xs = sub[X_base_cols+[v]].values.astype(float)
    Es = sub.E.values.astype(int); Ts = sub.T.values
    # also refit base on same subset for fair LR test
    m_b = PHReg(Ts, sub[X_base_cols].values.astype(float), status=Es).fit()
    m_a = PHReg(Ts, Xs, status=Es).fit()
    LR = 2*(m_a.llf - m_b.llf)
    p_LR = 1 - chi2.cdf(LR, df=1)
    risk_b = (sub[X_base_cols].values.astype(float) @ m_b.params).flatten()
    risk_a = (Xs @ m_a.params).flatten()
    c_b = concordance_index_censored(Es.astype(bool), Ts, risk_b)[0]
    c_a = concordance_index_censored(Es.astype(bool), Ts, risk_a)[0]
    aic_b = -2*m_b.llf + 2*m_b.params.size
    aic_a = -2*m_a.llf + 2*m_a.params.size
    inc_rows.append({'var':v,'n':len(sub),'events':int(sub.E.sum()),
                     'HR_adj':float(np.exp(m_a.params[-1])),
                     'CI_lo':float(np.exp(m_a.conf_int()[-1,0])),
                     'CI_hi':float(np.exp(m_a.conf_int()[-1,1])),
                     'p_var':float(m_a.pvalues[-1]),
                     'LR_chi2':LR,'p_LR':p_LR,
                     'C_base':c_b,'C_full':c_a,'delta_C':c_a-c_b,
                     'AIC_base':aic_b,'AIC_full':aic_a,'delta_AIC':aic_a-aic_b})

res_inc = pd.DataFrame(inc_rows).sort_values('p_LR' if 'p_LR' in pd.DataFrame(inc_rows).columns else 'var')
print(res_inc.to_string(index=False))
res_inc.to_csv('/home/user/dialysis/analysis_outputs/incremental_value.csv', index=False)
print('\nSaved: univariable_cox.csv, base_model_coefs.csv, incremental_value.csv')
