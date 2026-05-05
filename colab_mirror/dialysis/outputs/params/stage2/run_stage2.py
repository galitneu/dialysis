"""
Stage 2 — Descriptive analysis + model-readiness checks.

Inputs:
  /home/user/dialysis/colab_mirror/dialysis/outputs/params/stage1/  (Stage 1 FIXED v2 outputs)

Outputs:
  /home/user/dialysis/colab_mirror/dialysis/outputs/params/stage2/
  /home/user/dialysis/colab_mirror/dialysis/outputs/params/stage2/plots/

Per agreed decisions:
  - DEC-045: Stage 2 = descriptive + model-readiness only (no models)
  - DEC-046: storage = Drive + GitHub
  - DEC-047: NO p-values in Table 1
  - DEC-048: model-readiness flags are advisory
  - 15-20 plots PNG, including descriptive overall KM (no group comparisons)
  - EPV per outcome
  - Use Stage 1 FIXED v2 with DEC-044 alias mapping
"""
import json
import warnings; warnings.filterwarnings('ignore')
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

S1 = Path('/home/user/dialysis/colab_mirror/dialysis/outputs/params/stage1')
OUT = Path('/home/user/dialysis/colab_mirror/dialysis/outputs/params/stage2')
PLOTS = OUT / 'plots'
OUT.mkdir(parents=True, exist_ok=True)
PLOTS.mkdir(parents=True, exist_ok=True)

print('Stage 2 starting')
print(f'  inputs:  {S1}')
print(f'  outputs: {OUT}')

# =============================================================
# 1. Setup, load, validate
# =============================================================
def load(name):
    return pd.read_csv(S1 / name)

main_df = load('stage1_main_analysis.csv')
sens_df = load('stage1_sensitivity_analysis.csv')
expl_df = load('stage1_exploratory_analysis.csv')
ds_1y = load('stage1_oneyear_mortality.csv')
ds_surv = load('stage1_survival_analysis.csv')
ds_hosp = load('stage1_hospitalization_analysis.csv')

main_pred_list = load('stage1_main_predictor_list.csv').iloc[:,0].tolist()
sens_pred_list = load('stage1_sensitivity_exploratory_predictor_list.csv').iloc[:,0].tolist()
exclusions_log = load('stage1_exclusions_log.csv')
miss_s1 = load('stage1_missingness_report.csv')
cat_counts = load('stage1_categorical_counts_before_after.csv')
echo_timing_summary = load('stage1_echo_to_dialysis_timing_summary.csv')
echo_timing_cats = load('stage1_echo_to_dialysis_timing_categories.csv')
outliers_log = load('stage1_outlier_action_log.csv')
proc_log = load('stage1_variable_processing_log.csv')

run_meta = {
    'run_datetime': datetime.now().isoformat(timespec='seconds'),
    'inputs_dir': str(S1),
    'outputs_dir': str(OUT),
    'stage1_source': 'stage1_prepare_analytic_datasets_FIXED_v2 (DEC-044 alias mapping)',
    'decisions_applied': ['DEC-045','DEC-046','DEC-047','DEC-048','DEC-044'],
}
(OUT/'stage2_run_metadata.json').write_text(json.dumps(run_meta, indent=2))

# =============================================================
# 2. Input validation
# =============================================================
expected = {'stage1_main_analysis': (644, None),
           'stage1_oneyear_mortality': (617, None),
           'stage1_survival_analysis': (644, None),
           'stage1_hospitalization_analysis': (644, None),
           'stage1_sensitivity_analysis': (644, None)}

val_rows = []
for name, df_, exp in [('stage1_main_analysis', main_df, expected['stage1_main_analysis']),
                      ('stage1_oneyear_mortality', ds_1y, expected['stage1_oneyear_mortality']),
                      ('stage1_survival_analysis', ds_surv, expected['stage1_survival_analysis']),
                      ('stage1_hospitalization_analysis', ds_hosp, expected['stage1_hospitalization_analysis']),
                      ('stage1_sensitivity_analysis', sens_df, expected['stage1_sensitivity_analysis'])]:
    val_rows.append({
        'dataset': name,
        'n_rows': len(df_),
        'expected_n_rows': exp[0],
        'matches_expected_n': len(df_) == exp[0],
        'patient_id_present': 'patient_id' in df_.columns,
        'patient_id_unique': df_['patient_id'].is_unique if 'patient_id' in df_.columns else False,
    })
