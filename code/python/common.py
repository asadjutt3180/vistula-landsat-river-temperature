"""Matching, quality control and metrics shared by all scripts."""
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LinearRegression
from config import RAW_INSITU, RAW_LANDSAT, STATIONS, Z_THRESHOLD


def load_insitu(station):
    d = pd.read_csv(RAW_INSITU / f'{station}_insitu_water_temperature.csv')
    d['Date'] = pd.to_datetime(d[['year', 'month', 'day']])
    return d


def load_landsat(station):
    d = pd.read_csv(RAW_LANDSAT / f'{station}_landsat_lst.csv')
    d['Date'] = pd.to_datetime(d['Date'])
    d = d.rename(columns={'Satellite_LST_Celsius': 'Satellite_LST'})
    d['Station'] = station
    return d


def match(window=3):
    """Pair each Landsat scene with the mean of the daily in-situ readings within +/- window days."""
    rows = []
    for st in STATIONS:
        ins = load_insitu(st)
        lat, lon = ins.latitude.mean(), ins.longitude.mean()
        for r in load_landsat(st).itertuples():
            c = ins[(ins.Date - r.Date).abs().dt.days <= window]
            if len(c):
                rows.append(dict(Date=r.Date, Station=st, Latitude=lat, Longitude=lon,
                                 Satellite_LST=r.Satellite_LST, InSitu_Temp=c.water_temp_C.mean()))
    return pd.DataFrame(rows).dropna().reset_index(drop=True)


def quality_control(df, z=Z_THRESHOLD, return_stages=False):
    """Four-stage screening: physical bounds, 1:1 residual z-score, iterative regression z-score, IQR."""
    n0 = len(df)
    d = df[df.Satellite_LST.between(-5, 40) & df.InSitu_Temp.between(-5, 40)].copy(); n1 = len(d)
    d = d[np.abs(stats.zscore(d.InSitu_Temp - d.Satellite_LST)) <= z].copy(); n2 = len(d)
    for _ in range(20):
        m = LinearRegression().fit(d[['Satellite_LST']], d.InSitu_Temp)
        zr = np.abs(stats.zscore(d.InSitu_Temp - m.predict(d[['Satellite_LST']])))
        if zr.max() <= z:
            break
        d = d[zr <= z].copy()
    n3 = len(d)
    m = LinearRegression().fit(d[['Satellite_LST']], d.InSitu_Temp)
    r = d.InSitu_Temp - m.predict(d[['Satellite_LST']])
    q1, q3 = np.percentile(r, [25, 75]); iq = q3 - q1
    d = d[(r >= q1 - 1.5 * iq) & (r <= q3 + 1.5 * iq)]
    return (d, (n0, n1, n2, n3, len(d))) if return_stages else d


def metrics(obs, pred):
    obs, pred = np.asarray(obs), np.asarray(pred)
    r = obs - pred
    return dict(n=int(len(obs)), R2=float(1 - (r ** 2).sum() / ((obs - obs.mean()) ** 2).sum()),
                RMSE=float(np.sqrt((r ** 2).mean())), MAE=float(np.abs(r).mean()), mean_residual=float(r.mean()))
