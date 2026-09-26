/**
 * ============================================================================
 * CODE 3: AUGUST 2020 HEATWAVE -- TIFF EXPORT
 * ============================================================================
 * 
 * Purpose:
 *   Export Land Surface Temperature (LST) data for the August 2020 heatwave
 *   period around the Vistula River. Creates a 4km buffered corridor around
 *   the river centerline and exports three products:
 *     1) CSV with point-sampled LST values per scene
 *     2) GeoTIFF with median LST composite for the full period
 *     3) Shapefile of the buffered corridor polygon
 * 
 * Prerequisites:
 *   - Points feature collection (GEE asset with Point_ID, OSM_ID, River_Name,
 *     River_Km properties)
 *   - Centerline feature collection (GEE asset, optional -- falls back to
 *     points geometry)
 * 
 * Outputs:
 *   - CSV: Point samples with LST and scene date per point
 *   - GeoTIFF: Median LST image clipped to 4km corridor
 *   - Shapefile: 4km buffered corridor around centerline
 * 
 * Author: [Your Name]
 * Date: 2024
 * ============================================================================
 */

// ---------- CONFIG -- EDIT THESE ----------
// Points generated along the Vistula River centerline
var POINTS_ASSET     = 'projects/r2riveer/assets/CenterlineDerivedPoints01';

// River centerline feature collection
var CENTERLINE_ASSET = 'projects/r2riveer/assets/Vistula_centerline';

// If you do NOT have the centerline as a GEE asset, comment the line above
// and uncomment the fallback below -- it uses the points' own geometry:
// var CENTERLINE_ASSET = null;

// Date range for the heatwave period
var DATE_START = '2020-08-01';
var DATE_END   = '2020-08-21';   // exclusive

// Spatial parameters
var BUFFER_M   = 4000;           // corridor width (meters) around the centerline
var TIFF_SCALE = 100;            // 100 m = native Landsat thermal resolution
                                 // (use 30 for a finer but ~9x bigger file)
// ------------------------------------------

var points = ee.FeatureCollection(POINTS_ASSET);

// Region of interest: centerline if available, otherwise the points
var roi;
if (CENTERLINE_ASSET) {
  roi = ee.FeatureCollection(CENTERLINE_ASSET).geometry();
} else {
  roi = points.geometry();
}

// The buffered corridor (used for display + TIFF + SHP)
var corridor = roi.buffer(BUFFER_M);

Map.centerObject(ee.FeatureCollection(roi), 7);
Map.addLayer(points, {color: 'FF0000'}, 'Sampling points');
Map.addLayer(ee.FeatureCollection([ee.Feature(corridor)]),
             {color: '0000FF'}, '4 km corridor', false);

// ---------- Landsat 8 -> LST deg C with cloud mask ----------
/**
 * Prepares Landsat 8 image: converts ST_B10 to Celsius and masks clouds.
 * 
 * @param {ee.Image} img - Landsat 8 Collection 2 Level-2 image
 * @returns {ee.Image} - Cloud-masked LST in Celsius
 */
function prepLST(img) {
  var qa = img.select('QA_PIXEL');
  // Mask dilated cloud, cirrus, cloud, and cloud shadow
  var clear = qa.bitwiseAnd(1 << 1).eq(0)   // dilated cloud
    .and(qa.bitwiseAnd(1 << 2).eq(0))        // cirrus
    .and(qa.bitwiseAnd(1 << 3).eq(0))        // cloud
    .and(qa.bitwiseAnd(1 << 4).eq(0));       // cloud shadow

  // ST_B10 -> Kelvin -> Celsius
  var lstC = img.select('ST_B10')
    .multiply(0.00341802).add(149.0)         // -> Kelvin
    .subtract(273.15);                       // -> Celsius

  return lstC.updateMask(clear)
    .copyProperties(img, ['system:time_start', 'system:index']);
}

// Filter Landsat 8 collection for the heatwave period
var lstCol = ee.ImageCollection('LANDSAT/LC08/C02/T1_L2')
  .filterBounds(roi)
  .filterDate(DATE_START, DATE_END)
  .map(prepLST);

print('Scenes found:', lstCol.size());
print('Scene dates:', lstCol.aggregate_array('system:time_start')
  .map(function(t) { return ee.Date(t).format('YYYY-MM-dd'); }));

// ---------- Median composite for display + TIFF ----------
var lstMedian = lstCol.median().clip(corridor).rename('LST_Celsius').toFloat();

var vis = {
  min: 0, max: 35,
  palette: ['#30123b','#4146d1','#4277fe','#2bd4fc',
            '#2bf5d7','#4dfa8e','#a4fc3c','#f0e921',
            '#fec832','#fd9b2d','#f55b16','#c31b04','#7a0403']
};
Map.addLayer(lstMedian, vis, 'LST median 1-20 Aug 2020 (4 km corridor)');

// ---------- EXPORT 1: CSV -- point samples with scene date ----------
var sampled = lstCol.map(function(img) {
  var dateStr = ee.Date(img.get('system:time_start')).format('YYYY-MM-dd');
  return img.sampleRegions({
    collection: points, scale: 30, tileScale: 4, geometries: true
  }).map(function(f) {
    var lonlat = f.geometry().coordinates();
    return f.set({
      'Scene_Date': dateStr,
      'Scene_ID':   img.get('system:index'),
      'Longitude':  lonlat.get(0),
      'Latitude':   lonlat.get(1)
    }).setGeometry(null);   // no bulky .geo column in the CSV
  });
}).flatten();

var sampledClean = sampled.filter(ee.Filter.notNull(['LST_Celsius']));

Export.table.toDrive({
  collection:  sampledClean,
  description: 'Vistula_LST_Heatwave_Aug2020_CSV',
  fileNamePrefix: 'Vistula_LST_Heatwave_Aug2020',
  fileFormat: 'CSV',
  selectors: ['Point_ID', 'OSM_ID', 'River_Name', 'River_Km',
              'Longitude', 'Latitude', 'LST_Celsius', 'Scene_Date', 'Scene_ID']
});

// ---------- EXPORT 2: GeoTIFF -- median LST in the corridor ----------
Export.image.toDrive({
  image: lstMedian,
  description: 'Vistula_LST_Heatwave_Aug2020_TIFF',
  fileNamePrefix: 'Vistula_LST_Heatwave_Aug2020_median',
  region: corridor,
  scale: TIFF_SCALE,
  crs: 'EPSG:4326',
  maxPixels: 1e13
});

// ---------- EXPORT 3: Shapefile -- buffered corridor ----------
var corridorFC = ee.FeatureCollection([
  ee.Feature(corridor, {'buffer_m': BUFFER_M,
                        'source': 'Vistula centerline', 'crs': 'EPSG:4326'})
]);

Export.table.toDrive({
  collection:  corridorFC,
  description: 'Vistula_centerline_buffer_4km_SHP',
  fileNamePrefix: 'Vistula_centerline_buffer_4km',
  fileFormat: 'SHP'
});

print('3 export tasks created. Go to Tasks tab and click RUN on each.');
