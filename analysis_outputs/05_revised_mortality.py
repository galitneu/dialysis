"""
STAGE 5 - REVISED MORTALITY ANALYSIS
Addresses critical reviewer comment: include e' velocities (lateral, septal) which
I previously omitted, and treat TR categorically. Also reproduce the parsimonious
base used by the comparator model: age + sex + creatinine + echo_to_dialysis_days.
"""
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
import statsmodels.api as sm
from statsmodels.duration.hazard_regression import PHReg
from sksurv.metrics import concordance_index_censored
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler
from scipy.stats import chi2

np.random.seed(42)
d = pd.read_csv('/home/user/dialysis/analysis_outputs/primary_cohort.csv')

print(f'Cohort: n={len(d)}', flush=True)

# Confirm variables exist
for v in ['TissueDopplerEVelositySeptal','TissueDopplerEVelosityLateral']:
    print(f'  {v}: missing={d[v].isna().sum()} ({100*d[v].isna().mean():.1f}%), '
          f'mean={d[v].mean():.2f}, median={d[v].median():.2f}', flush=True)

# === A) Univariable on full follow-up Cox for the previously-omitted e' velocities ===
T = d.time_to_event_days.values; E = d.event.astype(int).values

def cox_univ(d, var):
    sub = d[[var]].dropna().copy()
    Tt = T[sub.index]; Ee = E[sub.index]
    if len(sub)<50: return None
    x = sub[var].values.astype(float)
    if sub[var].nunique()>5: x=(x-x.mean())/x.std()
    try:
        m = PHReg(Tt, x.reshape(-1,1), status=Ee).fit()
        return dict(var=var, n=len(sub), events=int(Ee.sum()),
                    HR_per_SD=float(np.exp(m.params[0])),
                    CIlo=float(np.exp(m.conf_int()[0,0])),
                    CIhi=float(np.exp(m.conf_int()[0,1])),
                    p=float(m.pvalues[0]))
    except Exception as e: return dict(var=var, error=str(e))

print('\n=== A. UNIVARIABLE Cox (full FU) for the omitted e\' velocities ===')
for v in ['TissueDopplerEVelositySeptal','TissueDopplerEVelosityLateral']:
    print(' ', cox_univ(d, v))

# Same for 1y mortality logistic
def logit_univ(d, var):
    sub = d[d.died_1year.notna() & d[var].notna()].copy()
    if len(sub)<50: return None
    x = sub[var].values.astype(float)
    if sub[var].nunique()>5: x=(x-x.mean())/x.std()
    try:
        m = sm.Logit(sub.died_1year.astype(int).values, sm.add_constant(x.reshape(-1,1))).fit(disp=0)
        auc = roc_auc_score(sub.died_1year.values, m.predict(sm.add_constant(x.reshape(-1,1))))
        return dict(var=var, n=len(sub), events=int(sub.died_1year.sum()),
                    OR_per_SD=float(np.exp(m.params[1])),
                    CIlo=float(np.exp(m.conf_int()[1,0])),
                    CIhi=float(np.exp(m.conf_int()[1,1])),
                    p=float(m.pvalues[1]), AUC=auc)
    except Exception as e: return dict(var=var, error=str(e))

print('\n=== B. UNIVARIABLE LOGIT (1y mort) for the omitted e\' velocities ===')
for v in ['TissueDopplerEVelositySeptal','TissueDopplerEVelosityLateral']:
    print(' ', logit_univ(d, v))

# === C) Incremental over (1) full base (mine) and (2) parsimonious base (theirs)
def design(df, cols):
    X = df[cols].copy()
    for c in cols:
        if X[c].isna().any(): X[c] = X[c].fillna(X[c].median())
    return X

CLIN_FULL = ['AgeAtFirstHFDate','sex_male','HD_binary','IHD_binary','AFIB_binary',
             'Diabetes mellitus_binary','HTN_binary','COPD_binary','MI_binary','CABG_binary',
             'albumin-numeric result','creatinine-numeric result','GFR',
             'hb-numeric result','crp-numeric result']