val_df = pd.DataFrame(val_rows)
val_df.to_csv(OUT/'stage2_input_validation.csv', index=False)
print('  input_validation:', dict(val_df['matches_expected_n'].value_counts()))

# =============================================================
# 3. Cohort & outcome summary
# =============================================================
def safe_int(x): return int(x) if pd.notna(x) else 0

cohort_rows = [
    {'dataset': 'main_analysis', 'n': len(main_df), 'description': 'after DEC-040 exclusion'},
    {'dataset': 'one_year_mortality', 'n': len(ds_1y),
     'description': 'died_1year not missing',
     'n_events_1y': safe_int(ds_1y.died_1year.sum()) if 'died_1year' in ds_1y.columns else 0,
     'oneyear_mortality_pct': round(100*ds_1y.died_1year.mean(),2) if 'died_1year' in ds_1y.columns else None},
    {'dataset': 'survival', 'n': len(ds_surv),
     'description': 'event valid + time_to_event>=0',
     'n_events_total': safe_int(ds_surv.event.sum()) if 'event' in ds_surv.columns else 0,
     'pct_events': round(100*ds_surv.event.mean(),2) if 'event' in ds_surv.columns else None,
     'median_followup_days': float(ds_surv.time_to_event_days.median()) if 'time_to_event_days' in ds_surv.columns else None,
     'q1_followup': float(ds_surv.time_to_event_days.quantile(0.25)) if 'time_to_event_days' in ds_surv.columns else None,
     'q3_followup': float(ds_surv.time_to_event_days.quantile(0.75)) if 'time_to_event_days' in ds_surv.columns else None},
    {'dataset': 'hospitalization', 'n': len(ds_hosp),
     'description': 'hosp_total valid + followup_days>0',
     'total_hospitalizations': safe_int(ds_hosp.hosp_total.sum()),
     'mean_hosp_per_patient': round(ds_hosp.hosp_total.mean(),3),
     'median_hosp_per_patient': float(ds_hosp.hosp_total.median()),
     'max_hosp_per_patient': int(ds_hosp.hosp_total.max()),
     'sum_followup_years': round(ds_hosp.followup_years.sum(),2) if 'followup_years' in ds_hosp.columns else None,
     'rate_per_person_year': round(ds_hosp.hosp_total.sum()/ds_hosp.followup_years.sum(), 3) if 'followup_years' in ds_hosp.columns else None},
    {'dataset': 'sensitivity', 'n': len(sens_df), 'description': 'all main + sens predictors'},
]
pd.DataFrame(cohort_rows).to_csv(OUT/'stage2_cohort_summary.csv', index=False)
pd.DataFrame(cohort_rows).to_csv(OUT/'stage2_outcome_summary.csv', index=False)  # same content per workplan
print('  cohort_summary written')

# =============================================================
# 4. Table 1 overall (NO p-values per DEC-047)
# =============================================================
CONT = ['AgeAtFirstHFDate','creatinine-numeric result','GFR','albumin-numeric result',
       'hb-numeric result','crp-numeric result','LV_EF','LeftVentricleEstimatedMassIndex',
       'EstimatedSysPAPressure','MitralInflowPeakEWave','TissueDopplerEERatioSeptal',
       'TissueDopplerEERatioLateral','TissueDopplerEVelositySeptal','TissueDopplerEVelosityLateral',
       'days_echo_to_dialysis']
BIN = ['MI_binary','CABG_binary','IHD_binary','AFIB_binary','HTN_binary',
       'Diabetes mellitus_binary','COPD_binary']
CAT = ['m/f','HD/PD','LACavitySize','ECHO_SPAP',
       'mitral_regurgitation_clin_grouped','tricuspid_regurgitation_clin_grouped']

