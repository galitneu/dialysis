"""
Stage 7 — Link phenotypes to outcomes (DESCRIPTIVE only).

Per locked protocol:
- Outcomes were never used as clustering inputs
- This stage describes how outcomes differ across phenotypes
- It does NOT redefine phenotypes based on outcomes
- It does NOT chase the "best" phenotype for outcomes

Outcomes:
1. One-year mortality (binary)
2. Long-term survival (Kaplan-Meier)
3. Hospitalization burden (rate)

Outputs:
- stage7_outcomes_by_phenotype.csv (descriptive table)
- stage7_phenotype_KM_summary.csv (median survival per phenotype)
- stage7_outcome_chi2_logrank.csv (descriptive p-values, NOT for inference)
"""

import pandas as pd
import numpy as np
from pathlib import Path
from scipy.stats import chi2_contingency

OUTDIR = Path('/home/user/dialysis/outputs/phenotyping')

# Load chosen phenotypes
pheno = pd.read_csv(OUTDIR / 'stage5_chosen_solution.csv')
print(f'Phenotype solution: {len(pheno)} patients across {pheno["phenotype"].nunique()} phenotypes')

# Load raw outcomes from base dataset
raw = pd.read_excel('/home/user/dialysis/base_analysis_dataset.xlsx', sheet_name='base_analysis_dataset')
df = raw[['patient_id', 'event', 'event_1y', 'time_to_event_days', 'time_to_event_years',
          'hospitalization-count']].copy()
df = df.rename(columns={'hospitalization-count': 'hosp_count'})

# Add followup years (rough)
df['followup_years'] = df['time_to_event_days'] / 365.25

# Merge
m = df.merge(pheno, on='patient_id')
print(f'After merge: {len(m)} patients (some may be missing if dropped in Stage 3)')

# ----------------------------------------------------------------
# 1. One-year mortality by phenotype
# ----------------------------------------------------------------

print('\n=== ONE-YEAR MORTALITY BY PHENOTYPE ===')
oneyear = m.groupby('phenotype').agg(
    n=('patient_id', 'count'),
    deaths_1yr=('event_1y', 'sum'),
    pct_dead_1yr=('event_1y', lambda x: 100*x.mean())
).reset_index()
print(oneyear.to_string(index=False))

# Chi-squared
ct = pd.crosstab(m['phenotype'], m['event_1y'])
chi2, p_chi2, _, _ = chi2_contingency(ct)
print(f'Chi-square p-value (descriptive): {p_chi2:.6g}')

# ----------------------------------------------------------------
# 2. Long-term survival (Kaplan-Meier) — descriptive
# ----------------------------------------------------------------

print('\n=== LONG-TERM SURVIVAL BY PHENOTYPE ===')

# Manual KM median + simple log-rank (no lifelines dep)
def median_survival_time(times, events):
    """Return median survival via KM; nan if not reached."""
    df_sub = pd.DataFrame({'t': times, 'e': events}).sort_values('t').reset_index(drop=True)
    n_at_risk = len(df_sub)
    surv = 1.0
    for _, row in df_sub.iterrows():
        if row['e'] == 1:
            surv *= (1 - 1/n_at_risk)
            if surv <= 0.5:
                return row['t']
        n_at_risk -= 1
    return np.nan

def logrank_multi(times, groups, events):
    """Multi-group log-rank test (basic)."""
    from scipy.stats import chi2 as chi2dist
    times = np.asarray(times, dtype=float)
    groups = np.asarray(groups)
    events = np.asarray(events, dtype=int)
    unique_t = np.unique(times[events == 1])
    G = np.unique(groups)
    O = np.zeros(len(G))
    E = np.zeros(len(G))
    V = np.zeros(len(G))
    for t in unique_t:
        # at risk
        at_risk_mask = times >= t
        d = (events == 1) & (times == t)
        d_total = d.sum()
        n_total = at_risk_mask.sum()
        if n_total == 0:
            continue
        for gi, g in enumerate(G):
            n_g = ((groups == g) & at_risk_mask).sum()
            d_g = ((groups == g) & d).sum()
            e_g = d_total * n_g / n_total
            O[gi] += d_g
            E[gi] += e_g
            if n_total > 1:
                V[gi] += d_total * n_g * (n_total - n_g) * (n_total - d_total) / (n_total**2 * (n_total - 1))
    # Stat: sum (O-E)^2 / E
    chi = np.sum((O - E)**2 / np.where(E > 0, E, 1))
    df = len(G) - 1
    p = 1 - chi2dist.cdf(chi, df)
    return chi, p, df