CLIN_PARS = ['AgeAtFirstHFDate','sex_male','creatinine-numeric result','echo_to_dialysis_days']

def cox_inc(df, base, addv, T_arr, E_arr):
    keep = base + [addv]
    sub = df[keep].dropna(subset=[addv]).copy()
    for c in base:
        if sub[c].isna().any(): sub[c] = sub[c].fillna(sub[c].median())
    if len(sub)<50: return None
    Tt = T_arr[sub.index]; Ee = E_arr[sub.index]
    Xb_arr = StandardScaler().fit_transform(sub[base].values)
    xv = sub[[addv]].values.astype(float)
    if sub[addv].nunique()>5: xv=(xv-xv.mean())/xv.std()
    Xa_arr = np.hstack([Xb_arr, xv])
    try:
        mb = PHReg(Tt, Xb_arr, status=Ee).fit()
        ma = PHReg(Tt, Xa_arr, status=Ee).fit()
        LR = 2*(ma.llf - mb.llf); pLR = 1 - chi2.cdf(max(LR,0), df=1)
        risk_b = (Xb_arr @ mb.params).flatten()
        risk_a = (Xa_arr @ ma.params).flatten()
        Cb = concordance_index_censored(Ee.astype(bool), Tt, risk_b)[0]
        Ca = concordance_index_censored(Ee.astype(bool), Tt, risk_a)[0]
        return dict(n=len(sub), events=int(Ee.sum()),
                    HR=float(np.exp(ma.params[-1])),
                    CIlo=float(np.exp(ma.conf_int()[-1,0])),
                    CIhi=float(np.exp(ma.conf_int()[-1,1])),
                    p=float(ma.pvalues[-1]),
                    LR_chi2=LR, p_LR=pLR, C_base=Cb, C_full=Ca, dC=Ca-Cb)
    except Exception as e: return None

def logit_inc(df, base, addv):
    keep = base + [addv]
    sub = df[keep + ['died_1year']].dropna(subset=[addv,'died_1year']).copy()
    for c in base:
        if sub[c].isna().any(): sub[c]=sub[c].fillna(sub[c].median())
    if len(sub)<50: return None
    Xb_arr = StandardScaler().fit_transform(sub[base].values)
    xv = sub[[addv]].values.astype(float)
    if sub[addv].nunique()>5: xv=(xv-xv.mean())/xv.std()
    Xa_arr = np.hstack([Xb_arr, xv])
    ys = sub.died_1year.astype(int).values
    try:
        mb = sm.Logit(ys, sm.add_constant(Xb_arr)).fit(disp=0)
        ma = sm.Logit(ys, sm.add_constant(Xa_arr)).fit(disp=0)
        LR=2*(ma.llf-mb.llf); pLR=1-chi2.cdf(max(LR,0),df=1)
        Ab = roc_auc_score(ys, mb.predict(sm.add_constant(Xb_arr)))
        Aa = roc_auc_score(ys, ma.predict(sm.add_constant(Xa_arr)))
        return dict(n=len(sub), events=int(ys.sum()),
                    OR=float(np.exp(ma.params[-1])),
                    CIlo=float(np.exp(ma.conf_int()[-1,0])),
                    CIhi=float(np.exp(ma.conf_int()[-1,1])),
                    p=float(ma.pvalues[-1]), p_LR=pLR,
                    AUC_base=Ab, AUC_full=Aa, dAUC=Aa-Ab)
    except Exception as e: return None

# Test the OMITTED e' velocities + the INCLUDED EeRatio family
TARGETS = ['TissueDopplerEVelositySeptal','TissueDopplerEVelosityLateral',  # omitted before
           'TissueDopplerEERatioLateral','TissueDopplerEERatioSeptal','EeRatio_avg',  # included
           'TricuspidRegurgitation_ord','LV_EF']  # references

