"""Step 5 – monthly river-mean composites and coverage, coverage-controlled trends, August 2020 anomaly and the
longitudinal profile of the lower Vistula.
Requires the whole-river monthly centreline composites (Zenodo, ~1.3 GB) in data/large/:
    Vistula_LST_<Month>_2000_2024.csv   (columns: Date, Year, Month, Point_ID, Longitude, Latitude, OSM_ID,
                                         River_Name, LST_Celsius, River_Km, Source_File, Month_Name)
If they are absent, the steps that need only the monthly river means use data/processed/monthly_river_mean_lst.csv.
Paper: Sections 2.3.2, 2.6, 3.2, 3.3; Figures 8–9; Supplementary Tables S10–S12, S20."""
import json
import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats
from config import LARGE, PROCESSED, TABLES, FIGURES, MONTHS, GAUGE_KM

CAL_SLOPE, CAL_INTERCEPT = 0.8125, 2.7965          # calibration of Section 3.1.1
have_large = all((LARGE / f'Vistula_LST_{m}_2000_2024.csv').exists() for m in MONTHS)

# ---------------- monthly river means and coverage (Table S10 / Figure S1 annotations)
if have_large:
    rows = []
    for mo in MONTHS:
        d = pd.read_csv(LARGE / f'Vistula_LST_{mo}_2000_2024.csv', usecols=['Year', 'Point_ID', 'LST_Celsius'])
        npts = d.Point_ID.nunique()
        for yr, g in d.groupby('Year'):
            rows.append(dict(Month=mo, Year=yr, LST=round(g.LST_Celsius.mean(), 1), Coverage=round(100 * g.LST_Celsius.notna().sum() / npts)))
    mm = pd.DataFrame(rows); mm.to_csv(PROCESSED / 'monthly_river_mean_lst.csv', index=False)
else:
    mm = pd.read_csv(PROCESSED / 'monthly_river_mean_lst.csv')

# ---------------- trends: OLS, Theil–Sen and coverage-controlled (Tables S11, S12)
tr = []
for mo in MONTHS:
    g = mm[mm.Month == mo]
    ols = stats.linregress(g.Year, g.LST)
    ts = stats.theilslopes(g.LST, g.Year)
    mc = sm.OLS(g.LST, sm.add_constant(g[['Year', 'Coverage']])).fit()
    rcy, pcy = stats.pearsonr(g.Coverage, g.Year); rcl, pcl = stats.pearsonr(g.Coverage, g.LST)
    tr.append(dict(month=mo, ols_per_decade=10 * ols.slope, ols_p=ols.pvalue, theil_sen_per_decade=10 * ts[0],
                   controlled_per_decade=10 * mc.params['Year'], controlled_p=mc.pvalues['Year'],
                   r_coverage_year=rcy, p_coverage_year=pcy, r_coverage_lst=rcl, p_coverage_lst=pcl))
pd.DataFrame(tr).round(4).to_csv(TABLES / 'monthly_trends.csv', index=False)

# ---------------- August anomaly (Section 3.3, Table S10)
au = mm[mm.Month == 'August'].copy()
mu, sd = au.LST.mean(), au.LST.std()
au['z'] = (au.LST - mu) / sd
au['rank'] = au.LST.rank(ascending=False, method='min').astype(int)
au.round(2).to_csv(TABLES / 'august_record.csv', index=False)
print('August mean %.2f sd %.2f; 2020:' % (mu, sd), au[au.Year == 2020].round(2).to_dict('records'))

# ---------------- longitudinal profile of the lower Vistula (Figure 8, Table S20)
if have_large:
    aL = np.array([898.3, 1246.26, 1366.55, 1587.66])      # centreline km of the gauges (OSM line)
    aO = np.array([GAUGE_KM['Warszawa'], GAUGE_KM['Torun'], GAUGE_KM['Chelmno'], GAUGE_KM['Gdansk_Swibno']])
    ratio = (aL[-1] - aL[1]) / (aO[-1] - aO[1])
    tokm = lambda L: np.where(L > aL[-1], aO[-1] + (L - aL[-1]) / ratio, np.interp(L, aL, aO))
    prof = {}
    for mo in MONTHS:
        d = pd.read_csv(LARGE / f'Vistula_LST_{mo}_2000_2024.csv', usecols=['Year', 'River_Km', 'LST_Celsius'])
        d = d[(d.River_Km >= 1098.46) & (d.River_Km <= 1593.18) & d.LST_Celsius.between(-5, 40)]
        good = mm[(mm.Month == mo) & (mm.Coverage >= 90)].Year.values
        d = d[d.Year.isin(good)]
        d['bin'] = (tokm(d.River_Km.values) // 5) * 5 + 2.5
        d['T'] = CAL_SLOPE * d.LST_Celsius + CAL_INTERCEPT
        yb = d.groupby(['Year', 'bin']).T.mean().unstack()
        clim = yb.mean()
        prof[mo] = clim[yb.notna().sum() >= max(1, len(good) // 2)]
    P = pd.DataFrame(prof); P.index.name = 'river_km_bin_centre'
    P.round(3).to_csv(TABLES / 'longitudinal_profile_by_month.csv')
    A = P[MONTHS[:6]] - P[MONTHS[:6]].mean()
    warm = pd.DataFrame({'months_above_0.7C': (A > 0.7).sum(axis=1), 'mean_anomaly_C': A.mean(axis=1).round(2)})
    warm[warm['months_above_0.7C'] >= 4].to_csv(TABLES / 'recurrent_warm_reaches.csv')
    c = A.corr().values
    print('mean between-month correlation of anomaly patterns: %.2f' % c[np.triu_indices(6, 1)].mean())
    try:
        import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(9, 4.4), dpi=600)
        for mo, col in zip(MONTHS[:6], plt.cm.viridis(np.linspace(0, 0.9, 6))):
            s = P[mo].dropna(); ax.plot(s.index, s.values, color=col, lw=1.4, label=mo)
        for k in ('Torun', 'Chelmno', 'Gdansk_Swibno'):
            ax.axvline(GAUGE_KM[k], color='grey', ls='--', lw=0.8)
        ax.set_xlabel('Official river kilometre (km)'); ax.set_ylabel('Calibrated water temperature (°C)'); ax.legend(ncol=6, fontsize=8)
        fig.tight_layout(); fig.savefig(FIGURES / 'Figure8_longitudinal_profile.png')
    except Exception as e:
        print('figure skipped:', e)
print('done')
