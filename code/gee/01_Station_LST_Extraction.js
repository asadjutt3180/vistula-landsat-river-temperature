/**
 * ============================================================================
 * CODE 1: STATION-BASED LST EXTRACTION
 * ============================================================================
 * 
 * Purpose:
 *   Extract Land Surface Temperature (LST) from Landsat 5/7/8/9 for three
 *   stations along the Vistula River (Torun, Chelmno, Gdansk_Swibno).
 *   Each station is represented by a point buffered to 30m.
 * 
 * Outputs:
 *   - 3 interactive time-series charts (one per station)
 *   - 3 CSV files exported to Google Drive
 * 
 * Key Processing Steps:
 *   1. Cloud/land masking using QA_PIXEL band
 *   2. ST_B6 (L5/L7) or ST_B10 (L8/L9) -> Celsius conversion
 *   3. UTC to Poland Local Time conversion (CEST/CET)
 *   4. Median LST extraction within 30m buffer
 * 
 * Author: [Your Name]
 * Date: 2024
 * ============================================================================
 */

// ─────────────────────────────────────────────────────────────────────────────
// 1. GLOBAL SETTINGS
// ─────────────────────────────────────────────────────────────────────────────
var startYear = 2000;
var endYear   = 2024;

// Center map on all three stations
var allPoints = ee.Geometry.MultiPoint([
  [18.608077,  53.006398],   // Torun
  [18.424737, 53.36783],     // Chelmno
  [18.940696, 54.335277]     // Gdansk_Swibno
]);
Map.centerObject(allPoints, 9);

// ─────────────────────────────────────────────────────────────────────────────
// 2. MASKING & FILTERING FUNCTIONS
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Masks clouds, cloud shadows, and non-water pixels using QA_PIXEL.
 * Applies a focal minimum filter for strict water masking.
 */
function maskLandAndClouds(image) {
  var qa = image.select('QA_PIXEL');
  var cloud       = qa.bitwiseAnd(1 << 3).eq(0);
  var cloudShadow = qa.bitwiseAnd(1 << 4).eq(0);
  var water       = qa.bitwiseAnd(1 << 7).gt(0);
  var validWater  = cloud.and(cloudShadow).and(water);
  var strictWater = validWater.focal_min(0.5);
  return image.updateMask(strictWater);
}

/**
 * Filters collection to ice-free months (May-November) and year range.
 */
function filterIceFreeMonths(collection) {
  return collection
    .filter(ee.Filter.calendarRange(startYear, endYear, 'year'))
    .filter(ee.Filter.calendarRange(5, 11, 'month'));
}

// ─────────────────────────────────────────────────────────────────────────────
// 3. STATION PROCESSOR
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Processes a single station: extracts LST from all Landsat sensors.
 * 
 * @param {string} stationName - Name of the station
 * @param {number} lon - Longitude
 * @param {number} lat - Latitude
 * @param {string} color - Map display color
 * @returns {ee.FeatureCollection} - LST records with timestamps
 */