print('\n=== C1. INCREMENTAL Cox (full FU) over PARSIMONIOUS base (their base) ===')
print('Base: age + sex + creatinine + echo_to_dialysis_days')
rows=[]
for v in TARGETS:
    r = cox_inc(d, CLIN_PARS+['LV_EF'] if v!='LV_EF' else CLIN_PARS, v, T, E)
    if r: r.update(dict(var=v)); rows.append(r)
df_pars = pd.DataFrame(rows).sort_values('p_LR')
print(df_pars.to_string(index=False))

print('\n=== C2. INCREMENTAL Cox (full FU) over FULL base (my base) ===')
rows=[]
for v in TARGETS:
    r = cox_inc(d, CLIN_FULL+['LV_EF'] if v!='LV_EF' else CLIN_FULL, v, T, E)
    if r: r.update(dict(var=v)); rows.append(r)
df_full = pd.DataFrame(rows).sort_values('p_LR')
print(df_full.to_string(index=False))

# Now 1y mortality
print('\n=== C3. INCREMENTAL Logit (1y mort) over PARSIMONIOUS base ===')
rows=[]
for v in TARGETS:
    r = logit_inc(d, CLIN_PARS+['LV_EF'] if v!='LV_EF' else CLIN_PARS, v)
    if r: r.update(dict(var=v)); rows.append(r)
print(pd.DataFrame(rows).sort_values('p_LR').to_string(index=False))

print('\n=== C4. INCREMENTAL Logit (1y mort) over FULL base (my base) ===')
rows=[]
for v in TARGETS:
    r = logit_inc(d, CLIN_FULL+['LV_EF'] if v!='LV_EF' else CLIN_FULL, v)
    if r: r.update(dict(var=v)); rows.append(r)
print(pd.DataFrame(rows).sort_values('p_LR').to_string(index=False))

# === D) TR as CATEGORICAL block (test their finding) ===
print('\n=== D. TR as CATEGORICAL BLOCK test (Trivial=ref) ===')
TR_CATS = ['Mild (I)','Mild-to-moderate (I-II)','Moderate (II)',
           'Moderately-severe (III)','Severe (IV)']

def cat_block_test(df, base_cols, cat_var, ref_cat='Trivial', T_arr=None, E_arr=None, outcome='cox'):
    sub = df[base_cols + [cat_var, 'died_1year' if outcome=='logit' else 'event']].dropna(subset=[cat_var]).copy()
    sub = sub[sub[cat_var]!='No Value']
    sub = sub[sub[cat_var].isin([ref_cat]+TR_CATS)]
    for c in base_cols:
        if sub[c].isna().any(): sub[c]=sub[c].fillna(sub[c].median())
    if len(sub)<50: return None
    # build dummies
    dummies = pd.get_dummies(sub[cat_var], prefix=cat_var, drop_first=False)
    if f'{cat_var}_{ref_cat}' in dummies.columns:
        dummies = dummies.drop(columns=f'{cat_var}_{ref_cat}')
    Xb_arr = StandardScaler().fit_transform(sub[base_cols].values)
    Xa_arr = np.hstack([Xb_arr, dummies.values.astype(float)])
    n_dummy = dummies.shape[1]
    if outcome=='cox':
        Tt = T_arr[sub.index]; Ee = E_arr[sub.index]
        if len(sub)<50: return None
        try:
            mb = PHReg(Tt, Xb_arr, status=Ee).fit()
            ma = PHReg(Tt, Xa_arr, status=Ee).fit()
            LR=2*(ma.llf-mb.llf); pLR=1-chi2.cdf(max(LR,0),df=n_dummy)
            cats = list(dummies.columns)
            HR_per_cat = {c:float(np.exp(ma.params[len(base_cols)+i])) for i,c in enumerate(cats)}
            CI_per_cat = {c:(float(np.exp(ma.conf_int()[len(base_cols)+i,0])),
                            float(np.exp(ma.conf_int()[len(base_cols)+i,1]))) for i,c in enumerate(cats)}
            p_per_cat = {c:float(ma.pvalues[len(base_cols)+i]) for i,c in enumerate(cats)}
            return dict(n=len(sub), events=int(Ee.sum()), LR=LR, df=n_dummy, p_block=pLR,
                       HR=HR_per_cat, CI=CI_per_cat, p_per=p_per_cat)
        except Exception as e: return dict(error=str(e))
    else:
        ys = sub.died_1year.astype(int).values
        try:
            mb = sm.Logit(ys, sm.add_constant(Xb_arr)).fit(disp=0)
            ma = sm.Logit(ys, sm.add_constant(Xa_arr)).fit(disp=0)
            LR=2*(ma.llf-mb.llf); pLR=1-chi2.cdf(max(LR,0),df=n_dummy)
            cats = list(dummies.columns)
            OR_per_cat = {c:float(np.exp(ma.params[1+len(base_cols)+i])) for i,c in enumerate(cats)}
            return dict(n=len(sub), events=int(ys.sum()), LR=LR, df=n_dummy, p_block=pLR,
                       OR=OR_per_cat)
        except Exception as e: return dict(error=str(e))

