"""
STAGE 3d - Robust bootstrap optimism for hosp rate using out-of-bag (.632+) approach.
Avoid numerical blow-up by clipping linear predictor to [-15,15] before exp().
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
            'LeftVentricleSystolicFunction_ord','LeftVentricleCavitySize_ord','ECHO_SPAP_ord']
CLIN = ['AgeAtFirstHFDate','sex_male','HD_binary','IHD_binary','AFIB_binary',
        'Diabetes mellitus_binary','HTN_binary','COPD_binary','MI_binary','CABG_binary',
        'albumin-numeric result','creatinine-numeric result','GFR',
        'hb-numeric result','crp-numeric result']

def design(df,cols):
    X=df[cols].copy()
    for c in cols:
        if X[c].isna().any(): X[c]=X[c].fillna(X[c].median())
    return X

dh=d[d.followup_days>0].copy().reset_index(drop=True)
y=dh.hosp_total.values; off=np.log(dh.followup_days/365.25)
Xb=design(dh,CLIN+['LV_EF']).values
Xf=design(dh,CLIN+ECHO_NUM+ECHO_ORD).values
print(f'n={len(y)}, hosp={y.sum()}', flush=True)

# Use .632+ bootstrap with linear-predictor clipping for numerical safety.
def fit_pred(X, y, off):
    sc=StandardScaler().fit(X); Xz=sc.transform(X)
    m=sm.GLM(y,sm.add_constant(Xz),family=sm.families.Poisson(),offset=off,
             ).fit_regularized(alpha=0.01, L1_wt=0.0, maxiter=500)  # tiny ridge for stability
    return sc, m

def predict(packed, X, off):
    sc, m = packed
    Xz = sc.transform(X)
    eta = sm.add_constant(Xz) @ m.params + off
    eta = np.clip(eta, -10, 10)
    return np.exp(eta)

def pll(y, mu):
    mu = np.maximum(mu, 1e-9)
    return np.sum(y*np.log(mu) - mu)

# null reference (intercept-only with offset → mean rate)
def null_ll(y, off):
    mu0 = np.exp(off + np.log(max(y.sum(),1)/np.exp(off).sum()))
    return pll(y, mu0)

mb=fit_pred(Xb,y,off); mf=fit_pred(Xf,y,off)
ll0 = null_ll(y, off)
mu_b = predict(mb, Xb, off); mu_f = predict(mf, Xf, off)
mcF_b_app = 1 - pll(y,mu_b)/ll0; mcF_f_app = 1 - pll(y,mu_f)/ll0
print(f'Apparent McFadden R^2 (ridge α=0.01): base={mcF_b_app:.4f}, full={mcF_f_app:.4f}, Δ={mcF_f_app-mcF_b_app:+.4f}', flush=True)

# .632+ bootstrap: estimate optimism using OOB error
n=len(y); rng=np.random.default_rng(42)
oob_devs_b=[]; oob_devs_f=[]
in_devs_b=[]; in_devs_f=[]
n_boot=200
for b in range(n_boot):
    idx=rng.integers(0,n,n)
    in_set=set(idx); oob=[i for i in range(n) if i not in in_set]
    if len(oob)<20: continue
    yb=y[idx]; ob_=off[idx]; Xb_b=Xb[idx]; Xf_b=Xf[idx]
    if yb.sum()<5: continue
    try:
        mbb=fit_pred(Xb_b,yb,ob_); mff=fit_pred(Xf_b,yb,ob_)
        # in-sample (apparent on bootstrap)
        mu_b_in = predict(mbb, Xb_b, ob_); mu_f_in = predict(mff, Xf_b, ob_)
        ll0_b = null_ll(yb, ob_)
        in_devs_b.append(1 - pll(yb,mu_b_in)/ll0_b)
        in_devs_f.append(1 - pll(yb,mu_f_in)/ll0_b)
        # OOB on original-not-in-bootstrap
        oob_idx = np.array(oob)
        mu_b_oob = predict(mbb, Xb[oob_idx], off[oob_idx])
        mu_f_oob = predict(mff, Xf[oob_idx], off[oob_idx])
        ll0_oob = null_ll(y[oob_idx], off[oob_idx])
        oob_devs_b.append(1 - pll(y[oob_idx],mu_b_oob)/ll0_oob)
        oob_devs_f.append(1 - pll(y[oob_idx],mu_f_oob)/ll0_oob)
    except Exception:
        continue
    if (b+1)%50==0: print(f'  {b+1}/{n_boot}', flush=True)

# Trim extreme outliers (top/bottom 5% on OOB) for stability
def trim(arr, p=0.05):
    arr=np.array(arr); lo,hi=np.quantile(arr,[p,1-p]); return arr[(arr>=lo)&(arr<=hi)]

oob_b=np.median(oob_devs_b); oob_f=np.median(oob_devs_f)  # median is robust
oob_b_t = trim(oob_devs_b).mean(); oob_f_t = trim(oob_devs_f).mean()
in_b = np.mean(in_devs_b); in_f = np.mean(in_devs_f)
print('\n=== HOSP BOOTSTRAP (robust .632) ===')
print(f'BASE: Apparent McF={mcF_b_app:.4f}, OOB median={oob_b:.4f}, OOB trimmed-mean={oob_b_t:.4f}, '
      f'.632 corrected={0.368*mcF_b_app+0.632*oob_b_t:.4f}')
print(f'FULL: Apparent McF={mcF_f_app:.4f}, OOB median={oob_f:.4f}, OOB trimmed-mean={oob_f_t:.4f}, '
      f'.632 corrected={0.368*mcF_f_app+0.632*oob_f_t:.4f}')
delta_corr=(0.368*mcF_f_app+0.632*oob_f_t) - (0.368*mcF_b_app+0.632*oob_b_t)
delta_app=mcF_f_app-mcF_b_app
print(f'>>> APPARENT  Δ McF = {delta_app:+.4f}')
print(f'>>> CORRECTED Δ McF (.632) = {delta_corr:+.4f}')

pd.DataFrame({'metric':['McF_app_base','McF_app_full','OOB_med_base','OOB_med_full',
                       'OOB_trimmean_base','OOB_trimmean_full','dot632_corr_base',
                       'dot632_corr_full','delta_app','delta_corr_dot632'],
              'value':[mcF_b_app, mcF_f_app, oob_b, oob_f,
                      oob_b_t, oob_f_t,
                      0.368*mcF_b_app+0.632*oob_b_t, 0.368*mcF_f_app+0.632*oob_f_t,
                      delta_app, delta_corr]}).to_csv(
    '/home/user/dialysis/analysis_outputs/bootstrap_hosp_robust.csv', index=False)
print('Saved bootstrap_hosp_robust.csv')
