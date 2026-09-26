# Large files (not stored in Git)

Download from Zenodo (https://doi.org/10.5281/zenodo.22970527) and unzip here:

| File in the Zenodo record | Contents | Size |
|---|---|---|
| `Vistula_LST_monthly_centreline_composites_2000_2024.zip` | 7 CSV files, `Vistula_LST_<Month>_2000_2024.csv` (May–November): monthly mean Landsat surface temperature at 54,396 centreline points (30 m spacing) of the entire mapped Vistula course, one row per point and year | 252 MB zipped, 1.3 GB unzipped |
| `Vistula_centreline_points_30m_shapefile.zip` | `CenterlineDerivedPoints01` shapefile (points, WGS 84) used as the Earth Engine asset for script 02 | 1.8 MB zipped, 75 MB unzipped |

After unzipping, `data/large/` should contain `Vistula_LST_May_2000_2024.csv` … `Vistula_LST_November_2000_2024.csv`. Check integrity with the `.sha256` files in the record.