# TR categorical, Cox, full base + EF
print('\n--- TR categorical, Cox full FU, base = full clinical + LV_EF ---')
r = cat_block_test(d, CLIN_FULL+['LV_EF'], 'TricuspidRegurgitation', T_arr=T, E_arr=E, outcome='cox')
if r and 'error' not in r:
    print(f'  n={r["n"]}, events={r["events"]}, BLOCK LR={r["LR"]:.2f}, df={r["df"]}, p_block={r["p_block"]:.4f}')
    for c in r["HR"]:
        cat_name = c.replace('TricuspidRegurgitation_','')
        print(f'    {cat_name}: HR={r["HR"][c]:.3f} ({r["CI"][c][0]:.3f}-{r["CI"][c][1]:.3f}), p={r["p_per"][c]:.4f}')

print('\n--- TR categorical, Cox full FU, parsimonious base + EF ---')
r = cat_block_test(d, CLIN_PARS+['LV_EF'], 'TricuspidRegurgitation', T_arr=T, E_arr=E, outcome='cox')
if r and 'error' not in r:
    print(f'  n={r["n"]}, events={r["events"]}, BLOCK LR={r["LR"]:.2f}, df={r["df"]}, p_block={r["p_block"]:.4f}')
    for c in r["HR"]:
        cat_name = c.replace('TricuspidRegurgitation_','')
        print(f'    {cat_name}: HR={r["HR"][c]:.3f} ({r["CI"][c][0]:.3f}-{r["CI"][c][1]:.3f}), p={r["p_per"][c]:.4f}')

# === E) FINAL revised mortality model: clinical+EF + e' lateral + TR (categorical) ===
print('\n=== E. REVISED FINAL MORTALITY MODEL: clinical+EF+e\'lateral+TR_cat (Cox full FU) ===')
sub = d[CLIN_FULL+['LV_EF','TissueDopplerEVelosityLateral','TricuspidRegurgitation']].copy()
sub = sub[sub.TricuspidRegurgitation.isin(['Trivial']+TR_CATS) & sub.TissueDopplerEVelosityLateral.notna()]
for c in CLIN_FULL:
    if sub[c].isna().any(): sub[c]=sub[c].fillna(sub[c].median())
Tt = T[sub.index]; Ee = E[sub.index]
print(f'n={len(sub)}, events={int(Ee.sum())}')
Xb_arr = StandardScaler().fit_transform(sub[CLIN_FULL+['LV_EF']].values)
xe = ((sub.TissueDopplerEVelosityLateral - sub.TissueDopplerEVelosityLateral.mean())
      / sub.TissueDopplerEVelosityLateral.std()).values.reshape(-1,1)
