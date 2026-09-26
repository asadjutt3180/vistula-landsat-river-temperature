"""Shared paths and constants for the Vistula Landsat river-temperature analysis."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW_INSITU = ROOT / 'data' / 'raw' / 'insitu_imgw'
RAW_LANDSAT = ROOT / 'data' / 'raw' / 'landsat_station'
PROCESSED = ROOT / 'data' / 'processed'
LARGE = Path(os.environ.get('VISTULA_LARGE_DIR', ROOT / 'data' / 'large'))   # whole-river monthly composites (Zenodo)
TABLES = ROOT / 'results' / 'tables'
FIGURES = ROOT / 'results' / 'figures'
for _p in (PROCESSED, TABLES, FIGURES):
    _p.mkdir(parents=True, exist_ok=True)

STATIONS = ['Chelmno', 'Gdansk_Swibno', 'Torun']   # order of the original analysis (fixes the CV fold assignment)
STATION_LABEL = {'Torun': 'Toruń', 'Chelmno': 'Chełmno', 'Gdansk_Swibno': 'Gdańsk-Świbno'}
STATION_COORDS = {'Torun': (18.608077, 53.006398), 'Chelmno': (18.424737, 53.36783), 'Gdansk_Swibno': (18.940696, 54.335277)}
GAUGE_KM = {'Warszawa': 513.0, 'Torun': 734.7, 'Chelmno': 806.6, 'Gdansk_Swibno': 939.0}   # official river kilometre
MONTHS = ['May', 'June', 'July', 'August', 'September', 'October', 'November']
SEED = 42
MATCH_WINDOW_DAYS = 3
Z_THRESHOLD = 2.5
