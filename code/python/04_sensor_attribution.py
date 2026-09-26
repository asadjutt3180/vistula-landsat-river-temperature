"""Step 4 – attribute each scene to Landsat 5/7/8/9 from its WRS-2 orbital phase and compute
sensor-stratified calibration statistics.
The stations are imaged from two adjacent WRS-2 paths (16-day repeat). Landsat 5 and 8 share one phase
(days-since-2000-01-01 mod 16 in {5, 14}); Landsat 7 and 9 share the phase eight days later ({6, 13}), which
is fixed by 2012, when only Landsat 7 operated. Off-grid dates after 2022 are Landsat 7 in its lower orbit.
Paper: Sections 2.5.4, 3.1.5; Supplementary Section S1.11, Table S16."""
import json
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import KFold, cross_val_predict
from common import load_landsat, metrics
from config import PROCESSED, TABLES, STATIONS, SEED

REF = pd.Timestamp('2000-01-01')


def sensor(date, r, duplicated):
    A, B = r in (5, 14), r in (6, 13)
    if duplicated:
        return 'unassigned'
    if date.year <= 2011:
        return 'L5' if A else ('L7' if B else 'unassigned')
    if date.year == 2012:
        return 'L7' if B else 'unassigned'
    if date < pd.Timestamp('2021-10-31'):
        return 'L8' if A else ('L7' if B else 'unassigned')
    if date.year == 2021:
        return 'L8' if A else ('unassigned' if B else 'L7')
    return 'L8' if A else ('L9' if B else 'L7')


S = []
for st in STATIONS:
    g = load_landsat(st)
    g['r'] = ((g.Date - REF).dt.days) % 16
    dup = g.Date.duplicated(keep=False)
    g['sensor'] = [sensor(t, r, u) for t, r, u in zip(g.Date, g.r, dup)]
    S.append(g)
S = pd.concat(S)
d = pd.read_csv(PROCESSED / 'matched_pairs_qc.csv', parse_dates=['Date'])
S['key'] = S.Satellite_LST.round(3); d['key'] = d.Satellite_LST.round(3)
d = d.merge(S[['Station', 'Date', 'key', 'sensor']], on=['Station', 'Date', 'key'], how='left').drop(columns='key')
X, y = d[['Satellite_LST']].values, d.InSitu_Temp.values
d['pred'] = LinearRegression().fit(X, y).predict(X); d['res'] = y - d.pred
out = {'counts': d.sensor.value_counts().to_dict(), 'sensors': {}}
for s, g in d.groupby('sensor'):
    own = LinearRegression().fit(g[['Satellite_LST']], g.InSitu_Temp)
    out['sensors'][s] = dict(first=str(g.Date.min().date()), last=str(g.Date.max().date()), own_slope=float(own.coef_[0]), **metrics(g.InSitu_Temp, g.pred))
A = d[d.sensor.isin(['L5', 'L7', 'L8', 'L9'])]
grp = [g.res.values for _, g in A.groupby('sensor')]
F, p = stats.f_oneway(*grp); H, pH = stats.kruskal(*grp)
ssb = sum(len(v) * (v.mean() - A.res.mean()) ** 2 for v in grp); sst = ((A.res - A.res.mean()) ** 2).sum()
out['anova'] = dict(F=float(F), df=[len(grp) - 1, len(A) - len(grp)], p=float(p), kruskal_H=float(H), kruskal_p=float(pH), eta2=float(ssb / sst))
kf = KFold(10, shuffle=True, random_state=SEED)
Xs = np.column_stack([A[['Satellite_LST']].values, pd.get_dummies(A.sensor, drop_first=True).values.astype(float)])
out['cv_pooled'] = metrics(A.InSitu_Temp, cross_val_predict(LinearRegression(), A[['Satellite_LST']].values, A.InSitu_Temp, cv=kf))
out['cv_sensor_intercepts'] = metrics(A.InSitu_Temp, cross_val_predict(LinearRegression(), Xs, A.InSitu_Temp, cv=kf))
d.drop(columns=['pred', 'res']).to_csv(PROCESSED / 'matched_pairs_qc_with_sensor.csv', index=False)
json.dump(out, open(TABLES / 'sensor_statistics.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
