"""Step 1 – temporal matching (±3 days) and four-stage quality control.
Outputs: data/processed/matched_pairs_raw.csv (942), matched_pairs_qc.csv (876), results/tables/qc_summary.json
Paper: Sections 2.4 and 3.1.6; Supplementary Tables S1, S2, S2a, S2b."""
import json
import numpy as np
from common import match, quality_control, metrics
from config import PROCESSED, TABLES
from sklearn.linear_model import LinearRegression

raw = match(3)
qc, stages = quality_control(raw, return_stages=True)
raw.to_csv(PROCESSED / 'matched_pairs_raw.csv', index=False)
qc.to_csv(PROCESSED / 'matched_pairs_qc.csv', index=False)

def fit(d):
    m = LinearRegression().fit(d[['Satellite_LST']], d.InSitu_Temp)
    return metrics(d.InSitu_Temp, m.predict(d[['Satellite_LST']]))

rem = raw.loc[~raw.index.isin(qc.index)]
out = dict(stages_raw_bounds_z11_zreg_iqr=stages,
           pairs_by_station_raw=raw.Station.value_counts().to_dict(),
           pairs_by_station_qc=qc.Station.value_counts().to_dict(),
           before_qc=fit(raw), after_qc=fit(qc),
           removed=dict(n=len(rem), by_station=rem.Station.value_counts().to_dict(),
                        june_august=int(rem.Date.dt.month.isin([6, 7, 8]).sum()),
                        mean_one_to_one_deviation=float((rem.InSitu_Temp - rem.Satellite_LST).mean())),
           retained_mean_one_to_one_deviation=float((qc.InSitu_Temp - qc.Satellite_LST).mean()))
json.dump(out, open(TABLES / 'qc_summary.json', 'w'), indent=1, default=str)
print(json.dumps(out, indent=1, default=str))