def describe_continuous(s):
    s = pd.to_numeric(s, errors='coerce')
    return dict(n=int(s.notna().sum()),
               n_missing=int(s.isna().sum()),
               pct_missing=round(100*s.isna().mean(),1),
               mean=round(s.mean(),3) if s.notna().any() else None,
               sd=round(s.std(),3) if s.notna().any() else None,
               median=round(s.median(),3) if s.notna().any() else None,
               q1=round(s.quantile(0.25),3) if s.notna().any() else None,
               q3=round(s.quantile(0.75),3) if s.notna().any() else None,
               min=round(s.min(),3) if s.notna().any() else None,
               max=round(s.max(),3) if s.notna().any() else None)

def describe_categorical(s, levels=None):
    n_total = len(s)
    n_miss = int(s.isna().sum())
    s2 = s.dropna().astype(str)
    counts = s2.value_counts()
    if levels: counts = counts.reindex(levels).fillna(0).astype(int)
    rows = []
    for lvl, n in counts.items():
        rows.append({'level': str(lvl), 'n': int(n), 'pct_of_nonmissing': round(100*n/max(len(s2),1),1)})
    return rows, dict(n_missing=n_miss, pct_missing=round(100*n_miss/n_total,1))

# Table 1 overall
t1_rows = []
for v in CONT:
    if v in main_df.columns:
        d = describe_continuous(main_df[v])
        t1_rows.append({'variable': v, 'type': 'continuous', **d})
for v in BIN:
    if v in main_df.columns:
        d = describe_continuous(main_df[v])
        t1_rows.append({'variable': v, 'type': 'binary', 'n': d['n'],
                       'n_missing': d['n_missing'], 'pct_missing': d['pct_missing'],
                       'n_pos': int(main_df[v].sum()),
                       'pct_pos': round(100*main_df[v].mean(),1)})
for v in CAT:
    if v not in main_df.columns: continue
    rows, m = describe_categorical(main_df[v])
    for r in rows:
        t1_rows.append({'variable': v, 'type': 'categorical', 'level': r['level'],
                       'n_in_level': r['n'], 'pct_of_nonmissing': r['pct_of_nonmissing'],
                       'n_missing': m['n_missing'], 'pct_missing': m['pct_missing']})
pd.DataFrame(t1_rows).to_csv(OUT/'stage2_table1_overall.csv', index=False)
print(f'  table1_overall: {len(t1_rows)} rows')

# =============================================================
# 5. Table 1 BY 1y mortality (descriptive only, NO p-values)
# =============================================================
if 'died_1year' in ds_1y.columns:
    g0 = ds_1y[ds_1y.died_1year == 0]
    g1 = ds_1y[ds_1y.died_1year == 1]
    t1by_rows = []
    n0, n1 = len(g0), len(g1)
    for v in CONT:
        if v not in ds_1y.columns: continue
        d0, d1 = describe_continuous(g0[v]), describe_continuous(g1[v])
        t1by_rows.append({'variable': v, 'type': 'continuous',
                         'group0_n': d0['n'], 'group0_median': d0['median'],
                         'group0_q1': d0['q1'], 'group0_q3': d0['q3'],
                         'group0_pct_missing': d0['pct_missing'],
                         'group1_n': d1['n'], 'group1_median': d1['median'],
                         'group1_q1': d1['q1'], 'group1_q3': d1['q3'],
                         'group1_pct_missing': d1['pct_missing']})
    for v in BIN:
        if v not in ds_1y.columns: continue
        t1by_rows.append({'variable': v, 'type': 'binary',
                         'group0_n_pos': int(g0[v].sum()), 'group0_pct_pos': round(100*g0[v].mean(),1),
                         'group1_n_pos': int(g1[v].sum()), 'group1_pct_pos': round(100*g1[v].mean(),1)})
    for v in CAT:
        if v not in ds_1y.columns: continue
        for grp_label, grp in [('group0', g0), ('group1', g1)]:
            rows, m = describe_categorical(grp[v])
            for r in rows:
                t1by_rows.append({'variable': v, 'type': 'categorical', 'level': r['level'],
                                 'group': grp_label, 'n': r['n'], 'pct_of_nonmissing': r['pct_of_nonmissing']})
    pd.DataFrame(t1by_rows).to_csv(OUT/'stage2_table1_by_oneyear_mortality.csv', index=False)
    print(f'  table1_by_1y_mortality: {len(t1by_rows)} rows (group0={n0}, group1={n1})')

