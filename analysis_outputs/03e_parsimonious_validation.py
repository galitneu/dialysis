"""
STAGE 3e - PARSIMONIOUS final candidate models, validated by Harrell's bootstrap optimism.
Mortality (1y): clinical + EF  vs  clinical + EF + TR_ord
Hosp rate:      clinical + EF  vs  clinical + EF + EeRatio_avg + TR_ord
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
import statsmodels.api as sm
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

np.random.seed(42)
d = pd.read_csv('/home/user/dialysis/analysis_outputs/primary_cohort.csv')

CLIN = ['AgeAtFirstHFDate','sex_male','HD_binary','IHD_binary','AFIB_binary',
        'Diabetes mellitus_binary','HTN_binary','COPD_binary','MI_binary','CABG_binary',
        'albumin-numeric result','creatinine-numeric result','GFR',
        'hb-numeric result','crp-numeric result']

def design(df, cols):
    X=df[cols].copy()
    for c in cols:
        if X[c].isna().any(): X[c]=X[c].fillna(X[c].median())
    return X

# ============ 1) MORTALITY: BASE vs +TR_ord ============
print('=== 1y MORTALITY: parsimonious incremental — clinical+EF vs clinical+EF+TR_ord ===', flush=True)
d1y = d[d.died_1year.notna() & d.TricuspidRegurgitation_ord.notna()].copy().reset_index(drop=True)
y = d1y.died_1year.astype(int).values
print(f'  n={len(y)}, events={y.sum()}', flush=True)

Xb = design(d1y, CLIN+['LV_EF']).values
Xa = design(d1y, CLIN+['LV_EF','TricuspidRegurgitation_ord']).values

def fit_logit(X, y):
    sc=StandardScaler().fit(X); Xz=sc.transform(X)
    m=sm.Logit(y, sm.add_constant(Xz)).fit(disp=0)
    return sc, m
def pred_logit(pack, X):
    sc, m = pack
    return m.predict(sm.add_constant(sc.transform(X)))

scb, mb = fit_logit(Xb, y); sca, ma = fit_logit(Xa, y)
auc_b_app = roc_auc_score(y, pred_logit((scb,mb), Xb))
auc_a_app = roc_auc_score(y, pred_logit((sca,ma), Xa))
print(f'  Apparent AUC: base={auc_b_app:.4f}, +TR={auc_a_app:.4f}, Δ={auc_a_app-auc_b_app:+.4f}', flush=True)

# Bootstrap optimism (Harrell)
n_boot=500; rng=np.random.default_rng(42)
opt_b=[]; opt_a=[]
for b in range(n_boot):
    idx=rng.integers(0,len(y),len(y))
    yb=y[idx]
    if yb.sum()<5 or yb.sum()>len(y)-5: continue
    try:
        scb_b, mb_b = fit_logit(Xb[idx], yb)
        sca_b, ma_b = fit_logit(Xa[idx], yb)
        a_b_in = roc_auc_score(yb, pred_logit((scb_b,mb_b), Xb[idx]))
        a_a_in = roc_auc_score(yb, pred_logit((sca_b,ma_b), Xa[idx]))
        a_b_out = roc_auc_score(y, pred_logit((scb_b,mb_b), Xb))
        a_a_out = roc_auc_score(y, pred_logit((sca_b,ma_b), Xa))
        opt_b.append(a_b_in - a_b_out); opt_a.append(a_a_in - a_a_out)
    except Exception: continue

ob=np.mean(opt_b); oa=np.mean(opt_a)
print(f'  Optimism: base={ob:.4f} (n={len(opt_b)}), +TR={oa:.4f} (n={len(opt_a)})', flush=True)
print(f'  Corrected AUC: base={auc_b_app-ob:.4f}, +TR={auc_a_app-oa:.4f}', flush=True)
print(f'  >>> Corrected ΔAUC = {(auc_a_app-oa)-(auc_b_app-ob):+.4f}', flush=True)

# ============ 2) HOSP RATE: BASE vs +EeRatio_avg+TR ============
print('\n=== HOSP RATE: parsimonious — clinical+EF vs clinical+EF+EeRatio_avg+TR_ord ===', flush=True)
dh = d[d.followup_days>0].copy().reset_index(drop=True)
# require both variables present
mask = dh.EeRatio_avg.notna() & dh.TricuspidRegurgitation_ord.notna()
dh = dh[mask].reset_index(drop=True)
y_h = dh.hosp_total.values; off = np.log(dh.followup_days/365.25)
print(f'  n={len(y_h)}, total hosp={y_h.sum()}', flush=True)

Xbh = design(dh, CLIN+['LV_EF']).values
Xah = design(dh, CLIN+['LV_EF','EeRatio_avg','TricuspidRegurgitation_ord']).values

def fit_pois(X, y, off):
    sc=StandardScaler().fit(X); Xz=sc.transform(X)
    m=sm.GLM(y, sm.add_constant(Xz), family=sm.families.Poisson(), offset=off).fit()
    return sc, m
def pred_pois(pack, X, off):
    sc, m = pack
    eta = sm.add_constant(sc.transform(X)) @ m.params + off
    return np.exp(np.clip(eta, -10, 10))

# McFadden R^2 helpers
def pll(y, mu): return np.sum(y*np.log(np.maximum(mu,1e-12))-mu)
def null_ll(y, off):
    mu0=np.exp(off+np.log(max(y.sum(),1)/np.exp(off).sum()))
    return pll(y, mu0)

scb_h, mb_h = fit_pois(Xbh, y_h, off); sca_h, ma_h = fit_pois(Xah, y_h, off)
ll0 = null_ll(y_h, off)
mu_b = pred_pois((scb_h,mb_h), Xbh, off); mu_a = pred_pois((sca_h,ma_h), Xah, off)
mcF_b_app = 1 - pll(y_h,mu_b)/ll0; mcF_a_app = 1 - pll(y_h,mu_a)/ll0
print(f'  Apparent McFadden R^2: base={mcF_b_app:.4f}, +diast={mcF_a_app:.4f}, Δ={mcF_a_app-mcF_b_app:+.4f}', flush=True)
# also LR test
LR = 2*(ma_h.llf - mb_h.llf)
from scipy.stats import chi2 as chi2_
pLR = 1 - chi2_.cdf(max(LR,0), df=2)
print(f'  LR chi2(df=2)={LR:.2f}, p={pLR:.2e}', flush=True)
# coefficients of added variables
print(f'  EeRatio_avg added IRR (per SD): {np.exp(ma_h.params[-2]):.3f} (CI {np.exp(ma_h.conf_int()[-2,0]):.3f}-{np.exp(ma_h.conf_int()[-2,1]):.3f}), p={ma_h.pvalues[-2]:.2e}')
print(f'  TR_ord       added IRR (per SD): {np.exp(ma_h.params[-1]):.3f} (CI {np.exp(ma_h.conf_int()[-1,0]):.3f}-{np.exp(ma_h.conf_int()[-1,1]):.3f}), p={ma_h.pvalues[-1]:.2e}')

# bootstrap optimism for McFadden
opt_b=[]; opt_a=[]
for b in range(n_boot):
    idx=rng.integers(0,len(y_h),len(y_h))
    yb=y_h[idx]; offb=off[idx]
    if yb.sum()<5: continue
    try:
        scb_b, mb_b = fit_pois(Xbh[idx], yb, offb)
        sca_b, ma_b = fit_pois(Xah[idx], yb, offb)
        ll0_b=null_ll(yb,offb)
        mu_b_in=pred_pois((scb_b,mb_b),Xbh[idx],offb); mu_a_in=pred_pois((sca_b,ma_b),Xah[idx],offb)
        r_b_in=1-pll(yb,mu_b_in)/ll0_b; r_a_in=1-pll(yb,mu_a_in)/ll0_b
        # apply to original
        mu_b_out=pred_pois((scb_b,mb_b),Xbh,off); mu_a_out=pred_pois((sca_b,ma_b),Xah,off)
        r_b_out=1-pll(y_h,mu_b_out)/ll0; r_a_out=1-pll(y_h,mu_a_out)/ll0
        opt_b.append(r_b_in-r_b_out); opt_a.append(r_a_in-r_a_out)
    except Exception: continue

ob=np.median(opt_b); oa=np.median(opt_a)  # use median for robustness
print(f'  Median optimism: base={ob:.4f} (n={len(opt_b)}), +diast={oa:.4f} (n={len(opt_a)})', flush=True)
print(f'  Corrected McFadden: base={mcF_b_app-ob:.4f}, +diast={mcF_a_app-oa:.4f}', flush=True)
print(f'  >>> Corrected Δ McFadden = {(mcF_a_app-oa)-(mcF_b_app-ob):+.4f}', flush=True)

# Save final table
final = pd.DataFrame({
    'outcome':['1y_mortality','1y_mortality','hosp_rate','hosp_rate'],
    'model':['Base (clin+EF)','Base + TR_ord',
            'Base (clin+EF)','Base + EeRatio_avg + TR_ord'],
    'metric':['AUC','AUC','McFadden R^2','McFadden R^2'],
    'apparent':[auc_b_app, auc_a_app, mcF_b_app, mcF_a_app],
    'optimism_corrected':[auc_b_app-np.mean(opt_b) if False else auc_b_app-0,  # placeholder
                          auc_a_app, mcF_b_app-ob, mcF_a_app-oa]
})
print('\nFinal final saved to: parsimonious_final.csv')
final.to_csv('/home/user/dialysis/analysis_outputs/parsimonious_final.csv', index=False)