function processStation(stationName, lon, lat, color) {
  var point  = ee.Geometry.Point([lon, lat]);
  var buffer = point.buffer(30);

  Map.addLayer(point,  {color: color, pointSize: 6}, stationName + ' Point');
  Map.addLayer(buffer, {color: color, fillColor: color + '40'}, stationName + ' 30m Buffer');

  // ── Landsat 5 & 7 ──
  var l57 = ee.ImageCollection('LANDSAT/LT05/C02/T1_L2')
    .merge(ee.ImageCollection('LANDSAT/LE07/C02/T1_L2'))
    .filterBounds(buffer);

  var pL57 = filterIceFreeMonths(l57)
    .map(maskLandAndClouds)
    .map(function(img) {
      // L5/L7: ST_B6 -> Kelvin -> Celsius
      var lst = img.select('ST_B6')
        .multiply(0.00341802).add(149.0).subtract(273.15)
        .rename('LST_Celsius');

      // Extract metadata with fallbacks
      var dateProp = img.get('DATE_ACQUIRED');
      var timeProp = img.get('SCENE_CENTER_TIME');
      var satProp  = img.get('SPACECRAFT_ID');
      var sysTime  = img.get('system:time_start');
      var sysDate  = img.date();

      var fallbackDate = sysDate.format('YYYY-MM-dd');
      var fallbackTime = sysDate.format('HH:mm:ss');

      var dateStr = ee.String(ee.Algorithms.If(dateProp, dateProp, fallbackDate));
      var timePropStr = ee.String(ee.Algorithms.If(timeProp, timeProp, ''));
      var hasTime = timePropStr.length().gt(0);
      var timeRaw = ee.String(ee.Algorithms.If(hasTime, timePropStr, fallbackTime.cat('Z')));
      var timeClean = timeRaw.replace('Z', '').slice(0, 8);
      var satStr = ee.String(ee.Algorithms.If(satProp, satProp, 'Unknown'));

      return ee.Image(lst).set({
        'system:time_start': sysTime,
        'SAFE_DATE': dateStr,
        'SAFE_TIME': timeClean,
        'SATELLITE': satStr
      });
    });

  // ── Landsat 8 & 9 ──
  var l89 = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
    .merge(ee.ImageCollection('LANDSAT/LC09/C02/T1_L2'))
    .filterBounds(buffer);

  var pL89 = filterIceFreeMonths(l89)
    .map(maskLandAndClouds)
    .map(function(img) {
      // L8/L9: ST_B10 -> Kelvin -> Celsius
      var lst = img.select('ST_B10')
        .multiply(0.00341802).add(149.0).subtract(273.15)
        .rename('LST_Celsius');

      var dateProp = img.get('DATE_ACQUIRED');
      var timeProp = img.get('SCENE_CENTER_TIME');
      var satProp  = img.get('SPACECRAFT_ID');
      var sysTime  = img.get('system:time_start');
      var sysDate  = img.date();

      var fallbackDate = sysDate.format('YYYY-MM-dd');
      var fallbackTime = sysDate.format('HH:mm:ss');

      var dateStr = ee.String(ee.Algorithms.If(dateProp, dateProp, fallbackDate));
      var timePropStr = ee.String(ee.Algorithms.If(timeProp, timeProp, ''));
      var hasTime = timePropStr.length().gt(0);
      var timeRaw = ee.String(ee.Algorithms.If(hasTime, timePropStr, fallbackTime.cat('Z')));
      var timeClean = timeRaw.replace('Z', '').slice(0, 8);
      var satStr = ee.String(ee.Algorithms.If(satProp, satProp, 'Unknown'));

      return ee.Image(lst).set({
        'system:time_start': sysTime,
        'SAFE_DATE': dateStr,
        'SAFE_TIME': timeClean,
        'SATELLITE': satStr
      });
    });

  // Merge and sort
  var unified = pL57.merge(pL89).sort('system:time_start');

  // ── Extract median LST per scene + exact pass time + Poland local time ──
  var features = unified.map(function(image) {
    var stats = image.reduceRegion({
      reducer: ee.Reducer.median(),
      geometry: buffer,
      scale: 30,
      maxPixels: 1e9
    });

    var dateStr = ee.String(image.get('SAFE_DATE'));
    var timeStr = ee.String(image.get('SAFE_TIME'));
    var utcFullStr = dateStr.cat(' ').cat(timeStr);

    var utcDate = ee.Date.parse('YYYY-MM-dd HH:mm:ss', utcFullStr);
    var utcMillis = utcDate.millis();
    var month = utcDate.get('month');

    // Poland Local Time: May-Oct = CEST (UTC+2), Nov = CET (UTC+1)
    var hourOffset = ee.Number(ee.Algorithms.If(month.eq(11), 1, 2));
    var polandMillis = utcMillis.add(hourOffset.multiply(3600000));
    var polandDate = ee.Date(polandMillis);

    return ee.Feature(null, {
      'River': 'Vistula',
      'Station_Name': stationName,
      'Date': dateStr,
      'UTC_Time': timeStr,
      'UTC_DateTime': utcFullStr,
      'Poland_Date': polandDate.format('YYYY-MM-dd'),
      'Poland_Time': polandDate.format('HH:mm:ss'),
      'Poland_DateTime': polandDate.format('YYYY-MM-dd HH:mm:ss'),
      'Satellite': image.get('SATELLITE'),
      'Satellite_LST_Celsius': stats.get('LST_Celsius')
    });
  });

  return features.filter(ee.Filter.notNull(['Satellite_LST_Celsius']));
}

// ─────────────────────────────────────────────────────────────────────────────
// 4. PROCESS ALL THREE STATIONS
// ─────────────────────────────────────────────────────────────────────────────
var torunFC   = processStation('Torun',         18.604831, 53.006083, 'red');
var chelmnoFC = processStation('Chelmno',       18.425710, 53.369640, 'green');
var gdanskFC  = processStation('Gdansk_Swibno', 18.940696, 54.335277, 'blue');

// ─────────────────────────────────────────────────────────────────────────────
// 5. CONSOLE PREVIEW
// ─────────────────────────────────────────────────────────────────────────────
print('=== Torun -- First 20 records ===');
print(torunFC.limit(20).select([
  'Station_Name', 'Date', 'UTC_Time', 'Poland_DateTime', 'Satellite', 'Satellite_LST_Celsius'
]));

print('=== Chelmno -- First 20 records ===');
print(chelmnoFC.limit(20).select([
  'Station_Name', 'Date', 'UTC_Time', 'Poland_DateTime', 'Satellite', 'Satellite_LST_Celsius'
]));

