"""Step 3 – leave-one-station-out validation (annual and seasonal models), nested quality control,
temporal-window sensitivity and 7-day in-situ variability.
Paper: Sections 2.4, 3.1.3, 3.1.6, 3.4; Table 6; Supplementary Tables S2a, S17, S19."""
import json
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import KFold
from scipy import stats
from common import match, quality_control, metrics, load_insitu
from config import PROCESSED, TABLES, STATIONS, SEED, Z_THRESHOLD

d = pd.read_csv(PROCESSED / 'matched_pairs_qc.csv', parse_dates=['Date'])
y = d.InSitu_Temp.values
doy = d.Date.dt.dayofyear.values
X1 = d[['Satellite_LST']].values
X2 = np.column_stack([X1[:, 0], np.sin(2 * np.pi * doy / 365), np.cos(2 * np.pi * doy / 365)])
out = {'loso': {}}
for name, X in (('annual', X1), ('seasonal', X2)):
    rows, allp = [], np.zeros(len(y))
    for st in STATIONS:
        t = (d.Station == st).values
        m = LinearRegression().fit(X[~t], y[~t]); p = m.predict(X[t]); allp[t] = p
        rows.append(dict(station=st, slope=float(m.coef_[0]), **metrics(y[t], p)))
    out['loso'][name] = dict(stations=rows, pooled=metrics(y, allp),
                             mean_of_stations={k: float(np.mean([r[k] for r in rows])) for k in ('R2', 'RMSE', 'MAE', 'mean_residual')})

# nested ten-fold CV: QC fitted on training folds only, test folds screened with training thresholds
raw = pd.read_csv(PROCESSED / 'matched_pairs_raw.csv', parse_dates=['Date'])
Xr = raw[raw.Satellite_LST.between(-5, 40) & raw.InSitu_Temp.between(-5, 40)].reset_index(drop=True)
obs, pred = [], []
for tr, te in KFold(10, shuffle=True, random_state=SEED).split(Xr):
    T, E = Xr.iloc[tr], Xr.iloc[te]
    Tc = quality_control(T)
    d11 = T.InSitu_Temp - T.Satellite_LST
    E = E[np.abs(((E.InSitu_Temp - E.Satellite_LST) - d11.mean()) / d11.std(ddof=0)) <= Z_THRESHOLD]
    m = LinearRegression().fit(Tc[['Satellite_LST']], Tc.InSitu_Temp)
    rt = Tc.InSitu_Temp - m.predict(Tc[['Satellite_LST']]); q1, q3 = np.percentile(rt, [25, 75]); iq = q3 - q1
    re_ = E.InSitu_Temp - m.predict(E[['Satellite_LST']])
    E = E[(np.abs((re_ - rt.mean()) / rt.std(ddof=0)) <= Z_THRESHOLD) & (re_ >= q1 - 1.5 * iq) & (re_ <= q3 + 1.5 * iq)]
    obs += list(E.InSitu_Temp); pred += list(m.predict(E[['Satellite_LST']]))
out['nested_qc_cv'] = metrics(obs, pred)

# matching-window sensitivity
out['window_sensitivity'] = {}
for w in (1, 2, 3):
    rw = match(w); q = quality_control(rw)
    m = LinearRegression().fit(q[['Satellite_LST']], q.InSitu_Temp)
    out['window_sensitivity'][f'±{w} d'] = dict(matched=len(rw), **metrics(q.InSitu_Temp, m.predict(q[['Satellite_LST']])))

# in-situ variability within centred 7-day windows (the span of the ±3-day window), May–November
sd = pd.concat([load_insitu(s).set_index('Date')['water_temp_C'].sort_index().rolling(7, center=True).std().dropna() for s in STATIONS])
out['insitu_7day_sd'] = dict(mean=float(sd.mean()), by_month=sd.groupby(sd.index.month).mean().round(3).to_dict())

json.dump(out, open(TABLES / 'loso_and_sensitivity.json', 'w'), indent=1)
print(json.dumps(out, indent=1))
