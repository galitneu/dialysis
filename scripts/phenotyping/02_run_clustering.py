"""
Stage 5 — Execute clustering per LOCKED protocol DEC-PHENO-006.

Algorithms: KMeans, Ward (AgglomerativeClustering), GMM
K range: 2-6
Quality metrics: Silhouette, Calinski-Harabasz, Davies-Bouldin, bootstrap stability

NO outcomes used as input.

Outputs:
- stage5_cluster_assignments_all_solutions.csv  (one row per patient × algo × K)
- stage5_cluster_quality_metrics.csv
- stage5_cross_algorithm_ARI.csv
- stage5_chosen_solution.csv
- stage5_chosen_solution_metadata.json
"""

import pandas as pd
import numpy as np
import json
from pathlib import Path
from sklearn.cluster import KMeans, AgglomerativeClustering
from sklearn.mixture import GaussianMixture
from sklearn.metrics import silhouette_score, calinski_harabasz_score, davies_bouldin_score, adjusted_rand_score

OUTDIR = Path('/home/user/dialysis/outputs/phenotyping')
RANDOM_SEED = 4242

# ----------------------------------------------------------------
# Load preprocessed matrix
# ----------------------------------------------------------------

mat = pd.read_csv(OUTDIR / 'stage3_preprocessed_matrix_core.csv')
pid = mat['patient_id'].values
features = [c for c in mat.columns if c != 'patient_id']
X = mat[features].values
print(f'Loaded matrix: {X.shape}, features: {len(features)}')

# ----------------------------------------------------------------
# Run all (algorithm, K) combinations
# ----------------------------------------------------------------

K_RANGE = [2, 3, 4, 5, 6]
ALGORITHMS = ['kmeans', 'ward', 'gmm']

assignments_rows = []
quality_rows = []

for algo in ALGORITHMS:
    for K in K_RANGE:
        if algo == 'kmeans':
            model = KMeans(n_clusters=K, random_state=RANDOM_SEED, n_init=20)
            labels = model.fit_predict(X)
        elif algo == 'ward':
            model = AgglomerativeClustering(n_clusters=K, linkage='ward')
            labels = model.fit_predict(X)
        elif algo == 'gmm':
            model = GaussianMixture(n_components=K, random_state=RANDOM_SEED, n_init=10, covariance_type='full')
            model.fit(X)
            labels = model.predict(X)

        # Save assignments
        for i, p in enumerate(pid):
            assignments_rows.append({
                'patient_id': p,
                'algorithm': algo,
                'K': K,
                'cluster': int(labels[i]),
            })

        # Quality metrics
        if K >= 2 and len(np.unique(labels)) > 1:
            sil = silhouette_score(X, labels)
            ch = calinski_harabasz_score(X, labels)
            db = davies_bouldin_score(X, labels)
        else:
            sil = ch = db = np.nan

        # Hard floor check: any cluster <30?
        cluster_sizes = pd.Series(labels).value_counts()
        min_size = int(cluster_sizes.min())
        max_size = int(cluster_sizes.max())
        n_clusters_below_30 = int((cluster_sizes < 30).sum())

        quality_rows.append({
            'algorithm': algo,
            'K': K,
            'silhouette': sil,
            'calinski_harabasz': ch,
            'davies_bouldin': db,
            'min_cluster_size': min_size,
            'max_cluster_size': max_size,
            'n_clusters_below_30': n_clusters_below_30,
            'disqualified_size_floor': bool(n_clusters_below_30 > 0),
        })
        print(f'  {algo} K={K}  sil={sil:.3f}  CH={ch:.0f}  DB={db:.3f}  min_size={min_size}  '
              f'{"DISQUALIFIED" if n_clusters_below_30 > 0 else "OK"}')

assigns_df = pd.DataFrame(assignments_rows)
quality_df = pd.DataFrame(quality_rows)
assigns_df.to_csv(OUTDIR / 'stage5_cluster_assignments_all_solutions.csv', index=False)
quality_df.to_csv(OUTDIR / 'stage5_cluster_quality_metrics.csv', index=False)
print(f'\nAssignments saved: {OUTDIR / "stage5_cluster_assignments_all_solutions.csv"}')

# ----------------------------------------------------------------
# Bootstrap stability for each (algo, K) — only for K not size-disqualified
# 100 bootstraps × 3 algo × 5 K = 1500 fits. Trim to 50 bootstraps to keep runtime manageable.
# ----------------------------------------------------------------

print('\n--- Bootstrap stability (vectorized; 50 resamples) ---')
# For each bootstrap: subsample 80% (without replacement). Refit. Predict labels for ALL original patients.
# Then for each pair (i, j), agreement = (label_orig[i] == label_orig[j]) == (label_b[i] == label_b[j]).
# Mean agreement per cluster = stability.

