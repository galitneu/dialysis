"""
STAGE 4 - Sensitivity analyses
  (a) Echo timing window: 90d, 30d, all (sensitivity)
  (b) Full-followup Cox PH for time-to-death (alongside 1y logistic)
  (c) Multiple imputation for missing echo (chained equations, m=10) for top candidates
  (d) HFpEF (EF>=50) vs HFrEF (EF<40) subgroup analysis
  (e) Restricted cubic spline check for non-linearity in EF, E/e', SPAP
  (f) Influence diagnostic: leave-one-out
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
import statsmodels.api as sm
from statsmodels.duration.hazard_regression import PHReg
from sksurv.metrics import concordance_index_censored
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler
from sklearn.experimental import enable_iterative_imputer
from sklearn.impute import IterativeImputer, SimpleImputer
from scipy.stats import chi2

np.random.seed(42)
df_all = pd.read_csv('/home/user/dialysis/analysis_outputs/cohort_flagged.csv')

# Re-encode ordinals for full df_all
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
    df_all[col+'_ord'] = df_all[col].map(m)

CLIN_BASE = ['AgeAtFirstHFDate','sex_male','HD_binary','IHD_binary','AFIB_binary',
             'Diabetes mellitus_binary','HTN_binary','COPD_binary','MI_binary','CABG_binary',
             'albumin-numeric result','creatinine-numeric result','GFR',
             'hb-numeric result','crp-numeric result']

# Top echo candidates from Stage 2 incremental analysis
TOP_MORT = ['TricuspidRegurgitation_ord','TissueDopplerSVelocitySeptal','LV_EF']
TOP_HOSP = ['EeRatio_avg','TissueDopplerEERatioSeptal','TissueDopplerEERatioLateral',
            'MitralInflowPeakEWave','RVSystolicFunction_ord','TricuspidRegurgitation_ord',
            'LeftVentricleSystolicFunction_ord']
ALL_TOP = list(dict.fromkeys(TOP_MORT + TOP_HOSP))

def fit_logit_inc(df, base_cols, echo_var, y='died_1year'):
    sub = df[base_cols + [echo_var, y]].dropna(subset=[echo_var, y]).copy()
    for c in base_cols:
        sub[c] = sub[c].fillna(sub[c].median())
    if len(sub) < 50: return None
    ys = sub[y].astype(int).values
    Xb = StandardScaler().fit_transform(sub[base_cols].values)
    xv = sub[[echo_var]].values.astype(float)
    if sub[echo_var].nunique()>5: xv = (xv - xv.mean())/xv.std()
    Xa = np.hstack([Xb, xv])
    try:
        mb = sm.Logit(ys, sm.add_constant(Xb)).fit(disp=0)
        ma = sm.Logit(ys, sm.add_constant(Xa)).fit(disp=0)
    except Exception: return None
    LR = 2*(ma.llf - mb.llf); pLR = 1 - chi2.cdf(max(LR,0),df=1)
    aucb = roc_auc_score(ys, mb.predict(sm.add_constant(Xb)))
    auca = roc_auc_score(ys, ma.predict(sm.add_constant(Xa)))
    return dict(n=len(sub), events=int(ys.sum()),
                OR_per_SD=float(np.exp(ma.params[-1])),
                CIlo=float(np.exp(ma.conf_int()[-1,0])),
                CIhi=float(np.exp(ma.conf_int()[-1,1])),
                p=float(ma.pvalues[-1]), p_LR=pLR,
                AUC_base=aucb, AUC_full=auca, dAUC=auca-aucb)

def fit_pois_inc(df, base_cols, echo_var):
    sub = df[base_cols + [echo_var,'hosp_total','followup_days']].dropna(subset=[echo_var]).copy()
    for c in base_cols:
        sub[c] = sub[c].fillna(sub[c].median())
    sub = sub[sub.followup_days>0]
    if len(sub) < 50: return None
    Xb = StandardScaler().fit_transform(sub[base_cols].values)
    xv = sub[[echo_var]].values.astype(float)
    if sub[echo_var].nunique()>5: xv = (xv - xv.mean())/xv.std()
    Xa = np.hstack([Xb, xv])
    off = np.log(sub.followup_days/365.25)
    yy = sub.hosp_total.values
    try:
        mb = sm.GLM(yy, sm.add_constant(Xb), family=sm.families.Poisson(), offset=off).fit(cov_type='HC1')
        ma = sm.GLM(yy, sm.add_constant(Xa), family=sm.families.Poisson(), offset=off).fit(cov_type='HC1')
    except Exception: return None
    LR = 2*(ma.llf - mb.llf); pLR = 1 - chi2.cdf(max(LR,0),df=1)
    return dict(n=len(sub), total_hosp=int(yy.sum()),
                IRR_per_SD=float(np.exp(ma.params[-1])),
                CIlo=float(np.exp(ma.conf_int()[-1,0])),
                CIhi=float(np.exp(ma.conf_int()[-1,1])),
                p=float(ma.pvalues[-1]), p_LR=pLR)

def fit_cox_inc(df, base_cols, echo_var):
    sub = df[base_cols + [echo_var,'time_to_event_days','event']].dropna(subset=[echo_var]).copy()
    for c in base_cols:
        sub[c] = sub[c].fillna(sub[c].median())
    if len(sub) < 50: return None
    T = sub.time_to_event_days.values; E = sub.event.astype(int).values
    Xb = StandardScaler().fit_transform(sub[base_cols].values)
    xv = sub[[echo_var]].values.astype(float)
    if sub[echo_var].nunique()>5: xv = (xv - xv.mean())/xv.std()
    Xa = np.hstack([Xb, xv])
    try:
        mb = PHReg(T, Xb, status=E).fit()
        ma = PHReg(T, Xa, status=E).fit()
    except Exception: return None
    LR = 2*(ma.llf - mb.llf); pLR = 1 - chi2.cdf(max(LR,0),df=1)
    risk_b = (Xb @ mb.params).flatten(); risk_a = (Xa @ ma.params).flatten()
    cb = concordance_index_censored(E.astype(bool), T, risk_b)[0]
    ca = concordance_index_censored(E.astype(bool), T, risk_a)[0]
    return dict(n=len(sub), events=int(E.sum()),
                HR_per_SD=float(np.exp(ma.params[-1])),
                CIlo=float(np.exp(ma.conf_int()[-1,0])),
                CIhi=float(np.exp(ma.conf_int()[-1,1])),
                p=float(ma.pvalues[-1]), p_LR=pLR,
                C_base=cb, C_full=ca, dC=ca-cb)

# Build cohorts
df_all['c_primary'] = ((df_all.echo_timing_class.isin(['before','same_day'])) &
                      (df_all.echo_to_dialysis_days.between(0,365))).astype(int)
df_all['c_90'] = ((df_all.c_primary==1) & (df_all.echo_to_dialysis_days<=90)).astype(int)
df_all['c_30'] = ((df_all.c_primary==1) & (df_all.echo_to_dialysis_days<=30)).astype(int)
df_all['c_all'] = 1

cohorts = {'primary_365d': df_all[df_all.c_primary==1].copy(),
           '90d': df_all[df_all.c_90==1].copy(),
           '30d': df_all[df_all.c_30==1].copy(),
           'all_incl_post': df_all[df_all.c_all==1].copy()}
for n, c in cohorts.items():
    print(f'  {n}: n={len(c)}')

# === A. Echo timing window sensitivity ===
print('\n=== A. SENSITIVITY: ECHO TIMING WINDOWS — incremental value over base ===')
rows = []
for cohort_name, cohort in cohorts.items():
    d1y = cohort[cohort.died_1year.notna()].copy()
    for v in ALL_TOP:
        if v == 'LV_EF': base = CLIN_BASE
        else: base = CLIN_BASE + ['LV_EF']
        r = fit_logit_inc(d1y, base, v)
        if r is None: continue
        r.update(dict(cohort=cohort_name, var=v, outcome='1y_mortality')); rows.append(r)
    for v in ALL_TOP:
        if v == 'LV_EF': base = CLIN_BASE
        else: base = CLIN_BASE + ['LV_EF']
        r = fit_pois_inc(cohort, base, v)
        if r is None: continue
        r.update(dict(cohort=cohort_name, var=v, outcome='hosp_rate')); rows.append(r)
    for v in ALL_TOP:
        if v == 'LV_EF': base = CLIN_BASE
        else: base = CLIN_BASE + ['LV_EF']
        r = fit_cox_inc(cohort, base, v)
        if r is None: continue
        r.update(dict(cohort=cohort_name, var=v, outcome='full_FU_Cox')); rows.append(r)

res = pd.DataFrame(rows)
piv = res[['cohort','var','outcome','n','p_LR']].copy()
print('\nPer-cohort p_LR for top variables:')
print(piv.pivot_table(index=['var','outcome'], columns='cohort', values='p_LR').round(4).to_string())
res.to_csv('/home/user/dialysis/analysis_outputs/sensitivity_timing.csv', index=False)

# === B. Multiple imputation for top candidates ===
print('\n=== B. SENSITIVITY: MULTIPLE IMPUTATION (m=10, IterativeImputer) ===')
d_prim = cohorts['primary_365d']
d1y = d_prim[d_prim.died_1year.notna()].copy().reset_index(drop=True)

ECHO_FOR_MI = TOP_HOSP + TOP_MORT  # variables to impute
ECHO_FOR_MI = list(dict.fromkeys(ECHO_FOR_MI))
work_cols = CLIN_BASE + ECHO_FOR_MI
sub = d1y[work_cols + ['died_1year','hosp_total','followup_days']].copy()

mi_results_mort = []
mi_results_hosp = []
for m_idx in range(10):
    imp = IterativeImputer(random_state=m_idx, max_iter=20, sample_posterior=True)
    sub_imp = sub.copy()
    sub_imp[work_cols] = imp.fit_transform(sub_imp[work_cols])
    # 1y mortality - inc value of each top var
    for v in ECHO_FOR_MI:
        Xb_df = sub_imp[CLIN_BASE+(['LV_EF'] if v!='LV_EF' else [])].copy()
        Xb = StandardScaler().fit_transform(Xb_df.values)
        xv = sub_imp[[v]].values.astype(float)
        if sub_imp[v].nunique()>5: xv = (xv - xv.mean())/xv.std()
        Xa = np.hstack([Xb, xv])
        ys = sub_imp.died_1year.astype(int).values
        try:
            ma = sm.Logit(ys, sm.add_constant(Xa)).fit(disp=0)
            mi_results_mort.append(dict(m=m_idx, var=v,
                                        beta=ma.params[-1], se=ma.bse[-1],
                                        OR=np.exp(ma.params[-1])))
        except Exception: pass
    # hosp
    sub_h = sub_imp[sub_imp.followup_days>0]
    off = np.log(sub_h.followup_days/365.25)
    for v in ECHO_FOR_MI:
        Xb_df = sub_h[CLIN_BASE+(['LV_EF'] if v!='LV_EF' else [])].copy()
        Xb = StandardScaler().fit_transform(Xb_df.values)
        xv = sub_h[[v]].values.astype(float)
        if sub_h[v].nunique()>5: xv = (xv - xv.mean())/xv.std()
        Xa = np.hstack([Xb, xv])
        try:
            ma = sm.GLM(sub_h.hosp_total.values, sm.add_constant(Xa),
                       family=sm.families.Poisson(), offset=off).fit(cov_type='HC1')
            mi_results_hosp.append(dict(m=m_idx, var=v,
                                       beta=ma.params[-1], se=ma.bse[-1],
                                       IRR=np.exp(ma.params[-1])))
        except Exception: pass

# Rubin's rules pooling
def rubin(df_mi, value_col='beta', se_col='se'):
    rows = []
    for v, g in df_mi.groupby('var'):
        m = len(g)
        Q = g[value_col].mean()
        U = (g[se_col]**2).mean()
        B = g[value_col].var(ddof=1)
        T = U + (1+1/m)*B
        se = np.sqrt(T)
        rows.append(dict(var=v, beta=Q, se=se, exp_est=np.exp(Q),
                        CIlo=np.exp(Q-1.96*se), CIhi=np.exp(Q+1.96*se),
                        p=2*(1 - __import__('scipy').stats.norm.cdf(abs(Q/se))) if se>0 else np.nan))
    return pd.DataFrame(rows).sort_values('p')

mi_mort = pd.DataFrame(mi_results_mort)
mi_hosp = pd.DataFrame(mi_results_hosp)
pooled_mort = rubin(mi_mort)
pooled_hosp = rubin(mi_hosp)
print('\n--- 1y mortality (Rubin pooled) ---')
print(pooled_mort.to_string(index=False))
print('\n--- Hosp rate (Rubin pooled) ---')
print(pooled_hosp.to_string(index=False))
pooled_mort.to_csv('/home/user/dialysis/analysis_outputs/MI_pooled_mortality.csv', index=False)
pooled_hosp.to_csv('/home/user/dialysis/analysis_outputs/MI_pooled_hosp.csv', index=False)

# === C. HFrEF / HFpEF subgroup ===
print('\n=== C. HFrEF (EF<40) vs HFpEF (EF>=50) SUBGROUP ANALYSIS ===')
d_prim = cohorts['primary_365d']
sub_rows=[]
for grp_name, mask in [('HFrEF (EF<40)', d_prim.LV_EF<40),
                       ('HFmrEF (40-49)', (d_prim.LV_EF>=40)&(d_prim.LV_EF<50)),
                       ('HFpEF (>=50)', d_prim.LV_EF>=50)]:
    g = d_prim[mask].copy()
    if len(g) < 50: continue
    print(f'\n  {grp_name}: n={len(g)}, events_1y={int(g.died_1year.sum())}, total_hosp={int(g.hosp_total.sum())}')
    g1y = g[g.died_1year.notna()]
    for v in ALL_TOP:
        if v == 'LV_EF': continue
        rL = fit_logit_inc(g1y, CLIN_BASE+['LV_EF'], v)
        rP = fit_pois_inc(g, CLIN_BASE+['LV_EF'], v)
        if rL is not None:
            rL.update(dict(group=grp_name, var=v, outcome='1y_mort')); sub_rows.append(rL)
        if rP is not None:
            rP.update(dict(group=grp_name, var=v, outcome='hosp_rate')); sub_rows.append(rP)

res_sub = pd.DataFrame(sub_rows)
piv2 = res_sub.pivot_table(index=['var','outcome'], columns='group', values='p_LR').round(4)
print('\nSubgroup p_LR (added to clinical+EF):')
print(piv2.to_string())
res_sub.to_csv('/home/user/dialysis/analysis_outputs/sensitivity_subgroups.csv', index=False)

print('\nDone Stage 4.')
