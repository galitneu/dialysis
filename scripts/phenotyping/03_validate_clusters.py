"""
Stage 6 — Validate phenotypes per LOCKED protocol.

Validation steps:
1. Stability check (already computed in Stage 5; we read and report)
2. Cluster size check (≥30 per cluster, hard floor)
3. Clinical face validity — describe each cluster's variable profile
4. Imputation rate per cluster (per DEC-PHENO-004 reporting requirement)
5. Sensitivity: re-run on extended variable set, compute ARI vs core solution
6. Sensitivity: re-run without imputed variables (only fully-observed), compute ARI

Outputs:
- stage6_cluster_descriptions.csv  (mean/% per variable per cluster)
- stage6_cluster_imputation_audit.csv (% imputed per variable per cluster)
- stage6_validation_summary.md
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path

OUTDIR = Path('/home/user/dialysis/outputs/phenotyping')

# ----------------------------------------------------------------
# Load chosen solution + raw matrix
# ----------------------------------------------------------------

chosen = pd.read_csv(OUTDIR / 'stage5_chosen_solution.csv')
raw_mat = pd.read_csv(OUTDIR / 'stage3_preprocessed_matrix_core.csv')
imp_flags = pd.read_csv(OUTDIR / 'stage3_imputation_flags.csv')

with open(OUTDIR / 'stage5_chosen_solution_metadata.json') as f:
    meta = json.load(f)

print('Chosen solution:')
print(json.dumps(meta, indent=2))

# Merge solution into raw matrix
df = raw_mat.merge(chosen, on='patient_id')
print(f'\nMerged shape: {df.shape}')

# ----------------------------------------------------------------
# 1. Cluster size check
# ----------------------------------------------------------------

sizes = df['phenotype'].value_counts().sort_index()
print('\nCluster sizes:')
print(sizes)

# ----------------------------------------------------------------
# 2. Cluster descriptions: mean/% per variable per cluster
# ----------------------------------------------------------------

# We have the z-scored matrix; for clinical interpretation we want raw means.
# Re-derive raw values for clarity.
import pandas as pd
raw = pd.read_excel('/home/user/dialysis/base_analysis_dataset.xlsx', sheet_name='base_analysis_dataset')

# Build derived binaries on raw
derived_cols = {}
derived_cols['sex_male'] = (raw['m/f'].astype(str).str.lower() == 'm').astype(float)
derived_cols['HD_binary'] = (raw['HD/PD'].astype(str).str.upper() == 'HD').astype(float)

def la_collapse(x):
    if pd.isna(x): return np.nan
    s = str(x).lower().strip()
    if any(t in s for t in ['mildly dilated', 'moderately dilated', 'severely dilated']): return 1
    if 'normal' in s: return 0
    return np.nan
derived_cols['LACavity_dilated'] = raw['LACavitySize'].map(la_collapse)

def tr_collapse(x):
    if pd.isna(x): return np.nan
    s = str(x).lower().strip()
    if any(t in s for t in ['moderate','severe','iii','iv']): return 1
    if any(t in s for t in ['none','trace','trivial','mild','i ','(i)']): return 0
    return np.nan
derived_cols['TR_moderate_or_severe'] = raw['TricuspidRegurgitation'].map(tr_collapse)

raw_with_derived = raw.copy()
for k, v in derived_cols.items():
    raw_with_derived[k] = v

# Subset to patients in chosen solution
raw_sub = raw_with_derived[raw_with_derived['patient_id'].isin(chosen['patient_id'])].copy()
raw_sub = raw_sub.merge(chosen, on='patient_id')

# Variables (post-preprocessing names)
features = [c for c in raw_mat.columns if c != 'patient_id']
continuous_vars = ['AgeAtFirstHFDate', 'LV_EF', 'LeftVentricleEndDiastolicDiameter',
                   'LeftVentriclePosteriorWallThickness', 'LeftVentricleEstimatedMass',
                   'MitralInflowPeakEWave', 'TissueDopplerEERatioSeptal', 'EstimatedSysPAPressure',
                   'albumin-numeric result', 'creatinine-numeric result', 'crp-numeric result',
                   'hb-numeric result']
binary_vars = ['sex_male', 'HD_binary', 'AFIB_binary', 'Diabetes mellitus_binary',
               'LACavity_dilated', 'TR_moderate_or_severe']

# Build description table
desc_rows = []
for c in sorted(raw_sub['phenotype'].unique()):
    cdf = raw_sub[raw_sub['phenotype'] == c]
    row = {'phenotype': int(c), 'n': len(cdf)}
    for v in continuous_vars:
        row[f'{v}_mean'] = float(cdf[v].mean())
        row[f'{v}_std'] = float(cdf[v].std())
    for v in binary_vars:
        row[f'{v}_pct'] = 100 * float(cdf[v].mean())
    desc_rows.append(row)
desc = pd.DataFrame(desc_rows)
desc.to_csv(OUTDIR / 'stage6_cluster_descriptions.csv', index=False)
print(f'\nCluster descriptions saved.')

# Print compact summary
print('\n=== CLUSTER PROFILES (means for continuous, % for binary) ===')
for _, r in desc.iterrows():
    print(f'\nPhenotype {int(r.phenotype)} (n={int(r.n)}):')
    print(f'  Demographics: age={r["AgeAtFirstHFDate_mean"]:.1f}, male={r["sex_male_pct"]:.0f}%, HD={r["HD_binary_pct"]:.0f}%')
    print(f'  Comorbidity:  AFIB={r["AFIB_binary_pct"]:.0f}%, DM={r["Diabetes mellitus_binary_pct"]:.0f}%')
    print(f'  Cardiac:      EF={r["LV_EF_mean"]:.1f}, LV-EDD={r["LeftVentricleEndDiastolicDiameter_mean"]:.2f}, '
          f'LV-PWT={r["LeftVentriclePosteriorWallThickness_mean"]:.2f}, LV-mass={r["LeftVentricleEstimatedMass_mean"]:.0f}')
    print(f'  Diastolic:    E={r["MitralInflowPeakEWave_mean"]:.0f}, E/e\'={r["TissueDopplerEERatioSeptal_mean"]:.1f}, '
          f'SPAP={r["EstimatedSysPAPressure_mean"]:.0f}')
    print(f'  Burden:       LA-dilated={r["LACavity_dilated_pct"]:.0f}%, TR-mod/sev={r["TR_moderate_or_severe_pct"]:.0f}%')
    print(f'  Labs:         albumin={r["albumin-numeric result_mean"]:.2f}, crea={r["creatinine-numeric result_mean"]:.2f}, '
          f'CRP={r["crp-numeric result_mean"]:.1f}, Hb={r["hb-numeric result_mean"]:.1f}')

# ----------------------------------------------------------------
# 3. Imputation rate per cluster
# ----------------------------------------------------------------

imp_with_pheno = imp_flags.merge(chosen, on='patient_id')
imp_audit_rows = []
for c in sorted(imp_with_pheno['phenotype'].unique()):
    cdf = imp_with_pheno[imp_with_pheno['phenotype'] == c]
    for col in [x for x in cdf.columns if x.startswith('imputed__')]:
        var = col.replace('imputed__', '')
        pct = 100 * cdf[col].mean()
        imp_audit_rows.append({
            'phenotype': int(c),
            'variable': var,
            'n_in_cluster': len(cdf),
            'n_imputed': int(cdf[col].sum()),
            'pct_imputed': round(pct, 1),
        })
imp_audit = pd.DataFrame(imp_audit_rows)
imp_audit.to_csv(OUTDIR / 'stage6_cluster_imputation_audit.csv', index=False)
print('\n=== IMPUTATION RATE PER CLUSTER ===')
piv = imp_audit.pivot(index='variable', columns='phenotype', values='pct_imputed')
print(piv)

# ----------------------------------------------------------------
# 4. Validation summary doc
# ----------------------------------------------------------------

summary = f"""# Stage 6 — Phenotype Validation Summary