tr_dum = pd.get_dummies(sub.TricuspidRegurgitation, prefix='TR').drop(columns='TR_Trivial')
Xa_arr = np.hstack([Xb_arr, xe, tr_dum.values.astype(float)])
mb = PHReg(Tt, Xb_arr, status=Ee).fit()
ma = PHReg(Tt, Xa_arr, status=Ee).fit()
LR = 2*(ma.llf-mb.llf); pLR = 1-chi2.cdf(LR, df=1+tr_dum.shape[1])
cb = concordance_index_censored(Ee.astype(bool), Tt, (Xb_arr@mb.params).flatten())[0]
ca = concordance_index_censored(Ee.astype(bool), Tt, (Xa_arr@ma.params).flatten())[0]
print(f'  Block LR (e\'lat + 5xTR cat) = {LR:.2f} on df={1+tr_dum.shape[1]}, p={pLR:.4e}')
print(f'  C-index: base={cb:.4f}, full={ca:.4f}, ΔC={ca-cb:+.4f}')
print(f'  e\' lateral HR per SD = {np.exp(ma.params[len(CLIN_FULL+["LV_EF"])]):.3f}, '
      f'p={ma.pvalues[len(CLIN_FULL+["LV_EF"])]:.4f}')

# === F) Bootstrap optimism for the revised mortality model ===
print('\n=== F. Bootstrap optimism for revised mortality model (Cox C-index) ===')
n=len(Tt)
rng = np.random.default_rng(42)
opt_b=[]; opt_a=[]
n_boot=200
Xb_full = sub[CLIN_FULL+['LV_EF']].values
xe_full = sub.TissueDopplerEVelosityLateral.values.reshape(-1,1)
tr_full = tr_dum.values.astype(float)

for b in range(n_boot):
    idx = rng.integers(0, n, n)
    if E[sub.index][idx].sum() < 10: continue
    try:
        Xb_bs = StandardScaler().fit_transform(Xb_full[idx])
        xe_bs = ((xe_full[idx]-xe_full[idx].mean())/xe_full[idx].std())
        Xa_bs = np.hstack([Xb_bs, xe_bs, tr_full[idx]])
        Tb = Tt[idx]; Eb = Ee[idx]
        mb_b = PHReg(Tb, Xb_bs, status=Eb).fit()
        ma_b = PHReg(Tb, Xa_bs, status=Eb).fit()
        # apparent on bootstrap
        cb_in = concordance_index_censored(Eb.astype(bool), Tb, (Xb_bs@mb_b.params).flatten())[0]
        ca_in = concordance_index_censored(Eb.astype(bool), Tb, (Xa_bs@ma_b.params).flatten())[0]
        # apply to original
        Xb_z = StandardScaler().fit(Xb_full[idx]).transform(Xb_full)
        xe_z = (xe_full - xe_full[idx].mean())/xe_full[idx].std()
        Xa_z = np.hstack([Xb_z, xe_z, tr_full])
        cb_out = concordance_index_censored(Ee.astype(bool), Tt, (Xb_z@mb_b.params).flatten())[0]
        ca_out = concordance_index_censored(Ee.astype(bool), Tt, (Xa_z@ma_b.params).flatten())[0]
        opt_b.append(cb_in - cb_out); opt_a.append(ca_in - ca_out)
    except Exception: continue

opt_b_m = np.mean(opt_b); opt_a_m = np.mean(opt_a)
print(f'  Apparent C: base={cb:.4f}, full={ca:.4f}')
print(f'  Optimism:   base={opt_b_m:.4f} (n={len(opt_b)}), full={opt_a_m:.4f}')
print(f'  Corrected C: base={cb-opt_b_m:.4f}, full={ca-opt_a_m:.4f}')
print(f'  >>> Corrected ΔC = {(ca-opt_a_m)-(cb-opt_b_m):+.4f}')
print(f'  >>> Apparent  ΔC = {ca-cb:+.4f}')

print('\nDone Stage 5.')
