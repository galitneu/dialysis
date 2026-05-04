"""
Stage 4b: lean version of MI + subgroups (re-run only the parts that failed)
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
import statsmodels.api as sm
from sklearn.preprocessing import StandardScaler
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer
from scipy.stats import chi2, norm

np.random.seed(42)
df = pd.read_csv('/home/user/dialysis/analysis_outputs/cohort_flagged.csv')

ord_maps = {
    'LACavitySize': {'Normal':0,'Mildly dilated':1,'Moderately dilated':2,'Severely dilated':3},
    'MitralRegurgitation': {'Trivial':0,'Mild (I)':1,'Mild-to-moderate (I-II)':2,'Moderate (II)':3,
                            'Moderately-severe (III)':4,'Severe (IV)':5},
    'TricuspidRegurgitation': {'Trivial':0,'Mild (I)':1,'Mild-to-moderate (I-II)':2,'Moderate (II)':3,
                              'Moderately-severe (III)':4,'Severe (IV)':5},
    'RVSize': {'Normal':0,'Mildly dilated':1,'Dilated':2,'RVH':2},
    'RVSystolicFunction': {'Normal':0,'Mildly reduced':1,'Moderately reduced':2,'Severely reduced':3},
    'LeftVentricleSystolicFunction': {'Increased (hyperdynamic)':0,'Normal':0,'Mildly reduced':1,
                                      'Mild-moderately reduced':2,'Moderately reduced':3,
                                      'Moderate-severely reduced':4,'Severely reduced':5},
    'LeftVentricleCavitySize': {'Small':-1,'Normal':0,'Mildly dilated':1,'Moderately dilated':2,'Severely dilated':3},
    'LeftVentricleWallThickness': {'Normal':0,'Mildly increased':1,'Moderately increased':2,'Severely increased':3},
    'ECHO_SPAP': {'Normal':0,'Mildly increased':1,'Moderately increased':2,'Severely increased':3},
}
for col, m in ord_maps.items():
    df[col+'_ord'] = df[col].map(m)

CLIN_BASE = ['AgeAtFirstHFDate','sex_male','HD_binary','IHD_binary','AFIB_binary',
             'Diabetes mellitus_binary','HTN_binary','COPD_binary','MI_binary','CABG_binary',
             'albumin-numeric result','creatinine-numeric result','GFR',
             'hb-numeric result','crp-numeric result']

TOP = ['LV_EF','TricuspidRegurgitation_ord','TissueDopplerSVelocitySeptal',
       'EeRatio_avg','TissueDopplerEERatioSeptal','TissueDopplerEERatioLateral',
       'MitralInflowPeakEWave','RVSystolicFunction_ord','LeftVentricleSystolicFunction_ord']

d_prim = df[(df.echo_timing_class.isin(['before','same_day'])) &
            (df.echo_to_dialysis_days.between(0,365))].copy().reset_index(drop=True)
print(f'Primary cohort: n={len(d_prim)}', flush=True)

# === B. Multiple imputation ===
print('\n=== B. MULTIPLE IMPUTATION (m=10) ===', flush=True)
d1y = d_prim[d_prim.died_1year.notna()].reset_index(drop=True)
work_cols = CLIN_BASE + TOP
sub = d1y[work_cols + ['died_1year','hosp_total','followup_days']].copy()

mi_mort = []
mi_hosp = []
for m_idx in range(10):
    imp = IterativeImputer(random_state=m_idx, max_iter=20, sample_posterior=True)
    sub_imp = sub.copy()
    sub_imp[work_cols] = imp.fit_transform(sub_imp[work_cols])
    for v in TOP:
        clin = CLIN_BASE+(['LV_EF'] if v!='LV_EF' else [])
        Xb = StandardScaler().fit_transform(sub_imp[clin].values)
        xv = sub_imp[[v]].values.astype(float)
        if sub_imp[v].nunique()>5: xv = (xv-xv.mean())/xv.std()
        Xa = np.hstack([Xb, xv])
        ys = sub_imp.died_1year.astype(int).values
        try:
            m = sm.Logit(ys, sm.add_constant(Xa)).fit(disp=0)
            mi_mort.append(dict(m=m_idx,var=v,beta=m.params[-1],se=m.bse[-1]))
        except Exception: pass
    sh = sub_imp[sub_imp.followup_days>0]
    off = np.log(sh.followup_days/365.25)
    for v in TOP:
        clin = CLIN_BASE+(['LV_EF'] if v!='LV_EF' else [])
        Xb = StandardScaler().fit_transform(sh[clin].values)
        xv = sh[[v]].values.astype(float)
        if sh[v].nunique()>5: xv = (xv-xv.mean())/xv.std()
        Xa = np.hstack([Xb, xv])
        try:
            m = sm.GLM(sh.hosp_total.values, sm.add_constant(Xa),
                      family=sm.families.Poisson(), offset=off).fit(cov_type='HC1')
            mi_hosp.append(dict(m=m_idx,var=v,beta=m.params[-1],se=m.bse[-1]))
        except Exception: pass

def rubin(rows):
    df_mi = pd.DataFrame(rows)
    out = []
    for v, g in df_mi.groupby('var'):
        Q = g.beta.mean(); U = (g.se**2).mean(); B = g.beta.var(ddof=1)
        T = U + (1+1/len(g))*B
        se = np.sqrt(T)
        z = Q/se if se>0 else 0
        p = 2*(1 - norm.cdf(abs(z))) if se>0 else np.nan
        out.append(dict(var=v, beta=Q, se=se, est=np.exp(Q),
                       CIlo=np.exp(Q-1.96*se), CIhi=np.exp(Q+1.96*se), p=p))
    return pd.DataFrame(out).sort_values('p')

print('\n--- MI pooled OR for 1y mortality (added to clinical+EF) ---')
pm = rubin(mi_mort); print(pm.to_string(index=False))
print('\n--- MI pooled IRR for hosp rate (added to clinical+EF) ---')
ph = rubin(mi_hosp); print(ph.to_string(index=False))
pm.to_csv('/home/user/dialysis/analysis_outputs/MI_pooled_mortality.csv', index=False)
ph.to_csv('/home/user/dialysis/analysis_outputs/MI_pooled_hosp.csv', index=False)

# === C. Subgroups (HFrEF/HFmrEF/HFpEF) ===
print('\n=== C. SUBGROUPS by EF strata ===', flush=True)
def fit_pois_inc(df_, base_cols, v):
    sub = df_[base_cols+[v,'hosp_total','followup_days']].dropna(subset=[v]).copy()
    for c in base_cols: sub[c] = sub[c].fillna(sub[c].median())
    sub = sub[sub.followup_days>0]
    if len(sub)<40: return None
    Xb = StandardScaler().fit_transform(sub[base_cols].values)
    xv = sub[[v]].values.astype(float)
    if sub[v].nunique()>5: xv=(xv-xv.mean())/xv.std()
    Xa = np.hstack([Xb,xv])
    off = np.log(sub.followup_days/365.25); yy = sub.hosp_total.values
    try:
        mb=sm.GLM(yy,sm.add_constant(Xb),family=sm.families.Poisson(),offset=off).fit()
        ma=sm.GLM(yy,sm.add_constant(Xa),family=sm.families.Poisson(),offset=off).fit(cov_type='HC1')
    except Exception: return None
    LR=2*(ma.llf-mb.llf); pLR=1-chi2.cdf(max(LR,0),df=1)
    return dict(n=len(sub), IRR=float(np.exp(ma.params[-1])),
               CIlo=float(np.exp(ma.conf_int()[-1,0])),
               CIhi=float(np.exp(ma.conf_int()[-1,1])),
               p=float(ma.pvalues[-1]), p_LR=pLR)

def fit_logit_inc(df_, base_cols, v):
    sub = df_[base_cols+[v,'died_1year']].dropna(subset=[v,'died_1year']).copy()
    for c in base_cols: sub[c]=sub[c].fillna(sub[c].median())
    if len(sub)<40 or sub.died_1year.sum()<5: return None
    Xb = StandardScaler().fit_transform(sub[base_cols].values)
    xv = sub[[v]].values.astype(float)
    if sub[v].nunique()>5: xv=(xv-xv.mean())/xv.std()
    Xa = np.hstack([Xb,xv])
    ys = sub.died_1year.astype(int).values
    try:
        mb=sm.Logit(ys,sm.add_constant(Xb)).fit(disp=0)
        ma=sm.Logit(ys,sm.add_constant(Xa)).fit(disp=0)
    except Exception: return None
    LR=2*(ma.llf-mb.llf); pLR=1-chi2.cdf(max(LR,0),df=1)
    return dict(n=len(sub), events=int(ys.sum()),
               OR=float(np.exp(ma.params[-1])),
               CIlo=float(np.exp(ma.conf_int()[-1,0])),
               CIhi=float(np.exp(ma.conf_int()[-1,1])),
               p=float(ma.pvalues[-1]), p_LR=pLR)

rows=[]
for grp_name, mask in [('HFrEF (EF<40)', d_prim.LV_EF<40),
                       ('HFmrEF (40-49)', (d_prim.LV_EF>=40)&(d_prim.LV_EF<50)),
                       ('HFpEF (>=50)', d_prim.LV_EF>=50)]:
    g = d_prim[mask].copy()
    if len(g)<40: continue
    print(f'  {grp_name}: n={len(g)}, events_1y={int(g.died_1year.sum())}, total_hosp={int(g.hosp_total.sum())}')
    g1y = g[g.died_1year.notna()]
    for v in TOP:
        if v=='LV_EF': continue
        rL = fit_logit_inc(g1y, CLIN_BASE+['LV_EF'], v)
        rP = fit_pois_inc(g, CLIN_BASE+['LV_EF'], v)
        if rL: rL.update(dict(group=grp_name,var=v,outcome='1y_mort')); rows.append(rL)
        if rP: rP.update(dict(group=grp_name,var=v,outcome='hosp_rate')); rows.append(rP)
res = pd.DataFrame(rows)
piv = res.pivot_table(index=['var','outcome'], columns='group', values='p_LR').round(4)
print('\nSubgroup p_LR (added to clinical+EF):')
print(piv.to_string())
res.to_csv('/home/user/dialysis/analysis_outputs/sensitivity_subgroups.csv', index=False)
print('\nDone Stage 4b.')
