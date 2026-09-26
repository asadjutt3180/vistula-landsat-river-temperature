/**
 * ============================================================================
 * CODE 2: CENTERLINE POINTS -- PIXEL-BASED LST EXTRACTION
 * ============================================================================
 * 
 * Purpose:
 *   Extract pixel-based Land Surface Temperature (LST) at points generated
 *   along the Vistula River centerline at 30m intervals. Exports monthly
 *   mean LST values for each point across the full study period.
 * 
 * Prerequisites:
 *   - A centerline feature collection as a GEE asset
 *   - Points generated along the centerline at 30m spacing (with Point_ID,
 *     OSM_ID, River_Name, and optionally River_Km properties)
 * 
 * Outputs:
 *   - 175 CSV files (25 years x 7 ice-free months) exported to Google Drive
 *   - Each CSV contains: Date, Year, Month, Point_ID, Longitude, Latitude,
 *     OSM_ID, River_Name, LST_Celsius, [River_Km]
 * 
 * Key Processing Steps:
 *   1. Load pre-generated points along river centerline (30m spacing)
 *   2. Collect Landsat 5/7/8/9 imagery for each month
 *   3. Cloud mask and convert thermal bands to Celsius
 *   4. Compute monthly mean LST composite
 *   5. Sample LST at each point location
 *   6. Export as monthly CSV files
 * 
 * Author: [Your Name]
 * Date: 2024
 * ============================================================================
 */

// ============================================
// PART 1: LOAD POINTS
// ============================================
// Points generated along the Vistula River centerline at 30m intervals
var pointsFC = ee.FeatureCollection('projects/r2riveer/assets/CenterlineDerivedPoints01');

// Quick verification
print('First point:', pointsFC.first());
print('Properties:', pointsFC.first().propertyNames());

// Check if River_Km property exists (client-side boolean)
var HAS_RIVER_KM = pointsFC.first().propertyNames().contains('River_Km').getInfo();
print('Has River_Km:', HAS_RIVER_KM);

// ============================================
// PART 2: PARAMETERS
// ============================================
var START_YEAR = 2000;
var END_YEAR = 2024;
var DRIVE_FOLDER = 'Vistula LST 2000 to 2024';

var monthNames = {
  5: 'May', 6: 'June', 7: 'July', 8: 'August',
  9: 'September', 10: 'October', 11: 'November'
};

// ============================================
// PART 3: LANDSAT LST -- ALL SATELLITES
// ============================================

/**
 * Converts thermal band DN to Celsius and applies cloud mask.
 * 
 * @param {ee.Image} image - Landsat image
 * @param {string} thermalBand - Band name ('ST_B6' for L5/L7, 'ST_B10' for L8/L9)
 * @returns {ee.Image} - Masked LST in Celsius
 */
function prepImage(image, thermalBand) {
  // Convert DN to Kelvin then Celsius
  var lstCelsius = image.select(thermalBand)
    .multiply(0.00341802)
    .add(149.0)
    .subtract(273.15)
    .rename('LST_Celsius');

  // QA_PIXEL: mask cloud (bit 3) and cloud shadow (bit 4)
  var qa = image.select('QA_PIXEL');
  var mask = qa.bitwiseAnd(1 << 3).eq(0)   // No cloud
    .and(qa.bitwiseAnd(1 << 4).eq(0));     // No cloud shadow

  // Additional temperature range filter (-5 to 45 deg C)
  var lstMasked = lstCelsius
    .updateMask(mask)
    .updateMask(lstCelsius.gte(-5).and(lstCelsius.lte(45)));

  return lstMasked.copyProperties(image, ['system:time_start', 'system:index']);
}

/**
 * Creates a merged Landsat collection (L5, L7, L8, L9) for the given period.
 */
