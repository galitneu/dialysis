"""
STAGE 1 - Univariable associations of each echo parameter with:
  (a) 1-year all-cause mortality   (logistic regression, OR per 1 SD)
  (b) hospitalization rate          (Negative Binomial with log(FU-yrs) offset)
Cohort: primary (n=528, echo within 365d before/at dialysis start)
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
import statsmodels.api as sm
from statsmodels.discrete.discrete_model import NegativeBinomial
from scipy.stats import chi2

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

# 1) restrict to those with computable 1y mortality
d1y = d[d['died_1year'].notna()].copy()
print(f'1-year cohort: n={len(d1y)}, deaths-by-1y={int(d1y.died_1year.sum())} ({100*d1y.died_1year.mean():.1f}%)')

# z-score continuous (mean/SD on this sample for interpretability of OR/IRR per SD)
def z(s):
    return (s - s.mean())/s.std()

def fit_logit_univ(df, var):
    sub = df[[var,'died_1year']].dropna()
    if len(sub) < 50 or sub.died_1year.sum() < 10: return None
    x = sub[var].values.astype(float)
    if sub[var].nunique()>5: x = (x-x.mean())/x.std()
    X = sm.add_constant(x)
    try:
        m = sm.Logit(sub.died_1year.values, X).fit(disp=0)
        b = m.params[1]; ci = m.conf_int()[1]; p = m.pvalues[1]
        # AUC
        from sklearn.metrics import roc_auc_score
        auc = roc_auc_score(sub.died_1year.values, m.predict(X))
        return dict(var=var, n=len(sub), events=int(sub.died_1year.sum()),
                    OR_per_SD=float(np.exp(b)), CIlo=float(np.exp(ci[0])),
                    CIhi=float(np.exp(ci[1])), p=float(p), AUC=auc)
    except Exception as e:
        return dict(var=var, error=str(e))

print('\n=== UNIVARIABLE LOGISTIC: 1-YEAR MORTALITY (OR per 1 SD; ordinal per category) ===')
rows = [r for r in (fit_logit_univ(d1y, v) for v in ECHO_ALL) if r is not None]
res_log = pd.DataFrame(rows).sort_values('p')
# BH-FDR
from statsmodels.stats.multitest import multipletests
mask = res_log.p.notna()
res_log.loc[mask,'p_FDR'] = multipletests(res_log.loc[mask,'p'], method='fdr_bh')[1]
print(res_log.to_string(index=False))
res_log.to_csv('/home/user/dialysis/analysis_outputs/univariable_logit_1y_mort.csv', index=False)

# 2) Negative Binomial for hospitalization rate, offset = log(FU-yrs)
print('\n=== UNIVARIABLE NEGATIVE BINOMIAL: HOSP RATE per person-yr (IRR per 1 SD) ===')
d_h = d[d.followup_days > 0].copy()
d_h['logFUyr'] = np.log(d_h.followup_days/365.25)
print(f'Hosp cohort: n={len(d_h)}, total hosp={int(d_h.hosp_total.sum())}, '
      f'mean rate={d_h.hosp_total.sum()/(d_h.followup_days.sum()/365.25):.2f}/yr')

def fit_nb_univ(df, var):
    sub = df[[var,'hosp_total','logFUyr']].dropna()
    if len(sub) < 50: return None
    x = sub[var].values.astype(float)
    if sub[var].nunique()>5: x = (x-x.mean())/x.std()
    X = sm.add_constant(x)
    try:
        m = sm.NegativeBinomial(sub.hosp_total.values, X, exposure=np.exp(sub.logFUyr.values)).fit(disp=0)
        b = m.params[1]; ci = m.conf_int()[1]; p = m.pvalues[1]
        return dict(var=var, n=len(sub), total_hosp=int(sub.hosp_total.sum()),
                    IRR_per_SD=float(np.exp(b)), CIlo=float(np.exp(ci[0])),
                    CIhi=float(np.exp(ci[1])), p=float(p))
    except Exception as e:
        return dict(var=var, n=len(sub), error=str(e))

rows = [r for r in (fit_nb_univ(d_h, v) for v in ECHO_ALL) if r is not None]
res_nb = pd.DataFrame(rows).sort_values('p')
mask = res_nb.p.notna() if 'p' in res_nb.columns else None
if mask is not None and mask.any():
    res_nb.loc[mask,'p_FDR'] = multipletests(res_nb.loc[mask,'p'], method='fdr_bh')[1]
print(res_nb.to_string(index=False))
res_nb.to_csv('/home/user/dialysis/analysis_outputs/univariable_nb_hosp.csv', index=False)
print('\nSaved univariable_logit_1y_mort.csv, univariable_nb_hosp.csv')