# =============================================================
# 6. Missingness reports (per cohort + flags)
# =============================================================
miss_rows = []
def add_missing(label, df_, vars_):
    for v in vars_:
        if v in df_.columns:
            n_miss = int(df_[v].isna().sum())
            miss_rows.append({'dataset': label, 'variable': v,
                             'n': len(df_), 'n_missing': n_miss,
                             'pct_missing': round(100*n_miss/len(df_),2)})

ALL_PRED = list(set(main_pred_list + sens_pred_list))
add_missing('main_analysis', main_df, ALL_PRED)
add_missing('one_year_mortality', ds_1y, ALL_PRED)
add_missing('survival', ds_surv, ALL_PRED)
add_missing('hospitalization', ds_hosp, ALL_PRED)
add_missing('sensitivity', sens_df, ALL_PRED)
miss_df = pd.DataFrame(miss_rows)
miss_df.to_csv(OUT/'stage2_missingness_by_dataset.csv', index=False)

# Flags
flags_rows = []
for v in ALL_PRED:
    sub = miss_df[miss_df.variable == v]
    if sub.empty: continue
    pct_main = float(sub[sub.dataset == 'main_analysis'].pct_missing.iloc[0]) if not sub[sub.dataset == 'main_analysis'].empty else None
    role = 'main' if v in main_pred_list else 'sensitivity'
    flags_rows.append({'variable': v, 'role': role,
                      'pct_missing_main': pct_main,
                      'over_20': pct_main is not None and pct_main > 20,
                      'over_50': pct_main is not None and pct_main > 50,
                      'flag_for_model_readiness': pct_main is not None and pct_main > 20})
pd.DataFrame(flags_rows).to_csv(OUT/'stage2_missingness_flags.csv', index=False)
print(f'  missingness_by_dataset: {len(miss_df)} rows')

# =============================================================
# 7. Echo timing distribution
# =============================================================
# Use the values in main_df (canonical timing var = days_echo_to_dialysis)
g = pd.to_numeric(main_df['days_echo_to_dialysis'], errors='coerce')
timing_rows = pd.DataFrame([{
    'metric': k, 'value': v
} for k, v in [
    ('n_nonmissing', int(g.notna().sum())),
    ('mean', round(g.mean(),2)),
    ('median', round(g.median(),2)),
    ('sd', round(g.std(),2)),
    ('min', int(g.min())),
    ('q25', int(g.quantile(0.25))),
    ('q75', int(g.quantile(0.75))),
    ('max', int(g.max())),
]])
timing_rows.to_csv(OUT/'stage2_echo_timing_distribution.csv', index=False)

if 'echo_to_dialysis_timing_category' in main_df.columns:
    cnt = main_df.echo_to_dialysis_timing_category.value_counts(dropna=False).reset_index()
    cnt.columns = ['category', 'n']
    cnt['pct'] = round(100*cnt['n']/len(main_df), 2)
    cnt.to_csv(OUT/'stage2_echo_timing_category_counts.csv', index=False)

# Plot histogram
fig, ax = plt.subplots(figsize=(8, 5))
ax.hist(g.dropna(), bins=40, edgecolor='black', alpha=0.7)
ax.axvline(0, color='red', linestyle='--', label='Dialysis start')
ax.set_xlabel('Days from Echo to Dialysis (negative = echo BEFORE dialysis)')
ax.set_ylabel('Number of patients')
ax.set_title(f'Echo-to-Dialysis timing (n={int(g.notna().sum())})')
ax.legend()
plt.tight_layout()
plt.savefig(PLOTS/'stage2_echo_timing_histogram.png', dpi=120)
plt.close()

