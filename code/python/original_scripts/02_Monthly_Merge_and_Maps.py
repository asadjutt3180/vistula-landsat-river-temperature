"""
================================================================================
CODE 2: MONTHLY LST MERGE AND MAP FIGURES
================================================================================

Purpose:
    Merge 175 monthly CSV files (exported from GEE Code 2) into 7 consolidated
    monthly datasets (one per month: May-November), and create publication-ready
    5x5 panel map figures showing 25 years of LST data per month.

    This script:
    1. Reads all CSV files from a ZIP archive
    2. Parses year and month from filenames
    3. Merges all years for each month into a single CSV
    4. Creates 7 figures (one per month) with 25 year-panels each (5x5 layout)
    5. Bundles all outputs into a downloadable ZIP

Input:
    - ZIP file containing 175 monthly CSV files from GEE Code 2
      (naming format: Vistula_LST_<Month>_<Year>.csv)

Output:
    - 7 merged CSV files (one per month, all years combined)
    - 7 PNG figures (5x5 panels, 25 years per figure)
    - 1 ZIP bundle with all outputs

Environment:
    Designed for Google Colab (uses google.colab.files for download).
    Can be adapted for local Jupyter notebooks.

Author: [Your Name]
Date: 2024
================================================================================
"""

# Install contextily for basemap support (Google Colab)
!pip install contextily -q

import zipfile
import re
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import contextily as ctx
from google.colab import files


# =============================================================================
# CONFIGURATION -- UPDATE THESE PATHS
# =============================================================================

# Path to the ZIP file containing 175 monthly CSVs from GEE
ZIP_NAME = '/content/drive-download-20260716T231317Z-1-001.zip'

# Output directories
OUT_DIR = '/content/monthly_output'
MAP_DIR = '/content/monthly_figures'
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(MAP_DIR, exist_ok=True)

# Month configuration
MONTHS = [5, 6, 7, 8, 9, 10, 11]
MONTH_NAMES = {
    5: 'May', 6: 'June', 7: 'July', 8: 'August',
    9: 'September', 10: 'October', 11: 'November'
}

# Visualization settings
VMIN, VMAX = 0, 35                    # Temperature range for colormap
CMAP = plt.get_cmap('turbo')          # Colormap
BASEMAP = ctx.providers.OpenStreetMap.Mapnik  # Basemap source

# Font configuration
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'Liberation Serif', 'DejaVu Serif']


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

# Month name to number mapping (handles various naming conventions)
MONTH_MAP = {
    'may': 5, 'june': 6, 'jun': 6, 'july': 7, 'jul': 7,
    'august': 8, 'aug': 8, 'september': 9, 'sep': 9, 'sept': 9,
    'october': 10, 'oct': 10, 'november': 11, 'nov': 11
}


def parse_year(fname):
    """
    Extract 4-digit year (19xx or 20xx) from filename.

    Parameters:
        fname (str): CSV filename

    Returns:
        int or None: Extracted year
    """
    m = re.search(r'(19|20)\d{2}', fname)
    return int(m.group(0)) if m else None


def parse_month(fname):
    """
    Extract month number from filename using month name patterns.

    Parameters:
        fname (str): CSV filename

    Returns:
        int or None: Month number (5-11)
    """
    pattern = r'(september|sept|sep|november|nov|october|oct|august|aug|july|jul|june|jun|may)'
    m = re.search(pattern, fname.lower())
    return MONTH_MAP[m.group(1)] if m else None


def lonlat_to_mercator(lon, lat):
    """
    Convert longitude/latitude (WGS84) to Web Mercator (EPSG:3857).

    Required for aligning scatter data with contextily basemaps.

    Parameters:
        lon (float or np.ndarray): Longitude(s)
        lat (float or np.ndarray): Latitude(s)

    Returns:
        tuple: (x, y) coordinates in Web Mercator meters
    """
    x = np.radians(lon) * 6378137.0
    y = np.log(np.tan(np.pi / 4.0 + np.radians(lat) / 2.0)) * 6378137.0
    return x, y