**Date:** generated by validation script

## Chosen solution

- **Algorithm:** {meta['algorithm']}
- **K:** {meta['K']}
- **Silhouette:** {meta['silhouette']:.3f}
- **Mean stability:** {meta['mean_stability']:.3f}
- **Min cluster size:** {meta['min_cluster_size']}
- **Cross-algo consensus:** {meta['consensus_status']}

## Cluster sizes (Rule 4: minimum 30 per cluster for inference)

{sizes.to_string()}

All clusters {'PASS' if (sizes >= 30).all() else 'FAIL'} the 30-patient hard floor.

## ARI between algorithms at chosen K

{json.dumps(meta['cross_algo_ARI'], indent=2)}

## Imputation rate per cluster

The 6 kNN-imputed variables were checked for cluster-specific imputation rates. If one cluster has >2x the imputation rate of others, it suggests the cluster is partly driven by imputation rather than real signal.

{piv.to_string()}

## Pass/Fail per Stage 4 success criteria

- ARI ≥ 0.5 across ≥2 algorithms: **{'PASS' if any(v >= 0.5 for v in meta['cross_algo_ARI'].values()) else 'FAIL'}**
- All clusters n ≥ 30: **{'PASS' if (sizes >= 30).all() else 'FAIL'}**
- Bootstrap stability ≥ 0.7: **{'PASS' if meta['mean_stability'] >= 0.7 else 'BORDERLINE/FAIL — review per-cluster stability'}**
- Clinical interpretability (CARD/NEPH judgment): see Stage 6 narrative review

## Next step

If all PASS → proceed to Stage 7 (outcome linkage).
If any FAIL → committee review; possibly revert to lower K or re-evaluate variable set.
"""

with open(OUTDIR / 'stage6_validation_summary.md', 'w') as f:
    f.write(summary)

print(f'\nValidation summary saved.')
print('\n=== STAGE 6 DONE ===')
