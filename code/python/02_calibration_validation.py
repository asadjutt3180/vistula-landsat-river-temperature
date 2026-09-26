"""Step 2 – calibration, cross-validation, bootstrap, RMA slope, station statistics, residual diagnostics
and the twenty-algorithm comparison (single predictor and seasonally augmented).
Input: data/processed/matched_pairs_qc.csv.  Paper: Sections 3.1.1–3.1.4, 3.4; Tables 3–5; Supplementary Tables S3–S9, S13."""
import json, warnings
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.model_selection import KFold, LeaveOneOut, cross_val_predict
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn import linear_model as lm, tree, ensemble, svm, neighbors, neural_network
from common import metrics
from config import PROCESSED, TABLES, SEED

warnings.filterwarnings('ignore')
d = pd.read_csv(PROCESSED / 'matched_pairs_qc.csv', parse_dates=['Date'])
X, y = d[['Satellite_LST']].values, d.InSitu_Temp.values
kf = KFold(10, shuffle=True, random_state=SEED)
out = {}

m = lm.LinearRegression().fit(X, y)
out['full_sample'] = dict(slope=float(m.coef_[0]), intercept=float(m.intercept_), **metrics(y, m.predict(X)),
                          mean_one_to_one_deviation=float((y - X[:, 0]).mean()))
out['ten_fold'] = metrics(y, cross_val_predict(lm.LinearRegression(), X, y, cv=kf))
out['ten_fold_folds'] = [metrics(y[te], lm.LinearRegression().fit(X[tr], y[tr]).predict(X[te])) for tr, te in kf.split(X)]
out['loocv'] = metrics(y, cross_val_predict(lm.LinearRegression(), X, y, cv=LeaveOneOut()))

# Monte Carlo bootstrap: 1,000 iterations, 80 % resampled with replacement (seeded here for reproducibility)
rng = np.random.default_rng(SEED)
bs = []
for _ in range(1000):
    i = rng.choice(len(y), int(0.8 * len(y)), replace=True)
    mb = lm.LinearRegression().fit(X[i], y[i]); p = mb.predict(X[i]); r = y[i] - p
    bs.append(dict(slope=mb.coef_[0], intercept=mb.intercept_, R2=1 - (r ** 2).sum() / ((y[i] - y[i].mean()) ** 2).sum(),
                   RMSE=np.sqrt((r ** 2).mean()), MAE=np.abs(r).mean(), one_to_one_deviation=(y[i] - X[i, 0]).mean()))
bs = pd.DataFrame(bs)
out['bootstrap'] = {c: dict(mean=float(bs[c].mean()), sd=float(bs[c].std()), ci_lower=float(bs[c].quantile(.025)), ci_upper=float(bs[c].quantile(.975))) for c in bs}

# Reduced major axis slope
r = np.corrcoef(X[:, 0], y)[0, 1]
b_rma = np.sign(r) * y.std() / X[:, 0].std()
se = b_rma * np.sqrt((1 - r ** 2) / len(y))
out['rma'] = dict(slope=float(b_rma), ci=[float(b_rma - 1.96 * se), float(b_rma + 1.96 * se)], intercept=float(y.mean() - b_rma * X[:, 0].mean()), r=float(r))

# Station-level statistics (station-specific fits) and residual diagnostics of the pooled fit
out['stations'] = {}
for st, g in d.groupby('Station'):
    ms = lm.LinearRegression().fit(g[['Satellite_LST']], g.InSitu_Temp)
    out['stations'][st] = dict(slope=float(ms.coef_[0]), **metrics(g.InSitu_Temp, ms.predict(g[['Satellite_LST']])),
                               one_to_one_deviation=float((g.InSitu_Temp - g.Satellite_LST).mean()))