function getLandsatLST(start, end, region) {

  var cloudFilter = ee.Filter.lt('CLOUD_COVER', 60);

  // Landsat 5 TM (1984-2012) -> ST_B6
  var l5 = ee.ImageCollection('LANDSAT/LT05/C02/T1_L2')
    .filterDate(start, end)
    .filterBounds(region)
    .filter(cloudFilter)
    .map(function(img) { return prepImage(img, 'ST_B6'); });

  // Landsat 7 ETM+ (1999-present) -> ST_B6
  var l7 = ee.ImageCollection('LANDSAT/LE07/C02/T1_L2')
    .filterDate(start, end)
    .filterBounds(region)
    .filter(cloudFilter)
    .map(function(img) { return prepImage(img, 'ST_B6'); });

  // Landsat 8 OLI/TIRS (2013-present) -> ST_B10
  var l8 = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
    .filterDate(start, end)
    .filterBounds(region)
    .filter(cloudFilter)
    .map(function(img) { return prepImage(img, 'ST_B10'); });

  // Landsat 9 (2021-present) -> ST_B10
  var l9 = ee.ImageCollection('LANDSAT/LC09/C02/T1_L2')
    .filterDate(start, end)
    .filterBounds(region)
    .filter(cloudFilter)
    .map(function(img) { return prepImage(img, 'ST_B10'); });

  // Merge all -- empty collections (outside a satellite's lifetime) are harmless
  return l5.merge(l7).merge(l8).merge(l9);
}

// One collection for the whole study period (filtered lazily per month)
var lstCollection = getLandsatLST(
  START_YEAR + '-05-01',
  END_YEAR + '-11-30',
  pointsFC
);

// ============================================
// PART 4: EXPORT FUNCTION (YEAR + MONTH)
// ============================================

/**
 * Exports monthly mean LST sampled at all centerline points.
 * 
 * @param {number} year - Year to process
 * @param {number} month - Month to process (5-11)
 * @param {string} monthName - Month name for file naming
 */
function exportMonth(year, month, monthName) {

  var startOfMonth = ee.Date.fromYMD(year, month, 1);
  var endOfMonth = startOfMonth.advance(1, 'month');
  var monthLabel = startOfMonth.format('YYYY-MM');

  // Compute monthly mean LST composite
  var monthlyMean = lstCollection
    .filterDate(startOfMonth, endOfMonth)
    .mean()
    .rename('LST_Celsius');

  // Sample at all points
  var sampled = monthlyMean.reduceRegions({
    collection: pointsFC,
    reducer: ee.Reducer.mean(),
    scale: 30,
    crs: 'EPSG:4326',
    tileScale: 4
  });

  // Format output properties
  var formatted = sampled.map(function(feature) {
    var properties = {
      'Date': monthLabel,
      'Year': year,
      'Month': month,
      'Point_ID': feature.get('OBJECTID'),
      'Longitude': feature.geometry().coordinates().get(0),
      'Latitude': feature.geometry().coordinates().get(1),
      'OSM_ID': feature.get('osm_id'),
      'River_Name': feature.get('name'),
      'LST_Celsius': feature.get('mean')
    };

    if (HAS_RIVER_KM) {
      properties['River_Km'] = feature.get('River_Km');
    }

    return ee.Feature(null, properties);
  });

  var exportColumns = ['Date', 'Year', 'Month', 'Point_ID', 'Longitude',
                       'Latitude', 'OSM_ID', 'River_Name', 'LST_Celsius'];
  if (HAS_RIVER_KM) {
    exportColumns.push('River_Km');
  }

  Export.table.toDrive({
    collection: formatted,
    description: 'Vistula_LST_' + monthName + '_' + year,
    folder: DRIVE_FOLDER,
    fileFormat: 'CSV',
    selectors: exportColumns
  });
}

// ============================================
// PART 5: CREATE ALL EXPORT TASKS (175 TOTAL)
// ============================================
// 25 years x 7 ice-free months = 175 export tasks
for (var year = START_YEAR; year <= END_YEAR; year++) {
  for (var m = 5; m <= 11; m++) {
    exportMonth(year, m, monthNames[m]);
  }
}

// ============================================
// PART 6: VISUALIZATION (July 2024 as check)
// ============================================
Map.centerObject(pointsFC, 8);
Map.addLayer(pointsFC, {color: 'yellow', pointSize: 2}, 'Vistula Points');

var julyLST = lstCollection.filterDate('2024-07-01', '2024-07-31').mean();
Map.addLayer(julyLST, {
  min: 15, max: 35,
  palette: ['blue', 'cyan', 'yellow', 'orange', 'red']
}, 'July 2024 LST');

print('All export tasks created: 25 years x 7 months = 175 tasks');
print('Go to Tasks tab and click RUN on each export.');
print('All files will be saved in Drive folder: ' + DRIVE_FOLDER);
