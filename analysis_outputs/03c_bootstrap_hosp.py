"""
STAGE 3c - Bootstrap optimism correction for hospitalization rate (Poisson GLM).
Compare BASE (clinical+EF) vs FULL (clinical+EF+all echo) using out-of-bag pseudo-R^2 (Cragg-Uhler-like)
and explained deviance.
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
import statsmodels.api as sm
from sklearn.preprocessing import StandardScaler

np.random.seed(42)
d = pd.read_csv('/home/user/dialysis/analysis_outputs/primary_cohort.csv')

ECHO_NUM = ['LV_EF','LeftVentricleEstimatedMassIndex',
            'LeftVentricleInterventricularSeptumThickness',
            'LeftVentricleEndDiastolicDiameter','LeftVentricleEndSystolicDiameter',
            'LeftVentriclePosteriorWallThickness','MitralInflowPeakEWave',
            'TissueDopplerEERatioSeptal','TissueDopplerEERatioLateral','EeRatio_avg',
            'EstimatedSysPAPressure','TissueDopplerSVelocityLateral',
            'LeftVentricleScoreIndex','LeftVentricleEstimatedMass']
ECHO_ORD = ['LACavitySize_ord','MitralRegurgitation_ord','TricuspidRegurgitation_ord',
            'LeftVentricleSystolicFunction_ord','LeftVentricleCavitySize_ord',
            'ECHO_SPAP_ord']
CLIN_BASE = ['AgeAtFirstHFDate','sex_male','HD_binary','IHD_binary','AFIB_binary',
             'Diabetes mellitus_binary','HTN_binary','COPD_binary','MI_binary','CABG_binary',
             'albumin-numeric result','creatinine-numeric result','GFR',
             'hb-numeric result','crp-numeric result']

def design(df, cols):
    X = df[cols].copy()
    for c in cols:
        if X[c].isna().any():
            X[c] = X[c].fillna(X[c].median())
    return X

dh = d[d.followup_days>0].copy().reset_index(drop=True)
y = dh.hosp_total.values
off = np.log(dh.followup_days/365.25)

Xb = design(dh, CLIN_BASE+['LV_EF']).values
Xf = design(dh, CLIN_BASE+ECHO_NUM+ECHO_ORD).values
print(f'n={len(y)}, total hosp={y.sum()}')
print(f'Base p={Xb.shape[1]}, Full p={Xf.shape[1]}')

# McFadden's pseudo-R^2: 1 - llf_full / llf_null
def fit_pois(X, y, off):
    sc = StandardScaler().fit(X); Xz = sc.transform(X)
    m = sm.GLM(y, sm.add_constant(Xz), family=sm.families.Poisson(), offset=off).fit()
    return m, sc

def predict_pois(model_pack, X, off):
    m, sc = model_pack
    Xz = sc.transform(X)
    return m.predict(sm.add_constant(Xz), offset=off)

# poisson log-likelihood (no constants) on test data with mu predictions
def pois_ll(y, mu):
    mu = np.maximum(mu, 1e-12)
    return np.sum(y*np.log(mu) - mu)

# null model
m_null = sm.GLM(y, np.ones((len(y),1)), family=sm.families.Poisson(), offset=off).fit()
ll_null = m_null.llf

mb, scb = fit_pois(Xb, y, off)
mf, scf = fit_pois(Xf, y, off)
ll_b_app = mb.llf; ll_f_app = mf.llf
mcF_b_app = 1 - ll_b_app/ll_null
mcF_f_app = 1 - ll_f_app/ll_null
print(f'\nApparent McFadden R^2: base={mcF_b_app:.4f}, full={mcF_f_app:.4f}, Δ={mcF_f_app-mcF_b_app:+.4f}')

# Bootstrap optimism for McFadden R^2
n_boot=200
opt_b, opt_f = [], []
rng = np.random.default_rng(42)
for b in range(n_boot):
    idx = rng.integers(0, len(y), len(y))
    yb = y[idx]; offb = off[idx]; Xb_b = Xb[idx]; Xf_b = Xf[idx]
    if yb.sum() < 5: continue
    try:
        mbb, scbb = fit_pois(Xb_b, yb, offb)
        mbf, scbf = fit_pois(Xf_b, yb, offb)
        # null on bootstrap
        ll_null_b = sm.GLM(yb, np.ones((len(yb),1)), family=sm.families.Poisson(), offset=offb).fit().llf
        # apparent on bootstrap
        ll_b_b = mbb.llf; ll_b_f = mbf.llf
        r_b_app = 1 - ll_b_b/ll_null_b; r_f_app = 1 - ll_b_f/ll_null_b
        # apply to original
        mu_b = predict_pois((mbb,scbb), Xb, off); mu_f = predict_pois((mbf,scbf), Xf, off)
        ll_b_test = pois_ll(y, mu_b); ll_f_test = pois_ll(y, mu_f)
        # Compute pseudo-R^2 on original using log-lik computed manually
        ll_null_const = pois_ll(y, np.exp(off + np.log(y.sum()/np.exp(off).sum())))
        r_b_test = 1 - ll_b_test/ll_null_const; r_f_test = 1 - ll_f_test/ll_null_const
        opt_b.append(r_b_app - r_b_test); opt_f.append(r_f_app - r_f_test)
    except Exception:
        continue
    if (b+1)%50==0: print(f'  {b+1}/{n_boot}', flush=True)

ob = np.mean(opt_b); of = np.mean(opt_f)
print('\n=== HOSP RATE BOOTSTRAP RESULTS ===')
print(f'BASE: McF apparent={mcF_b_app:.4f}, optimism={ob:.4f}, corrected={mcF_b_app-ob:.4f} ({len(opt_b)} iters)')
print(f'FULL: McF apparent={mcF_f_app:.4f}, optimism={of:.4f}, corrected={mcF_f_app-of:.4f} ({len(opt_f)} iters)')
print(f'>>> APPARENT  Δ McF = {mcF_f_app-mcF_b_app:+.4f}')
print(f'>>> CORRECTED Δ McF = {(mcF_f_app-of)-(mcF_b_app-ob):+.4f}')

pd.DataFrame({'metric':['McF_app_base','McF_app_full','optimism_base','optimism_full',
                       'McF_corr_base','McF_corr_full','delta_app','delta_corr'],
              'value':[mcF_b_app, mcF_f_app, ob, of,
                      mcF_b_app-ob, mcF_f_app-of,
                      mcF_f_app-mcF_b_app, (mcF_f_app-of)-(mcF_b_app-ob)]}).to_csv(
    '/home/user/dialysis/analysis_outputs/bootstrap_hosp.csv', index=False)
print('Saved bootstrap_hosp.csv')
