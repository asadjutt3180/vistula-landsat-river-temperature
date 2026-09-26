# Data dictionary

## data/raw/insitu_imgw/`<Station>`_insitu_water_temperature.csv
Daily observations from IMGW-PIB gauges, May–November 2000–2024 (Gdańsk-Świbno to 2023). Toruń 5,320 rows, Chełmno 5,289, Gdańsk-Świbno 5,075.

| Column | Unit | Description |
|---|---|---|
| latitude, longitude | degrees (WGS 84) | gauge location |
| station | – | Torun, Chelmno, Gdansk_Swibno |
| year, month, day | – | observation date |
| water_level_m_asl | m a.s.l. | water level |
| water_temp_C | °C | water temperature (daily reading) |

## data/raw/landsat_station/`<Station>`_landsat_lst.csv
Output of `code/gee/01_Station_LST_Extraction.js`: median Collection 2 Level 2 surface temperature of the valid water pixels within a 30 m buffer around the gauge, per Landsat scene (May–November, 2000–2024).

| Column | Unit | Description |
|---|---|---|
| Date | YYYY-MM-DD | acquisition date |
| Satellite_LST_Celsius | °C | surface temperature |

## data/processed/matched_pairs_raw.csv (942 rows) and matched_pairs_qc.csv (876 rows)
Satellite scenes matched with the mean in-situ temperature within ±3 days; `_qc` after four-stage quality control (script 01).

| Column | Unit | Description |
|---|---|---|
| Date | – | Landsat acquisition date |
| Station | – | gauge |
| Latitude, Longitude | degrees | gauge location |
| Satellite_LST | °C | Landsat surface temperature |
| InSitu_Temp | °C | mean in-situ water temperature within ±3 days |

`matched_pairs_qc_with_sensor.csv` adds `sensor` (L5, L7, L8, L9 or unassigned; script 04).

## data/processed/monthly_river_mean_lst.csv
Mean Landsat surface temperature over the entire mapped Vistula course for each month and year (source of Supplementary Table S10 and Figure S1 annotations).

| Column | Unit | Description |
|---|---|---|
| Month, Year | – | composite month and year |
| LST | °C | mean over all centreline points with a valid value |
| Coverage | % | percentage of centreline points with a valid value |

## Zenodo: Vistula_LST_`<Month>`_2000_2024.csv (7 files)
Monthly mean Landsat surface temperature (all cloud-masked scenes of the month) sampled at 54,396 centreline points spaced 30 m along the mapped course of the Vistula (script `02_Centerline_Points_Export.js`).

| Column | Unit | Description |
|---|---|---|
| Date | YYYY-MM | composite month |
| Year, Month, Month_Name | – | – |
| Point_ID, OSM_ID | – | centreline point and OpenStreetMap way identifiers |
| Longitude, Latitude | degrees | point location |
| River_Name | – | "Vistula, Poland" |
| LST_Celsius | °C | monthly mean surface temperature (empty where no valid pixel) |
| River_Km | km | distance along the digitized OpenStreetMap line (not the official river kilometre; conversion in script 05) |
| Source_File | – | original GEE export |

## results/tables
| File | Content (paper section / table) |
|---|---|
| qc_summary.json | QC stages, before/after statistics, removed vs retained (Tables S1, S2, S2a, S2b) |
| calibration_validation.json | calibration, CV, folds, bootstrap, RMA, stations, residuals (Tables 3–5, S3, S4, S9) |
| algorithm_comparison_single_predictor.csv / _seasonal_augmented.csv | twenty algorithms (Tables S7, S13) |
| loso_and_sensitivity.json | LOSO annual/seasonal, nested QC, windows, 7-day SD (Table 6, S2a, S17, S19) |
| sensor_statistics.json | sensor attribution and statistics (Table S16) |
| monthly_trends.csv | OLS, Theil–Sen and coverage-controlled trends; coverage correlations (Tables S11, S12) |
| august_record.csv | August means, z-scores and ranks (Table S10, Figure 9) |
| longitudinal_profile_by_month.csv, recurrent_warm_reaches.csv | Figure 8, Table S20 |