# =============================================================
# 8. Continuous distributions (with histograms)
# =============================================================
cont_rows = []
for v in CONT:
    if v not in main_df.columns: continue
    s = pd.to_numeric(main_df[v], errors='coerce')
    if s.dropna().empty: continue
    d = describe_continuous(s)
    skew = float(s.skew()) if s.notna().sum() > 2 else None
    cont_rows.append({'variable': v, **d,
                     'skewness': round(skew,3) if skew is not None else None,
                     'flag_high_skew': skew is not None and abs(skew) > 2})
    # Plot
    fig, ax = plt.subplots(figsize=(7,4))
    ax.hist(s.dropna(), bins=30, edgecolor='black', alpha=0.7)
    ax.set_title(f'{v} (n={d["n"]}, miss={d["pct_missing"]}%)')
    ax.set_xlabel(v); ax.set_ylabel('Count')
    plt.tight_layout()
    plt.savefig(PLOTS/f'stage2_hist_{v.replace("/","_").replace(" ","_")}.png', dpi=100)
    plt.close()
pd.DataFrame(cont_rows).to_csv(OUT/'stage2_continuous_distributions.csv', index=False)
print(f'  continuous distributions: {len(cont_rows)} vars')

# =============================================================
# 9. Categorical distributions (with bar plots)
# =============================================================
cat_rows = []
for v in CAT + BIN:
    if v not in main_df.columns: continue
    n_miss = int(main_df[v].isna().sum())
    if v in BIN:
        n_pos = int(main_df[v].sum())
        cat_rows.append({'variable': v, 'level': '1', 'n': n_pos,
                        'pct_of_nonmissing': round(100*n_pos/(len(main_df)-n_miss),1) if n_miss<len(main_df) else None,
                        'pct_missing': round(100*n_miss/len(main_df),1)})
        cat_rows.append({'variable': v, 'level': '0', 'n': len(main_df)-n_miss-n_pos,
                        'pct_of_nonmissing': round(100*(len(main_df)-n_miss-n_pos)/(len(main_df)-n_miss),1) if n_miss<len(main_df) else None,
                        'pct_missing': round(100*n_miss/len(main_df),1)})
    else:
        rows, m = describe_categorical(main_df[v])
        for r in rows:
            cat_rows.append({'variable': v, 'level': r['level'], 'n': r['n'],
                            'pct_of_nonmissing': r['pct_of_nonmissing'],
                            'pct_missing': m['pct_missing']})
        # bar plot
        if rows:
            fig, ax = plt.subplots(figsize=(7,4))
            labs = [r['level'] for r in rows]; ns = [r['n'] for r in rows]
            ax.bar(range(len(labs)), ns)
            ax.set_xticks(range(len(labs)))
            ax.set_xticklabels(labs, rotation=45, ha='right', fontsize=8)
            ax.set_title(f'{v} (miss={m["pct_missing"]}%)')
            plt.tight_layout()
            plt.savefig(PLOTS/f'stage2_bar_{v.replace("/","_").replace(" ","_")}.png', dpi=100)
            plt.close()
pd.DataFrame(cat_rows).to_csv(OUT/'stage2_categorical_distributions.csv', index=False)
print(f'  categorical distributions: {len(cat_rows)} rows')

# =============================================================
# 10. Grouped category stability (after DEC-037 grouping)
# =============================================================
GROUPED_VARS = ['lv_cavity_size_clin_grouped','lv_wall_thickness_clin_grouped',
                'rv_size_clin_grouped','aortic_valve_structure_clin_grouped',
                'aortic_regurgitation_clin_grouped','mitral_regurgitation_clin_grouped',
                'tricuspid_regurgitation_clin_grouped']
stab_rows = []
for v in GROUPED_VARS:
    if v not in main_df.columns: continue
    n_total = len(main_df); n_miss = int(main_df[v].isna().sum())
    counts = main_df[v].value_counts(dropna=False)
    for lvl, n in counts.items():
        pct = round(100*n/n_total, 1)
        stab_rows.append({'variable': v, 'level': str(lvl), 'n': int(n),
                         'pct_of_total': pct,
                         'rare_under_5pct': pct < 5 and pd.notna(lvl),
                         'is_rare_ignored': str(lvl) == 'Rare/ignored',
                         'is_missing': pd.isna(lvl)})