n = len(X)
B = 50
SUB_FRAC = 0.8
rng = np.random.default_rng(RANDOM_SEED)
stability_scores = {}

for algo in ALGORITHMS:
    for K in K_RANGE:
        orig = assigns_df[(assigns_df.algorithm == algo) & (assigns_df.K == K)].sort_values('patient_id')
        orig_labels = orig['cluster'].values
        same_orig = orig_labels[:, None] == orig_labels[None, :]  # n×n boolean of co-cluster in original

        per_cluster_agree = np.zeros((K,), dtype=float)
        per_cluster_pairs = np.zeros((K,), dtype=int)
        boot_count = 0

        for b in range(B):
            sub_n = int(SUB_FRAC * n)
            sample_idx = rng.choice(n, size=sub_n, replace=False)
            X_b = X[sample_idx]
            try:
                if algo == 'kmeans':
                    fit = KMeans(n_clusters=K, random_state=b, n_init=10).fit(X_b)
                    m_full = fit.predict(X)  # predict on FULL set
                elif algo == 'ward':
                    # Ward has no predict; refit on full but seeded with subsample is impractical.
                    # Use KMeans with subsample-derived centroids? Alternative: fit Ward on X_b then assign all X by 1NN to subsample.
                    fit = AgglomerativeClustering(n_clusters=K, linkage='ward').fit(X_b)
                    sub_labels = fit.labels_
                    # Assign each original patient to nearest subsample point's cluster
                    from scipy.spatial.distance import cdist
                    d = cdist(X, X_b)
                    nn_idx = d.argmin(axis=1)
                    m_full = sub_labels[nn_idx]
                elif algo == 'gmm':
                    fit = GaussianMixture(n_components=K, random_state=b, n_init=3, covariance_type='full').fit(X_b)
                    m_full = fit.predict(X)
            except Exception:
                continue

            same_b = m_full[:, None] == m_full[None, :]
            agree = (same_orig == same_b)  # n×n boolean

            # Per-cluster agreement: average over within-cluster pairs of original
            for c in range(K):
                members = np.where(orig_labels == c)[0]
                if len(members) < 2: continue
                # pairs: members × members upper triangle excluding diag
                sub = agree[np.ix_(members, members)]
                triu = np.triu(np.ones_like(sub), k=1).astype(bool)
                per_cluster_agree[c] += sub[triu].mean()
                per_cluster_pairs[c] += 1

            boot_count += 1

        # Per-cluster mean across bootstraps
        per_cluster = []
        for c in range(K):
            if per_cluster_pairs[c] > 0:
                per_cluster.append(per_cluster_agree[c] / per_cluster_pairs[c])

        mean_stab = float(np.mean(per_cluster)) if per_cluster else np.nan
        min_stab = float(np.min(per_cluster)) if per_cluster else np.nan
        stability_scores[(algo, K)] = {
            'mean_stability': mean_stab,
            'min_stability': min_stab,
            'per_cluster': per_cluster,
        }
        print(f'  {algo} K={K}  mean_stab={mean_stab:.3f}  min_stab={min_stab:.3f}  ({boot_count} successful bootstraps)')

# Add stability to quality df
for i, row in quality_df.iterrows():
    s = stability_scores.get((row.algorithm, row.K), {})
    quality_df.at[i, 'mean_stability'] = s.get('mean_stability', np.nan)
    quality_df.at[i, 'min_stability'] = s.get('min_stability', np.nan)

quality_df.to_csv(OUTDIR / 'stage5_cluster_quality_metrics.csv', index=False)

# ----------------------------------------------------------------
# Cross-algorithm ARI — for each K, compare every algorithm pair
# ----------------------------------------------------------------

print('\n--- Cross-algorithm ARI (Adjusted Rand Index) ---')
ari_rows = []
for K in K_RANGE:
    labs = {}
    for algo in ALGORITHMS:
        sub = assigns_df[(assigns_df.algorithm == algo) & (assigns_df.K == K)].sort_values('patient_id')
        labs[algo] = sub['cluster'].values
    pairs = [('kmeans', 'ward'), ('kmeans', 'gmm'), ('ward', 'gmm')]
    for a, b in pairs:
        ari = adjusted_rand_score(labs[a], labs[b])
        ari_rows.append({'K': K, 'algo_a': a, 'algo_b': b, 'ARI': ari})
        print(f'  K={K}  {a} vs {b}  ARI={ari:.3f}')

ari_df = pd.DataFrame(ari_rows)
ari_df.to_csv(OUTDIR / 'stage5_cross_algorithm_ARI.csv', index=False)

# ----------------------------------------------------------------
# Choose the final solution per locked criteria
# ----------------------------------------------------------------

print('\n=== APPLYING LOCKED SELECTION CRITERIA ===')

eligible = quality_df[~quality_df['disqualified_size_floor']].copy()