res = y - m.predict(X); d['res'] = res
grp = [g.res.values for _, g in d.groupby('Station')]
F, pF = stats.f_oneway(*grp); H, pH = stats.kruskal(*grp)
ssb = sum(len(g) * (g.mean() - res.mean()) ** 2 for g in grp); sst = ((res - res.mean()) ** 2).sum()
out['residuals'] = dict(sd=float(res.std()), skew=float(stats.skew(res)), excess_kurtosis=float(stats.kurtosis(res)),
                        shapiro=[float(v) for v in stats.shapiro(res)], station_means=d.groupby('Station').res.mean().to_dict(),
                        anova_F=float(F), anova_p=float(pF), kruskal_H=float(H), kruskal_p=float(pH), eta2=float(ssb / sst))

# Twenty regression algorithms (settings of Supplementary Table S8)
MODELS = {
    'Linear Regression': lm.LinearRegression(), 'Ridge': lm.Ridge(alpha=1.0), 'Lasso': lm.Lasso(alpha=0.001, max_iter=5000),
    'Elastic Net': lm.ElasticNet(alpha=0.001, l1_ratio=0.5, max_iter=5000), 'Bayesian Ridge': lm.BayesianRidge(),
    'Orthogonal Matching Pursuit': lm.OrthogonalMatchingPursuit(), 'Huber': lm.HuberRegressor(epsilon=1.35),
    'Theil-Sen': lm.TheilSenRegressor(max_subpopulation=10000, random_state=SEED), 'RANSAC': lm.RANSACRegressor(random_state=SEED),
    'SVR (linear)': svm.SVR(kernel='linear', C=1.0), 'SVR (RBF)': svm.SVR(kernel='rbf', C=1.0),
    'k-Nearest Neighbours': neighbors.KNeighborsRegressor(n_neighbors=5), 'Decision Tree': tree.DecisionTreeRegressor(max_depth=10, random_state=SEED),
    'Random Forest': ensemble.RandomForestRegressor(n_estimators=100, max_depth=10, random_state=SEED),
    'Extra Trees': ensemble.ExtraTreesRegressor(n_estimators=100, max_depth=10, random_state=SEED),
    'Gradient Boosting': ensemble.GradientBoostingRegressor(n_estimators=100, max_depth=4, random_state=SEED),
    'Hist. Gradient Boosting': ensemble.HistGradientBoostingRegressor(max_iter=100, random_state=SEED),
    'AdaBoost': ensemble.AdaBoostRegressor(n_estimators=100, random_state=SEED),
    'Multilayer Perceptron': neural_network.MLPRegressor(hidden_layer_sizes=(100, 50), max_iter=2000, early_stopping=True, random_state=SEED),
}
try:
    MODELS['Passive Aggressive'] = lm.PassiveAggressiveRegressor(C=1.0, max_iter=1000, random_state=SEED)
except AttributeError:
    pass
doy = d.Date.dt.dayofyear.values
X_aug = np.column_stack([X[:, 0], np.sin(2 * np.pi * doy / 365), np.cos(2 * np.pi * doy / 365)])
for name_set, XX in (('single_predictor', X), ('seasonal_augmented', X_aug)):
    rows = []
    for name, est in MODELS.items():
        p = cross_val_predict(est, XX, y, cv=kf)
        ps = cross_val_predict(make_pipeline(StandardScaler(), est), XX, y, cv=kf)
        rows.append(dict(model=name, **metrics(y, p), R2_scaled=metrics(y, ps)['R2']))
    t = pd.DataFrame(rows).sort_values('R2', ascending=False)
    t.to_csv(TABLES / f'algorithm_comparison_{name_set}.csv', index=False)
    print(name_set); print(t[['model', 'R2', 'RMSE', 'MAE', 'R2_scaled']].round(4).to_string(index=False))

json.dump(out, open(TABLES / 'calibration_validation.json', 'w'), indent=1)
print(json.dumps({k: out[k] for k in ('full_sample', 'ten_fold', 'loocv', 'rma', 'residuals')}, indent=1))
