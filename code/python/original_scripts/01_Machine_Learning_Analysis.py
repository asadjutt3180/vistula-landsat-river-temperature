"""
================================================================================
CODE 1: MACHINE LEARNING ANALYSIS
================================================================================

Purpose:
    Validate Landsat-derived Land Surface Temperature (LST) against in-situ
    water temperature measurements using Linear Regression with comprehensive
    statistical validation.

    This script performs the following analyses:
    1. Data loading and temporal matching (+/-3 days)
    2. Four-step outlier removal
    3. Min-Max normalization [0,1]
    4. 10-Fold Cross-Validation
    5. Leave-One-Out Cross-Validation (LOOCV)
    6. Monte Carlo Bootstrap Uncertainty (n=1000)
    7. Moran's I Spatial Autocorrelation

Study Area:
    Vistula River, Poland
    Stations: Torun (53.006N, 18.605E), Chelmno (53.370N, 18.426E),
              Gdansk_Swibno (54.335N, 18.941E)

Input:
    - In-situ temperature data (Excel files, one per station)
    - Landsat LST data (CSV files exported from GEE Code 1)

Output:
    - Cross-validation metrics (R2, RMSE, MAE, Bias)
    - Monte Carlo confidence intervals
    - Moran's I statistics with p-value

Author: [Your Name]
Date: 2024
================================================================================
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy import stats
from scipy.spatial.distance import pdist, squareform
from sklearn.model_selection import LeaveOneOut, KFold
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.preprocessing import MinMaxScaler
import warnings
warnings.filterwarnings('ignore')

# ============ FONT CONFIGURATION ============
# Times New Roman for publication-quality figures
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman', 'Liberation Serif', 'DejaVu Serif']
plt.rcParams['axes.unicode_minus'] = False


# =============================================================================
# 1. DATA LOADING AND TEMPORAL MATCHING
# =============================================================================

def load_and_merge_data(station_name, insitu_path, landsat_path):
    """
    Load in-situ temperature and Landsat LST data, merge by date (+/-3 days).

    Parameters:
        station_name (str): Name of the monitoring station
        insitu_path (str): Path to in-situ Excel file (columns: Lat, Lon, year, month, day, T)
        landsat_path (str): Path to Landsat CSV file (columns: Date, Satellite_LST_Celsius)

    Returns:
        df (pd.DataFrame): Merged data with Date, Satellite_LST, InSitu_Temp, Latitude, Longitude, Station
        lat (float): Station latitude
        lon (float): Station longitude
    """
    insitu = pd.read_excel(insitu_path)

    # Find temperature column (named 'T' or last column)
    temp_col = None
    for col in insitu.columns:
        if col.strip() == 'T':
            temp_col = col
            break
    if temp_col is None:
        temp_col = insitu.columns[-1]

    lat_col = insitu.columns[0]
    lon_col = insitu.columns[1]

    # Parse dates from year/month/day columns
    insitu['Date'] = pd.to_datetime(insitu[['year', 'month', 'day']])
    insitu['InSitu_Temp'] = pd.to_numeric(insitu[temp_col], errors='coerce')
    lat = insitu[lat_col].astype(float).mean()
    lon = insitu[lon_col].astype(float).mean()

    # Load Landsat LST
    landsat = pd.read_csv(landsat_path)
    landsat['Date'] = pd.to_datetime(landsat['Date'])
    landsat['Satellite_LST'] = pd.to_numeric(landsat['Satellite_LST_Celsius'], errors='coerce')

    # Match Landsat to in-situ within +/-3 days
    merged_data = []
    for _, landsat_row in landsat.iterrows():
        sat_date = landsat_row['Date']
        sat_temp = landsat_row['Satellite_LST']
        date_diffs = abs((insitu['Date'] - sat_date).dt.days)
        closest = insitu[date_diffs <= 3]
        if len(closest) > 0:
            insitu_temp = closest['InSitu_Temp'].mean()
            merged_data.append({
                'Date': sat_date,
                'Satellite_LST': sat_temp,
                'InSitu_Temp': insitu_temp,
                'Latitude': lat,
                'Longitude': lon,
                'Station': station_name
            })

    df = pd.DataFrame(merged_data)
    df = df.dropna()
    return df, lat, lon


# =============================================================================
# 2. OUTLIER REMOVAL (4-Step Procedure)
# =============================================================================

def thorough_outlier_filter(df, z_threshold=2.5):
    """
    Four-step outlier removal procedure:
        Step 1: Physical bounds (-5 to 40 deg C)
        Step 2: Z-score filter on 1:1 residuals (|z| <= 2.5)
        Step 3: Iterative regression residual filter (|z| <= 2.5)
        Step 4: IQR method (Q1 - 1.5*IQR to Q3 + 1.5*IQR)

    Parameters:
        df (pd.DataFrame): Merged data with Satellite_LST and InSitu_Temp columns
        z_threshold (float): Z-score threshold for outlier detection (default: 2.5)

    Returns:
        pd.DataFrame: Filtered data with outliers removed
    """
    df_clean = df.copy()

    # Step 1: Physical bounds
    mask = (df_clean['Satellite_LST'] >= -5) & (df_clean['Satellite_LST'] <= 40) & \
           (df_clean['InSitu_Temp'] >= -5) & (df_clean['InSitu_Temp'] <= 40)
    df_clean = df_clean[mask].copy()

    # Step 2: Z-score on 1:1 residuals
    residuals_1to1 = df_clean['InSitu_Temp'] - df_clean['Satellite_LST']
    z_scores = np.abs(stats.zscore(residuals_1to1))
    df_clean = df_clean[z_scores <= z_threshold].copy()

    # Step 3: Iterative regression residual filter
    for _ in range(20):
        X_temp = df_clean['Satellite_LST'].values.reshape(-1, 1)
        y_temp = df_clean['InSitu_Temp'].values
        model = LinearRegression()
        model.fit(X_temp, y_temp)
        reg_residuals = y_temp - model.predict(X_temp)
        z_reg = np.abs(stats.zscore(reg_residuals))
        if z_reg.max() <= z_threshold:
            break
        df_clean = df_clean[z_reg <= z_threshold].copy()

    # Step 4: IQR method
    X_temp = df_clean['Satellite_LST'].values.reshape(-1, 1)
    y_temp = df_clean['InSitu_Temp'].values
    model = LinearRegression()
    model.fit(X_temp, y_temp)
    final_residuals = y_temp - model.predict(X_temp)
    Q1, Q3 = np.percentile(final_residuals, [25, 75])
    IQR = Q3 - Q1
    mask = (final_residuals >= Q1 - 1.5 * IQR) & (final_residuals <= Q3 + 1.5 * IQR)
    df_clean = df_clean[mask].copy().reset_index(drop=True)

    return df_clean


# =============================================================================
# 3. CROSS-VALIDATION
# =============================================================================

def perform_cross_validation(X, y):
    """
    Perform 10-Fold CV and LOOCV for Linear Regression.

    Parameters:
        X (np.ndarray): Normalized satellite LST (n_samples, 1)
        y (np.ndarray): Normalized in-situ temperature (n_samples,)

    Returns:
        dict: Cross-validation results with metrics for LOOCV and 10-Fold
    """
    results = {}

    # LOOCV
    loo = LeaveOneOut()
    y_true_loo, y_pred_loo = [], []
    for train_idx, test_idx in loo.split(X):
        model = LinearRegression()
        model.fit(X[train_idx], y[train_idx])
        y_pred = model.predict(X[test_idx])
        y_true_loo.append(y[test_idx][0])
        y_pred_loo.append(y_pred[0])
    y_true_loo = np.array(y_true_loo)
    y_pred_loo = np.array(y_pred_loo)
    results['LOOCV'] = {
        'RMSE': np.sqrt(mean_squared_error(y_true_loo, y_pred_loo)),
        'MAE': mean_absolute_error(y_true_loo, y_pred_loo),
        'R2': r2_score(y_true_loo, y_pred_loo),
        'Bias': np.mean(y_true_loo - y_pred_loo),
        'y_true': y_true_loo, 'y_pred': y_pred_loo,
        'residuals': y_true_loo - y_pred_loo
    }

    # 10-Fold CV
    kf = KFold(n_splits=10, shuffle=True, random_state=42)
    fold_metrics, y_true_kf, y_pred_kf = [], [], []
    for fold, (train_idx, test_idx) in enumerate(kf.split(X), 1):
        model = LinearRegression()
        model.fit(X[train_idx], y[train_idx])
        y_pred = model.predict(X[test_idx])
        fold_metrics.append({
            'Fold': fold,
            'RMSE': np.sqrt(mean_squared_error(y[test_idx], y_pred)),
            'MAE': mean_absolute_error(y[test_idx], y_pred),
            'R2': r2_score(y[test_idx], y_pred)
        })
        y_true_kf.extend(y[test_idx])
        y_pred_kf.extend(y_pred)
    y_true_kf = np.array(y_true_kf)
    y_pred_kf = np.array(y_pred_kf)
    results['10Fold'] = {
        'RMSE': np.sqrt(mean_squared_error(y_true_kf, y_pred_kf)),
        'MAE': mean_absolute_error(y_true_kf, y_pred_kf),
        'R2': r2_score(y_true_kf, y_pred_kf),
        'Bias': np.mean(y_true_kf - y_pred_kf),
        'y_true': y_true_kf, 'y_pred': y_pred_kf,
        'residuals': y_true_kf - y_pred_kf,
        'fold_details': pd.DataFrame(fold_metrics)
    }
    return results


# =============================================================================
# 4. MONTE CARLO UNCERTAINTY ANALYSIS
# =============================================================================

def monte_carlo_uncertainty(X, y, n_simulations=1000, sample_fraction=0.8):
    """
    Monte Carlo bootstrap analysis for uncertainty quantification.

    Parameters:
        X (np.ndarray): Normalized satellite LST (n_samples, 1)
        y (np.ndarray): Normalized in-situ temperature (n_samples,)
        n_simulations (int): Number of bootstrap iterations (default: 1000)
        sample_fraction (float): Fraction of data to sample per iteration (default: 0.8)

    Returns:
        dict: Statistics for Slope, Intercept, R2, RMSE, MAE, Bias with mean, std, and 95% CI
    """
    n_samples = len(X)
    sample_size = int(n_samples * sample_fraction)
    mc_slopes, mc_intercepts, mc_r2 = [], [], []
    mc_rmse, mc_mae, mc_bias = [], [], []

    for _ in range(n_simulations):
        indices = np.random.choice(n_samples, size=sample_size, replace=True)
        X_s, y_s = X[indices], y[indices]
        model = LinearRegression()
        model.fit(X_s, y_s)
        y_p = model.predict(X_s)
        mc_slopes.append(model.coef_[0])
        mc_intercepts.append(model.intercept_)
        mc_r2.append(r2_score(y_s, y_p))
        mc_rmse.append(np.sqrt(mean_squared_error(y_s, y_p)))
        mc_mae.append(mean_absolute_error(y_s, y_p))
        mc_bias.append(np.mean(y_s - y_p))

    mc_stats = {}
    for name, vals in [('Slope', np.array(mc_slopes)), ('Intercept', np.array(mc_intercepts)),
                       ('R2', np.array(mc_r2)), ('RMSE', np.array(mc_rmse)),
                       ('MAE', np.array(mc_mae)), ('Bias', np.array(mc_bias))]:
        mc_stats[name] = {
            'Mean': np.mean(vals), 'Std': np.std(vals),
            'CI_lower': np.percentile(vals, 2.5),
            'CI_upper': np.percentile(vals, 97.5),
            'values': vals
        }
    return mc_stats


# =============================================================================
# 5. MORAN'S I SPATIAL AUTOCORRELATION
# =============================================================================

def morans_i_analysis(X, y, latitudes, longitudes, stations_labels):
    """
    Calculate Moran's I statistic to test for spatial autocorrelation in residuals.

    Uses inverse distance weighting matrix with coordinate jittering for duplicate
    station locations. Tests the null hypothesis that residuals are randomly
    distributed (no spatial pattern).

    Parameters:
        X (np.ndarray): Normalized satellite LST (n_samples, 1)
        y (np.ndarray): Normalized in-situ temperature (n_samples,)
        latitudes (np.ndarray): Latitude coordinates
        longitudes (np.ndarray): Longitude coordinates
        stations_labels (np.ndarray): Station name for each sample

    Returns:
        dict: Moran's I, expected value, z-score, p-value, residuals, predictions
    """
    model = LinearRegression()
    model.fit(X, y)
    y_pred = model.predict(X)
    residuals = y - y_pred

    # Coordinate jittering for duplicate locations (same station)
    coords = np.column_stack([longitudes, latitudes]).copy()
    unique_coords = {}
    for i in range(len(coords)):
        ct = (coords[i, 0], coords[i, 1])
        if ct not in unique_coords:
            unique_coords[ct] = 0
        else:
            unique_coords[ct] += 1
            coords[i] += np.random.normal(0, 0.001, 2)

    # Inverse distance weighting matrix
    dist_matrix = squareform(pdist(coords, metric='euclidean'))
    np.fill_diagonal(dist_matrix, 1e-10)
    dist_matrix[dist_matrix < 1e-10] = 1e-10
    w_matrix = 1.0 / dist_matrix
    np.fill_diagonal(w_matrix, 0)
    w_matrix = w_matrix / w_matrix.sum(axis=1)[:, np.newaxis]

    # Moran's I calculation
    n = len(residuals)
    rd = residuals - np.mean(residuals)
    num = np.sum(w_matrix * np.outer(rd, rd))
    den = np.sum(rd ** 2)
    S0 = np.sum(w_matrix)
    morans_i = (n / S0) * (num / den)
    expected_i = -1.0 / (n - 1)

    # Variance and z-score
    S1 = np.sum((w_matrix + w_matrix.T) ** 2) / 2.0
    S2 = np.sum((w_matrix.sum(axis=1) + w_matrix.sum(axis=0)) ** 2)
    var_i = (n ** 2 * S1 - n * S2 + 3 * S0 ** 2) / (S0 ** 2 * (n ** 2 - 1)) - expected_i ** 2
    var_i = max(var_i, 1e-10)
    z_score = (morans_i - expected_i) / np.sqrt(var_i)
    p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))

    # Per-station residuals
    station_residuals = {}
    for s in np.unique(stations_labels):
        station_residuals[s] = residuals[stations_labels == s]

    return {
        'morans_i': morans_i, 'expected_i': expected_i,
        'z_score': z_score, 'p_value': p_value,
        'residuals': residuals, 'y_pred': y_pred,
        'station_residuals': station_residuals
    }


# =============================================================================
# MAIN EXECUTION
# =============================================================================

if __name__ == '__main__':
    # Station configuration -- UPDATE PATHS for your environment
    stations = {
        'Chelmno': {
            'insitu': '/mnt/agents/upload/Chelmno.xlsx',
            'landsat': '/mnt/agents/upload/Chelmno Final Landsat.csv'
        },
        'Gdansk_Swibno': {
            'insitu': '/mnt/agents/upload/Gdansk_Swibno.xlsx',
            'landsat': '/mnt/agents/upload/Gdansk_Swibno Final Landsat.csv'
        },
        'Torun': {
            'insitu': '/mnt/agents/upload/Torun.xlsx',
            'landsat': '/mnt/agents/upload/Torun Final Landsat.csv'
        }
    }

    print("=" * 60)
    print("MACHINE LEARNING ANALYSIS")
    print("Vistula River LST Validation")
    print("=" * 60)

    # Step 1: Load data
    print("\n[1] Loading data...")
    all_data, station_coords = [], {}
    for name, paths in stations.items():
        df, lat, lon = load_and_merge_data(name, paths['insitu'], paths['landsat'])
        print(f"    {name}: {len(df)} matched samples")
        station_coords[name] = (lat, lon)
        all_data.append(df)

    combined_df = pd.concat(all_data, ignore_index=True)
    print(f"    Total raw: {len(combined_df)} samples")

    # Step 2: Outlier removal
    print("\n[2] Filtering outliers (4-step procedure)...")
    filtered_df = thorough_outlier_filter(combined_df, z_threshold=2.5)
    print(f"    Retained: {len(filtered_df)} samples ({len(filtered_df)/len(combined_df)*100:.1f}%)")

    # Step 3: Normalization
    print("\n[3] Normalizing data [0,1]...")
    sat_scaler = MinMaxScaler(feature_range=(0, 1))
    ins_scaler = MinMaxScaler(feature_range=(0, 1))
    filtered_df['Satellite_LST_Norm'] = sat_scaler.fit_transform(
        filtered_df['Satellite_LST'].values.reshape(-1, 1))
    filtered_df['InSitu_Temp_Norm'] = ins_scaler.fit_transform(
        filtered_df['InSitu_Temp'].values.reshape(-1, 1))

    X = filtered_df['Satellite_LST_Norm'].values.reshape(-1, 1)
    y = filtered_df['InSitu_Temp_Norm'].values
    latitudes = filtered_df['Latitude'].values
    longitudes = filtered_df['Longitude'].values
    stations_labels = filtered_df['Station'].values

    # Step 4: Cross-validation
    print("\n[4] Cross-validation...")
    cv_results = perform_cross_validation(X, y)
    print(f"    LOOCV   -> R2={cv_results['LOOCV']['R2']:.4f}, "
          f"RMSE={cv_results['LOOCV']['RMSE']:.4f}, "
          f"MAE={cv_results['LOOCV']['MAE']:.4f}")
    print(f"    10-Fold -> R2={cv_results['10Fold']['R2']:.4f}, "
          f"RMSE={cv_results['10Fold']['RMSE']:.4f}, "
          f"MAE={cv_results['10Fold']['MAE']:.4f}")

    # Step 5: Monte Carlo
    print("\n[5] Monte Carlo uncertainty (n=1000)...")
    mc_results = monte_carlo_uncertainty(X, y)
    for param in ['Slope', 'Intercept', 'R2', 'RMSE', 'MAE']:
        r = mc_results[param]
        print(f"    {param:12s}: Mean={r['Mean']:.4f}, "
              f"Std={r['Std']:.4f}, "
              f"95% CI=[{r['CI_lower']:.4f}, {r['CI_upper']:.4f}]")

    # Step 6: Moran's I
    print("\n[6] Moran's I spatial autocorrelation...")
    moran_results = morans_i_analysis(X, y, latitudes, longitudes, stations_labels)
    print(f"    Moran's I = {moran_results['morans_i']:.4f} "
          f"(p={moran_results['p_value']:.4f})")
    if moran_results['p_value'] >= 0.05:
        print("    --> Residuals are randomly distributed (NOT significant)")
    else:
        print("    --> Significant spatial autocorrelation detected")

    print("\n" + "=" * 60)
    print("Analysis complete!")
    print("=" * 60)