def make_month_figure(year_dict, month_num, all_years, out_png):
    """
    Create a 5x5 panel figure for a single month showing all years.

    Each panel shows LST data for one year overlaid on an OpenStreetMap
    basemap. Panels are arranged chronologically left-to-right, top-to-bottom.

    Parameters:
        year_dict (dict): {year: dataframe} for the given month
        month_num (int): Month number (5-11)
        all_years (list): Sorted list of all years to display
        out_png (str): Output PNG file path
    """
    # Compute common extent from all data (Web Mercator coordinates)
    any_df = next(iter(year_dict.values()))
    x_all, y_all = lonlat_to_mercator(
        any_df['Longitude'].values, any_df['Latitude'].values)
    xmin, xmax = np.nanmin(x_all), np.nanmax(x_all)
    ymin, ymax = np.nanmin(y_all), np.nanmax(y_all)

    # Add padding
    pad_x = (xmax - xmin) * 0.015
    pad_y = (ymax - ymin) * 0.015
    x0, x1 = xmin - pad_x, xmax + pad_x
    y0, y1 = ymin - pad_y, ymax + pad_y

    # Calculate panel dimensions (tall/narrow river = no white gaps)
    aspect = (y1 - y0) / (x1 - x0)
    PW = 2.5  # panel width (inches)
    PH = PW * aspect

    # Create 5x5 subplot grid
    fig, axes = plt.subplots(5, 5, figsize=(5 * PW + 1.2, 5 * PH + 1.0))
    plt.subplots_adjust(
        left=0.01, right=0.90, top=0.96, bottom=0.01,
        wspace=0.04, hspace=0.10)
    axes = axes.ravel()
    sc = None  # For colorbar reference

    # Fill each panel with one year
    for i, yr in enumerate(all_years):
        ax = axes[i]
        ax.set_xlim(x0, x1)
        ax.set_ylim(y0, y1)

        # Add OpenStreetMap basemap
        ctx.add_basemap(ax, crs='EPSG:3857', source=BASEMAP, zoom=8)

        # Get data for this year
        if yr in year_dict:
            sub_all = year_dict[yr]
            sub = sub_all.dropna(subset=['LST_Celsius'])
        else:
            sub_all, sub = [], []

        if len(sub) > 0:
            # Plot LST points with temperature colormap
            xs, ys = lonlat_to_mercator(
                sub['Longitude'].values, sub['Latitude'].values)
            sc = ax.scatter(xs, ys, c=sub['LST_Celsius'], cmap=CMAP,
                            vmin=VMIN, vmax=VMAX, s=1, marker='s',
                            linewidths=0, zorder=5, rasterized=True)
            cov = 100 * len(sub) / len(sub_all)
            mean_temp = sub['LST_Celsius'].mean()
            ttl = f"{yr}  ({mean_temp:.1f} deg C, {cov:.0f}%)"
        else:
            ttl = f"{yr}  (no data)"
            ax.text(0.5, 0.5, 'no data', transform=ax.transAxes,
                    ha='center', va='center', fontsize=9, color='gray', zorder=6)

        ax.set_title(ttl, fontsize=10, fontweight='bold')
        ax.set_aspect('equal')
        ax.set_xticks([])
        ax.set_yticks([])

    # Add shared colorbar
    if sc is not None:
        cbar = fig.colorbar(sc, ax=list(axes), location='right',
                            fraction=0.025, aspect=40, pad=0.01)
        cbar.set_label('Land Surface Temperature (deg C)', fontsize=12)
        cbar.ax.tick_params(labelsize=9)

    # Overall title
    fig.suptitle(
        f'Vistula River -- {MONTH_NAMES[month_num]} LST, '
        f'{all_years[0]} to {all_years[-1]} (Landsat)',
        fontsize=18, fontweight='bold', y=0.995)

    fig.savefig(out_png, dpi=200, bbox_inches='tight')
    plt.show()
    plt.close(fig)


# =============================================================================
# MAIN EXECUTION
# =============================================================================

print("=" * 60)
print("MONTHLY LST MERGE AND MAP FIGURES")
print("=" * 60)

# Step 1: Read all CSV files from the ZIP
months_data = {}       # months_data[month][year] = dataframe
all_years_set = set()

with zipfile.ZipFile(ZIP_NAME) as z:
    csvs = [n for n in z.namelist()
            if n.lower().endswith('.csv') and '__MACOSX' not in n]
    print(f"\n[1] Found {len(csvs)} CSV files in the ZIP\n")

    for name in csvs:
        mn, yr = parse_month(name), parse_year(name)
        if mn is None or yr is None:
            print(f"    !! Skipped (cannot parse): {name}")
            continue
        df = pd.read_csv(z.open(name))
        df['Year'] = yr
        df['Source_File'] = os.path.basename(name)
        months_data.setdefault(mn, {})[yr] = df
        all_years_set.add(yr)

ALL_YEARS = sorted(all_years_set)
print(f"[2] Years found: {ALL_YEARS[0]} to {ALL_YEARS[-1]} "
      f"({len(ALL_YEARS)} years)")

# Step 2: Process each month -- merge CSVs + create figures
out_files, fig_files = [], []
print('\n[3] Merging by month and building figures...')

for mn in MONTHS:
    if mn not in months_data:
        print(f"    {MONTH_NAMES[mn]}: no files found, skipped")
        continue

    year_dict = months_data[mn]

    # Merge all years for this month
    mdf = pd.concat(year_dict.values(), ignore_index=True)
    mdf['Month_Name'] = MONTH_NAMES[mn]
    sort_cols = [c for c in ['Year', 'River_Km'] if c in mdf.columns]
    mdf = mdf.sort_values(sort_cols).reset_index(drop=True)

    n_miss = mdf['LST_Celsius'].isna().sum()

    # Save merged CSV
    out_csv = f"{OUT_DIR}/Vistula_LST_{MONTH_NAMES[mn]}_" \
              f"{ALL_YEARS[0]}_{ALL_YEARS[-1]}.csv"
    mdf.to_csv(out_csv, index=False)
    out_files.append(out_csv)

    print(f"\n    {MONTH_NAMES[mn]:12s}: {len(mdf):>9,} rows | "
          f"{mdf['Year'].nunique()} years | "
          f"missing LST: {100*n_miss/len(mdf):5.1f}%")

    # Create 5x5 figure
    out_png = f"{MAP_DIR}/Vistula_LST_{MONTH_NAMES[mn]}_AllYears_" \
              f"{ALL_YEARS[0]}_{ALL_YEARS[-1]}.png"
    make_month_figure(year_dict, mn, ALL_YEARS, out_png)
    fig_files.append(out_png)

# Step 3: Bundle everything into one ZIP
print("\n[4] Bundling outputs...")
bundle = '/content/Vistula_LST_Monthly_Maps.zip'
with zipfile.ZipFile(bundle, 'w', zipfile.ZIP_DEFLATED) as z:
    for f in out_files:
        z.write(f, os.path.basename(f))
    for f in fig_files:
        z.write(f, os.path.basename(f))

print(f"    Bundle: {bundle}")
print(f"    CSV files: {len(out_files)}")
print(f"    Figure files: {len(fig_files)}")

# Download (Google Colab)
print('\n[5] Downloading...')
files.download(bundle)

print("\n" + "=" * 60)
print("Done! Check your Downloads folder.")
print("=" * 60)
