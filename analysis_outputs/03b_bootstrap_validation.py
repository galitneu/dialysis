"""
STAGE 3b - Lean bootstrap optimism correction (200 reps)
For both BASE clinical+EF and FULL clinical+EF+echo (LASSO-tuned).
"""
import sys
import warnings; warnings.filterwarnings('ignore')
import numpy as np, pandas as pd
import statsmodels.api as sm
from sklearn.metrics import roc_auc_score
from sklearn.linear_model import LogisticRegression
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

d1y = d[d.died_1year.notna()].copy().reset_index(drop=True)
y = d1y.died_1year.astype(int).values

def design(df, cols):
    X = df[cols].copy()
    for c in cols:
        if X[c].isna().any():
            X[c] = X[c].fillna(X[c].median())
    return X

# Build BASE design and FULL design
Xb_df = design(d1y, CLIN_BASE+['LV_EF']).values
Xf_df = design(d1y, CLIN_BASE+ECHO_NUM+ECHO_ORD).values  # include LV_EF too

print(f'Cohort: n={len(y)}, events={y.sum()}', flush=True)
print(f'Base p={Xb_df.shape[1]}, Full p={Xf_df.shape[1]}', flush=True)

# Fixed C from previous Stage 3 LASSO output: best C=0.16
C_LASSO = 0.16

def fit_apparent_auc_base(X, y):
    sc = StandardScaler().fit(X); Xz = sc.transform(X)
    m = sm.Logit(y, sm.add_constant(Xz)).fit(disp=0)
    p = m.predict(sm.add_constant(Xz))
    return roc_auc_score(y, p), (sc, m)

def fit_apparent_auc_full(X, y, C=C_LASSO):
    sc = StandardScaler().fit(X); Xz = sc.transform(X)
    clf = LogisticRegression(C=C, penalty='l1', solver='saga', max_iter=10000).fit(Xz, y)
    p = clf.predict_proba(Xz)[:,1]
    return roc_auc_score(y, p), (sc, clf)

def predict_base(model_pack, X):
    sc, m = model_pack
    Xz = sc.transform(X)
    return m.predict(sm.add_constant(Xz))

def predict_full(model_pack, X):
    sc, clf = model_pack
    Xz = sc.transform(X)
    return clf.predict_proba(Xz)[:,1]

print('\nBootstrap optimism correction, n_boot=200...', flush=True)
auc_b_app, _ = fit_apparent_auc_base(Xb_df, y)
auc_f_app, _ = fit_apparent_auc_full(Xf_df, y)
print(f'Apparent AUC base={auc_b_app:.4f}, full={auc_f_app:.4f}', flush=True)

n_boot = 200
opt_b, opt_f = [], []
rng = np.random.default_rng(42)
for b in range(n_boot):
    idx = rng.integers(0, len(y), len(y))
    yb = y[idx]
    if yb.sum() < 5 or yb.sum() > len(y)-5:
        continue
    Xb_b = Xb_df[idx]; Xf_b = Xf_df[idx]
    try:
        a1, mp1 = fit_apparent_auc_base(Xb_b, yb)
        a2, mp2 = fit_apparent_auc_full(Xf_b, yb, C=C_LASSO)
        # apply to original
        p1 = predict_base(mp1, Xb_df); p2 = predict_full(mp2, Xf_df)
        a1_orig = roc_auc_score(y, p1); a2_orig = roc_auc_score(y, p2)
        opt_b.append(a1 - a1_orig)
        opt_f.append(a2 - a2_orig)
    except Exception as e:
        continue
    if (b+1) % 50 == 0:
        print(f'  done {b+1}/{n_boot}', flush=True)

opt_b_mean = np.mean(opt_b); opt_f_mean = np.mean(opt_f)
print('\n=== RESULTS ===', flush=True)
print(f'BASE clinical+EF:    apparent AUC = {auc_b_app:.4f}, optimism = {opt_b_mean:.4f}, '
      f'corrected AUC = {auc_b_app - opt_b_mean:.4f} ({len(opt_b)} valid boot iters)')
print(f'FULL clinical+echo:  apparent AUC = {auc_f_app:.4f}, optimism = {opt_f_mean:.4f}, '
      f'corrected AUC = {auc_f_app - opt_f_mean:.4f} ({len(opt_f)} valid boot iters)')
print(f'>>> CORRECTED ΔAUC = {(auc_f_app-opt_f_mean) - (auc_b_app-opt_b_mean):+.4f}')
print(f'>>> APPARENT  ΔAUC = {auc_f_app - auc_b_app:+.4f}')

# Also estimate 95% CI of optimism via bootstrap percentile of opt_f - opt_b
delta_app = auc_f_app - auc_b_app
delta_corr = (auc_f_app - opt_f_mean) - (auc_b_app - opt_b_mean)

pd.DataFrame({'metric':['AUC_apparent_base','AUC_apparent_full','optimism_base','optimism_full',
                        'AUC_corrected_base','AUC_corrected_full','delta_AUC_apparent','delta_AUC_corrected'],
              'value':[auc_b_app, auc_f_app, opt_b_mean, opt_f_mean,
                      auc_b_app - opt_b_mean, auc_f_app - opt_f_mean,
                      delta_app, delta_corr]}).to_csv(
    '/home/user/dialysis/analysis_outputs/bootstrap_validation.csv', index=False)
print('\nSaved bootstrap_validation.csv', flush=True)