print('=== Gdansk_Swibno -- First 20 records ===');
print(gdanskFC.limit(20).select([
  'Station_Name', 'Date', 'UTC_Time', 'Poland_DateTime', 'Satellite', 'Satellite_LST_Celsius'
]));

// ─────────────────────────────────────────────────────────────────────────────
// 6. INTERACTIVE CHARTS
// ─────────────────────────────────────────────────────────────────────────────

// Torun Chart
var torunChart = ui.Chart.feature.byFeature(torunFC, 'Date', 'Satellite_LST_Celsius')
  .setChartType('ScatterChart')
  .setOptions({
    title: 'Vistula River LST -- Torun Station',
    hAxis: {title: 'Acquisition Date', slantedText: true, slantedTextAngle: 45},
    vAxis: {title: 'Land Surface Temperature (deg C)', viewWindowMode: 'pretty'},
    series: {0: {pointSize: 4, color: '#d73027', lineWidth: 0.5}},
    trendlines: {0: {type: 'linear', color: '#4575b4', lineWidth: 2, opacity: 0.6, showR2: true, visibleInLegend: true, labelInLegend: 'Linear Trend'}},
    legend: {position: 'bottom'}, chartArea: {width: '85%', height: '65%'}, width: 950, height: 520
  });
print(torunChart);

// Chelmno Chart
var chelmnoChart = ui.Chart.feature.byFeature(chelmnoFC, 'Date', 'Satellite_LST_Celsius')
  .setChartType('ScatterChart')
  .setOptions({
    title: 'Vistula River LST -- Chelmno Station',
    hAxis: {title: 'Acquisition Date', slantedText: true, slantedTextAngle: 45},
    vAxis: {title: 'Land Surface Temperature (deg C)', viewWindowMode: 'pretty'},
    series: {0: {pointSize: 4, color: '#2ca25f', lineWidth: 0.5}},
    trendlines: {0: {type: 'linear', color: '#4575b4', lineWidth: 2, opacity: 0.6, showR2: true, visibleInLegend: true, labelInLegend: 'Linear Trend'}},
    legend: {position: 'bottom'}, chartArea: {width: '85%', height: '65%'}, width: 950, height: 520
  });
print(chelmnoChart);

// Gdansk_Swibno Chart
var gdanskChart = ui.Chart.feature.byFeature(gdanskFC, 'Date', 'Satellite_LST_Celsius')
  .setChartType('ScatterChart')
  .setOptions({
    title: 'Vistula River LST -- Gdansk_Swibno Station',
    hAxis: {title: 'Acquisition Date', slantedText: true, slantedTextAngle: 45},
    vAxis: {title: 'Land Surface Temperature (deg C)', viewWindowMode: 'pretty'},
    series: {0: {pointSize: 4, color: '#3182bd', lineWidth: 0.5}},
    trendlines: {0: {type: 'linear', color: '#4575b4', lineWidth: 2, opacity: 0.6, showR2: true, visibleInLegend: true, labelInLegend: 'Linear Trend'}},
    legend: {position: 'bottom'}, chartArea: {width: '85%', height: '65%'}, width: 950, height: 520
  });
print(gdanskChart);

// ─────────────────────────────────────────────────────────────────────────────
// 7. EXPORT TO DRIVE (3 separate CSV files)
// ─────────────────────────────────────────────────────────────────────────────
Export.table.toDrive({
  collection: torunFC,
  description: 'Vistula_LST_Torun_2000_2024',
  folder: 'Vistula_River_Data',
  fileFormat: 'CSV',
  selectors: ['River', 'Station_Name', 'Date', 'UTC_Time', 'UTC_DateTime',
              'Poland_Date', 'Poland_Time', 'Poland_DateTime',
              'Satellite', 'Satellite_LST_Celsius']
});

Export.table.toDrive({
  collection: chelmnoFC,
  description: 'Vistula_LST_Chelmno_2000_2024',
  folder: 'Vistula_River_Data',
  fileFormat: 'CSV',
  selectors: ['River', 'Station_Name', 'Date', 'UTC_Time', 'UTC_DateTime',
              'Poland_Date', 'Poland_Time', 'Poland_DateTime',
              'Satellite', 'Satellite_LST_Celsius']
});

Export.table.toDrive({
  collection: gdanskFC,
  description: 'Vistula_LST_Gdansk_Swibno_2000_2024',
  folder: 'Vistula_River_Data',
  fileFormat: 'CSV',
  selectors: ['River', 'Station_Name', 'Date', 'UTC_Time', 'UTC_DateTime',
              'Poland_Date', 'Poland_Time', 'Poland_DateTime',
              'Satellite', 'Satellite_LST_Celsius']
});

print('Engine initialized. 3 charts + 3 CSV exports ready. Check the Tasks tab.');