pd.DataFrame(stab_rows).to_csv(OUT/'stage2_grouped_category_stability.csv', index=False)
print(f'  grouped_category_stability: {len(stab_rows)} rows')

# =============================================================
# 11. Correlation matrix + collinearity flags
# =============================================================
NUM_PRED_FOR_CORR = [v for v in CONT if v in main_df.columns]
corr_data = main_df[NUM_PRED_FOR_CORR].apply(pd.to_numeric, errors='coerce')
corr = corr_data.corr(method='spearman')
corr.to_csv(OUT/'stage2_predictor_correlation_matrix.csv')

coll_rows = []
for i, a in enumerate(corr.columns):
    for b in corr.columns[i+1:]:
        r = corr.loc[a, b]
        if pd.isna(r): continue
        flag = 'severe_collinearity' if abs(r) >= 0.85 else ('high_correlation' if abs(r) >= 0.70 else None)
        if flag:
            coll_rows.append({'var1': a, 'var2': b, 'spearman_r': round(r,3), 'flag': flag})
pd.DataFrame(coll_rows).to_csv(OUT/'stage2_collinearity_flags.csv', index=False)

# Heatmap
fig, ax = plt.subplots(figsize=(10,8))
im = ax.imshow(corr.values, cmap='coolwarm', vmin=-1, vmax=1, aspect='auto')
ax.set_xticks(range(len(corr.columns))); ax.set_xticklabels(corr.columns, rotation=90, fontsize=7)
ax.set_yticks(range(len(corr.columns))); ax.set_yticklabels(corr.columns, fontsize=7)
plt.colorbar(im, ax=ax, label='Spearman r')
ax.set_title('Predictor correlations (Spearman, main analysis cohort)')
plt.tight_layout()
plt.savefig(PLOTS/'stage2_correlation_heatmap.png', dpi=120)
plt.close()
print(f'  collinearity flags: {len(coll_rows)}')

# =============================================================
# 12. Clinical overlap flags
# =============================================================
overlap_rows = [
    {'family': 'Kidney function', 'vars': 'creatinine + GFR',
     'note': 'main: creatinine; sensitivity: GFR (per DEC-034)', 'enforced': True},
    {'family': 'Pulmonary pressure', 'vars': 'EstimatedSysPAPressure + ECHO_SPAP',
     'note': 'do not include together; one is numeric, one is categorical of same construct', 'enforced': False},
    {'family': 'LV mass', 'vars': 'LeftVentricleEstimatedMass + LeftVentricleEstimatedMassIndex',
     'note': 'prefer LVMI; main is LVMI per Stage 0', 'enforced': True},
    {'family': 'Timing', 'vars': 'days_echo_to_dialysis + (months variants, gap variant)',
     'note': 'use days_echo_to_dialysis only (DEC-032)', 'enforced': True},
    {'family': 'Outcomes vs predictors', 'vars': 'event/event_1y/hosp_total/hospitalization-count',
     'note': 'never used as predictors (DEC-031)', 'enforced': True},
    {'family': 'EF/systolic function', 'vars': 'LV_EF + LeftVentricleSystolicFunction',
     'note': 'high overlap; LV_EF is benchmark; LeftVentricleSystolicFunction is in sensitivity', 'enforced': True},
    {'family': 'Diastolic function', 'vars': 'TissueDoppler E/e ratio septal/lateral + e velocities',
     'note': 'overlap within Echo: LV diastolic axis; Stage 4 should pick one representative', 'enforced': False},
]
pd.DataFrame(overlap_rows).to_csv(OUT/'stage2_clinical_overlap_flags.csv', index=False)