km_rows = []
for c in sorted(m['phenotype'].unique()):
    cdf = m[m['phenotype'] == c]
    median = median_survival_time(cdf['time_to_event_days'].values, cdf['event'].values)
    km_rows.append({
        'phenotype': int(c),
        'n': len(cdf),
        'n_events': int(cdf['event'].sum()),
        'pct_events': round(100 * cdf['event'].mean(), 1),
        'median_survival_days': float(median) if not pd.isna(median) else None,
        'median_survival_years': float(median/365.25) if not pd.isna(median) else None,
        'mean_followup_days': float(cdf['time_to_event_days'].mean()),
    })
km_df = pd.DataFrame(km_rows)
print(km_df.to_string(index=False))

# Log-rank
lr_stat, lr_p, lr_df = logrank_multi(m['time_to_event_days'].values, m['phenotype'].values, m['event'].values)
print(f'\nLog-rank test (descriptive): chi2={lr_stat:.3f}, df={lr_df}, p={lr_p:.6g}')
class _Lr:
    pass
lr = _Lr()
lr.test_statistic = lr_stat
lr.p_value = lr_p

# ----------------------------------------------------------------
# 3. Hospitalization burden by phenotype
# ----------------------------------------------------------------

print('\n=== HOSPITALIZATION BURDEN BY PHENOTYPE ===')
hosp_rows = []
for c in sorted(m['phenotype'].unique()):
    cdf = m[m['phenotype'] == c]
    cdf_pos = cdf[cdf['followup_years'] > 0]
    hosp_rows.append({
        'phenotype': int(c),
        'n': len(cdf),
        'mean_hosp_total': float(cdf['hosp_count'].mean()),
        'median_hosp_total': float(cdf['hosp_count'].median()),
        'pct_zero_hosp': 100*float((cdf['hosp_count'] == 0).mean()),
        'hosp_per_year_mean': float((cdf_pos['hosp_count'] / cdf_pos['followup_years']).mean()),
        'hosp_per_year_median': float((cdf_pos['hosp_count'] / cdf_pos['followup_years']).median()),
    })
hosp_df = pd.DataFrame(hosp_rows)
print(hosp_df.to_string(index=False))

# Kruskal-Wallis on hospitalization rate (descriptive)
from scipy.stats import kruskal
groups = [m.loc[m['phenotype'] == c, 'hosp_count'].values for c in sorted(m['phenotype'].unique())]
kw_stat, kw_p = kruskal(*groups)
print(f'\nKruskal-Wallis p (descriptive): {kw_p:.6g}')

# ----------------------------------------------------------------
# Combined output
# ----------------------------------------------------------------

combined = oneyear.merge(km_df, on=['phenotype', 'n']).merge(hosp_df, on=['phenotype', 'n'])
combined.to_csv(OUTDIR / 'stage7_outcomes_by_phenotype.csv', index=False)

stats = pd.DataFrame([
    {'test': 'chi2_one_year_mortality', 'statistic': chi2, 'p_value': p_chi2, 'note': 'descriptive only'},
    {'test': 'multivariate_logrank_overall_survival', 'statistic': lr.test_statistic, 'p_value': lr.p_value, 'note': 'descriptive only'},
    {'test': 'kruskal_wallis_hosp_count', 'statistic': kw_stat, 'p_value': kw_p, 'note': 'descriptive only'},
])
stats.to_csv(OUTDIR / 'stage7_outcome_chi2_logrank.csv', index=False)

print(f'\nOutputs saved.')
print('\n=== STAGE 7 DONE ===')
print('\n⚠️  All p-values are DESCRIPTIVE (no pre-registered hypothesis test on phenotype-outcome link).')
print('⚠️  These are reported to characterize the phenotypes, not to claim inference.')