if eligible.empty:
    print('NO eligible (algo, K) combinations passed the n>=30 hard floor.')
    chosen = None
else:
    # For each algorithm, pick the K with the best multi-criterion ranking
    print('\nFor each algorithm, find best K by multi-criterion ranking:')
    best_per_algo = {}
    for algo in ALGORITHMS:
        algo_data = eligible[eligible.algorithm == algo].copy()
        if algo_data.empty:
            print(f'  {algo}: no eligible K')
            continue
        # Rank by each metric (lower rank = better)
        algo_data['rank_sil'] = algo_data['silhouette'].rank(ascending=False)
        algo_data['rank_ch'] = algo_data['calinski_harabasz'].rank(ascending=False)
        algo_data['rank_db'] = algo_data['davies_bouldin'].rank(ascending=True)
        algo_data['rank_stab'] = algo_data['mean_stability'].rank(ascending=False)
        algo_data['avg_rank'] = algo_data[['rank_sil', 'rank_ch', 'rank_db', 'rank_stab']].mean(axis=1)
        # Tiebreak: lower K
        algo_data['K_neg'] = -algo_data['K']
        algo_data = algo_data.sort_values(['avg_rank', 'K'], ascending=[True, True])
        best = algo_data.iloc[0]
        best_per_algo[algo] = int(best.K)
        print(f'  {algo}: best K = {int(best.K)} (avg rank {best.avg_rank:.2f})')

    # Cross-algorithm consensus check at the best K's
    if len(best_per_algo) == 3:
        # If all three agree on K, that's the chosen K
        if len(set(best_per_algo.values())) == 1:
            chosen_K = list(best_per_algo.values())[0]
        else:
            # Use modal K, prefer lower if tie
            from collections import Counter
            counts = Counter(best_per_algo.values())
            top = counts.most_common()
            if len(top) > 1 and top[0][1] == top[1][1]:
                chosen_K = min(t[0] for t in top if t[1] == top[0][1])
            else:
                chosen_K = top[0][0]

        # Pick the algorithm with highest stability at the chosen K
        chosen_K_data = eligible[eligible.K == chosen_K]
        chosen_K_data = chosen_K_data.sort_values('mean_stability', ascending=False)
        chosen_algo = chosen_K_data.iloc[0]['algorithm']

        chosen = {
            'algorithm': chosen_algo,
            'K': int(chosen_K),
            'silhouette': float(chosen_K_data.iloc[0]['silhouette']),
            'mean_stability': float(chosen_K_data.iloc[0]['mean_stability']),
            'min_cluster_size': int(chosen_K_data.iloc[0]['min_cluster_size']),
            'rationale': 'multi-criterion best per algorithm + cross-algorithm modal K + highest-stability algorithm',
        }

        # Cross-algorithm ARI at chosen K
        ari_at_chosen = ari_df[ari_df.K == chosen_K]
        chosen['cross_algo_ARI'] = ari_at_chosen.set_index(['algo_a','algo_b'])['ARI'].to_dict()

        # ARI rule check
        max_ari = ari_at_chosen['ARI'].max()
        if max_ari >= 0.7:
            chosen['consensus_status'] = 'STRONG_consensus'
        elif max_ari >= 0.5:
            chosen['consensus_status'] = 'MODERATE_consensus'
        else:
            chosen['consensus_status'] = 'WEAK_consensus_results_exploratory'

        print(f'\nCHOSEN SOLUTION: algorithm={chosen_algo}, K={chosen_K}')
        print(f'  silhouette={chosen["silhouette"]:.3f}, mean_stability={chosen["mean_stability"]:.3f}')
        print(f'  min cluster size: {chosen["min_cluster_size"]}')
        print(f'  consensus status: {chosen["consensus_status"]}')

        # Save the chosen solution patient assignments
        chosen_assigns = assigns_df[(assigns_df.algorithm == chosen_algo) & (assigns_df.K == chosen_K)].copy()
        chosen_assigns = chosen_assigns.rename(columns={'cluster': 'phenotype'})
        chosen_assigns[['patient_id', 'phenotype']].to_csv(OUTDIR / 'stage5_chosen_solution.csv', index=False)

        with open(OUTDIR / 'stage5_chosen_solution_metadata.json', 'w') as f:
            # Convert tuple-keyed dict for JSON
            chosen_serialisable = dict(chosen)
            chosen_serialisable['cross_algo_ARI'] = {f'{k[0]}__{k[1]}': v for k, v in chosen['cross_algo_ARI'].items()}
            chosen_serialisable['best_K_per_algo'] = best_per_algo
            json.dump(chosen_serialisable, f, indent=2)

        print(f'\nChosen solution saved.')
    else:
        print('Could not establish consensus across 3 algorithms.')

print('\n=== STAGE 5 DONE ===')