# =============================================================
# 13. Model readiness per outcome
# =============================================================
n_main = len(main_pred_list)
def epv_block(label, n, n_events, predictors_n):
    epv = (n_events / predictors_n) if predictors_n else None
    rec_max = int(n_events // 10) if n_events else 0
    return {'outcome': label, 'n_cohort': n,
           'n_events': int(n_events),
           'n_candidate_predictors_main': predictors_n,
           'events_per_variable_main_only': round(epv,2) if epv else None,
           'recommended_max_predictors': rec_max,
           'flag_low_epv': (epv is not None and epv < 10),
           'note': 'Conservative rule of thumb: >=10 events per variable.'}

readiness_rows = []
n_1y_events = int(ds_1y.died_1year.sum()) if 'died_1year' in ds_1y.columns else 0
readiness_rows.append(epv_block('one_year_mortality', len(ds_1y), n_1y_events, n_main))
n_surv_events = int(ds_surv.event.sum()) if 'event' in ds_surv.columns else 0
readiness_rows.append(epv_block('survival_full_followup', len(ds_surv), n_surv_events, n_main))

# Hosp NB: compute mean and variance + overdispersion ratio
mean_hosp = float(ds_hosp.hosp_total.mean())
var_hosp = float(ds_hosp.hosp_total.var())
overdispersion = round(var_hosp/mean_hosp, 3) if mean_hosp else None
total_hosp = int(ds_hosp.hosp_total.sum())
sum_pyrs = float(ds_hosp.followup_years.sum()) if 'followup_years' in ds_hosp.columns else None
readiness_rows.append({
    'outcome': 'hospitalization_count_NB',
    'n_cohort': len(ds_hosp),
    'total_hospitalizations': total_hosp,
    'mean_hosp_total': round(mean_hosp,3),
    'var_hosp_total': round(var_hosp,3),
    'overdispersion_ratio_var_over_mean': overdispersion,
    'sum_followup_years': round(sum_pyrs,2) if sum_pyrs else None,
    'rate_per_person_year': round(total_hosp/sum_pyrs, 3) if sum_pyrs else None,
    'n_candidate_predictors_main': n_main,
    'overdispersion_flag': overdispersion is not None and overdispersion > 1.5,
    'candidate_predictor_capacity_note': f'Total events ({total_hosp}); EPV not directly applicable to NB. Aim for parsimonious model. Suggested max predictors ~ {min(int(total_hosp/15), n_main)}',
})
pd.DataFrame(readiness_rows).to_csv(OUT/'stage2_model_readiness_by_outcome.csv', index=False)
print(f'  model readiness: {len(readiness_rows)} outcomes')

# =============================================================
# Descriptive overall KM (no group comparisons, no log-rank)
# =============================================================
from sksurv.nonparametric import kaplan_meier_estimator
mask = ds_surv.event.notna() & ds_surv.time_to_event_days.notna()
times, surv = kaplan_meier_estimator(ds_surv.loc[mask,'event'].astype(bool).values,
                                     ds_surv.loc[mask,'time_to_event_days'].values)
fig, ax = plt.subplots(figsize=(8, 5))
ax.step(times, surv, where='post')
for d in [30, 90, 180, 365, 730]:
    if d <= times.max():
        idx = (times <= d).sum() - 1
        if idx >= 0:
            s_at_d = surv[idx]
            ax.axvline(d, alpha=0.2, color='gray')
            ax.annotate(f'S({d})={s_at_d:.2f}', (d, s_at_d), fontsize=8, ha='left', va='bottom')
ax.set_xlabel('Days from dialysis start')
ax.set_ylabel('Survival probability')
ax.set_title(f'Overall Kaplan-Meier (descriptive only, n={int(mask.sum())}, events={int(ds_surv.loc[mask,"event"].sum())})')
ax.set_ylim(0, 1.02)
plt.tight_layout()
plt.savefig(PLOTS/'stage2_KM_overall_descriptive.png', dpi=120)
plt.close()

# Save KM table
km_df = pd.DataFrame({'time_days': times, 'survival_prob': surv})
km_df.to_csv(OUT/'stage2_KM_overall_descriptive.csv', index=False)

# Hospitalization count distribution plot
fig, ax = plt.subplots(figsize=(7,4))
ds_hosp.hosp_total.value_counts().sort_index().plot(kind='bar', ax=ax)
ax.set_xlabel('Number of hospitalizations'); ax.set_ylabel('Number of patients')
ax.set_title(f'Hospitalization count distribution (n={len(ds_hosp)}, mean={mean_hosp:.2f}, var={var_hosp:.2f})')
plt.tight_layout()
plt.savefig(PLOTS/'stage2_hosp_count_distribution.png', dpi=100)
plt.close()

# =============================================================
# 14. Model-readiness summary report (Markdown)
# =============================================================
report = []
report.append('# Stage 2 — Model-Readiness Report\n')
report.append(f'**Generated:** {run_meta["run_datetime"]}')
report.append(f'**Stage 1 source:** {run_meta["stage1_source"]}')
report.append('\n## Cohort flow\n')
for r in cohort_rows:
    desc = r.get('description','')
    extra = ''
    if 'n_events_1y' in r: extra = f' | events_1y={r["n_events_1y"]} ({r.get("oneyear_mortality_pct")}%)'
    if 'n_events_total' in r: extra = f' | events={r["n_events_total"]} ({r.get("pct_events")}%) | median FU={r.get("median_followup_days")}d'
    if 'total_hospitalizations' in r: extra = f' | total hosp={r["total_hospitalizations"]} | rate={r.get("rate_per_person_year")}/p-y'
    report.append(f'- **{r["dataset"]}**: n={r["n"]} ({desc}){extra}')

report.append('\n## Decisions applied\n')
report.append('- DEC-044: alias mapping for MR/TR/AR labels; merged correctly.')
report.append('- DEC-045..048: this stage is descriptive + model-readiness only.')
report.append('- DEC-047: NO p-values in Table 1.')

report.append('\n## Missingness flags (vars with >20% missing in main analysis)')
flagged = pd.DataFrame(flags_rows)
flagged_high = flagged[flagged.over_20]
if len(flagged_high):
    report.append(f'\n{flagged_high.to_string(index=False)}')
else:
    report.append('\n_No main predictors with >20% missing._')

report.append('\n## Echo timing distribution (main cohort)')
report.append(f'- median {round(g.median(),1)}d, IQR ({int(g.quantile(0.25))}, {int(g.quantile(0.75))})')
report.append(f'- range [{int(g.min())}, {int(g.max())}]')

report.append('\n## Outliers (from Stage 1 DEC-030)')
if len(outliers_log):
    report.append(f'\n{outliers_log[["patient_id","variable","original_value","action"]].to_string(index=False)}')
else:
    report.append('\n_No outliers flagged in Stage 1._')

report.append('\n## Collinearity flags (Spearman |r| ≥ 0.70)')
if len(coll_rows):
    report.append(f'\n{pd.DataFrame(coll_rows).to_string(index=False)}')
else:
    report.append('\n_No high-correlation pairs among main continuous predictors._')

report.append('\n## Clinical overlap flags (advisory)')
report.append(pd.DataFrame(overlap_rows).to_string(index=False))

report.append('\n## Model readiness per outcome')
report.append(pd.DataFrame(readiness_rows).to_string(index=False))

report.append('\n## Open issues / decisions needed before Stage 3')
report.append('- OPEN-002: confirm administrative censor date (working: 2025-08-16).')
report.append('- Stage 4 candidate selection: confirm one representative per axis.')

report.append('\n## Outputs (this stage)\n')
for f in sorted(OUT.glob('*')):
    if f.is_file():
        report.append(f'- `{f.name}`')
report.append('\n## Plots (this stage)\n')
for f in sorted(PLOTS.glob('*')):
    if f.is_file():
        report.append(f'- `plots/{f.name}`')

(OUT/'stage2_model_readiness_report.md').write_text('\n'.join(report))
print('\nStage 2 complete.')
print(f'Files in {OUT}: {len(list(OUT.glob("*")))}')
print(f'Plots: {len(list(PLOTS.glob("*")))}')
